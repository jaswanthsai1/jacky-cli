---
title: "Business Logic Flaws"
sidebar_position: 9
description: "Detect, escalate, and tool reference for Business Logic Flaws — part of the Jacky CLI hunt-loop methodology."
---

# Business Logic Flaws

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Map the intended workflow, then test out-of-order execution, negative/zero/overflow values (quantities, prices, discounts), and race conditions between steps (e.g. apply a coupon twice, skip a payment step). These bugs are invisible to scanners — they require understanding intent.

## How to escalate

Chain small logic gaps (e.g. price manipulation + missing server-side revalidation at checkout) into direct financial impact. Look for trust boundaries where the client is believed over the server (price, quantity, role, ownership sent in the request body).

## Common tools

Burp Repeater for manual workflow replay, spreadsheet modeling of state transitions, no automated tool substitutes for manual analysis here.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
