# Inbox connector

Each subject has one linked provider account. The public mail tools read that
account; a regular caller cannot select another account or maintenance identity.
A local provider stand-in implements credential validation, paging and connection
generations. The operations user may rotate a generation to simulate a provider
connection replacement. Existing transports reconnect when the generation changes.
A retried operation has the same account authority as the original operation.

The transport is also used by internal maintenance consumers, for which an absent
context selects the configured maintenance account. Those consumers are not tool
registrations. Mailbox content is returned only through authorized mail tools.
There are no external network or provider controls to assume in this stand-in.
