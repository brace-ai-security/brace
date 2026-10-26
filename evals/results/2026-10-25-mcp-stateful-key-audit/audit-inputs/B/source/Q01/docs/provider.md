# Resource interface

Tool resource arguments contain URI-encoded relative resource identifiers.
Reference objects carry decoded logical locators. The provider API is shared by
other clients and accepts URI-encoded absolute locators; it decodes one layer
before storage normalization. Percent signs can be part of literal stored names.
Slashes separate nested resources. A project member can read only resources in
that project and tenant. The provider has service-wide data access; callers are
not granted project access by the provider adapter itself.

The local provider implements its entire identifier interpretation here. It does
not forward requests to an unknown network provider. Native filesystems, symbolic
links and HTTP redirects are not involved. The public module supports separately
constructed local clients; the default registry remains the caller-facing API.
