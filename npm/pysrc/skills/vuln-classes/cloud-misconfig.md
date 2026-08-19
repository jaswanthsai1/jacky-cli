# Cloud / Kubernetes Misconfiguration

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Check cloud storage buckets (S3/GCS/Azure Blob) for public read/write/list, exposed cloud metadata endpoints reachable via SSRF, overly permissive IAM roles, and Kubernetes API servers/kubelet endpoints exposed without auth.

## How to escalate

Public-write buckets can be used for stored XSS/malware hosting; leaked cloud credentials from metadata endpoints or exposed `.env`/config files often grant far broader access than the original bug's surface suggests — always check the blast radius of any leaked key.

## Common tools

`S3Scanner`/`cloud_enum` for storage discovery, `kube-hunter` for Kubernetes exposure, `ScoutSuite`/`Prowler` for broader cloud misconfig audits (only within authorized scope).

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
