# Example: security map and action plan for billing-agent

**Illustrative only.** `sample-findings.json` was written by hand from the known
gaps in [`evals/expected/billing-agent.yaml`](../../../../evals/expected/billing-agent.yaml)
to show the format. It is not the output of a review run and covers only 8 items.

| File | What it is |
|---|---|
| `brace-topology.overlay.json` | Parts and connections traced in the fixture's code, each with `path:line` and a quote. |
| `sample-findings.json` | Eight findings with `components`, and plain `fix` steps. |
| `topology.cdx.json` | The CycloneDX 1.7 map built from the fixture plus the overlay. |
| `action-plan.md` | The report people read: map, risky connections, action list, fix steps. |
| `actions.csv` | The action list for an issue tracker. |
| `action-plan.html` | The same plan as a web page with diagrams. |
| `topology-report.html` | Interactive map: declared vs found in code, with findings. |
| `action-plan.json` | The plan for CI (`brace-action-plan/1`). |
| `brace.sarif` | SARIF 2.1.0 for code scanning. |

To regenerate (the tests check these files are current):

```sh
tmp=$(mktemp -d) && cp -R evals/fixtures/billing-agent "$tmp/" && r="$tmp/billing-agent"
cp tools/brace/examples/billing-agent/brace-topology.overlay.json "$r/"
python skills/brace-review/scripts/review_coverage.py inventory "$r"
cd tools/brace/examples/billing-agent
python ../../topology.py build "$r" -o topology.cdx.json --agent-config "$r/config/agent.yaml"
python ../../action_plan.py sample-findings.json topology.cdx.json -o action-plan.md --csv actions.csv \
    --json action-plan.json --sarif brace.sarif --html action-plan.html --strict
python ../../topology.py report topology.cdx.json --findings sample-findings.json -o topology-report.html
```
