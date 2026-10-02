package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"

	"github.com/northwind-platform/cloudops-agent/internal/agent"
	"github.com/northwind-platform/cloudops-agent/internal/approval"
	"github.com/northwind-platform/cloudops-agent/internal/audit"
	"github.com/northwind-platform/cloudops-agent/internal/config"
	"github.com/northwind-platform/cloudops-agent/internal/ingest"
	"github.com/northwind-platform/cloudops-agent/internal/investigator"
	"github.com/northwind-platform/cloudops-agent/internal/killswitch"
	"github.com/northwind-platform/cloudops-agent/internal/mcpclient"
	"github.com/northwind-platform/cloudops-agent/internal/runner"
	"github.com/northwind-platform/cloudops-agent/internal/tools"
)

func main() {
	if err := run(); err != nil {
		slog.Error("fatal", "err", err)
		os.Exit(1)
	}
}

func must[T any](v T, err error) T {
	if err != nil {
		slog.Error("startup", "err", err)
		os.Exit(1)
	}
	return v
}

func run() error {
	var cfg config.Config
	var teams config.Teams
	if err := config.Load("/config/agent.yaml", &cfg); err != nil {
		return err
	}
	if err := config.Load(cfg.TeamsFile, &teams); err != nil {
		return err
	}
	id := agent.Identity{AccountableParty: cfg.AccountableParty, OperationalOwner: cfg.OperationalOwner,
		AgentTypeID: must(agent.TypeID(&cfg)), AgentInstanceID: agent.NewInstanceID()}

	root, cancelRoot := context.WithCancel(context.Background())
	defer cancelRoot()
	ctx, stop := signal.NotifyContext(root, syscall.SIGTERM)
	defer stop()
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(must(otlptracegrpc.New(ctx))))
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	defer tp.Shutdown(context.Background())

	db := must(pgxpool.New(ctx, os.Getenv("AUDIT_DATABASE_URL")))
	auditStore := &audit.Store{DB: db}
	reg := must(tools.LoadRegistry(cfg.ToolsFile))

	// One kubeconfig per workload cluster, each using that cluster's cloudops-agent service account.
	kube := &tools.Kube{Clusters: map[string]kubernetes.Interface{}, Dynamic: map[string]dynamic.Interface{}, Teams: teams}
	for _, f := range must(filepath.Glob("/etc/cloudops/clusters/*.yaml")) {
		name, rc := strings.TrimSuffix(filepath.Base(f), ".yaml"), must(clientcmd.BuildConfigFromFlags("", f))
		kube.Clusters[name], kube.Dynamic[name] = must(kubernetes.NewForConfig(rc)), must(dynamic.NewForConfig(rc))
	}
	obs := &tools.Observe{PromURL: os.Getenv("PROM_PROXY_URL"), LokiURL: os.Getenv("LOKI_PROXY_URL"),
		HTTP: &http.Client{Timeout: 20 * time.Second}, Kube: kube}
	slack := &tools.Slack{Token: os.Getenv("SLACK_BOT_TOKEN"), HTTP: &http.Client{Timeout: 10 * time.Second}, Teams: teams}
	for name, h := range map[string]tools.Handler{"metrics_query": obs.MetricsQuery, "logs_query": obs.LogsQuery,
		"scale_deployment": kube.ScaleDeployment, "rollback_release": kube.RollbackRelease, "slack_post": slack.Post} {
		if err := reg.Bind(name, h); err != nil {
			return err
		}
	}
	if err := (&mcpclient.Manager{Registry: reg, Teams: teams}).Start(ctx, cfg.MCPFile); err != nil {
		return err
	}

	approvals := &approval.Service{DB: db, Teams: teams, TTL: time.Duration(cfg.ApprovalTTL) * time.Second,
		Notifier: &approvalsBot{url: os.Getenv("APPROVALS_BOT_URL"), http: &http.Client{}}}
	router := &tools.Router{Reg: reg, Teams: teams, Approvals: approvals, Audit: auditStore}
	loop := &runner.Loop{Client: anthropic.NewClient(), Model: cfg.ModelID, Router: router, Registry: reg}
	pool := &investigator.Pool{Loop: loop, Router: router, Audit: auditStore, Budget: cfg.Investigators,
		Prompt: string(must(os.ReadFile(cfg.InvestigatorPrompt))), ChildTypeID: id.AgentTypeID + "/investigator"}
	if err := reg.Bind("spawn_investigators", pool.Handler()); err != nil {
		return err
	}
	system := string(must(os.ReadFile(cfg.SystemPrompt)))

	ks := &killswitch.Switch{Client: must(kubernetes.NewForConfig(must(rest.InClusterConfig()))),
		Namespace: cfg.ControlNamespace, Name: cfg.ControlConfigMap}
	go ks.Run(ctx, cancelRoot)

	go func() {
		for range time.Tick(6 * time.Hour) {
			n, err := auditStore.Prune(ctx, time.Duration(cfg.AuditRetentionDays)*24*time.Hour)
			slog.Info("audit prune", "deleted", n, "err", err)
		}
	}()

	dispatch := func(a ingest.Alert, receiver string) error {
		if ks.Halted() {
			return fmt.Errorf("halted")
		}
		r := &tools.Run{ID: fmt.Sprintf("run-%s-%d", a.Fingerprint, time.Now().Unix()), Role: "oncall",
			Tenant: a.Labels["team"], Cluster: a.Labels["cluster"], Subject: "alertmanager:" + receiver,
			Identity: id, Budget: agent.NewBudget(cfg.Budget)}
		go func() {
			rctx, cancel := context.WithDeadline(ctx, r.Budget.Deadline())
			defer cancel()
			task := fmt.Sprintf("<alert>\nname: %s\nteam: %s\ncluster: %s\nnamespace: %s\nsummary: %s\ndescription: %s\n</alert>",
				a.Labels["alertname"], a.Labels["team"], a.Labels["cluster"], a.Labels["namespace"],
				a.Annotations["summary"], a.Annotations["description"])
			if _, err := loop.Run(rctx, r, system, task); err != nil {
				slog.Warn("run ended", "run", r.ID, "err", err)
			}
		}()
		return nil
	}

	mux := http.NewServeMux()
	mux.Handle("/alerts", &ingest.Handler{Secret: []byte(os.Getenv("ALERT_WEBHOOK_SECRET")),
		SignatureHeader: cfg.SignatureHeader, Dispatch: dispatch})
	srv := &http.Server{Addr: cfg.WebhookListen, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() { <-ctx.Done(); _ = srv.Shutdown(context.Background()) }()
	slog.Info("listening", "agent_type_id", id.AgentTypeID, "instance", id.AgentInstanceID)
	return srv.ListenAndServeTLS("/tls/tls.crt", "/tls/tls.key")
}

// approvalsBot is the platform's Slack approvals service. It posts an interactive card to
// the team's approvers and returns the Slack user ID of whoever answered.
type approvalsBot struct {
	url  string
	http *http.Client
}

func (b *approvalsBot) Ask(ctx context.Context, team, id, summary, argsJSON string, ttl time.Duration) (string, bool, error) {
	body, _ := json.Marshal(map[string]any{"id": id, "team": team, "summary": tools.EscapeMrkdwn(summary),
		"details": tools.EscapeMrkdwn(argsJSON), "ttl_seconds": int(ttl.Seconds())})
	ctx, cancel := context.WithTimeout(ctx, ttl)
	defer cancel()
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, b.url+"/v1/approvals?wait=true", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := b.http.Do(req)
	if err != nil {
		return "", false, err
	}
	defer resp.Body.Close()
	var d struct {
		Approver string `json:"approver"`
		Approved bool   `json:"approved"`
	}
	if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&d) != nil {
		return "", false, fmt.Errorf("approvals bot status %d", resp.StatusCode)
	}
	return d.Approver, d.Approved, nil
}
