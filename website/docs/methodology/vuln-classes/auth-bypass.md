---
title: "Authentication Bypass"
sidebar_position: 8
description: "Detect, escalate, and tool reference for Authentication Bypass — part of the Jacky CLI hunt-loop methodology."
---

# Authentication Bypass

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Test password reset, MFA, SSO/OAuth callback, and "remember me" flows for logic flaws: predictable tokens, missing rate limits, response manipulation (`"success": false` → `true`), or missing server-side verification of a client-asserted role/step.

## How to escalate

Look for step-skipping in multi-step auth (jumping straight to a post-auth endpoint), JWT algorithm confusion (`alg: none`, RS256→HS256), and session fixation. Chain a weak reset-token entropy issue with account takeover.

## Common tools

Burp Intruder for token brute-forcing/rate-limit testing, `jwt_tool` for JWT-specific bypass, manual step-replay/skip testing.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
