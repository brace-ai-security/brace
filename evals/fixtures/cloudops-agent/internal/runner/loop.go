package runner

import (
	"context"
	"encoding/json"
	"errors"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"

	"github.com/northwind-platform/cloudops-agent/internal/tools"
)

type Loop struct {
	Client   anthropic.Client
	Model    string
	Router   *tools.Router
	Registry *tools.Registry
}

// Run drives one conversation until the model stops calling tools or the budget is spent.
// Tool output goes back only as tool_result content in a block labelled untrusted.
func (l *Loop) Run(ctx context.Context, run *tools.Run, system, task string) (string, error) {
	msgs := []anthropic.MessageParam{anthropic.NewUserMessage(anthropic.NewTextBlock(task))}
	var defs []anthropic.ToolUnionParam
	for _, s := range l.Registry.SpecsFor(run.Role) {
		defs = append(defs, anthropic.ToolUnionParam{OfTool: &anthropic.ToolParam{
			Name: strings.ReplaceAll(s.Name, "/", "__"), Description: anthropic.String(s.Reason),
			InputSchema: anthropic.ToolInputSchemaParam{Properties: s.Args}}})
	}
	for {
		resp, err := l.Client.Messages.New(ctx, anthropic.MessageNewParams{Model: anthropic.Model(l.Model),
			MaxTokens: 4096, System: []anthropic.TextBlockParam{{Text: system}}, Messages: msgs, Tools: defs})
		if err != nil {
			return "", err
		}
		// Context size is the full input side of the call: uncached input plus cache reads and
		// writes. No usage block means unknown, never zero.
		u := resp.Usage
		run.ContextTokens, run.ContextMethod = nil, "unavailable"
		if n := int(u.InputTokens + u.CacheReadInputTokens + u.CacheCreationInputTokens); n > 0 {
			run.ContextTokens, run.ContextMethod = &n, "provider_usage"
		}
		if err := run.Budget.Step(int(u.InputTokens + u.CacheReadInputTokens + u.CacheCreationInputTokens)); err != nil {
			return "", err
		}
		msgs = append(msgs, resp.ToParam())
		var results []anthropic.ContentBlockParamUnion
		final := ""
		for _, block := range resp.Content {
			switch b := block.AsAny().(type) {
			case anthropic.TextBlock:
				final = b.Text
			case anthropic.ToolUseBlock:
				var args map[string]any
				if json.Unmarshal(b.Input, &args) != nil {
					results = append(results, anthropic.NewToolResultBlock(b.ID, "arguments must be a JSON object", true))
					continue
				}
				res, err := l.Router.Dispatch(ctx, run, strings.ReplaceAll(b.Name, "__", "/"), args, tools.DispatchOpts{})
				if errors.Is(err, context.Canceled) {
					return "", err
				} else if err != nil {
					results = append(results, anthropic.NewToolResultBlock(b.ID, `<tool_result status="error">`+tools.Redact(err.Error())+`</tool_result>`, true))
					continue
				}
				results = append(results, anthropic.NewToolResultBlock(b.ID, `<tool_result source="`+b.Name+`" trust="untrusted">`+res.Content+`</tool_result>`, false))
			}
		}
		if len(results) == 0 {
			return final, nil
		}
		msgs = append(msgs, anthropic.NewUserMessage(results...))
	}
}
