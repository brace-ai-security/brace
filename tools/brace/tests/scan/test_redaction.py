"""Secrets: detection, placeholders and redaction in every output."""
import json
import re

import pytest
from support import TOKEN, all_outputs, config, fast, found, mcp, report, result, rules, run, scan, write


def test_secret_is_never_printed_in_any_format(tmp_path):
    cfg = {"mcpServers": {
        "gh": {"command": "npx", "args": ["--token", TOKEN, "server-x@1.2.3"]},
        "s": {"command": "node", "env": {"KEY": "sk-ant-" + "x" * 40}},
        "u": {"url": "http://tools.example.com/mcp?key=" + TOKEN},
        "p": {"command": "npx", "args": [TOKEN]},
    }}
    write(tmp_path, ".mcp.json", json.dumps(cfg))
    sf, md = tmp_path / "r.sarif", tmp_path / "s.md"
    _, text = run(tmp_path)
    _, js = run(tmp_path, as_json=True, sarif_path=str(sf), md_path=str(md))
    blob = text + js + sf.read_text() + md.read_text()
    assert TOKEN not in blob and "sk-ant-" not in blob
    assert "AP05" in js


def test_words_ending_in_sk_are_not_secrets(tmp_path):
    write(tmp_path, "services/task-management-server-config/.mcp.json", json.dumps({"mcpServers": {"zendesk": {
        "command": "npx", "args": ["-y", "zendesk-mcp-server-official@1.2.3"],
        "env": {"QUEUE": "task-management-production"}}}}))
    write(tmp_path, "risk-assessment-procedures.sh", "claude --dangerously-skip-permissions\n")
    found = result(tmp_path).findings
    assert [(f.rule, f.file) for f in found] == [("AP01", "risk-assessment-procedures.sh")]


@pytest.mark.parametrize("value", ["Bearer YOUR-GITHUB-PERSONAL-ACCESS-TOKEN", "ghp_" + "x" * 36, "<your-token>",
                                   "sk-ant-api03-" + "x" * 40])
def test_placeholders_are_not_secrets(tmp_path, value):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "node", "headers": {"Authorization": value}}}}))
    assert rules(tmp_path) == []


def test_url_credentials_are_redacted_and_reported(tmp_path):
    root = tmp_path / "r"
    url = "git+https://deploy:Sup3rS3cretPassw0rd@git.example.com/x/y.git"
    mcp(root, {"command": "uvx", "args": ["--from", url, "tool"]})
    for out in all_outputs(root):
        assert "Sup3rS3cretPassw0rd" not in out and "deploy" not in out
    rules = {r for r, _ in found(root)}
    assert {"AP04", "AP05"} <= rules


@pytest.mark.parametrize("args", [
    ["-y", "mcp-remote@1.0.0", "https://x.example/sse", "--header", "Authorization: Bearer 9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f00"],
    ["-y", "srv@1.0.0", "--api-key=sk_" + "live_51H8xYzAbCdEfGhIjKlMnOpQr"],
    ["-y", "srv@1.0.0", "--api-key=9f8a7b6c5d4e3f2a1b0c9d8e"],
    ["-y", "srv@1.0.0", "--token", "Zx81kQ0aLm29VbN74TyU3wEr"],
    ["-y", "srv@1.0.0", "--header", "X-Api-Key: Zx81kQ0aLm29VbN74TyU3wEr"],
])
def test_secrets_in_arguments_are_found_and_redacted(tmp_path, args):
    mcp(tmp_path, {"command": "npx", "args": args})
    assert rules(tmp_path) == ["AP05"]
    secret = re.split(r"[=: ]", args[-1])[-1]
    assert secret not in scan(tmp_path, "--fail-on", "none")[1]


def test_a_stripe_test_key_is_reported_as_a_test_key(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "srv@1.0.0"], "env": {"STRIPE": "sk_test_51H8xYzAbCdEfGhIjKlMnOpQr"}})
    assert found(tmp_path) == [("AP05", "s0: env.STRIPE = <redacted> (a test key)")]


@pytest.mark.parametrize("args", [["-y", "srv@1.0.0", "--api-key=YOUR_API_KEY_GOES_HERE_1"],
                                  ["-y", "srv@1.0.0", "--token-file", "/run/secrets/token123456789012"],
                                  ["-y", "srv@1.0.0", "--auth-mode", "oauth"]])
def test_secret_flags_with_placeholders_or_paths_are_not_secrets(tmp_path, args):
    mcp(tmp_path, {"command": "npx", "args": args})
    assert rules(tmp_path) == []


def test_redaction_covers_bearer_and_flag_values():
    from open_agent_security.output import clean
    assert clean("Authorization: Bearer 9f8a7b6c5d4e3f2a1b0c9d8e7f6a") == "Authorization: Bearer <redacted>"
    assert clean("x --api-key=9f8a7b6c5d4e3f2a1b0c9d8e y") == "x --api-key=<redacted> y"


def test_redaction_runs_before_any_cut():
    from open_agent_security.output import clean
    long = "x " * 2045 + TOKEN  # the token straddles the 4096 characters once cut before redacting
    assert clean(long, 10_000).endswith("<redacted>") and "ghp_" not in clean(long, 10_000)


def test_a_long_package_with_a_custom_token_is_redacted_whole(tmp_path):
    token = "acme_" + "Q7w9E2r4T6y8U1i3O5p7A9s2"
    config(tmp_path, {"tokens": [{"name": "acme", "prefix": "acme_", "charset": "alnum", "min": 20, "max": 64}]})
    mcp(tmp_path, {"command": "npx", "args": ["-y", "a-" + "very-long-package-name-" * 3 + token]})
    detail = next(d for r, d in found(tmp_path) if r == "AP04")
    assert "<redacted>" in detail and "acme_" not in detail and "Q7w9" not in detail


def test_redacting_a_huge_detail_is_bounded():
    from open_agent_security.output import clean
    huge = ("Bearer " + "a1" * 999 + " ") * 2000  # each credential is near the longest a pattern takes
    assert fast(lambda: clean(huge), 1.0).startswith("Bearer <redacted>")


OPAQUE = "BSA1a2b3c4d5e6f7g8h9i0jKLMNOP"  # an opaque key: no known format, only its name says what it is


@pytest.mark.parametrize("server", [
    *({"command": "node", "env": {name: OPAQUE}} for name in (
        "BRAVE_API_KEY", "TAVILY_API_KEY", "NOTION_TOKEN", "LINEAR_API_KEY", "SENTRY_AUTH_TOKEN", "FIGMA_API_KEY",
        "SUPABASE_ACCESS_TOKEN", "POSTGRES_PASSWORD")),
    {"url": "https://mcp.example.com/mcp", "headers": {"X-API-Key": "8f3kd92j4h5g6f7d8s9a"}},
    {"url": "https://mcp.tavily.com/mcp/?tavilyApiKey=tvly-dev-8f3kd92j4h5g6f7d"},
    {"url": "https://mcp.example.com/sse?api_key=8f3kd92j4h5g6f7d8s9a"},
    {"command": "npx", "args": ["mcp-remote@1.0.0", "https://x.example.com/mcp?token=8f3kd92j4h5g6f7d8s9a"]},
    {"command": "docker", "args": ["run", "-e", "API_TOKEN=8f3kd92j4h5g6f7d8s9a", "img@sha256:" + "a" * 64]},
    {"command": "node", "args": ["s.js", "LINEAR_API_KEY=8f3kd92j4h5g6f7d8s9a"]}])
def test_opaque_values_under_secret_names_are_secrets(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == ["AP05"]
    assert "8f3kd92j" not in scan(tmp_path, "--fail-on", "none")[1] and OPAQUE not in json.dumps(report(tmp_path))


@pytest.mark.parametrize("env", [
    {"BRAVE_API_KEY": "${BRAVE_API_KEY}"}, {"BRAVE_API_KEY": "$BRAVE_API_KEY"}, {"API_KEY": "%API_KEY%"},
    {"API_KEY": "{{ secrets.API_KEY }}"}, {"API_KEY": "env:BRAVE_API_KEY_2024"}, {"API_TOKEN": "op://vault/item/k1"},
    {"API_KEY": "your-api-key-here-123456"}, {"API_KEY": "<your api key 2024>"}, {"AUTH_ENABLED": "true"},
    {"TOKEN_TTL": "3600"}, {"TOKEN_FILE": "secrets/token-2024.txt"}, {"AUTH_URL": "https://auth.example.com/v1"},
    {"KEY_PATH": "/run/secrets/key2024abcd"}, {"API_KEY": "short1"}, {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
    {"PASSWORD": "xxxxxxxxxxxxxxxx1"}])
def test_references_placeholders_and_settings_under_secret_names_are_not_secrets(tmp_path, env):
    mcp(tmp_path, {"command": "node", "args": ["s.js"], "env": env})
    assert rules(tmp_path) == []


def test_settings_env_opaque_value_is_a_secret(tmp_path):
    write(tmp_path, ".claude/settings.json", json.dumps({"env": {"BRAVE_API_KEY": OPAQUE}}))
    assert rules(tmp_path) == ["AP05"]
