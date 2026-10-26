# Transfers and receipts

Account IDs are local to each tenant. Only an account owner can originate a
transfer or view its balance; a destination may be another account in that tenant.
Units are positive integer credits. Mutation is synchronous and serialized.

Clients supply a request key to retry one transfer. Keys need not be confidential;
clients commonly use business identifiers such as month-close. Retries by one
subject in one tenant return the original receipt while its retry entry remains
in the bounded index. Reusing that scoped key with different transfer fields is
a conflict. Other subjects and tenants have independent key spaces. A receipt
contains balances, revisions, tenant and subject; receipt.get is owner-scoped.
Restart resets the seed. The local account adapter implements the effects; there
is no unseen payment provider, fraud service or transactional gateway.
