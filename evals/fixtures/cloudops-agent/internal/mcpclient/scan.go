package mcpclient

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"unicode"

	"github.com/mark3labs/mcp-go/mcp"
	"golang.org/x/text/unicode/norm"
)

var (
	validName    = regexp.MustCompile(`^[a-z][a-z0-9_]{0,63}$`)
	roleOverride = regexp.MustCompile(`(?i)(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above)|\byou are now\b|system\s*prompt|<\s*/?\s*(system|assistant|instructions?)\s*>|\bdo not (tell|inform|mention)\b`)
	crossTool    = regexp.MustCompile(`(?i)\b(before|after|instead of)\s+(using|calling)\b|\b(slack_post|rollback_release|scale_deployment|spawn_investigators|metrics_query|logs_query)\b`)
	sendTarget   = regexp.MustCompile(`(?i)https?://|\b[\w.+-]+@[\w-]+\.[\w.]+|\bwebhook\b|\bupload\b`)
	encodedBlob  = regexp.MustCompile(`[A-Za-z0-9+/]{60,}={0,2}|(?:\\x[0-9a-fA-F]{2}){8,}|(?:%[0-9a-fA-F]{2}){8,}`)
)

// ScanTool checks every metadata field the model can see: name, title, description, input
// and output schemas, and annotations. A finding, or a field that cannot be decoded, rejects
// the tool. Servers' prompts and resources are never loaded.
func ScanTool(t mcp.Tool) error {
	if !validName.MatchString(t.Name) || len(t.Description) > 1500 {
		return fmt.Errorf("name or description outside limits")
	}
	strs := []string{t.Description, t.Annotations.Title}
	for _, v := range []any{t.InputSchema, t.OutputSchema, t.Annotations} {
		raw, err := json.Marshal(v)
		var generic any
		if err != nil || len(raw) > 8<<10 || json.Unmarshal(raw, &generic) != nil {
			return fmt.Errorf("schema or annotations too large or not decodable for scanning")
		}
		collect(generic, &strs)
	}
	for _, s := range strs {
		if err := scanText(s); err != nil {
			return err
		}
	}
	return nil
}

func scanText(s string) error {
	for _, r := range s {
		if unicode.Is(unicode.Cf, r) || unicode.Is(unicode.Co, r) || (r >= 0xE0000 && r <= 0xE007F) ||
			(unicode.IsControl(r) && r != '\n' && r != '\t') {
			return fmt.Errorf("invisible or control character U+%04X", r)
		}
	}
	n := norm.NFKC.String(s)
	for what, re := range map[string]*regexp.Regexp{"instruction override": roleOverride,
		"reference to other tools": crossTool, "destination": sendTarget, "encoded payload": encodedBlob} {
		if re.MatchString(n) {
			return fmt.Errorf("metadata contains %s", what)
		}
	}
	return nil
}

func collect(v any, out *[]string) {
	switch x := v.(type) {
	case string:
		*out = append(*out, x)
	case map[string]any:
		for k, vv := range x {
			*out = append(*out, k)
			collect(vv, out)
		}
	case []any:
		for _, vv := range x {
			collect(vv, out)
		}
	}
}

// normalizeName folds case, width and separators so lookalike names collide.
func normalizeName(s string) string {
	return strings.NewReplacer("-", "", "_", "", ".", "").Replace(strings.ToLower(norm.NFKC.String(s)))
}
