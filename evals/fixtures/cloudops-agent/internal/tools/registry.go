package tools

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"sync"

	"gopkg.in/yaml.v3"
)

type Impact string

const (
	ImpactRead   Impact = "read"
	ImpactLow    Impact = "low"
	ImpactMedium Impact = "medium"
	ImpactHigh   Impact = "high"
)

type Spec struct {
	Name   string         `yaml:"name"`
	Impact Impact         `yaml:"impact"`
	Reason string         `yaml:"reason"`
	Args   map[string]any `yaml:"args"`
}

type Result struct{ Content string }

type Call struct {
	ID, Tool, Tenant, Cluster string
	Args                      map[string]any
}

type Handler func(ctx context.Context, call Call) (Result, error)

// Registry holds the role allowlists from tools.yaml and the handlers bound to them.
// Impact and permission come only from tools.yaml, never from what a tool server reports.
type Registry struct {
	mu            sync.RWMutex
	roles         map[string]map[string]Spec
	handlers      map[string]Handler
	fingerprints  map[string]string
	PolicyVersion string
}

func LoadRegistry(path string) (*Registry, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var f struct {
		Roles           map[string][]Spec `yaml:"roles"`
		MCPFingerprints map[string]string `yaml:"mcp_fingerprints"`
	}
	if err := yaml.Unmarshal(raw, &f); err != nil {
		return nil, err
	}
	sum := sha256.Sum256(raw)
	r := &Registry{roles: map[string]map[string]Spec{}, handlers: map[string]Handler{},
		fingerprints: f.MCPFingerprints, PolicyVersion: "tools.yaml@" + hex.EncodeToString(sum[:8])}
	for role, specs := range f.Roles {
		r.roles[role] = map[string]Spec{}
		for _, s := range specs {
			if s.Reason == "" || (s.Impact != ImpactRead && s.Impact != ImpactLow && s.Impact != ImpactMedium && s.Impact != ImpactHigh) {
				return nil, fmt.Errorf("tool %s in role %s needs a reason and a valid impact", s.Name, role)
			}
			r.roles[role][s.Name] = s
		}
	}
	return r, nil
}

// Bind attaches a handler. Tools that no role lists are refused; a name binds once.
func (r *Registry) Bind(name string, h Handler) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, dup := r.handlers[name]; dup {
		return fmt.Errorf("tool %s already bound", name)
	}
	for _, m := range r.roles {
		if _, ok := m[name]; ok {
			r.handlers[name] = h
			return nil
		}
	}
	return fmt.Errorf("tool %s is not in any role allowlist", name)
}

func (r *Registry) Unbind(name string) { r.mu.Lock(); delete(r.handlers, name); r.mu.Unlock() }

func (r *Registry) Lookup(role, name string) (Spec, Handler, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	spec, ok := r.roles[role][name]
	h, bound := r.handlers[name]
	return spec, h, ok && bound
}

func (r *Registry) SpecsFor(role string) []Spec {
	r.mu.RLock()
	defer r.mu.RUnlock()
	var out []Spec
	for _, s := range r.roles[role] {
		if _, bound := r.handlers[s.Name]; bound {
			out = append(out, s)
		}
	}
	return out
}

func (r *Registry) Fingerprint(name string) (string, bool) {
	fp, ok := r.fingerprints[name]
	return fp, ok
}
