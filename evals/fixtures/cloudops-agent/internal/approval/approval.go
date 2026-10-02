package approval

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/northwind-platform/cloudops-agent/internal/config"
)

var ErrNotFound = errors.New("no usable approval")

type Request struct {
	RunID, AgentInstanceID, Tenant, Tool, Target string
	Args                                         map[string]any
}

type Grant struct{ ID, Approver string }

// Notifier shows the approval card to the team's approvers and returns the decision.
type Notifier interface {
	Ask(ctx context.Context, team, id, summary, argsJSON string, ttl time.Duration) (approver string, approved bool, err error)
}

type Service struct {
	DB       *pgxpool.Pool
	Notifier Notifier
	Teams    config.Teams
	TTL      time.Duration
}

// fingerprint binds a grant to the requesting instance and the action it covers.
func fingerprint(r Request) string {
	h := sha256.Sum256([]byte(r.AgentInstanceID + "|" + r.Tenant + "|" + r.Tool + "|" + r.Target))
	return hex.EncodeToString(h[:])
}

// Require uses an unexpired grant for the same action if one exists; otherwise it asks the
// team's approvers and waits. Each use is counted in the statement that checks the grant.
// Any failure to reach approvers or record the grant refuses the action.
func (s *Service) Require(ctx context.Context, r Request) (Grant, error) {
	fp := fingerprint(r)
	if g, err := s.use(ctx, fp); !errors.Is(err, ErrNotFound) {
		return g, err
	}
	argsJSON, _ := json.MarshalIndent(r.Args, "", "  ")
	id := fmt.Sprintf("apr-%s-%d", fp[:12], time.Now().UnixNano())
	if _, err := s.DB.Exec(ctx, `INSERT INTO approvals (id, fingerprint, run_id, agent_instance_id, tenant, tool, target, args, expires_at)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`, id, fp, r.RunID, r.AgentInstanceID, r.Tenant, r.Tool, r.Target,
		string(argsJSON), time.Now().Add(s.TTL)); err != nil {
		return Grant{}, err
	}
	summary := fmt.Sprintf("%s on %s for team %s (run %s)", r.Tool, r.Target, r.Tenant, r.RunID)
	approver, ok, err := s.Notifier.Ask(ctx, r.Tenant, id, summary, string(argsJSON), s.TTL)
	switch {
	case err != nil:
		return Grant{}, err
	case !ok:
		return Grant{}, errors.New("rejected by " + approver)
	case !s.Teams.IsApprover(r.Tenant, approver):
		return Grant{}, fmt.Errorf("%s is not an approver for team %s", approver, r.Tenant)
	}
	if _, err := s.DB.Exec(ctx, `UPDATE approvals SET approver=$2, approved_at=now() WHERE id=$1`, id, approver); err != nil {
		return Grant{}, err
	}
	return s.use(ctx, fp)
}

func (s *Service) use(ctx context.Context, fp string) (Grant, error) {
	var g Grant
	err := s.DB.QueryRow(ctx, `
		UPDATE approvals SET uses = uses + 1, last_used_at = now()
		WHERE id = (SELECT id FROM approvals
			WHERE fingerprint = $1 AND approved_at IS NOT NULL AND expires_at > now()
			ORDER BY approved_at DESC LIMIT 1 FOR UPDATE)
		RETURNING id, approver`, fp).Scan(&g.ID, &g.Approver)
	if errors.Is(err, pgx.ErrNoRows) {
		return Grant{}, ErrNotFound
	}
	return g, err
}
