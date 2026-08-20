# SSRF (Server-Side Request Forgery)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Look for any server-side feature that fetches a user-supplied URL: webhooks, PDF/screenshot generators, URL preview/unfurl, image import by URL, SSO metadata/JWKS fetch, XML external entity paths, cloud-integration "import from URL" fields.

## How to escalate

Target cloud metadata endpoints (169.254.169.254 for AWS/GCP/Azure), internal admin panels, and localhost-bound services. Try DNS rebinding, redirect chains, alternate IP encodings (decimal/octal/IPv6), and protocol smuggling (`gopher://`, `file://`, `dict://`) where the fetcher allows them.

## Common tools

Burp Collaborator/interactsh for out-of-band confirmation, `ssrfmap`, `gopherus` for protocol smuggling, curl for manual encoding tests.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
