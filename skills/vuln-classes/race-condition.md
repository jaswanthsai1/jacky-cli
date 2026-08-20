# Race Conditions

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Any endpoint enforcing a limit (redeem-once coupon, single withdrawal, one-time invite, vote-once) is a candidate. Send the same request concurrently and check whether the limit is bypassed.

## How to escalate

Use single-packet-attack techniques to eliminate network jitter and win narrow races reliably; escalate a single bypassed limit into a repeatable exploit (double-spend, quota abuse, privilege duplication).

## Common tools

Burp's Turbo Intruder (single-packet attack), `race-the-web`, custom async scripts (httpx/asyncio) for last-byte-sync racing.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
