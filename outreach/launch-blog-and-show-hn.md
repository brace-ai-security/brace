# BRACE Launch Copy

> **Historical outreach draft — source review 2026-09-16:** Do not use its novelty, vendor-coverage, or incident-count claims as current evidence. See [SOURCE-REVIEW.md](../SOURCE-REVIEW.md), the [current checklist](../CHECKLIST.md), and [current telemetry proposal](../otel-conventions.md) before adapting this draft.

Three parts: a launch blog post, a Show HN post, and a suggested first comment.

---

## PART 1 — Blog Post

# Securing autonomous agents: you're securing the configuration, not the code

An autonomous agent takes actions without a human reviewing each one. That's the whole point — and it's also the whole problem. Once an agent can run a command, call an API, or write to a database on its own, a single bad decision lands before anyone can catch it.

This isn't hypothetical. A Replit deployment deleted a production database despite a stated code freeze. Google's Gemini CLI deleted a user's files after misreading a command. A poisoned pull request turned Amazon Q into a wiper ([CVE-2025-8217](https://www.cve.org/CVERecord?id=CVE-2025-8217)). Microsoft 365 Copilot leaked data through a prompt-injection chain that needed no user click at all — EchoLeak ([CVE-2025-32711](https://www.cve.org/CVERecord?id=CVE-2025-32711)). Different vendors, different failures, same shape: an agent acted, and there was no control standing between the action and the damage.

The field has mostly agreed on the diagnosis. The 2026 consensus is that no single framework is complete, and the missing piece isn't more threat taxonomy — it's concrete, agent-granular controls. People know what can go wrong. The gap is in what to actually build, and in what order. Call it the enforcement gap.

### The reframe

Here's the shift that makes the problem tractable. An autonomous agent is not the code that shipped. The model weights are fixed. What makes an agent an agent — and what makes it dangerous — is everything assembled around it at runtime: the container it runs in, the harness that drives it, the system prompt, the tools it can call, the memory it carries, the identity it acts under, and the network it can reach.

That bundle is a configuration. It changes per deployment, often per session. So the thing you secure is the configuration, not the code. This is good news, because configurations are inspectable and gateable in ways that model behavior is not. You can interpose on a tool call. You can scope a token. You can sign off on a deployment.

### BRACE

BRACE is a checklist of nine controls plus three observability requirements, organized by where they sit in the agent's lifecycle. The name encodes the five concerns it covers: Build-time, Run-time, Agent, Configuration, Ecosystem.

The nine controls, by group:

- **Build-time** — what you fix before the agent runs: architecture, capability-scoped API access, the container, and the harness (including destructive-verb interception — catching `DROP`, `rm -rf`, force-push, and friends before they execute).
- **Run-time** — what governs the agent while it runs: data handling, memory, and behavioral limits.
- **Closure** — how you stop and account for it: a tested kill switch and an audit trail.

And three observability requirements, because you can't govern what you can't see:

- Six identity fields on every agent action (including a content-hashed agent-type-id, so you can tell which exact agent configuration acted).
- Context-size logging.
- Sub-agent and parent-prompt provenance, so a spawned agent's actions trace back to who asked.

That's twelve things. You don't ship them all at once.

### Start here

Two things to grab first.

The **sign-off checklist** covers all five BRACE aspects with 53 checks, operational challenges, fallbacks, and acceptable tradeoffs. A companion verification guide gives procedures and evidence for each item, and the self-assessment scores the same IDs. If you take nothing else, start there.

Then ship in tier order. **Tier 1** is the five controls that stop the incidents above:

1. Destructive-verb interception (C4)
2. Capability-scoped tokens (C2)
3. A tested kill switch (C8)
4. An audit trail (C9)
5. The six identity fields (T1)

Tier 1 is the floor. Everything else builds on it.

### Where BRACE sits

BRACE does not replace OWASP, NIST, or MITRE — it composes with them. Use the OWASP Top 10 for Agentic Applications and MITRE ATLAS to understand what can go wrong. Use the NIST AI RMF to frame governance. Then use BRACE to decide what to build and in what order. The taxonomies tell you the threats; BRACE is the controls layer underneath, where the enforcement actually happens.

### Honest about what this is

BRACE is a synthesis of agent-security practice already in production. It pulls together the public framework landscape and a corpus of 35+ real incidents into one ordered set of controls. It is not yet a validated standard. It's published under CC BY 4.0 so you can use it, adapt it, and argue with it.

What I want back: tell me where it's wrong. If you've shipped agents and a control here is impractical, I want to know. If you have an incident the corpus is missing, send it. If you've mapped BRACE onto a specific vendor stack, I'd like to publish that mapping. The point is to make the controls better, not to defend a brand.

The BRACE paper and the repo are linked below. Start with the checklist.

---

## PART 2 — Show HN Post

**Title:**

Show HN: BRACE – a controls layer for autonomous-agent security

**Body:**

BRACE is a checklist of nine controls plus three observability requirements for securing autonomous AI agents — the kind that take actions without a human reviewing each one. It's for engineers shipping agents who already know the threat taxonomies (OWASP, MITRE, NIST) but need to decide what to actually build, and in what order. The core idea: an agent is a runtime configuration (container, harness, prompt, tools, memory, identity), so you secure the configuration, not the code. Sign-off checklist, verification guide, and the full paper are in the repo: [checklist](https://github.com/PLACEHOLDER/brace) · [site](https://PLACEHOLDER.example).

---

## PART 3 — Suggested First Comment

Maintainer here. This is a synthesis of in-production agent-security practice, not a standard — built by reading across the public framework landscape (OWASP's agentic Top 10, MITRE ATLAS, NIST AI RMF) and working through a corpus of 35+ real agent incidents, then asking what concrete controls would have stopped each one. It's meant to compose with those frameworks, not replace them: they tell you what can go wrong, BRACE tells you what to build first. The part we think is genuinely new is the agent-granularity instrumentation — six identity fields per action, a content-hashed agent-type-id so you can pin down which exact agent configuration acted, context-size logging, and sub-agent/parent-prompt provenance so a spawned agent's actions trace back to who asked. Parts of this are surely wrong or impractical in production, so we'd genuinely value being told where — especially from anyone who's shipped autonomous agents at scale.
