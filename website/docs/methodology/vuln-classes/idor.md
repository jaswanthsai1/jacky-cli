---
title: "IDOR (Insecure Direct Object Reference)"
sidebar_position: 2
description: "Detect, escalate, and tool reference for IDOR (Insecure Direct Object Reference) — part of the Jacky CLI hunt-loop methodology."
---

# IDOR (Insecure Direct Object Reference)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Enumerate every endpoint that takes an ID (numeric, UUID, slug) and diff responses between two authenticated accounts of different privilege/ownership. Check REST paths, GraphQL node IDs, and object references buried in JSON bodies, not just the URL.

## How to escalate

Test read AND write paths (GET leaking data is one bug; PUT/DELETE/PATCH on another user's object is often higher severity). Check batch/bulk endpoints and export/download features, which often skip the authorization check applied to the single-object endpoint.

## Common tools

Burp Autorize/Auth Analyzer for automated diffing across sessions, ffuf for ID enumeration, manual multi-account testing.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
