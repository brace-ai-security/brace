package tools

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"

	"github.com/northwind-platform/cloudops-agent/internal/config"
)

const maxObserveBytes = 64 << 10

// Observe queries Prometheus and Loki through prom-label-proxy, which adds the given
// namespace as a matcher to every selector in the query.
type Observe struct {
	PromURL, LokiURL string
	HTTP             *http.Client
	Kube             *Kube
}

func (o *Observe) MetricsQuery(ctx context.Context, c Call) (Result, error) {
	return o.query(ctx, c, "promql", o.PromURL+"/api/v1/query")
}

func (o *Observe) LogsQuery(ctx context.Context, c Call) (Result, error) {
	return o.query(ctx, c, "logql", o.LokiURL+"/loki/api/v1/query_range")
}

func (o *Observe) query(ctx context.Context, c Call, field, endpoint string) (Result, error) {
	ns, err := o.Kube.namespaceFor(c)
	if err != nil {
		return Result{}, err
	}
	q, _ := c.Args[field].(string)
	if q == "" || len(q) > 2000 {
		return Result{}, fmt.Errorf("%s must be 1-2000 characters", field)
	}
	v := url.Values{"query": {q}, "namespace": {ns}, "limit": {"200"}}
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"?"+v.Encode(), nil)
	req.Header.Set("X-Cluster", c.Cluster)
	resp, err := o.HTTP.Do(req)
	if err != nil {
		return Result{}, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, maxObserveBytes+1))
	var parsed struct {
		Status string          `json:"status"`
		Data   json.RawMessage `json:"data"`
	}
	switch {
	case resp.StatusCode != http.StatusOK:
		return Result{}, fmt.Errorf("upstream status %d", resp.StatusCode)
	case len(body) > maxObserveBytes:
		return Result{}, fmt.Errorf("response over %d bytes; narrow the query", maxObserveBytes)
	case json.Unmarshal(body, &parsed) != nil || parsed.Status != "success":
		return Result{}, fmt.Errorf("upstream returned a malformed or failed response")
	}
	return Result{Content: string(parsed.Data)}, nil
}

type Slack struct {
	Token string
	HTTP  *http.Client
	Teams config.Teams
}

// Post sends to the team's configured channel only; the model supplies text, not the
// destination. Links and media are not unfurled and Slack link syntax is escaped.
func (s *Slack) Post(ctx context.Context, c Call) (Result, error) {
	text, _ := c.Args["text"].(string)
	if !s.Teams.Known(c.Tenant) || text == "" || len(text) > 3500 {
		return Result{}, fmt.Errorf("need a known team and 1-3500 characters of text")
	}
	return Result{Content: "posted"}, s.Send(ctx, s.Teams.Teams[c.Tenant].SlackChannel, EscapeMrkdwn(text), nil)
}

func (s *Slack) Send(ctx context.Context, channel, text string, blocks any) error {
	body, _ := json.Marshal(map[string]any{"channel": channel, "text": text, "blocks": blocks,
		"unfurl_links": false, "unfurl_media": false})
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, "https://slack.com/api/chat.postMessage", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+s.Token)
	req.Header.Set("Content-Type", "application/json; charset=utf-8")
	resp, err := s.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	var sr struct {
		OK    bool   `json:"ok"`
		Error string `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&sr); err != nil || !sr.OK {
		return fmt.Errorf("slack post failed: %v %s", err, sr.Error)
	}
	return nil
}

var mrkdwn = strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", "`", "'")

func EscapeMrkdwn(s string) string { return mrkdwn.Replace(Redact(s)) }

var secretPatterns = []*regexp.Regexp{
	regexp.MustCompile(`AKIA[0-9A-Z]{16}`),
	regexp.MustCompile(`xox[abposr]-[0-9A-Za-z-]{10,}`),
	regexp.MustCompile(`(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}`),
	regexp.MustCompile(`eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}`),
	regexp.MustCompile(`-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----`),
	regexp.MustCompile(`(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*["']?[^\s"',]{6,}`),
	regexp.MustCompile(`postgres(ql)?://[^:\s]+:[^@\s]+@`),
}

// Redact masks credentials. It runs on every tool result before the model sees it, before
// it is written to the audit table, and on outgoing Slack text.
func Redact(s string) string {
	for _, p := range secretPatterns {
		s = p.ReplaceAllString(s, "[REDACTED]")
	}
	return s
}

func RedactJSON(v any) string {
	b, _ := json.Marshal(v)
	return Redact(string(b))
}
