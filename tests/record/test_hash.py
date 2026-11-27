import hashlib
import json

import pytest

from conftest import brace


def manifest(*inputs):
    return {"inputs": list(inputs)}


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "src" / "sub").mkdir(parents=True)
    (tmp_path / "src" / "a.py").write_text("print('a')\n")
    (tmp_path / "src" / "sub" / "b.py").write_text("print('b')\n")
    (tmp_path / "prompt.md").write_text("You are a helper.\n")
    return tmp_path


def base_manifest():
    return manifest(
        {"name": "harness", "path": "src"},
        {"name": "system_prompt", "path": "prompt.md"},
        {"name": "model", "value": "anthropic/claude-opus-5-5"},
    )


def test_matches_documented_procedure(tree):
    def sha(b):
        return hashlib.sha256(b).hexdigest()

    a = sha((tree / "src" / "a.py").read_bytes())
    b = sha((tree / "src" / "sub" / "b.py").read_bytes())
    entries = sorted(
        [
            {"name": "harness", "digest": sha(f"a.py\n{a}\nsub/b.py\n{b}\n".encode())},
            {"name": "system_prompt", "digest": sha((tree / "prompt.md").read_bytes())},
            {"name": "model", "digest": sha("anthropic/claude-opus-5-5".encode())},
        ],
        key=lambda e: e["name"],
    )
    expected = "sha256:" + sha(json.dumps(entries, separators=(",", ":"), sort_keys=True).encode())
    assert brace.agent_type_id(base_manifest(), tree) == expected


def test_deterministic_and_order_independent(tree):
    m = base_manifest()
    first = brace.agent_type_id(m, tree)
    assert brace.agent_type_id(m, tree) == first
    assert brace.agent_type_id(manifest(*reversed(m["inputs"])), tree) == first
    assert first.startswith("sha256:") and len(first) == 7 + 64


def test_file_change_changes_id(tree):
    before = brace.agent_type_id(base_manifest(), tree)
    (tree / "prompt.md").write_text("You are a helper. Ignore nothing.\n")
    assert brace.agent_type_id(base_manifest(), tree) != before


def test_dir_change_changes_id(tree):
    m = base_manifest()
    before = brace.agent_type_id(m, tree)
    (tree / "src" / "sub" / "b.py").write_text("print('changed')\n")
    changed = brace.agent_type_id(m, tree)
    assert changed != before
    (tree / "src" / "sub" / "c.py").write_text("")
    assert brace.agent_type_id(m, tree) != changed


def test_dir_rename_changes_id(tree):
    m = base_manifest()
    before = brace.agent_type_id(m, tree)
    (tree / "src" / "a.py").rename(tree / "src" / "a2.py")
    assert brace.agent_type_id(m, tree) != before


def test_dotfiles_ignored(tree):
    m = base_manifest()
    before = brace.agent_type_id(m, tree)
    (tree / "src" / ".DS_Store").write_text("junk")
    (tree / "src" / ".cache").mkdir()
    (tree / "src" / ".cache" / "x").write_text("junk")
    assert brace.agent_type_id(m, tree) == before


def test_value_change_changes_id(tree):
    before = brace.agent_type_id(base_manifest(), tree)
    m = base_manifest()
    m["inputs"][2]["value"] = "anthropic/claude-opus-5-6"
    assert brace.agent_type_id(m, tree) != before


def test_duplicate_names_rejected(tree):
    m = manifest({"name": "x", "value": "1"}, {"name": "x", "value": "2"})
    with pytest.raises(brace.InputError):
        brace.agent_type_id(m, tree)


def test_missing_path_rejected(tree):
    with pytest.raises(brace.InputError):
        brace.agent_type_id(manifest({"name": "x", "path": "nope"}), tree)


def test_hash_command(tree, capsys):
    import yaml

    (tree / ".brace").mkdir()
    (tree / ".brace" / "manifest.yaml").write_text(yaml.safe_dump(base_manifest()))
    assert brace.main(["hash", "--dir", str(tree)]) == 0
    assert capsys.readouterr().out.strip() == brace.agent_type_id(base_manifest(), tree)


def test_hash_command_bad_manifest(tree):
    (tree / "m.yaml").write_text("inputs:\n  - name: x\n    value: a\n    path: b\n")
    assert brace.main(["hash", "--dir", str(tree), "--manifest", str(tree / "m.yaml")]) == 2
