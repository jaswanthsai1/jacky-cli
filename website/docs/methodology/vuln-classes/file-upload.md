---
title: "File Upload Vulnerabilities"
sidebar_position: 15
description: "Detect, escalate, and tool reference for File Upload Vulnerabilities — part of the Jacky CLI hunt-loop methodology."
---

# File Upload Vulnerabilities

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Test content-type/extension validation bypass (double extensions, null bytes, case variation, MIME spoofing), and check whether uploaded files are stored in a web-accessible, executable path.

## How to escalate

Bypass filters to upload a web shell or script the server will execute (`.php`, `.jsp`, `.asp`, or a polyglot image/script), then locate/access it for RCE. Also check for path traversal in the filename (`../../`) and stored XSS via SVG/HTML uploads.

## Common tools

Burp Repeater for manual bypass iteration, `fuxploider` for automated upload fuzzing, magic-byte/polyglot file crafting.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](https://github.com/jaswanthsai1/jacky-cli/blob/main/skills/triage-validation/SKILL.md)
before treating it as a confirmed finding.
