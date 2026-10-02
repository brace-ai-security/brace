package config

import (
	"bytes"
	"os"
	"slices"

	"gopkg.in/yaml.v3"
)

type Budget struct {
	MaxSteps              int `yaml:"max_steps"`
	MaxInputTokens        int `yaml:"max_input_tokens"`
	MaxWallSeconds        int `yaml:"max_wall_seconds"`
	MaxToolCallsPerMinute int `yaml:"max_tool_calls_per_minute"`
}

type Config struct {
	AgentType          string `yaml:"agent_type"`
	Version            string `yaml:"version"`
	ModelProvider      string `yaml:"model_provider"`
	ModelID            string `yaml:"model_id"`
	SystemPrompt       string `yaml:"system_prompt"`
	InvestigatorPrompt string `yaml:"investigator_prompt"`
	ToolsFile          string `yaml:"tools_file"`
	TeamsFile          string `yaml:"teams_file"`
	MCPFile            string `yaml:"mcp_file"`
	Budget             Budget `yaml:"budget"`
	Investigators      Budget `yaml:"investigators"`
	WebhookListen      string `yaml:"webhook_listen"`
	SignatureHeader    string `yaml:"signature_header"`
	ApprovalTTL        int    `yaml:"approval_ttl_seconds"`
	AuditRetentionDays int    `yaml:"audit_retention_days"`
	ControlNamespace   string `yaml:"control_namespace"`
	ControlConfigMap   string `yaml:"control_configmap"`
	AccountableParty   string `yaml:"accountable_party"`
	OperationalOwner   string `yaml:"operational_owner"`
}

type Team struct {
	Namespaces   []string `yaml:"namespaces"`
	SlackChannel string   `yaml:"slack_channel"`
	Approvers    []string `yaml:"approvers"`
	NodeGroups   []string `yaml:"nodegroups"`
}

type Teams struct {
	Teams map[string]Team `yaml:"teams"`
}

func (t Teams) Known(name string) bool { _, ok := t.Teams[name]; return ok }
func (t Teams) OwnsNamespace(team, ns string) bool {
	return slices.Contains(t.Teams[team].Namespaces, ns)
}
func (t Teams) OwnsNodeGroup(team, ng string) bool {
	return slices.Contains(t.Teams[team].NodeGroups, ng)
}
func (t Teams) IsApprover(team, user string) bool {
	return slices.Contains(t.Teams[team].Approvers, user)
}

func Load(path string, out any) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	dec := yaml.NewDecoder(bytes.NewReader(b))
	dec.KnownFields(true)
	return dec.Decode(out)
}
