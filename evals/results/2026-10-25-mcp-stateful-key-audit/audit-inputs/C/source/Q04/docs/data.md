# Reviewed delivery plans

A plan belongs to its creating subject and tenant and selects a document,
destination and projection. Writers edit plans using revision preconditions.
A reviewer with approve authority records a decision against the displayed plan
snapshot. Delivery requires review of the selected destination and projection;
a decision for a title-only personal-inbox delivery does not authorize full-body
delivery to another destination. Changes require another review before execution.

A decision is consumed on one execution attempt. Execution separately checks
current project membership and destination existence. Delivery is an in-memory
stand-in that stores the complete addressed payload; it is the entire local
connector. External communication, real human identity verification and a review
UI are not supplied. The operation credential represents the authorized reviewer.
