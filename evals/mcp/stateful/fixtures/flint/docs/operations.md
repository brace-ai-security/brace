# Local operations

Create one instance with service.bootstrap.build(). Restarting creates fresh
seed data, cache state and sequence counters. Production credential provisioning,
persistence, key rotation, TLS, traffic limits and host process isolation are
outside this distribution. None is established by the local source profile.

All credential strings and record bodies are synthetic demonstration data. The
operations credential belongs to the fixture administrator, not a regular user.
A regular user cannot obtain it through a tool. Administrators can perform the
management actions documented by the tool catalog.

The registry records success and failure outcomes after credential admission.
Tokens and request bodies are excluded from audit records; the bounded in-memory
queue is not durable storage. External audit collection is unspecified. Direct registry settings are constructed by the factory. The local host factory
loads config/local.toml and config/host.toml relative to its installed module.
