# Document model

Documents belong to one tenant and project. Members can read a project with a
read credential and edit its titles with a write credential. Credential scopes
remain a bound on delegated operations even for another token of the same user.
The operations user manages memberships within its own tenant. Membership
changes affect subsequent calls. Revisions use compare-and-swap; mismatched
revisions produce Conflict. Lists are scoped before pagination.
