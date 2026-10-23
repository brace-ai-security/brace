# Public MCP review fixtures

These synthetic source fixtures are published under the repository's
[CC BY 4.0 license](../../../LICENSE), like the BRACE skills and data. They are
review inputs, not runnable MCP servers. Do not install their configured packages
or use their example credentials. The only credential value is intentionally fake.

`harbor` and `keystone` cover HTTP gateways; `meadow` and `cobalt` cover local
stdio components. Each contains untrusted reviewer-directed text. Hidden grading
cases are kept separately in [../expected/](../expected/), never in the
reviewer's workspace. See the [protocol](../README.md) for scoring and limits.

Once published, these are known regression fixtures. Independent qualification
claims require fresh holdouts.
