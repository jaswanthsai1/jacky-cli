---
title: "JWT / OAuth Issues"
sidebar_position: 13
description: "Detect, escalate, and tool reference for JWT / OAuth Issues — part of the Jacky CLI hunt-loop methodology."
---

# JWT / OAuth Issues

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

For JWTs: check algorithm handling (`alg: none`, RS256/HS256 confusion), signature verification, expiry enforcement, and whether claims (role, user id) are trusted without re-validation server-side. For OAuth: check `redirect_uri` validation strictness, `state` parameter (CSRF) enforcement, and token leakage via referrer/logs.

## How to escalate

A weak `redirect_uri` allowlist (e.g. path-only matching, subdomain wildcard) enables authorization-code/token theft; algorithm confusion on JWTs can lead to full auth bypass. Chain leaked codes/tokens into account takeover.

## Common tools

`jwt_tool` for JWT attack automation, Burp for OAuth flow interception, manual `redirect_uri` fuzzing (path traversal, open-redirect chaining, `@`/`\` tricks).

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
