# Example: topology report for travel-agent

**Illustrative only.** A small, made-up travel agent. The findings were written by
hand to show the report. They are not the output of a review run.

What it shows:

- an **undeclared** service: `book_flight` sends traveler names and emails to a
  marketing analytics service that no setting lists (`src/tools/flights.py:17`);
- an **undeclared** connection: the itinerary writer sub-agent can call `book_flight`;
- a **declared only** tool and service: `convert_currency` and the exchange-rate API
  are in the settings, but no code uses them;
- an MCP server (`travel-docs`) with its own outside API;
- a data store, trust zones, and an unknown zone;
- findings for all three gates, each with the role that usually leads the fix.

| File | What it is |
|---|---|
| `repo/` | The fictional agent's code and settings (`config/agent.yaml`, `.mcp.json`). |
| `brace-topology.overlay.json` | Parts and connections traced in the code, each with `path:line` and a quote. |
| `sample-findings.json` | Eight findings with parts, fix steps and a lead role. No people are named. |
| `topology.cdx.json` | The CycloneDX 1.7 map. |
| `topology-report.html` | The web page. Open it in a browser. |

To regenerate (the tests check these files are current), from this folder:

```sh
python ../../../../skills/brace-review/scripts/review_coverage.py inventory repo
python ../../topology.py build repo -o topology.cdx.json --agent-config repo/config/agent.yaml \
    --overlay brace-topology.overlay.json
python ../../topology.py report topology.cdx.json --findings sample-findings.json -o topology-report.html
```
