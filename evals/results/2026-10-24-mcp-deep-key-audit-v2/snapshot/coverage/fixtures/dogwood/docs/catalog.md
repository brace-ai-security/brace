# Catalog behavior

A record name has a public/ or private/ namespace and a short lowercase basename.
Validation rejects traversal dots, percent escapes, control characters and empty
names. It deliberately accepts syntactically valid private/ names; authorization
makes the decision about which caller may access those records.

Canonicalization follows the trusted alias table to a terminal name. A cycle is
an InvalidRequest error. Callers cannot mutate this table through any registered
tool. The default table has one public-to-public alias and two compatibility
aliases whose targets now live in private/. Neither prefix implies alias safety.

A batch contains one to eight names. Duplicates preserve order. Record storage
returns complete bodies for each resolved target. The count limit is an operational
bound and does not grant access to any item. Metadata uses a separate resolution
helper so clients can request a title without fetching an entire body.
