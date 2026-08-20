# XXE (XML External Entity Injection)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Any endpoint that parses XML (SOAP APIs, file uploads accepting XML/SVG/DOCX, SAML assertions) is a candidate. Submit a DOCTYPE with an external entity referencing a local file or an out-of-band URL.

## How to escalate

Escalate from local file read to SSRF (entity fetching an internal URL) or blind exfiltration via out-of-band XXE when direct responses aren't reflected. Check for XInclude and parameter-entity variants if the classic DOCTYPE payload is filtered.

## Common tools

Burp's XXE payloads, `interactsh`/Burp Collaborator for blind/OOB confirmation, manual DTD crafting.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
