package audit

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Event struct {
	RunID, CallID, AgentTypeID, AgentInstanceID, ParentInstanceID string
	AccountableParty, OperationalOwner, Subject, Tenant           string
	TraceID, SpanID, Tool, Args, Decision, PolicyVersion          string
	ApprovalID, Approver, Result, Error                           string
	ContextTokens                                                 *int
	ContextMethod                                                 string
}

// Store appends to audit_events. Each row carries the hash of the previous row.
type Store struct {
	DB   *pgxpool.Pool
	mu   sync.Mutex
	prev string
}

func (s *Store) Append(ctx context.Context, e Event) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.prev == "" {
		_ = s.DB.QueryRow(ctx, `SELECT hash FROM audit_events ORDER BY seq DESC LIMIT 1`).Scan(&s.prev)
	}
	now := time.Now().UTC()
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s|%s|%s|%s|%s|%s|%s|%s|%s", s.prev, now.Format(time.RFC3339Nano),
		e.CallID, e.AgentInstanceID, e.Tenant, e.Tool, e.Args, e.Decision, e.Result)))
	hash := hex.EncodeToString(sum[:])
	_, err := s.DB.Exec(ctx, `INSERT INTO audit_events (created_at, run_id, call_id, agent_type_id,
		agent_instance_id, parent_instance_id, accountable_party, operational_owner, subject, tenant,
		trace_id, span_id, tool, args, decision, policy_version, approval_id, approver, result, error,
		context_tokens, context_method, prev_hash, hash)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24)`,
		now, e.RunID, e.CallID, e.AgentTypeID, e.AgentInstanceID, e.ParentInstanceID, e.AccountableParty,
		e.OperationalOwner, e.Subject, e.Tenant, e.TraceID, e.SpanID, e.Tool, e.Args, e.Decision,
		e.PolicyVersion, e.ApprovalID, e.Approver, e.Result, e.Error, e.ContextTokens, e.ContextMethod, s.prev, hash)
	if err == nil {
		s.prev = hash
	}
	return err
}

// Prune removes rows older than the retention window.
func (s *Store) Prune(ctx context.Context, olderThan time.Duration) (int64, error) {
	tag, err := s.DB.Exec(ctx, `DELETE FROM audit_events WHERE created_at < $1`, time.Now().Add(-olderThan))
	return tag.RowsAffected(), err
}

// RecordSubagent stores the launch of a child agent and the redacted task its parent gave it.
func (s *Store) RecordSubagent(ctx context.Context, parent, child, childType, traceID, prompt string) error {
	_, err := s.DB.Exec(ctx, `INSERT INTO subagent_launches (parent_instance_id, child_instance_id,
		child_type_id, trace_id, prompt_redacted) VALUES ($1,$2,$3,$4,$5)`, parent, child, childType, traceID, prompt)
	return err
}
