---
title: "Vulnerability Class Reference"
sidebar_position: 0
description: "One reference page per major vulnerability class — detect, escalate, and tool notes for the enumerate and test stages of the hunt loop."
---

# Vulnerability Class Reference

Short, generic "how to detect / how to escalate / common tools" notes for
major web/API/cloud vulnerability classes, meant to be read during the
**enumerate** and **test** stages of the [hunt-loop methodology](../).

These are reference checklists, not auto-exploit scripts — Jacky assists a
human hunter; it doesn't guarantee findings. Every candidate finding should
still pass the gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before being treated as confirmed.

| Class | Reference |
|---|---|
| Server-Side Request Forgery | [ssrf.md](./ssrf) |
| Insecure Direct Object Reference | [idor.md](./idor) |
| Cross-Site Scripting | [xss.md](./xss) |
| SQL Injection | [sqli.md](./sqli) |
| Server-Side Template Injection | [ssti.md](./ssti) |
| XML External Entity Injection | [xxe.md](./xxe) |
| Cross-Site Request Forgery | [csrf.md](./csrf) |
| Authentication Bypass | [auth-bypass.md](./auth-bypass) |
| Business Logic Flaws | [business-logic.md](./business-logic) |
| Race Conditions | [race-condition.md](./race-condition) |
| CORS Misconfiguration | [cors.md](./cors) |
| Subdomain Takeover | [subdomain-takeover.md](./subdomain-takeover) |
| JWT / OAuth Issues | [jwt-oauth.md](./jwt-oauth) |
| Open Redirect | [open-redirect.md](./open-redirect) |
| File Upload Vulnerabilities | [file-upload.md](./file-upload) |
| GraphQL Misconfiguration | [graphql.md](./graphql) |
| API Misconfiguration | [api-misconfig.md](./api-misconfig) |
| Cloud / Kubernetes Misconfiguration | [cloud-misconfig.md](./cloud-misconfig) |
