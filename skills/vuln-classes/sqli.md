# SQLi (SQL Injection)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Test every parameter that reaches a database query — including headers, JSON body fields, and sort/filter params, not just obvious search boxes. Look for error-based signals first, then time-based blind if errors are suppressed.

## How to escalate

Move from error/boolean-based to full data extraction; check for stacked queries and OS command execution via `xp_cmdshell` (MSSQL) or `INTO OUTFILE` (MySQL) where permissions allow. Second-order SQLi (input stored, executed later) is often missed by scanners.

## Common tools

sqlmap for confirmation and extraction, Burp for manual probing, `--risk`/`--level` tuning to avoid false negatives on WAF-fronted targets.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
