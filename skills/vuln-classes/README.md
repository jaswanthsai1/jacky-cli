# Vulnerability Class Reference

Short, generic "how to detect / how to escalate / common tools" notes for
major web/API/cloud vulnerability classes, meant to be read during the
**enumerate** and **test** stages of the [hunt-loop methodology](../../docs/METHODOLOGY.md).

These are reference checklists, not auto-exploit scripts — Jacky assists a
human hunter; it doesn't guarantee findings. Every candidate finding should
still pass the gate in [`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before being treated as confirmed.

| File | Class |
|---|---|
| [`ssrf.md`](ssrf.md) | Server-Side Request Forgery |
| [`idor.md`](idor.md) | Insecure Direct Object Reference |
| [`xss.md`](xss.md) | Cross-Site Scripting |
| [`sqli.md`](sqli.md) | SQL Injection |
| [`ssti.md`](ssti.md) | Server-Side Template Injection |
| [`xxe.md`](xxe.md) | XML External Entity Injection |
| [`csrf.md`](csrf.md) | Cross-Site Request Forgery |
| [`auth-bypass.md`](auth-bypass.md) | Authentication Bypass |
| [`business-logic.md`](business-logic.md) | Business Logic Flaws |
| [`race-condition.md`](race-condition.md) | Race Conditions |
| [`cors.md`](cors.md) | CORS Misconfiguration |
| [`subdomain-takeover.md`](subdomain-takeover.md) | Subdomain Takeover |
| [`jwt-oauth.md`](jwt-oauth.md) | JWT / OAuth Issues |
| [`open-redirect.md`](open-redirect.md) | Open Redirect |
| [`file-upload.md`](file-upload.md) | File Upload Vulnerabilities |
| [`graphql.md`](graphql.md) | GraphQL Misconfiguration |
| [`api-misconfig.md`](api-misconfig.md) | API Misconfiguration |
| [`cloud-misconfig.md`](cloud-misconfig.md) | Cloud / Kubernetes Misconfiguration |
