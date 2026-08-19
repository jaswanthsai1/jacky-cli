---
name: jacky-doctrine
description: "The Jacky hunt-loop doctrine — a full offensive-security / bug-bounty methodology for autonomous agents. Covers the eight-stage hunt loop (scope, recon, rank, enumerate, test, validate, chain, report), parallel workstream execution, a living facts/negatives ledger, persistence when blocked, and self-evolution of skills from what you learn. Use this at the start of any authorized security engagement, when deciding what to do next, or when you feel stuck."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  jacky:
    tags: [methodology, doctrine, pentest, bug-bounty, offensive-security, agentic-workflow]
    related_skills: [bb-methodology, redteam-mindset, triage-validation, recon-scope-triage, report-writing, evidence-hygiene]
---

# The Jacky Hunt-Loop Doctrine

A reusable methodology for running a security engagement (bug bounty, authorized
pentest, or red team) end-to-end with an AI agent doing the work. It exists
because ad-hoc tool-firing produces weak coverage and duplicate effort. The
doctrine turns hunting into an explicit, resumable state machine instead of a
vibe.

**This is a methodology, not a specific tool.** It tells the agent (or the
human directing it) *how to think* through an engagement. It intentionally
does not assume any particular scanner, proxy, or platform — plug in whatever
tools you have.

## The eight-stage loop

```
scope → recon → rank → enumerate → test → validate → chain → report
```

1. **Scope** — Read the program/engagement rules before touching anything.
   Note what's in scope, what's excluded, rate limits, and any prohibited
   techniques (no destructive testing, no social engineering, no third-party
   assets unless explicitly authorized). When in doubt, it's out of scope.
2. **Recon** — Map the attack surface: subdomains, endpoints, technologies,
   exposed repos/buckets, JS bundles, API schemas. Cast wide before going
   deep. Prefer passive/low-noise recon first, active scanning second.
3. **Rank** — Don't test everything with equal priority. Score discovered
   surface by predicted exploitability: novelty × impact × reachability.
   Work the highest-expected-value target first, but keep a queue — don't
   fixate on one item to the exclusion of everything else.
4. **Enumerate** — For the top-ranked surface, enumerate everything relevant
   to it: parameters, auth states, roles, API versions, content types. This
   is where you build the hypothesis list for the test stage.
5. **Test** — Try the class of vulnerability that's the best hypothesis fit.
   One class at a time, methodically, with a specific technique in mind —
   not "throw every payload and see what sticks."
6. **Validate** — Run every candidate finding through a validation gate
   before you believe it (see `triage-validation` in this bundle for the
   full 7-question gate). Reproducible, in-scope, demonstrable business
   impact, independent of other unfixed bugs. A finding is a *lead* until
   it passes validation.
7. **Chain** — Before reporting, ask whether this finding combines with
   another lead into something higher-impact. A LOW + LOW can be a HIGH.
   SSRF often reaches cloud metadata; open redirect often reaches OAuth
   account takeover; IDOR often reaches mass-tenant exposure. Always spend
   a few minutes looking for the escalation before you write the report.
8. **Report** — Impact-first, reproducible, minimal PoC (see `report-writing`
   in this bundle). Then close the loop: record what worked and what didn't,
   so the next engagement starts smarter.

## Operating principles

**Work in parallel, not in a single-file queue.** Independent workstreams
(recon, a focused test on a ranked target, a background scan) can run
concurrently. Don't finish one class of test before starting to think about
the next — probe broadly, then go deep on what responds.

**Maintain a living ledger.** Keep a running record, per engagement, of:
confirmed facts, confirmed findings, and — just as important — *negative
results* (things you tried that didn't work). Never repeat a test you've
already run and ruled out. Feed the ledger into every decision about what to
try next. This is what makes an engagement resumable across sessions instead
of starting from zero every time.

**Persistence over premature surrender.** A task is not done until it's
proven done, one way or the other. If you hit a blocker:
- Try alternate encodings, ports, HTTP verbs, roles, or content types
- Re-enumerate — you may have missed something the first pass
- Switch to a different attack class and come back later with new context
- If a tool/technique fails, ask "what else do I have that could get past
  this?" before concluding it's a dead end

Never stop at the first wall, but also never confuse persistence with
scope creep — stay inside what's authorized.

**Validate before you believe it, chain before you report it.** These are
the two most common ways hunters lose credibility or leave value on the
table: reporting unproven "could potentially" findings, and reporting a low
severity issue standalone when it was one step from a chain into something
serious.

**Preserve negatives, they're as valuable as positives.** A documented "I
tried X against Y, it didn't work, here's why" saves the next session (or
the next hunter, if this is a team engagement) from repeating dead-end work.

**Evolve.** When an engagement teaches you something reusable — a technique,
a chain pattern, a class-specific check that worked — write it down as a
new skill or an addition to an existing one. The methodology should get
sharper with every engagement, not reset every time.

## How the bundled skills map onto the loop

| Stage | Skill in this bundle |
|---|---|
| Start-of-engagement orchestration, "what do I do next" | `bb-methodology` |
| Mindset corrections for authorized red-team engagements (vs. bug bounty) | `redteam-mindset` |
| Recon output triage — separating real assets from namespace-collision noise | `recon-scope-triage` |
| Deciding whether a candidate finding is real and reportable | `triage-validation` |
| Screenshot/HAR/PoC redaction discipline before submitting evidence | `evidence-hygiene` |
| Writing the actual report | `report-writing` |

See `docs/METHODOLOGY.md` for the full picture, including how
this doctrine relates to Jacky's other agentic capabilities (skills that
self-improve, persistent memory, subagents).

## See also

- `references/when-blocked.md` — the tools-first checklist for CAPTCHAs,
  rate limits, WAF challenges, session-bound anti-bot protections, and MFA
  prompts, plus the general persistence discipline.
- `references/multi-lead-probing.md` — testing multiple attack leads in
  parallel, inferring endpoint existence from response-code/header
  differences, and exploiting anomalous backend behavior instead of
  shrugging at it.

## Discipline

Authorized scope only. No destructive testing, no persistence mechanisms, no
credential attacks against real accounts, no social engineering, and no
testing of third-party systems unless the authorization explicitly covers
them. A finding is a lead until independently validated. When collaborating
with other agents or humans on the same engagement, coordinate instead of
silently duplicating or overriding each other's work.
