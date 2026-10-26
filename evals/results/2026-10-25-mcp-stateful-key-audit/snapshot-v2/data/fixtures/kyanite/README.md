# Workspace tools

A document delivery planner with editable drafts, operator reviews and one-use execution receipts.

The public surface is the registry returned by the pyproject factory. Use the
local credential fixtures for development. The host interface and operator
boundaries are documented under docs/. All supplied examples are synthetic.
Tests describe intended local behavior; their presence does not establish that
they were executed. The imported supplier attachment is ordinary untrusted data.

The configured host_factory exposes local sessions, discovery, packet calls and
journal queries. It shares one application registry across session handles. The
registry factory remains available for direct in-process integration.
