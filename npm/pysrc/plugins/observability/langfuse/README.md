# Langfuse Observability Plugin

This plugin ships bundled with Jacky but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
jacky tools  # → Langfuse Observability

# Manual
pip install langfuse
jacky plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.jacky/.env` (or via `jacky tools`):

```bash
JACKY_LANGFUSE_PUBLIC_KEY=pk-lf-...
JACKY_LANGFUSE_SECRET_KEY=sk-lf-...
JACKY_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
jacky plugins list                 # observability/langfuse should show "enabled"
jacky chat -q "hello"              # then check Langfuse for a "Jacky turn" trace
```

## Optional tuning

```bash
JACKY_LANGFUSE_ENV=production       # environment tag
JACKY_LANGFUSE_RELEASE=v1.0.0       # release tag
JACKY_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
JACKY_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
JACKY_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
jacky plugins disable observability/langfuse
```
