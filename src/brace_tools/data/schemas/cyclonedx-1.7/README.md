# CycloneDX 1.7 JSON schemas (vendored)

Unmodified copies of the official CycloneDX 1.7 JSON schemas, retrieved
2026-11-21 from
`https://raw.githubusercontent.com/CycloneDX/specification/master/schema/`.
They are licensed under the Apache License 2.0 (see `LICENSE`, copied from the
same repository).

| File | Purpose |
|---|---|
| `bom-1.7.schema.json` | CycloneDX 1.7 BOM schema (draft-07) |
| `spdx.schema.json` | SPDX license identifiers referenced by the BOM schema |
| `jsf-0.82.schema.json` | JSON Signature Format referenced by the BOM schema |
| `cryptography-defs.schema.json` | Cryptography definitions referenced by the BOM schema |

`brace map validate` resolves these references locally, without network access.
