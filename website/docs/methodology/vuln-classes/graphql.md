---
title: "GraphQL Misconfiguration"
sidebar_position: 16
description: "Detect, escalate, and tool reference for GraphQL Misconfiguration — part of the Jacky CLI hunt-loop methodology."
---

# GraphQL Misconfiguration

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Check whether introspection is enabled in production (`__schema` query), revealing the full API surface including undocumented fields/mutations. Test for missing authorization on individual fields/mutations even when the top-level query is protected.

## How to escalate

Use introspection to find and abuse admin-only mutations, batch multiple queries in one request to bypass rate limiting, or exploit deeply nested queries for a denial-of-service (query complexity abuse).

## Common tools

`InQL` / `graphql-cop` for automated introspection abuse and schema mapping, Burp's GraphQL support, manual query-depth/batching tests.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
