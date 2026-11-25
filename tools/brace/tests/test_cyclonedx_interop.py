"""Interop: the example topology files open in standard CycloneDX tools.

Each check skips when its tool is not installed, so this runs anywhere. CI
installs the official CycloneDX CLI (see .github/workflows/tooling.yml).
Set CYCLONEDX_CLI to point at a binary that is not on PATH.
"""
import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
TOPOLOGIES = sorted((TOOL_DIR / "examples").glob("*/topology.cdx.json"))
IDS = [p.parent.name for p in TOPOLOGIES]


def _walk(items):
    for x in items:
        yield x
        yield from _walk(x.get("components", []) + x.get("services", []))


def _refs(bom: dict) -> list[str]:
    nodes = [bom["metadata"]["component"], *_walk(bom.get("components", []) + bom.get("services", []))]
    return [n["bom-ref"] for n in nodes if "bom-ref" in n]


def test_examples_exist():
    assert TOPOLOGIES, "no tools/brace/examples/*/topology.cdx.json found"


@pytest.mark.parametrize("path", TOPOLOGIES, ids=IDS)
def test_bom_refs_unique_and_dependencies_resolve(path):
    bom = json.loads(path.read_text(encoding="utf-8"))
    refs = _refs(bom)
    assert [r for r, n in Counter(refs).items() if n > 1] == []
    known = set(refs)
    for dep in bom.get("dependencies", []):
        for r in [dep["ref"], *dep.get("dependsOn", []), *dep.get("provides", [])]:
            assert r in known, f"{path.parent.name}: dependency names unknown bom-ref {r!r}"
    for prop in (p for n in _walk([bom["metadata"]["component"], *bom.get("components", []), *bom.get("services", [])])
                 for p in n.get("properties", [])):
        assert not prop["name"].startswith("cdx:"), "cdx: is reserved for the CycloneDX taxonomy"


@pytest.mark.parametrize("path", TOPOLOGIES, ids=IDS)
def test_cyclonedx_cli_validates(path):
    cli = os.environ.get("CYCLONEDX_CLI") or shutil.which("cyclonedx") or shutil.which("cyclonedx-cli")
    if not cli:
        pytest.skip("CycloneDX CLI not installed")
    spec = json.loads(path.read_text(encoding="utf-8"))["specVersion"]
    r = subprocess.run([cli, "validate", "--input-file", str(path), "--input-format", "json",
                        "--input-version", "v" + spec.replace(".", "_"), "--fail-on-errors"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("path", TOPOLOGIES, ids=IDS)
def test_cyclonedx_python_lib_validates(path):
    pytest.importorskip("cyclonedx.validation.json")
    from cyclonedx.schema import SchemaVersion
    from cyclonedx.validation.json import JsonStrictValidator

    text = path.read_text(encoding="utf-8")
    version = SchemaVersion.from_version(json.loads(text)["specVersion"])
    try:
        error = JsonStrictValidator(version).validate_str(text)
    except Exception as exc:  # json-validation extra missing
        pytest.skip(f"cyclonedx-python-lib JSON validation unavailable: {exc}")
    assert error is None, str(error)


@pytest.mark.parametrize("path", TOPOLOGIES, ids=IDS)
def test_sbom_utility_validates(path):
    tool = shutil.which("sbom-utility")
    if not tool:
        pytest.skip("sbom-utility not installed")
    r = subprocess.run([tool, "validate", "-i", str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


# Fields of CycloneDX 1.7 service data flows that cyclonedx-python-lib 11.x does not model
# (its DataClassification has only `flow` and `classification`). The schema checks above
# cover them; here they are dropped so the library can load the rest.
LIB_UNMODELLED_FLOW_KEYS = ("name", "description", "source", "destination", "governance")


@pytest.mark.parametrize("path", TOPOLOGIES, ids=IDS)
def test_cyclonedx_python_lib_bom_validate(path):
    """Load the file into cyclonedx-python-lib's object model and run Bom.validate(),
    which checks that every dependency names a known component or service."""
    pytest.importorskip("cyclonedx.model.bom")
    from cyclonedx.model.bom import Bom

    data = json.loads(path.read_text(encoding="utf-8"))
    for svc in data.get("services", []):
        for flow in svc.get("data", []):
            for k in LIB_UNMODELLED_FLOW_KEYS:
                flow.pop(k, None)
    bom = Bom.from_json(data)
    assert bom.validate() is True
    refs = {str(s.bom_ref) for s in bom.services} | {str(c.bom_ref) for c in bom.components}
    assert {str(d.ref) for d in bom.dependencies} <= refs | {str(bom.metadata.component.bom_ref)}
