
import yaml

from conftest import GATE, ITEMS, brace, good_exception, good_na

G1, G2, G3 = "B05", "R01", "R09"
assert (GATE[G1], GATE[G2], GATE[G3]) == ("G1", "G2", "G3")


def reasons(result):
    return "\n".join(result["reasons"])


def test_go(repo):
    code, res = repo.check("--approvals", "off")
    assert code == 0, res["reasons"]
    assert res["decision"] == "GO"
    assert res["counts"]["G1"]["pass"] == 18
    assert sum(c["pass"] for c in res["counts"].values()) == 53


def test_go_with_strict_and_nothing_to_approve(repo):
    code, _ = repo.check("--approvals", "off", "--strict")
    assert code == 0


def test_missing_classification(repo):
    del repo.deployment["classification"]
    repo.write()
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "no classification" in reasons(res)


def test_incomplete_classification(repo):
    repo.deployment["classification"] = {"stakes": "low", "autonomy": "low"}
    repo.write()
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "rationale, approved_by" in reasons(res)


def test_unreviewed_item(repo):
    repo.set_item("A03", outcome="not_reviewed", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "A03 has not been reviewed" in reasons(res)
    assert res["items"]["A03"]["status"] == "blocked"


def test_missing_item(repo):
    del repo.record["items"]["E12"]
    repo.write()
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "E12 is missing from record.yaml" in reasons(res)


def test_pass_without_evidence(repo):
    repo.set_item("B03", outcome="pass", lead="@bob", evidence=[{"link": "https://x", "note": "no date"}])
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "B03 is marked pass but has no evidence" in reasons(res)


def test_g1_gap_blocked(repo):
    repo.set_item(G1, outcome="gap", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert f"{G1} is G1 and marked gap. G1 items can't be waived. Release is blocked." in res["reasons"]


def test_g1_exception_is_error(repo):
    repo.add("exceptions", f"{G1}-waiver", good_exception(G1))
    repo.set_item(G1, outcome="gap", lead="@bob", exception=f"{G1}-waiver")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert f"is a risk acceptance for {G1}, a G1 item" in reasons(res)


def test_g1_exception_file_is_error_even_when_item_passes(repo):
    repo.add("exceptions", f"{G1}-waiver", good_exception(G1))
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "G1 items can't be waived" in reasons(res)


def test_g3_gap_high_stakes_blocked(repo):
    repo.deployment["classification"]["stakes"] = "high"
    repo.write()
    repo.add("exceptions", f"{G3}-seq", good_exception(G3))
    repo.set_item(G3, outcome="gap", lead="@bob", exception=f"{G3}-seq")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert f"{G3} is G3 and marked gap" in reasons(res)
    assert "G3 risk acceptances aren't allowed" in reasons(res)


def test_g3_gap_high_autonomy_blocked(repo):
    repo.deployment["classification"]["autonomy"] = "high"
    repo.write()
    repo.set_item(G3, outcome="gap", lead="@bob")
    code, _ = repo.check("--approvals", "off")
    assert code == 1


def test_g3_gap_low_stakes_with_exception(repo):
    repo.add("exceptions", f"{G3}-seq", good_exception(G3))
    repo.set_item(G3, outcome="gap", lead="@bob", exception=f"{G3}-seq")
    code, res = repo.check("--approvals", "off")
    assert code == 0, res["reasons"]
    assert any("approval not verified" in w for w in res["warnings"])
    # --strict turns the unverified approval into a blocker
    code, res = repo.check("--approvals", "off", "--strict")
    assert code == 1
    assert "approval not verified" in reasons(res)


def test_g3_gap_low_stakes_without_exception(repo):
    repo.set_item(G3, outcome="gap", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "no risk acceptance" in reasons(res)


def test_g2_gap_without_exception(repo):
    repo.set_item(G2, outcome="gap", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert f"{G2} is G2 and marked gap with no risk acceptance" in reasons(res)


def test_g2_gap_exception_file_missing(repo):
    repo.set_item(G2, outcome="gap", lead="@bob", exception=f"{G2}-nope")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "does not exist" in reasons(res)


def test_g2_gap_exception_wrong_item(repo):
    repo.add("exceptions", f"{G2}-x", good_exception("R02"))
    repo.set_item(G2, outcome="gap", lead="@bob", exception=f"{G2}-x")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert f"is for R02, not {G2}" in reasons(res)


def test_g2_gap_exception_incomplete(repo):
    exc = good_exception(G2)
    del exc["tracking"]
    exc["threat"] = ""
    repo.add("exceptions", f"{G2}-x", exc)
    repo.set_item(G2, outcome="gap", lead="@bob", exception=f"{G2}-x")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "missing: threat, tracking" in reasons(res)


def test_na_without_file(repo):
    repo.set_item("R05", outcome="na", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "R05 is marked N/A but names no N/A file" in reasons(res)


def test_na_file_missing(repo):
    repo.set_item("R05", outcome="na", lead="@bob", na="R05-none")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "does not exist" in reasons(res)


def test_na_without_reviewer(repo):
    na = good_na("R05")
    del na["reviewer"]
    repo.add("na", "R05-no-memory", na)
    repo.set_item("R05", outcome="na", lead="@bob", na="R05-no-memory")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "missing: reviewer" in reasons(res)


def test_na_ok(repo):
    repo.add("na", "R05-no-memory", good_na("R05"))
    repo.set_item("R05", outcome="na", lead="@bob", na="R05-no-memory")
    code, res = repo.check("--approvals", "off")
    assert code == 0, res["reasons"]


def _with_manifest(repo):
    (repo.root / "prompt.md").write_text("system prompt\n")
    (repo.brace / "manifest.yaml").write_text(
        yaml.safe_dump({"inputs": [{"name": "system_prompt", "path": "prompt.md"}, {"name": "model", "value": "m1"}]})
    )
    value = brace.agent_type_id(brace.load_manifest(repo.brace / "manifest.yaml"), repo.root)
    repo.deployment["agent_type_id"] = {"value": value, "manifest": ".brace/manifest.yaml"}
    repo.write()
    return value


def test_type_id_matches(repo):
    value = _with_manifest(repo)
    code, res = repo.check("--approvals", "off")
    assert code == 0, res["reasons"]
    assert res["agent_type_id"] == {"recorded": value, "computed": value}


def test_type_id_mismatch(repo):
    _with_manifest(repo)
    (repo.root / "prompt.md").write_text("changed prompt\n")
    code, res = repo.check("--approvals", "off")
    assert code == 1
    assert "agent-type-id changed: re-review required" in reasons(res)


def test_type_id_manifest_missing_is_invalid(repo):
    repo.deployment["agent_type_id"] = {"manifest": ".brace/nope.yaml"}
    repo.write()
    code, _ = repo.check("--approvals", "off")
    assert code == 2


# ---- schema errors: exit 2, with both validators -------------------------

def test_schema_bad_outcome(repo, validator_kind):
    repo.set_item("B01", outcome="passed", lead="@bob")
    code, res = repo.check("--approvals", "off")
    assert code == 2 and res is None


def test_schema_expiry_field_rejected(repo, validator_kind):
    exc = good_exception(G2)
    exc["expires_on"] = "2027-01-01"
    repo.add("exceptions", f"{G2}-x", exc)
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_schema_bad_stakes(repo, validator_kind):
    repo.deployment["classification"]["stakes"] = "medium"
    repo.write()
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_schema_missing_governance(repo, validator_kind):
    repo.deployment["roles"] = {"agent_team": ["@x"]}
    repo.write()
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_schema_unknown_item(repo, validator_kind):
    repo.record["items"]["B13"] = {"outcome": "pass"}
    repo.write()
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_schema_bad_date(repo, validator_kind):
    repo.set_item("B01", outcome="pass", lead="@bob", evidence=[{"link": "https://x", "date": "last week"}])
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_schema_manifest_value_and_path(repo, validator_kind):
    (repo.brace / "manifest.yaml").write_text("inputs:\n  - name: x\n    value: a\n    path: b\n")
    repo.deployment["agent_type_id"] = {"manifest": ".brace/manifest.yaml"}
    repo.write()
    code, _ = repo.check("--approvals", "off")
    assert code == 2


def test_bad_yaml(repo, capsys):
    (repo.brace / "record.yaml").write_text("items: [unclosed\n")
    code, _ = repo.check("--approvals", "off")
    assert code == 2
    assert "not valid YAML" in capsys.readouterr().err


def test_missing_record_folder(tmp_path):
    assert brace.main(["check", "--dir", str(tmp_path), "--approvals", "off"]) == 2


def test_usage_error():
    assert brace.main(["check", "--approvals", "maybe"]) == 2


def test_github_mode_needs_env(repo):
    repo.git_init()
    code, _ = repo.check("--approvals", "github")
    assert code == 2


# ---- git mode ------------------------------------------------------------

def test_git_mode_uncommitted_exception_blocks(repo):
    repo.git_init()
    repo.add("exceptions", f"{G2}-x", good_exception(G2))
    repo.set_item(G2, outcome="gap", lead="@bob", exception=f"{G2}-x")
    code, res = repo.check("--approvals", "git")
    assert code == 1
    assert "is not committed" in reasons(res)


def test_git_mode_committed_exception_unverified(repo):
    repo.git_init()
    repo.add("exceptions", f"{G2}-x", good_exception(G2))
    repo.set_item(G2, outcome="gap", lead="@bob", exception=f"{G2}-x")
    repo.commit_all("add exception")
    code, res = repo.check("--approvals", "git")
    assert code == 0, res["reasons"]
    assert any("approval not verified" in w for w in res["warnings"])
    code, _ = repo.check("--approvals", "git", "--strict")
    assert code == 1


# ---- templates -----------------------------------------------------------

def test_init_and_template_check(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert brace.main(["init", "--dir", str(tmp_path)]) == 0
    assert brace.main(["init", "--dir", str(tmp_path)]) == 2  # refuses to overwrite
    record = yaml.safe_load((tmp_path / ".brace" / "record.yaml").read_text())
    assert len(record["items"]) == 53
    assert all(v["outcome"] == "not_reviewed" for v in record["items"].values())
    assert record["items"]["B05"]["lead"] == "TODO (agent_team)"
    # A fresh template is valid input and a NO-GO, not an error.
    assert brace.main(["check", "--dir", str(tmp_path), "--approvals", "off"]) == 1


def test_items_command(capsys):
    assert brace.main(["items", "--json"]) == 0
    import json
    items = json.loads(capsys.readouterr().out)
    assert len(items) == 53 == len(ITEMS)
    assert sum(i["top3"] for i in items) == 15


def test_generated_files_up_to_date():
    import gen_items
    assert gen_items.main(["--check"]) == 0
