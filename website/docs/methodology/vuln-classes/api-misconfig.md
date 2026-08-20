---
title: "API Misconfiguration"
sidebar_position: 17
description: "Detect, escalate, and tool reference for API Misconfiguration — part of the Jacky CLI hunt-loop methodology."
---

# API Misconfiguration

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Diff behavior between documented/versioned API endpoints (`/v1/` vs `/v2/` vs internal/undocumented paths found in JS bundles or mobile app decompilation) — older versions often lack fixes applied to the current one. Check for missing rate limiting, verbose error messages, and mass-assignment (extra JSON fields silently accepted).

## How to escalate

Mass assignment on a user-update endpoint (sending `"role": "admin"` in a profile-update body) is a fast path to privilege escalation. Deprecated API versions are a common source of reintroduced, already-patched bugs.

## Common tools

ffuf/gobuster for endpoint/version discovery, JS bundle analysis for hidden endpoints, Burp for parameter/mass-assignment fuzzing.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
