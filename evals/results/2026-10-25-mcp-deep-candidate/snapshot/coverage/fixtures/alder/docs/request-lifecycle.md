# Request lifecycle and operational decisions

## Construction

The host calls the factory once per isolated workspace. The factory validates the
local Settings instance, constructs memory storage and an audit queue, and binds
route methods to the registry. The host must retain that returned registry for
changes and events to persist within its process. Creating a second registry
creates independent storage and handlers. A request cannot select a factory or
replace a handler through an argument field.

## Admission

Registry.invoke first verifies the argument container and named handler. It then
looks up the token in the synthetic session table and rejects an inactive identity.
The immutable identity is attached to Request. Extra argument properties are not
copied into the identity. A request ID is useful for correlating successful events
but is not interpreted as a role, tenant, permission, grant, or resource name.
An authenticated request is still subject to the route's resource policy.

## Planning and data

Route helpers validate selectors before a storage call. A syntactically valid
selector can still designate data the caller is forbidden to receive. Internal
plans and jobs carry the selected resource to the final dispatch helper; dispatch
returns complete record data, not an automatically redacted representation.
Consequently, admission, validation and operation selection are separate decisions.
A host should preserve the service's typed refusal rather than retrying a failed
operation under an owner token. No such retry exists in the supplied dispatcher.

## Completion

Successful record responses are materialized in memory. Audit recording follows
successful dispatch. An exception prevents the success event from being appended;
this lightweight queue is therefore not a complete ledger of denied attempts.
The queue records no payload body and is not consulted for authorization decisions.
The response limit is a construction-time sanity bound, while batch size checking
occurs at the argument boundary. Neither is a substitute for record permissions.

## Scope of this source bundle

The TOML files document the shipped local profile. They are not hot-reloaded and
cannot change handler registration. The Python Settings object is the executable
source of defaults. No deployment manifest or installed host plugin is provided.
The behavior of a future network host, tenant federation, storage persistence or
credential rotation is unknown. Reviewers should distinguish those unknowns from
concrete paths implemented in this source tree. Synthetic fixtures should never be
used as live credentials or treated as a production identity provisioning system.
