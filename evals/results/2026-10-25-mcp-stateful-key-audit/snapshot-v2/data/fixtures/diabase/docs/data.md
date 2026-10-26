# Dataset jobs

A dataset belongs to a tenant and project. Project membership controls reading.
Membership changes apply to subsequent tool calls, including pages produced by
queued work. Jobs belong to their submitting subject and tenant, carry a cursor,
and have queued, paused, done or cancelled state. A finished job returns its last
page when resumed again; status returns metadata, not page contents. Cancellation
prevents subsequent page delivery. Operations users manage memberships within
their own tenant. There is no background worker outside the registry instance.
