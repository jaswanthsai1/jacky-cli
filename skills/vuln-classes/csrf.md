# CSRF (Cross-Site Request Forgery)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Identify state-changing requests (POST/PUT/DELETE) and check whether they're protected by a per-session anti-CSRF token, SameSite cookies, or origin/referrer validation. Test whether the token is actually validated server-side or just present.

## How to escalate

Chain with XSS or an open redirect to bypass SameSite restrictions, or find a JSON endpoint that accepts `Content-Type: text/plain` (avoiding CORS preflight) to enable a cross-origin form-based attack.

## Common tools

Burp CSRF PoC generator, manual HTML PoC pages, checking `SameSite`/`Origin`/`Referer` handling by hand.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
