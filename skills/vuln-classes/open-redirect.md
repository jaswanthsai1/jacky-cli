# Open Redirect

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Any parameter that triggers a server-side or client-side redirect (`?next=`, `?return_url=`, `?redirect=`) is a candidate. Test absolute URLs, protocol-relative URLs (`//evil.com`), and encoding tricks against the allowlist/validation logic.

## How to escalate

Standalone impact is usually low (Informative/Low) unless chained: use it to bypass OAuth `redirect_uri` allowlists, defeat SameSite cookie protections, or make phishing links appear to originate from the trusted domain.

## Common tools

Manual parameter fuzzing, `Burp` with a custom redirect payload list, checking both server-side (3xx) and client-side (`window.location`) redirect sinks.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
