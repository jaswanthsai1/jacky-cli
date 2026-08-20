# CORS Misconfiguration

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Send requests with an arbitrary `Origin` header and check whether `Access-Control-Allow-Origin` reflects it (especially combined with `Access-Control-Allow-Credentials: true`). Check for regex-based origin allowlists that can be bypassed with a crafted subdomain or suffix match.

## How to escalate

A reflected origin + credentials=true on an authenticated endpoint means any attacker-controlled page can read the victim's authenticated API responses — chain into full account data exfiltration via a hosted PoC page.

## Common tools

Burp's CORS scanner extension, manual `curl -H 'Origin: https://attacker.test'` testing, browser PoC pages for confirmation.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
