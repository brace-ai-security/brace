package tools

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"

	"github.com/northwind-platform/cloudops-agent/internal/agent"
	"github.com/northwind-platform/cloudops-agent/internal/approval"
	"github.com/northwind-platform/cloudops-agent/internal/audit"
	"github.com/northwind-platform/cloudops-agent/internal/config"
)

var ErrDenied = errors.New("tool call denied")

// Run is the execution context the harness builds for one alert or one investigator.
// Role, Tenant and identity fields are set by the harness, never by the model.
type Run struct {
	ID, Role, Tenant, Cluster, Subject, ParentInstanceID string
	Identity                                             agent.Identity
	Budget                                               *agent.Budget
	ContextTokens                                        *int
	ContextMethod                                        string
}

type runKey struct{}

func RunFromContext(ctx context.Context) (*Run, bool) {
	r, ok := ctx.Value(runKey{}).(*Run)
	return r, ok
}

type DispatchOpts struct{ PreApproved bool }

type Router struct {
	Reg       *Registry
	Teams     config.Teams
	Approvals *approval.Service
	Audit     *audit.Store
}

func (r *Router) Dispatch(ctx context.Context, run *Run, name string, args map[string]any, opts DispatchOpts) (Result, error) {
	ctx, span := otel.Tracer("cloudops-agent").Start(ctx, "execute_tool "+name)
	defer span.End()
	span.SetAttributes(
		attribute.String("gen_ai.tool.name", name),
		attribute.String("cloudops.run_id", run.ID),
		attribute.String("cloudops.agent.type_id", run.Identity.AgentTypeID),
		attribute.String("cloudops.agent.instance_id", run.Identity.AgentInstanceID),
		attribute.String("cloudops.agent.parent_instance_id", run.ParentInstanceID),
		attribute.String("cloudops.accountable_party", run.Identity.AccountableParty),
		attribute.String("cloudops.operational_owner", run.Identity.OperationalOwner),
		attribute.String("cloudops.context.method", run.ContextMethod))
	if run.ContextTokens != nil {
		span.SetAttributes(attribute.Int("cloudops.context.tokens", *run.ContextTokens))
	}

	ev := audit.Event{
		RunID: run.ID, CallID: newCallID(), Tool: name, Args: RedactJSON(args), Subject: run.Subject,
		AgentTypeID: run.Identity.AgentTypeID, AgentInstanceID: run.Identity.AgentInstanceID,
		ParentInstanceID: run.ParentInstanceID, AccountableParty: run.Identity.AccountableParty,
		OperationalOwner: run.Identity.OperationalOwner, Tenant: run.Tenant,
		TraceID: span.SpanContext().TraceID().String(), SpanID: span.SpanContext().SpanID().String(),
		PolicyVersion: r.Reg.PolicyVersion, ContextTokens: run.ContextTokens, ContextMethod: run.ContextMethod,
	}

	spec, h, ok := r.Reg.Lookup(run.Role, name)
	if !ok {
		return r.deny(ctx, ev, "not in allowlist for role "+run.Role)
	}
	if err := run.Budget.ToolCall(); err != nil {
		return r.deny(ctx, ev, err.Error())
	}
	tenant, err := resolveTenant(run, args, r.Teams)
	if err != nil {
		return r.deny(ctx, ev, err.Error())
	}
	ev.Tenant, ev.Decision = tenant, "allow"
	span.SetAttributes(attribute.String("cloudops.tenant", tenant))

	if spec.Impact == ImpactHigh && !opts.PreApproved {
		grant, err := r.Approvals.Require(ctx, approval.Request{RunID: run.ID, AgentInstanceID: run.Identity.AgentInstanceID,
			Tenant: tenant, Tool: name, Target: targetOf(args), Args: args})
		if err != nil {
			return r.deny(ctx, ev, "approval: "+err.Error())
		}
		ev.Decision, ev.ApprovalID, ev.Approver = "approved", grant.ID, grant.Approver
	}

	res, err := h(context.WithValue(ctx, runKey{}, run), Call{ID: ev.CallID, Tool: name, Args: args, Tenant: tenant, Cluster: run.Cluster})
	if err != nil {
		span.RecordError(err)
		return Result{}, fmt.Errorf("%s: %w", name, err)
	}
	res.Content = Redact(res.Content)
	ev.Result = res.Content
	if err := r.Audit.Append(ctx, ev); err != nil {
		return Result{}, fmt.Errorf("audit append: %w", err)
	}
	return res, nil
}

func (r *Router) deny(ctx context.Context, ev audit.Event, reason string) (Result, error) {
	ev.Decision, ev.Error = "deny", reason
	if err := r.Audit.Append(ctx, ev); err != nil {
		return Result{}, fmt.Errorf("audit append on deny: %w", err)
	}
	return Result{}, fmt.Errorf("%w: %s", ErrDenied, reason)
}

// resolveTenant picks the team the call acts for. A call can name another team explicitly,
// for example when that team's shared dependency is the cause of the alert.
func resolveTenant(run *Run, args map[string]any, teams config.Teams) (string, error) {
	if v, ok := args["team"].(string); ok && v != "" {
		if !teams.Known(v) {
			return "", fmt.Errorf("unknown team %q", v)
		}
		return v, nil
	}
	if run.Tenant == "" {
		return "", errors.New("run has no tenant")
	}
	return run.Tenant, nil
}

func targetOf(args map[string]any) string {
	ns, _ := args["namespace"].(string)
	for _, k := range []string{"release", "deployment", "nodegroup", "instance_id"} {
		if v, ok := args[k].(string); ok {
			return ns + "/" + v
		}
	}
	return ns
}

func newCallID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return "call-" + hex.EncodeToString(b)
}
