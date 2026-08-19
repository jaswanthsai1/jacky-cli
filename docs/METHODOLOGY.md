# The Jacky Hunt-Loop Methodology

Jacky CLI ships with a bundled offensive-security methodology, not just a
generic chat wrapper. This document is the map of that methodology and how
the skills under [`skills/`](skills/) implement it.

If you only read one file to understand the hunting side of this project,
read [`skills/jacky-doctrine/SKILL.md`](skills/jacky-doctrine/SKILL.md) —
this page is the summary and index.

## Why a methodology, and not just tools

An agent with tool access but no methodology tends to fire tools ad hoc:
duplicate effort, unranked targets, findings reported before they're
validated, low-severity bugs reported standalone when they were one step
from a serious chain. The doctrine turns a hunt into an explicit, resumable
process instead of a vibe.

## The eight-stage loop

```
scope → recon → rank → enumerate → test → validate → chain → report
```

| Stage | What happens | Bundled skill |
|---|---|---|
| **Scope** | Read the rules before touching anything: in-scope assets, exclusions, rate limits, prohibited techniques. | `jacky-doctrine`, `redteam-mindset` |
| **Recon** | Map the attack surface — subdomains, endpoints, tech stack, exposed repos/buckets, JS bundles, API schemas. | `jacky-doctrine`, `recon-scope-triage` |
| **Rank** | Score discovered surface by predicted exploitability (novelty × impact × reachability); work highest-EV first. | `jacky-doctrine`, `bb-methodology` |
| **Enumerate** | For the top-ranked target, enumerate parameters, auth states, roles, versions — build the hypothesis list. | `bb-methodology` |
| **Test** | Test one vulnerability class at a time with a specific technique, not blind payload spraying. | `jacky-doctrine` (see `references/multi-lead-probing.md`) |
| **Validate** | Run every candidate finding through a validation gate before believing it. | `triage-validation` |
| **Chain** | Look for how this finding combines with another lead into higher impact before reporting it standalone. | `jacky-doctrine`, `triage-validation` |
| **Report** | Impact-first, reproducible, minimal PoC; redact evidence properly; then record what worked. | `report-writing`, `evidence-hygiene` |

## Bundled skills

All of these live under [`skills/`](skills/) and are generalized,
reusable methodology — not tied to any specific engagement or target:

- **`jacky-doctrine`** — the flagship skill. The full hunt-loop doctrine,
  operating principles (parallel workstreams, a living facts/negatives
  ledger, persistence discipline, self-evolution), and two technique
  references (`when-blocked.md`, `multi-lead-probing.md`).
- **`bb-methodology`** — start-of-engagement orchestration: the non-linear
  hunting workflow plus a critical-thinking framework (developer
  psychology, anomaly detection, "what-if" experiments) for deciding what
  to do next at any point in an engagement.
- **`redteam-mindset`** — mindset corrections specific to authorized
  red-team engagements as opposed to bug-bounty/WAPT work, where
  conservative defaults tend to cause missed findings.
- **`recon-scope-triage`** — separating a target's real assets from
  namespace-collision noise in automated recon output, especially for
  brand names that collide with unrelated companies/repos/apps.
- **`triage-validation`** — the finding-validation gate: seven questions
  every candidate finding must pass before you believe it's reportable,
  plus a CVSS 3.1 quick reference and severity decision guide.
- **`evidence-hygiene`** — redaction discipline for screenshots, HAR
  files, and PoCs before they're attached to a report (cookies, PII,
  session tokens).
- **`report-writing`** — templates, tone guidelines, and formulas for
  writing an impact-first report that a triager will actually read and
  act on.
- **`vuln-classes`** — one short reference file per major vulnerability
  class (SSRF, IDOR, XSS, SQLi, SSTI, XXE, CSRF, auth bypass, business
  logic, race conditions, CORS, subdomain takeover, JWT/OAuth, open
  redirect, file upload, GraphQL, API misconfig, cloud/K8s misconfig)
  with a generic detect / escalate / tools structure — see
  [`skills/vuln-classes/README.md`](../skills/vuln-classes/README.md).

## How this fits the rest of Jacky CLI

The methodology is designed to run on top of Jacky's general agentic
capabilities:

- **Self-improving skills** — when an engagement teaches you a reusable
  technique, write it into a new skill (or extend an existing one) the
  same way these were written. Jacky's skill system is built for exactly
  this loop.
- **Persistent memory / cross-session state** — the "living ledger"
  principle in `jacky-doctrine` (never repeat a tried attack, preserve
  negatives) depends on state surviving across sessions. Use Jacky's
  memory and session features to keep a per-engagement ledger instead of
  starting from zero every time.
- **Subagents / parallel workstreams** — the doctrine's "work in parallel,
  not a single-file queue" principle maps directly onto Jacky's ability to
  spawn isolated subagents for independent recon/test workstreams.
- **Dual local + cloud model support** — run the methodology with a local
  model for offline/low-cost work, or a stronger cloud model for the parts
  of an engagement that need more reasoning depth. See the README for
  provider setup.

## Scope and ethics

Everything here assumes **authorized** testing: a bug-bounty program, a
contracted pentest, or your own infrastructure. Nothing in this bundle
grants permission to test systems you don't have authorization to test. A
finding is a lead until independently validated, and persistence never
overrides scope.
