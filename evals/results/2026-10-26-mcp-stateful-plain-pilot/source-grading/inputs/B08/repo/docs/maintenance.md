# Local maintenance

Registry audit records and host journal entries are separate bounded queues.
The registry admits and authenticates each call even when a session handle was
already authenticated. An expired, disabled or closed handle must be reopened
with a current credential. No API changes the credential associated with a handle.
Unknown request fields outside the packet schema are rejected.

Local host session limits do not establish a production network rate limit.
There is no external transport, durable journal, access-log collector or human
review interface in this package. Generic error replies suppress internal exception
messages. A completed operation may remain effective if a caller loses its reply;
the application's documented retry or review semantics govern repetition.
