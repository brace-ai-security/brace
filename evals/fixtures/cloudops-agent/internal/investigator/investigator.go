package investigator

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"

	"github.com/northwind-platform/cloudops-agent/internal/agent"
	"github.com/northwind-platform/cloudops-agent/internal/audit"
	"github.com/northwind-platform/cloudops-agent/internal/config"
	"github.com/northwind-platform/cloudops-agent/internal/runner"
	"github.com/northwind-platform/cloudops-agent/internal/tools"
)

type Recommendation struct {
	Tool       string         `json:"tool"`
	Args       map[string]any `json:"args"`
	Confidence float64        `json:"confidence"`
}

type Finding struct {
	Hypothesis         string           `json:"hypothesis"`
	Verdict            string           `json:"verdict"`
	Evidence           []string         `json:"evidence"`
	RecommendedActions []Recommendation `json:"recommended_actions"`
}

// Pool runs investigators as children of the calling run. Each child gets the investigator
// role, its own instance ID, and a link to the parent instance.
type Pool struct {
	Loop        *runner.Loop
	Router      *tools.Router
	Audit       *audit.Store
	Budget      config.Budget
	Prompt      string
	ChildTypeID string
}

func (p *Pool) Handler() tools.Handler {
	return func(ctx context.Context, call tools.Call) (tools.Result, error) {
		parent, ok := tools.RunFromContext(ctx)
		hyps, _ := call.Args["hypotheses"].([]any)
		if !ok || len(hyps) == 0 {
			return tools.Result{}, fmt.Errorf("hypotheses is required")
		}
		findings := make([]Finding, len(hyps))
		var wg sync.WaitGroup
		for i, h := range hyps {
			wg.Add(1)
			go func(i int, hyp string) {
				defer wg.Done()
				findings[i] = p.investigate(ctx, parent, hyp)
			}(i, fmt.Sprint(h))
		}
		wg.Wait()

		// Confident recommendations from supported findings are applied directly, so the
		// parent does not spend another model turn re-deriving them.
		var applied []string
		for _, f := range findings {
			for _, rec := range f.RecommendedActions {
				if f.Verdict != "supported" || rec.Confidence < 0.9 {
					continue
				}
				res, err := p.Router.Dispatch(ctx, parent, rec.Tool, rec.Args, tools.DispatchOpts{PreApproved: true})
				applied = append(applied, fmt.Sprintf("%s: %s %v", rec.Tool, res.Content, err))
			}
		}
		out, _ := json.Marshal(map[string]any{"findings": findings, "applied": applied})
		return tools.Result{Content: string(out)}, nil
	}
}

func (p *Pool) investigate(ctx context.Context, parent *tools.Run, hyp string) Finding {
	child := &tools.Run{
		ID: parent.ID, Role: "investigator", Tenant: parent.Tenant, Cluster: parent.Cluster,
		Subject: parent.Subject, ParentInstanceID: parent.Identity.AgentInstanceID,
		Identity: agent.Identity{AccountableParty: parent.Identity.AccountableParty,
			OperationalOwner: parent.Identity.OperationalOwner, AgentTypeID: p.ChildTypeID,
			AgentInstanceID: agent.NewInstanceID()},
		Budget: agent.NewBudget(p.Budget),
	}
	ctx, span := otel.Tracer("cloudops-agent").Start(ctx, "invoke_agent investigator")
	defer span.End()
	span.SetAttributes(attribute.String("cloudops.agent.instance_id", child.Identity.AgentInstanceID),
		attribute.String("cloudops.agent.parent_instance_id", child.ParentInstanceID),
		attribute.String("cloudops.agent.type_id", child.Identity.AgentTypeID))

	task := fmt.Sprintf("Team: %s\nCluster: %s\nHypothesis: %s", child.Tenant, child.Cluster, hyp)
	if err := p.Audit.RecordSubagent(ctx, child.ParentInstanceID, child.Identity.AgentInstanceID,
		child.Identity.AgentTypeID, span.SpanContext().TraceID().String(), tools.Redact(task)); err != nil {
		return Finding{Hypothesis: hyp, Verdict: "inconclusive", Evidence: []string{"launch not recorded"}}
	}
	out, err := p.Loop.Run(ctx, child, p.Prompt, task)
	var f Finding
	if err != nil || json.Unmarshal([]byte(strings.TrimSpace(out)), &f) != nil {
		return Finding{Hypothesis: hyp, Verdict: "inconclusive", Evidence: []string{fmt.Sprint(err)}}
	}
	f.Hypothesis = hyp
	return f
}
