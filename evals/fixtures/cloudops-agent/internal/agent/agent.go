package agent

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"sync"
	"time"

	"github.com/northwind-platform/cloudops-agent/internal/config"
)

// Identity is attached to every span and audit row the agent writes.
type Identity struct {
	AccountableParty, OperationalOwner, AgentTypeID, AgentInstanceID string
}

// TypeID fingerprints the deployed agent type.
func TypeID(cfg *config.Config) (string, error) {
	prompt, err := os.ReadFile(cfg.SystemPrompt)
	if err != nil {
		return "", err
	}
	h := sha256.New()
	h.Write([]byte("agent_type=" + cfg.AgentType + "\nrelease=" + cfg.Version + "\n"))
	h.Write([]byte("model=" + cfg.ModelProvider + "/" + cfg.ModelID + "\nsystem_prompt="))
	h.Write(prompt)
	return "sha256:" + hex.EncodeToString(h.Sum(nil)), nil
}

func NewInstanceID() string {
	b := make([]byte, 12)
	_, _ = rand.Read(b)
	return "inst-" + hex.EncodeToString(b)
}

var (
	ErrStepLimit  = errors.New("budget: step limit reached")
	ErrTokenLimit = errors.New("budget: input token limit reached")
	ErrWallLimit  = errors.New("budget: wall clock limit reached")
	ErrRateLimit  = errors.New("budget: tool call rate exceeded")
)

// Budget is enforced by the loop, not by the model.
type Budget struct {
	mu            sync.Mutex
	cfg           config.Budget
	started       time.Time
	steps, tokens int
	calls         []time.Time
}

func NewBudget(cfg config.Budget) *Budget { return &Budget{cfg: cfg, started: time.Now()} }

func (b *Budget) Step(inputTokens int) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.steps++
	b.tokens += inputTokens
	switch {
	case b.steps > b.cfg.MaxSteps:
		return ErrStepLimit
	case b.tokens > b.cfg.MaxInputTokens:
		return ErrTokenLimit
	case time.Now().After(b.Deadline()):
		return ErrWallLimit
	}
	return nil
}

func (b *Budget) ToolCall() error {
	b.mu.Lock()
	defer b.mu.Unlock()
	cut := time.Now().Add(-time.Minute)
	kept := b.calls[:0]
	for _, t := range b.calls {
		if t.After(cut) {
			kept = append(kept, t)
		}
	}
	if b.calls = kept; len(kept) >= b.cfg.MaxToolCallsPerMinute {
		return ErrRateLimit
	}
	b.calls = append(b.calls, time.Now())
	return nil
}

func (b *Budget) Deadline() time.Time {
	return b.started.Add(time.Duration(b.cfg.MaxWallSeconds) * time.Second)
}
