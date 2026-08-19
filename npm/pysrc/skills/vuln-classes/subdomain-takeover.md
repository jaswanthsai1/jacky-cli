# Subdomain Takeover

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Enumerate all subdomains, resolve their CNAMEs, and check for CNAMEs pointing to third-party services (S3, Heroku, GitHub Pages, Azure, Netlify, etc.) with no corresponding claimed resource — the classic "NXDOMAIN" or "no such app" fingerprint.

## How to escalate

Claim the dangling resource to serve attacker-controlled content on the trusted domain, then use it for cookie theft (if the domain shares a parent with session cookies), phishing, or bypassing domain-based allowlists (CORS, CSP, OAuth redirect_uri).

## Common tools

subfinder/amass for enumeration, `dnsx` for CNAME resolution, `can-i-take-over-xyz` fingerprint list for service-specific takeover signatures.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
