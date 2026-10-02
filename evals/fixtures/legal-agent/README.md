# Counsel Research Assistant

Internal legal-research assistant for Harrowell & Price LLP. A lawyer opens a session on a
client matter, asks a research question, and receives a draft memo with pinpoint citations to
documents in the firm's document index. Drafts can be emailed to the requesting lawyer.

## Components

| Component | What it does |
|---|---|
| `src/app.py` | FastAPI service: sessions, research runs, approvals, preferences |
| `graph/research_graph.py` | Orchestration: plan, retrieve, rerank, draft, cite-check, deliver |
| `src/retrieval.py` | Vector search over the matter document index (Qdrant) |
| `src/memory.py` | Per-lawyer long-term memory: preferences and past research |
| `src/judge.py` | Citation judge: confirms every cited passage supports the memo |
| `src/model_loader.py` | Loads the self-hosted fine-tuned drafting model into vLLM |
| `src/tools.py` | Tool registry exposed to the drafting model |
| `src/mailer.py` | Renders memos and sends them through the firm SMTP relay |

## Models

| Role | Source | Record |
|---|---|---|
| Drafting | Self-hosted, Llama 3.1 70B + firm LoRA adapter | `models/legal-ft/manifest.json` |
| Reranker | Hosted (Cohere Rerank) | `models/reranker.yaml` |
| Citation judge | Self-hosted vLLM | `models/judge.yaml` |
| Embeddings | Self-hosted bge-large | `config/settings.yaml` |

## Matters and ethical walls

Every matter is a tenant. A lawyer can open a session only on a matter they are staffed on and
not screened from. The matter registry and wall list are owned by Conflicts & Intake and are read
from the conflicts service; this service never writes to them.

## Owners

- Accountable party: Office of the General Counsel (risk@harrowellprice.com)
- Operational owner: Legal Engineering on-call (`#legal-eng-oncall`)
