"""MCP servers: unpinned packages (AP04), literal secrets (AP05), plain HTTP (AP07), container escapes (AP08), lethal combinations (AP09), and the config shapes they are read from."""
import json

import pytest
from support import TOKEN, TOKEN_MIXED, found, mcp, report, result, rules, run, scan, write

from open_agent_security.checks.mcp_servers import is_pinned
from open_agent_security.jsonc import strip_jsonc

CODEX = f'''model = "o3"

[mcp_servers.x]
command = "npx"
args = ["-y", "evil"]

[mcp_servers.x.env]
GITHUB_TOKEN = "{TOKEN_MIXED}"
'''


def test_mcp_server_rules(tmp_path):
    cfg = {"mcpServers": {
        "a": {"command": "npx", "args": ["-y", "@scope/thing"]},
        "b": {"command": "uvx", "args": ["tool@latest"]},
        "c": {"command": "docker", "args": ["run", "-v", "/var/run/docker.sock:/var/run/docker.sock", "img"]},
        "d": {"url": "http://tools.example.com/mcp"},
        "e": {"url": "http://localhost:3000/mcp"},
        "f": {"command": "node", "args": ["x.js"], "env": {"TOKEN": TOKEN}},
    }}
    write(tmp_path, ".mcp.json", json.dumps(cfg, indent=2))
    assert rules(tmp_path) == ["AP04", "AP04", "AP05", "AP07", "AP08"]


@pytest.mark.parametrize("entry,flagged", [
    ({"command": "uvx", "args": ["--python", "3.12", "mcp-server-time==1.0.0"]}, False),
    ({"command": "npx", "args": ["-y", "--package=foo@1.0.0", "foo-cli"]}, False),
    ({"command": "npx", "args": ["-y", "-p", "foo@1.0.0", "foo-cli"]}, False),
    ({"command": "uvx", "args": ["--from", "pkg==2.0", "tool"]}, False),
    ({"command": "npx", "args": ["-y", "@scope/pkg@1.2.3"]}, False),
    ({"command": "npx", "args": ["./local-server"]}, False),
    ({"command": "cmd", "args": ["/c", "npx", "-y", "some-mcp"]}, True),
    ({"command": "C:\\Program Files\\nodejs\\npx.cmd", "args": ["some-mcp"]}, True),
    ({"command": "npx", "args": ["some-mcp@next"]}, True),
    ({"command": "npx", "args": ["some-mcp@^1.2.0"]}, True),
    ({"command": "uvx", "args": ["pkg>=1.0"]}, True),
    ({"command": "npx", "args": ["--package", "foo", "foo-cli"]}, True),
])
def test_unpinned_package_detection(tmp_path, entry, flagged):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": entry}}))
    assert (rules(tmp_path) == ["AP04"]) is flagged


@pytest.mark.parametrize("url,flagged", [
    ("http://[::1]:3000/mcp", False),
    ("HTTP://tools.example.com/mcp", True),
    ("http://localhost:pw@evil.example.com/mcp", True),
    ("http://127.0.0.2:8080/mcp", False),
    ("https://tools.example.com/mcp", False),
])
def test_plain_http_host_parsing(tmp_path, url, flagged):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"url": url}}}))
    assert ("AP07" in rules(tmp_path)) is flagged


def test_plain_http_detail_has_no_userinfo(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"url": "http://user:s3cretpw@tools.example.com/x"}}}))
    details = {f.rule: f.detail for f in result(tmp_path).findings}
    assert details["AP07"] == "s: http://tools.example.com" and "s3cretpw" not in details["AP05"]


@pytest.mark.parametrize("args", [["run", "--privileged", "i"], ["run", "--volume", "/:/host", "i"],
                                  ["run", "--mount", "type=bind,source=/,target=/h", "i"], ["run", "--net=host", "i"],
                                  ["run", "--cap-add=SYS_ADMIN", "i"]])
def test_container_escape_forms(tmp_path, args):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "docker", "args": args}}}))
    assert rules(tmp_path) == ["AP08"]


def test_safe_container_mount_not_flagged(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "docker",
                                                              "args": ["run", "-v", "/srv/data:/data:ro", "i"]}}}))
    assert rules(tmp_path) == []


def test_jsonc_bom_and_trailing_commas_are_parsed(tmp_path):
    write(tmp_path, ".vscode/mcp.json", '// workspace servers\n{"servers": {"s": {"command": "npx", "args": ["x"],},},}\n')
    (tmp_path / ".mcp.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"mcpServers": {"t": {"command": "npx", "args": ["y"]}}}).encode())
    assert rules(tmp_path) == ["AP04", "AP04"]


def test_line_points_at_the_right_server(tmp_path):
    cfg = ('{\n "mcpServers": {\n  "a": {"command": "node", "env": {"KEY": "x"}},\n  "b": {\n   "command": "node",\n'
           '   "env": {"KEY": "' + TOKEN + '"}\n  }\n }\n}\n')
    write(tmp_path, ".mcp.json", cfg)
    assert [(f.rule, f.line) for f in result(tmp_path).findings] == [("AP05", 6)]


@pytest.mark.parametrize("text", [
    '{"mcpServers":{"a":{"command":"npx","args":5}}}',
    '{"mcpServers":{"a":{"command":"npx","args":[null, {"x":1}, "pkg"]}}}',
    '{"permissions":{"allow":5}}',
    '{"permissions":{"allow":[5, null]}}',
    '{"mcpServers": 5}',
    '[1, 2, 3]',
    '[' * 200000,
    '{"mcpServers":{"a":{"command":["npx"],"url":5,"env":{"K":["x"]}}}}',
])
def test_odd_json_does_not_crash(tmp_path, text):
    write(tmp_path, "x.json", text)
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    assert "AP01" in rules(tmp_path)


def test_lethal_combination(tmp_path):
    cfg = {"mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch==1.0"]},
                          "postgres": {"command": "node", "args": ["pg.js"]}}}
    write(tmp_path, ".mcp.json", json.dumps(cfg))
    assert rules(tmp_path) == ["AP09"]


def test_lethal_combination_no_substring_false_positives(tmp_path):
    cfg = {"mcpServers": {"docs": {"url": "https://mcp.example.com/sse"},
                          "sqlite": {"command": "node", "args": ["./sqlite-server.js"]},
                          "research": {"command": "node", "args": ["./laws-driver.js"]}}}
    write(tmp_path, ".mcp.json", json.dumps(cfg))
    assert rules(tmp_path) == []


def test_generic_servers_key_only_in_mcp_files(tmp_path):
    inv = {"servers": {"web-1": {"url": "http://10.0.0.5"}, "mail": {"url": "http://10.0.0.6"}, "db": {}}}
    write(tmp_path, "config/inventory.json", json.dumps(inv))
    assert rules(tmp_path) == []


def test_lethal_combination_consistent_for_one_server(tmp_path):
    write(tmp_path, "a/.mcp.json", json.dumps({"mcpServers": {"github": {"url": "https://api.githubcopilot.com/mcp/"}}}))
    write(tmp_path, "b/.mcp.json", json.dumps({"mcpServers": {"github": {"url": "https://api.githubcopilot.com/mcp/"},
                                                             "time": {"command": "node", "args": ["t.js"]}}}))
    assert rules(tmp_path) == ["AP09", "AP09"]


@pytest.mark.parametrize("pkg,cmd,pinned", [
    ("pkg@1", "npx", False), ("pkg@1.2", "npx", False), ("@scope/pkg@2", "npx", False), ("pkg@1.2.3", "npx", True),
    ("pkg==1.2", "uvx", True), ("pkg@1.2", "uvx", True), ("pkg", "uvx", False), ("pkg==1.*", "uvx", False),
])
def test_pinning_rules_per_runner(pkg, cmd, pinned):
    assert is_pinned(pkg, cmd) is pinned


@pytest.mark.parametrize("entry,rule", [
    ({"serverUrl": "http://tools.example.com/mcp"}, "AP07"),
    ({"httpUrl": "http://tools.example.com/mcp"}, "AP07"),
    ({"command": "npx -y some-other-mcp"}, "AP04"),
    ({"command": "uv", "args": ["tool", "run", "mcp-server-x"]}, "AP04"),
    ({"command": "npm", "args": ["exec", "--yes", "some-mcp-3"]}, "AP04"),
    ({"command": "pipx", "args": ["run", "mcp-thing"]}, "AP04"),
])
def test_other_config_spellings(tmp_path, entry, rule):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": entry}}))
    assert rules(tmp_path) == [rule]


def test_non_ascii_server_name_line(tmp_path):
    write(tmp_path, ".mcp.json", '{\n "mcpServers": {\n  "数据": {"command": "npx", "args": ["x"]}\n }\n}\n')
    assert [(f.rule, f.line) for f in result(tmp_path).findings] == [("AP04", 3)]


def test_jsonc_trailing_comma_inside_string_is_kept():
    assert json.loads(strip_jsonc('{// c\n"a":["x,]"],}')) == {"a": ["x,]"]}


def test_unknown_format_secret_flag_value_is_not_the_package(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"d": {"command": "npx", "args": [
        "--api-key", "0123456789abcdef0123456789abcdef", "pkg@1.0.0"]}}}))
    assert rules(tmp_path) == ["AP05"]  # a secret (review 6, finding 6), but not an unpinned package
    _, text = run(tmp_path)
    assert "0123456789abcdef" not in text


def test_uvx_directory_flag_value_is_skipped(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"t": {"command": "uvx", "args": ["--directory", "/x", "some-tool"]}}}))
    assert rules(tmp_path) == ["AP04"]


def test_git_source_pinned_by_commit():
    assert is_pinned("git+https://github.com/o/r@" + "a1" * 20, "uvx")
    assert not is_pinned("git+https://github.com/o/r@v1.2.3", "uvx")


def test_line_uses_the_server_path_not_the_first_same_named_key(tmp_path):
    write(tmp_path, ".mcp.json", '{\n "inputs": {"env": 1, "github": "x"},\n "mcpServers": {\n'
          '  "env": {"command": "npx", "args": ["a"]},\n  "github": {"command": "npx", "args": ["b"]}\n }\n}\n')
    assert sorted((f.rule, f.line) for f in result(tmp_path).findings if f.rule == "AP04") == [("AP04", 4), ("AP04", 5)]


def test_null_json_is_not_a_parse_error(tmp_path):
    write(tmp_path, ".mcp.json", "null")
    r = result(tmp_path)
    assert not r.incomplete and run(tmp_path, fail_on="high")[0] == 0


@pytest.mark.parametrize("cmd,args,expected", [
    ("npx", ["--yes", "@modelcontextprotocol/server-filesystem", "/data"], "npx @modelcontextprotocol/server-filesystem"),
    ("npx", ["--yes", "some-mcp@1.2.3", "serve"], None),
    ("uvx", ["--quiet", "mcp-server-git==2.0.1", "run"], None),
    ("uvx", ["--isolated", "mcp-server-git", "--repository", "repo"], "uvx mcp-server-git"),
    ("npx", ["--quiet", "some-mcp", "serve"], "npx some-mcp"),
    ("bash -c 'npx -y foo-mcp'", None, "npx foo-mcp"),
])
def test_unknown_flags_are_switches(tmp_path, cmd, args, expected):
    mcp(tmp_path, {"command": cmd, **({"args": args} if args is not None else {})})
    got = [d.split(": ", 1)[1] for r, d in found(tmp_path) if r == "AP04"]
    assert got == ([expected] if expected else [])


@pytest.mark.parametrize("server", [
    {"command": "env", "args": ["FOO=1", "npx", "-y", "x"]},
    {"command": "/usr/bin/env npx x"},
    {"command": "bash", "args": ["-c", "exec npx -y x"]},
    {"command": "sh", "args": ["-c", "cd /x && npx -y x"]},
    {"command": "sh", "args": ["-c", "echo hi; env -u HOME A=b exec uvx tool"]},
])
def test_runners_behind_env_exec_and_shell_strings(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == ["AP04"]


def test_every_package_flag_is_checked(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-p", "safe@1.0.0", "-p", "evil-unpinned", "run"]})
    found = report(tmp_path)["findings"]
    assert [(f["rule"], f["detail"]) for f in found] == [("AP04", "s0: npx evil-unpinned")]
    mcp(tmp_path, {"command": "npx", "args": ["-p", "safe@1.0.0", "--package=other@2.0.0", "run"]})
    assert rules(tmp_path) == []


def test_url_password_in_env_headers_and_settings(tmp_path):
    url = "postgres://admin:S3cretPassw0rd99@db.example.com/prod"
    mcp(tmp_path, {"command": "node", "args": ["s.js"], "env": {"DATABASE_URL": url}},
        {"url": "https://x.example.com/mcp", "headers": {"X-Upstream": url}})
    write(tmp_path, ".claude/settings.json", json.dumps({"env": {"DATABASE_URL": url}}))
    r = report(tmp_path)
    assert sorted((f["file"], f["rule"]) for f in r["findings"]) == [
        (".claude/settings.json", "AP05"), (".mcp.json", "AP05"), (".mcp.json", "AP05")]
    assert "S3cretPassw0rd99" not in json.dumps(r)


def test_codex_config_toml(tmp_path):
    write(tmp_path, ".codex/config.toml", CODEX)
    r = report(tmp_path)
    assert sorted((f["rule"], f["line"]) for f in r["findings"]) == [("AP04", 3), ("AP05", 7)]


def test_a_codex_config_that_does_not_parse_makes_the_scan_incomplete(tmp_path):
    write(tmp_path, ".codex/config.toml", "[mcp_servers.x\ncommand = \n")
    assert report(tmp_path)["incomplete"] is True


@pytest.mark.parametrize("rel,data", [
    (".vscode/settings.json", {"mcp": {"servers": {"x": {"command": "npx", "args": ["-y", "evil"]}}}}),
    ("opencode.json", {"mcp": {"x": {"type": "local", "command": ["npx", "-y", "evil"]}}}),
    (".zed/settings.json", {"context_servers": {"x": {"command": {"path": "npx", "args": ["-y", "evil"]}}}}),
    ("settings.json", {"context_servers": {"x": {"command": "npx", "args": ["-y", "evil"]}}}),
])
def test_more_json_mcp_shapes(tmp_path, rel, data):
    write(tmp_path, rel, json.dumps(data, indent=2))
    assert found(tmp_path) == [("AP04", "x: npx evil")]


def test_opencode_environment_and_zed_env_hold_secrets(tmp_path):
    write(tmp_path, "opencode.json", json.dumps({"mcp": {"x": {"command": ["npx", "-y", "a@1.0.0"],
                                                               "environment": {"T": TOKEN_MIXED}}}}))
    write(tmp_path, ".zed/settings.json", json.dumps({"context_servers": {"y": {"command": {
        "path": "npx", "args": ["-y", "a@1.0.0"], "env": {"T": TOKEN_MIXED}}}}}))
    assert rules(tmp_path) == ["AP05", "AP05"]


def test_plain_http_through_a_runner_bridge(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "mcp-remote@1.0.0", "http://tools.example.com/sse", "--allow-http"]})
    assert found(tmp_path) == [("AP07", "s0: http://tools.example.com")]


def test_npx_cache_value_is_not_the_package(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["--cache", "/tmp/c", "evil-pkg"]})
    assert found(tmp_path) == [("AP04", "s0: npx evil-pkg")]


def test_a_header_value_is_never_shown_as_the_package(tmp_path):
    opaque = "Zx81kQ0aLm29VbN74TyU3wErTy"
    mcp(tmp_path, {"command": "npx", "args": ["--header", f"Authorization: Bearer {opaque}", "mcp-remote"]})
    out = scan(tmp_path, "--fail-on", "none")[1]
    assert ("AP04", "s0: npx mcp-remote") in found(tmp_path) and opaque not in out


def test_a_long_package_name_with_a_digit_is_shown(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "k8s-mcp-server-for-claude-code"]})
    assert found(tmp_path) == [("AP04", "s0: npx k8s-mcp-server-for-claude-code")]


@pytest.mark.parametrize("server", [
    {"command": "wsl.exe", "args": ["npx", "-y", "some-mcp"]},
    {"command": "wsl", "args": ["-d", "Ubuntu", "--", "npx", "-y", "some-mcp"]},
    {"command": "wsl", "args": ["bash", "-c", "npx -y some-mcp"]},
    {"command": "wsl bash -c \"npx -y some-mcp\""},
    {"command": "op", "args": ["run", "--env-file", ".env", "--", "npx", "-y", "some-mcp"]},
    {"command": "dotenvx", "args": ["run", "--", "npx", "some-mcp"]},
    {"command": "doppler", "args": ["run", "--", "uvx", "some-mcp"]},
    {"command": "infisical run -- npx -y some-mcp"},
    {"command": "aws-vault", "args": ["exec", "prod", "--", "npx", "some-mcp"]},
    {"command": "direnv", "args": ["exec", ".", "npx", "some-mcp"]},
    {"command": "uv", "args": ["run", "--with", "fastmcp", "fastmcp", "run", "server.py"]},
    {"command": "uvx", "args": ["--with", "a==1.0,some-mcp", "tool==2.0"]},
    {"command": "uvx", "args": ["--with=some-mcp", "tool==2.0"]}])
def test_unpinned_packages_behind_wsl_secret_injectors_and_uv_with(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == ["AP04"]


@pytest.mark.parametrize("server", [
    {"command": "npm", "args": ["run", "start", "--", "npx"]},
    {"command": "uv", "args": ["run", "--with", "fastmcp==2.3.0", "fastmcp", "run", "server.py"]},
    {"command": "op", "args": ["run", "--", "npx", "some-mcp@1.2.3"]}])
def test_pinned_or_local_commands_behind_wrappers(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == []


def test_a_megabyte_server_name_is_cut_before_it_reaches_findings(tmp_path):
    name = "n" * 900_000
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {name: {"command": "npx", "args": ["evil"]}}}))
    [f] = result(tmp_path).findings
    assert f.rule == "AP04" and len(f.detail) <= 160


# --- Round 8 review -------------------------------------------------------------------------

BEARER_VALUE = "Bearer " + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8"


@pytest.mark.parametrize("env", [
    {"OPENAPI_MCP_HEADERS": json.dumps({"Authorization": BEARER_VALUE, "Notion-Version": "2022-06-28"})},
    {"OTEL_EXPORTER_OTLP_HEADERS": "Authorization=" + BEARER_VALUE},
    {"NOTION_TOKEN": "ntn_" + "Ab1Cd2Ef3G" * 5},
    {"NOTION_API": "secret_" + "Ab1Cd2Ef3G" * 4 + "Hij"},
])
def test_a_bearer_credential_inside_a_longer_value_is_a_secret(tmp_path, env):
    """Finding 6."""
    mcp(tmp_path, {"command": "node", "args": ["s.js"], "env": env})
    assert rules(tmp_path) == ["AP05"]


def test_a_bearer_credential_inside_a_shell_string_is_a_secret(tmp_path):
    mcp(tmp_path, {"command": "bash", "args": ["-c", f"curl -H 'Authorization: {BEARER_VALUE}' https://x/mcp"]})
    assert "AP05" in rules(tmp_path)


def test_a_placeholder_bearer_inside_a_longer_value_is_not_a_secret(tmp_path):
    mcp(tmp_path, {"command": "node", "args": ["s.js"],
                   "env": {"H": json.dumps({"Authorization": "Bearer YOUR_TOKEN_HERE_xxxxxxxxxxxx"})}})
    assert rules(tmp_path) == []


def test_github_in_a_package_s_host_is_not_a_capability(tmp_path):
    """Finding 8: `github` from `git+https://github.com/...` or `github:owner/repo` adds no leg."""
    for pkg in ("git+https://github.com/oraios/serena@abc1234", "github:owner/tool#main", "owner/tool"):
        mcp(tmp_path, {"command": "uvx" if pkg.startswith("git+") else "npx", "args": ["-y", pkg]})
        assert "AP09" not in rules(tmp_path), pkg


def test_a_package_name_still_counts_for_the_lethal_combination(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "git+https://example.com/x/fetch-mcp.git"]},
        {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres@1.0.0"]},
        {"command": "npx", "args": ["-y", "slack-mcp@1.0.0"]})
    details = [f["detail"] for f in report(tmp_path)["findings"] if f["rule"] == "AP09"]
    assert len(details) == 1 and details[0].startswith("likely, from server and package names")


@pytest.mark.parametrize("server", [
    {"command": "aws-mcp", "args": ["--secret_arn", "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-AbC123"]},
    {"command": "node", "args": ["s.js"], "env": {"DB_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:1234:secret:x1"}},
    {"command": "node", "args": ["s.js"], "env": {"AUTH0_DOMAIN": "tenant123.eu.auth0.com"}},
    {"command": "node", "args": ["s.js"], "env": {"ENCRYPTION_KEY_ALIAS": "alias/prod-key-2024a"}},
    {"command": "node", "args": ["s.js"], "env": {"GPG_KEY_FINGERPRINT": "ABCD1234EF567890ABCD1234EF567890ABCD1234"}},
    {"command": "node", "args": ["s.js"], "env": {"OKTA_AUTHORIZATION_SERVER": "aus1abcd2EFGH3ijk4l5"}},
])
def test_non_secrets_under_secret_sounding_names_are_not_ap05(tmp_path, server):
    """Finding 9."""
    mcp(tmp_path, server)
    assert "AP05" not in rules(tmp_path)


@pytest.mark.parametrize("url", ["postgresql://user:password@localhost:5432/mydb",
                                 "mysql://username:password@db/app", "redis://:changeme@localhost:6379",
                                 "postgres://me:your-password@host/db"])
def test_placeholder_url_passwords_are_not_ap05(tmp_path, url):
    """Finding 15."""
    mcp(tmp_path, {"command": "node", "args": ["s.js", url]})
    assert "AP05" not in rules(tmp_path)


def test_a_real_url_password_is_still_ap05(tmp_path):
    mcp(tmp_path, {"command": "node", "args": ["s.js", "postgresql://user:Xk9pQ2mZ7vR4@db/app"]})
    assert rules(tmp_path) == ["AP05"]


def test_a_truncated_wsl_command_does_not_lose_other_servers(tmp_path):
    """Finding 13: `wsl -d` with no value raised IndexError and lost the file."""
    mcp(tmp_path, {"command": "wsl", "args": ["-d"]}, {"command": "npx", "args": ["-y", "unpinned-mcp"]})
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP04"] and not r["incomplete"]


WRAPPERS = [["wsl", "-d", "Ubuntu", "-u", "me", "--cd", "/x", "-e", "npx", "-y", "pkg"],
            ["cmd", "/c", "npx", "-y", "pkg"], ["bash", "-c", "cd /x && npx -y pkg"],
            ["env", "-u", "X", "-C", "/x", "A=b", "npx", "pkg"], ["op", "run", "--", "npx", "pkg"],
            ["uv", "run", "--with", "x", "--", "npx", "pkg"], ["direnv", "exec", ".", "npx", "pkg"],
            ["exec", "env", "wsl", "--", "sh", "-c", "npx pkg"], ["pwsh", "-command", "npx pkg"]]


def test_wrapper_argument_lists_never_raise():
    """Finding 13: every truncation and reshuffle of each wrapper's arguments resolves without an exception."""
    import random
    from open_agent_security.parse.mcp_json import resolve
    rng = random.Random(8)
    for words in WRAPPERS:
        for end in range(len(words) + 1):
            resolve(words[:end])
            for _ in range(30):
                cut = words[:end] + rng.sample(words, rng.randint(0, len(words)))
                resolve(cut[:rng.randint(0, len(cut))])


@pytest.mark.parametrize("rel,data", [
    ("crush.json", {"mcp": {"x": {"type": "stdio", "command": "npx", "args": ["-y", "evil"]}}}),
    (".crush.json", {"mcp": {"x": {"type": "stdio", "command": "npx", "args": ["-y", "evil"]}}}),
    (".amp/settings.json", {"amp.mcpServers": {"x": {"command": "npx", "args": ["-y", "evil"]}}}),
    (".vscode/settings.json", {"amp.mcpServers": {"x": {"command": "npx", "args": ["-y", "evil"]}}}),
])
def test_round9_crush_and_amp_mcp_config(tmp_path, rel, data):
    write(tmp_path, rel, json.dumps(data, indent=2))
    assert [(f["rule"], f["detail"], f["line"]) for f in report(tmp_path)["findings"]] == [("AP04", "x: npx evil", 3)]


@pytest.mark.parametrize("server", [
    {"command": "npx", "args": ["-y", "https://github.com/someone/some-mcp"]},
    {"command": "npx", "args": ["-y", "https://evil.example/pkg/-/pkg-latest.tgz"]},
    {"command": "uvx", "args": ["--from", "https://github.com/someone/tool/archive/refs/heads/main.zip", "tool"]},
    {"command": "bash", "args": ["-l", "-c", "npx -y some-mcp"]},
    {"command": "bash", "args": ["--login", "-c", "npx -y some-mcp"]},
    {"command": "sudo", "args": ["npx", "-y", "some-mcp"]},
    {"command": "sudo", "args": ["-u", "app", "npx", "-y", "some-mcp"]},
    {"command": "deno", "args": ["run", "-A", "npm:some-mcp-server"]},
    {"command": "deno", "args": ["run", "-A", "jsr:@scope/some-mcp@^1.2.0"]},
])
def test_round9_remote_urls_and_hidden_runners_are_unpinned(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == ["AP04"]


@pytest.mark.parametrize("server", [
    {"command": "npx", "args": ["-y", "https://github.com/someone/some-mcp/archive/" + "a1" * 20 + ".tar.gz"]},
    {"command": "npx", "args": ["-y", "https://evil.example/pkg.tgz#sha256=" + "ab" * 32]},
    {"command": "deno", "args": ["run", "-A", "npm:some-mcp-server@1.2.3"]},
    {"command": "deno", "args": ["run", "-A", "jsr:@scope/some-mcp@1.2.3"]},
    {"command": "deno", "args": ["run", "-A", "server.ts"]},
])
def test_round9_pinned_urls_and_deno_specifiers(tmp_path, server):
    mcp(tmp_path, server)
    assert rules(tmp_path) == []


def test_round9_an_opaque_value_is_never_shown_as_the_package(tmp_path):
    value = "Zq9fPqLmZtRvWbNcHdJsKkXyTn"
    mcp(tmp_path, {"command": "npx", "args": ["-k", value, "pkg@1.0.0"]})
    mcp(tmp_path, {"command": "npx", "args": ["-k", value, "pkg"]}, rel="b/.mcp.json")
    mcp(tmp_path, {"command": "npx", "args": ["--weird", value]}, rel="c/.mcp.json")
    out = scan(tmp_path, "--fail-on", "none")[1] + json.dumps(report(tmp_path))
    assert value not in out
    assert sorted(found(tmp_path)) == [("AP04", "s0: npx <redacted>"), ("AP04", "s0: npx pkg")]
