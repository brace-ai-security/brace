package mcpclient

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"sync"

	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"

	"github.com/northwind-platform/cloudops-agent/internal/config"
	"github.com/northwind-platform/cloudops-agent/internal/tools"
)

const maxResultBytes = 32 << 10

// Manager launches each stdio server in .mcp.json and binds its approved tools into the
// registry as "<key>/<tool>". Server identity is the .mcp.json key and the binary path baked
// into the image; the name a server reports in initialize is only logged.
type Manager struct {
	Registry *tools.Registry
	Teams    config.Teams
	mu       sync.Mutex
	clients  map[string]*client.Client
	bound    map[string]bool
}

func (m *Manager) Start(ctx context.Context, mcpFile string) error {
	var f struct {
		MCPServers map[string]struct {
			Command string            `json:"command"`
			Args    []string          `json:"args"`
			Env     map[string]string `json:"env"`
		} `json:"mcpServers"`
	}
	raw, err := os.ReadFile(mcpFile)
	if err != nil || json.Unmarshal(raw, &f) != nil {
		return fmt.Errorf("read %s: %v", mcpFile, err)
	}
	m.clients, m.bound = map[string]*client.Client{}, map[string]bool{}
	for key, def := range f.MCPServers {
		var env []string
		for k, v := range def.Env {
			env = append(env, k+"="+os.ExpandEnv(v))
		}
		c, err := client.NewStdioMCPClient(def.Command, env, def.Args...)
		if err != nil {
			return err
		}
		init, err := c.Initialize(ctx, mcp.InitializeRequest{})
		if err != nil {
			return err
		}
		slog.Info("mcp server started", "key", key, "reported_name", init.ServerInfo.Name)
		m.clients[key] = c
		srv := key
		c.OnNotification(func(n mcp.JSONRPCNotification) {
			if n.Method == "notifications/tools/list_changed" {
				if err := m.load(context.Background(), srv); err != nil {
					slog.Error("tool reload failed; server tools unbound", "server", srv, "err", err)
				}
			}
		})
		if err := m.load(ctx, key); err != nil {
			return err
		}
	}
	return nil
}

// load binds only tools whose fingerprint matches tools.yaml and whose metadata passes the
// scan. Every tool from the server is unbound first, so any failure leaves none bound.
func (m *Manager) load(ctx context.Context, server string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	for key := range m.bound {
		if strings.HasPrefix(key, server+"/") {
			m.Registry.Unbind(key)
			delete(m.bound, key)
		}
	}
	list, err := m.clients[server].ListTools(ctx, mcp.ListToolsRequest{})
	if err != nil {
		return err
	}
	seen := map[string]string{}
	for _, t := range list.Tools {
		if prev, dup := seen[normalizeName(t.Name)]; dup {
			return fmt.Errorf("server %s exposes confusable tool names %q and %q", server, prev, t.Name)
		}
		seen[normalizeName(t.Name)] = t.Name
		key := server + "/" + t.Name
		want, approved := m.Registry.Fingerprint(key)
		if !approved {
			continue
		}
		if got := fingerprint(t); got != want {
			return fmt.Errorf("tool %s metadata changed: fingerprint %s, approved %s", key, got, want)
		}
		if err := ScanTool(t); err != nil {
			return fmt.Errorf("tool %s: %w", key, err)
		}
		if err := m.Registry.Bind(key, m.handler(server, t.Name)); err != nil {
			return err
		}
		m.bound[key] = true
	}
	return nil
}

func (m *Manager) handler(server, tool string) tools.Handler {
	return func(ctx context.Context, call tools.Call) (tools.Result, error) {
		args := map[string]any{}
		for k, v := range call.Args {
			if k != "team" {
				args[k] = v
			}
		}
		if ng, ok := args["nodegroup"].(string); ok && !m.Teams.OwnsNodeGroup(call.Tenant, ng) {
			return tools.Result{}, fmt.Errorf("node group %s is not owned by team %s", ng, call.Tenant)
		}
		req := mcp.CallToolRequest{}
		req.Params.Name, req.Params.Arguments = tool, args
		res, err := m.clients[server].CallTool(ctx, req)
		if err != nil {
			return tools.Result{}, err
		}
		var b strings.Builder
		for _, c := range res.Content {
			if tc, ok := c.(mcp.TextContent); ok {
				b.WriteString(tc.Text)
			}
		}
		if b.Len() > maxResultBytes {
			return tools.Result{}, fmt.Errorf("%s result over %d bytes", tool, maxResultBytes)
		}
		if res.IsError {
			return tools.Result{}, fmt.Errorf("%s: %.300s", tool, b.String())
		}
		return tools.Result{Content: b.String()}, nil
	}
}

func fingerprint(t mcp.Tool) string {
	canon, _ := json.Marshal([]any{t.Name, t.Description, t.InputSchema, t.OutputSchema})
	sum := sha256.Sum256(canon)
	return hex.EncodeToString(sum[:])
}
