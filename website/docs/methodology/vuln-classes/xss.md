---
title: "XSS (Cross-Site Scripting)"
sidebar_position: 3
description: "Detect, escalate, and tool reference for XSS (Cross-Site Scripting) — part of the Jacky CLI hunt-loop methodology."
---

# XSS (Cross-Site Scripting)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Trace every reflected/stored input sink: search boxes, profile fields, file names, error messages, and any place user input is echoed into HTML, JS, or an attribute without contextual encoding. Check DOM sinks (`innerHTML`, `document.write`, `eval`) via source-to-sink tracing in bundled JS.

## How to escalate

Move from reflected to stored where possible (higher blast radius). Chain with CSRF or auth flows to steal tokens/cookies, pivot to account takeover, or use DOM XSS to bypass CSP if a trusted script gadget exists.

## Common tools

Burp Scanner + manual payload crafting, DOMPurify bypass techniques, `XSStrike`, browser devtools for sink tracing, CSP Evaluator.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
