---
sidebar_position: 1
title: "CLI Commands Reference"
description: "Authoritative reference for Jacky terminal commands and command families"
---

# CLI Commands Reference

This page covers the **terminal commands** you run from your shell.

For in-chat slash commands, see [Slash Commands Reference](./slash-commands.md).

## Global entrypoint

```bash
jacky [global-options] <command> [subcommand/options]
```

### Global options

| Option | Description |
|--------|-------------|
| `--version`, `-V` | Show version and exit. |
| `--profile <name>`, `-p <name>` | Select which Jacky profile to use for this invocation. Overrides the sticky default set by `jacky profile use`. |
| `--resume <session>`, `-r <session>` | Resume a previous session by ID or title. |
| `--continue [name]`, `-c [name]` | Resume the most recent session, or the most recent session matching a title. |
| `--worktree`, `-w` | Start in an isolated git worktree for parallel-agent workflows. |
| `--yolo` | Bypass dangerous-command approval prompts. |
| `--pass-session-id` | Include the session ID in the agent's system prompt. |
| `--ignore-user-config` | Ignore `~/.jacky/config.yaml` and fall back to built-in defaults. Credentials in `.env` are still loaded. |
| `--ignore-rules` | Skip auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, memory, and preloaded skills. |
| `--tui` | Launch the [TUI](../user-guide/tui.md) instead of the classic CLI. Equivalent to `JACKY_TUI=1`. Always wins over `display.interface`. |
| `--cli` | Force the classic prompt_toolkit REPL. Use this to override `display.interface: tui` for a single invocation. |
| `--dev` | With `--tui`: run the TypeScript sources directly via `tsx` instead of the prebuilt bundle (for TUI contributors). |

## Top-level commands

| Command | Purpose |
|---------|---------|
| `jacky chat` | Interactive or one-shot chat with the agent. |
| `jacky model` | Interactively choose the default provider and model. |
| `jacky moa` | Configure named Mixture of Agents presets selectable from the model picker. |
| `jacky fallback` | Manage fallback providers tried when the primary model errors. |
| `jacky gateway` | Run or manage the messaging gateway service. |
| `jacky proxy` | Local OpenAI-compatible proxy that attaches OAuth provider credentials. See [Subscription Proxy](../user-guide/features/subscription-proxy.md). |
| `jacky lsp` | Manage Language Server Protocol integration (semantic diagnostics for write_file/patch). |
| `jacky setup` | Interactive setup wizard for all or part of the configuration. |
| `jacky whatsapp` | Configure and pair the WhatsApp bridge. |
| `jacky whatsapp-cloud` | Configure the official Meta WhatsApp Business Cloud API adapter (Business account + public webhook required). Distinct from `jacky whatsapp` (Baileys personal-account bridge). |
| `jacky slack` | Slack helpers (currently: generate the app manifest with every command as a native slash). |
| `jacky auth` | Manage credentials — add, list, remove, reset, status, logout. Handles OAuth flows for Codex/Nous/Anthropic. |
| `jacky login` / `logout` | **Deprecated** — use `jacky auth` instead. |
| `jacky send` | Send a one-shot message to a configured messaging platform (Telegram, Discord, Slack, Signal, SMS, …). Useful from shell scripts, cron jobs, CI hooks, and monitoring daemons — no agent loop, no LLM. |
| `jacky secrets` | Manage external secret sources (currently Bitwarden Secrets Manager) for pulling API keys at process startup instead of from `~/.jacky/.env`. |
| `jacky migrate` | Diagnose and (optionally) rewrite `config.yaml` to replace references to retired models or deprecated settings (e.g. `migrate xai`). |
| `jacky status` | Show agent, auth, and platform status. |
| `jacky cron` | Inspect and tick the cron scheduler. |
| `jacky kanban` | Multi-profile collaboration board (tasks, links, dispatcher). |
| `jacky project` | Manage named, multi-folder workspaces (projects). Anchors desktop session grouping and, when bound to a kanban board, gives tasks a deterministic worktree + branch convention. State is per-profile. |
| `jacky webhook` | Manage dynamic webhook subscriptions for event-driven activation. |
| `jacky hooks` | Inspect, approve, or remove shell-script hooks declared in `config.yaml`. |
| `jacky doctor` | Diagnose config and dependency issues. |
| `jacky security audit` | On-demand supply-chain audit (OSV.dev) for the venv, plugin requirements, and pinned MCP servers. |
| `jacky dump` | Copy-pasteable setup summary for support/debugging. |
| `jacky prompt-size` | Show a byte breakdown of the system prompt + tool schemas (skills index, memory, profile). Runs offline. |
| `jacky debug` | Debug tools — upload logs and system info for support. |
| `jacky backup` | Back up Jacky home directory to a zip file. |
| `jacky checkpoints` | Inspect / prune / clear `~/.jacky/checkpoints/` (the shadow store used by `/rollback`). Run with no args for a status overview. |
| `jacky import` | Restore a Jacky backup from a zip file. |
| `jacky logs` | View, tail, and filter agent/gateway/error log files. |
| `jacky config` | Show, edit, migrate, and query configuration files. |
| `jacky pairing` | Approve or revoke messaging pairing codes. |
| `jacky skills` | Browse, install, publish, audit, and configure skills. |
| `jacky bundles` | Group several skills under a single `/<name>` slash command. See [Skill Bundles](../user-guide/features/skills.md#skill-bundles). |
| `jacky curator` | Background skill maintenance — status, run, pause, pin. See [Curator](../user-guide/features/curator.md). |
| `jacky memory` | Configure external memory provider. Plugin-specific subcommands (e.g. `jacky honcho`) register automatically when their provider is active. |
| `jacky acp` | Run Jacky as an ACP server for editor integration. |
| `jacky mcp` | Manage MCP server configurations and run Jacky as an MCP server. |
| `jacky plugins` | Manage Jacky Agent plugins (install, enable, disable, remove). |
| `jacky portal` | Nous Portal status, subscription link, and Tool Gateway routing. See [Tool Gateway](../user-guide/features/tool-gateway.md). |
| `jacky tools` | Configure enabled tools per platform. |
| `jacky computer-use` | Install or check the cua-driver backend (macOS Computer Use). |
| `jacky pets` | Browse, install, and select [petdex](../user-guide/features/pets.md) animated pets shown across the CLI, TUI, and desktop app. Subcommands: `list`, `install`, `select`, `show`, `off`, `scale`, `remove`, `doctor`. |
| `jacky sessions` | Browse, export, prune, rename, and delete sessions. |
| `jacky insights` | Show token/cost/activity analytics. |
| `jacky claw` | OpenClaw migration helpers. |
| `jacky dashboard` | Launch the web dashboard for managing config, API keys, and sessions. |
| `jacky desktop` (alias `gui`) | Build and launch the native Electron desktop app. |
| `jacky profile` | Manage profiles — multiple isolated Jacky instances. |
| `jacky completion` | Print shell completion scripts (bash/zsh/fish). |
| `jacky version` | Show version information. |
| `jacky update` | Pull latest code and reinstall dependencies. `--check` previews without installing; `--backup` takes a pre-pull `JACKY_HOME` snapshot. |
| `jacky uninstall` | Remove Jacky from the system. |

## `jacky chat`

```bash
jacky chat [options]
```

Common options:

| Option | Description |
|--------|-------------|
| `-q`, `--query "..."` | One-shot, non-interactive prompt. |
| `-m`, `--model <model>` | Override the model for this run. |
| `-t`, `--toolsets <csv>` | Enable a comma-separated set of toolsets. |
| `--provider <provider>` | Force a provider: `auto`, `openrouter`, `nous`, `openai-codex`, `copilot-acp`, `copilot`, `anthropic`, `gemini`, `huggingface`, `novita` (aliases `novita-ai`, `novitaai`), `openai-api`, `zai`, `kimi-coding`, `kimi-coding-cn`, `minimax`, `minimax-cn`, `minimax-oauth`, `kilocode`, `xiaomi`, `arcee`, `gmi`, `alibaba`, `alibaba-coding-plan` (alias `alibaba_coding`), `deepseek`, `nvidia`, `ollama-cloud`, `xai` (alias `grok`), `xai-oauth` (alias `grok-oauth`), `qwen-oauth`, `bedrock`, `opencode-zen`, `opencode-go`, `azure-foundry`, `lmstudio`, `stepfun`, `tencent-tokenhub` (alias `tencent`, `tokenhub`). |
| `-s`, `--skills <name>` | Preload one or more skills for the session (can be repeated or comma-separated). |
| `-v`, `--verbose` | Verbose output. |
| `-Q`, `--quiet` | Programmatic mode: suppress banner/spinner/tool previews. |
| `--image <path>` | Attach a local image to a single query. |
| `--resume <session>` / `--continue [name]` | Resume a session directly from `chat`. |
| `--worktree` | Create an isolated git worktree for this run. |
| `--checkpoints` | Enable filesystem checkpoints before destructive file changes. |
| `--yolo` | Skip approval prompts. |
| `--pass-session-id` | Pass the session ID into the system prompt. |
| `--ignore-user-config` | Ignore `~/.jacky/config.yaml` and use built-in defaults. Credentials in `.env` are still loaded. Useful for isolated CI runs, reproducible bug reports, and third-party integrations. |
| `--ignore-rules` | Skip auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, persistent memory, and preloaded skills. Combine with `--ignore-user-config` for a fully isolated run. |
| `--safe-mode` | Troubleshooting mode: disable ALL customizations — user config, rules/memory injection, plugins, shell hooks, and MCP servers (implies `--ignore-user-config` and `--ignore-rules`). Use to isolate whether a problem comes from your setup or from Jacky itself. |
| `--source <tag>` | Session source tag for filtering (default: `cli`). Use `tool` for third-party integrations that should not appear in user session lists. |
| `--max-turns <N>` | Maximum tool-calling iterations per conversation turn (default: 90, or `agent.max_turns` in config). |

Examples:

```bash
jacky
jacky chat -q "Summarize the latest PRs"
jacky chat --provider openrouter --model anthropic/claude-sonnet-4.6
jacky chat --toolsets web,terminal,skills
jacky chat --quiet -q "Return only JSON"
jacky chat --worktree -q "Review this repo and open a PR"
jacky chat --ignore-user-config --ignore-rules -q "Repro without my personal setup"
jacky chat --safe-mode -q "Is this bug mine or Jacky'?"
```

### `jacky -z <prompt>` — scripted one-shot

For programmatic callers (shell scripts, CI, cron, parent processes piping in a prompt), `jacky -z` is the purest one-shot entry point: **single prompt in, final response text out, nothing else on stdout or stderr.** No banner, no spinner, no tool previews, no `Session:` line — just the agent's final reply as plain text.

```bash
jacky -z "What's the capital of France?"
# → Paris.

# Parent scripts can cleanly capture the response:
answer=$(jacky -z "summarize this" < /path/to/file.txt)
```

Per-run overrides (no mutation to `~/.jacky/config.yaml`):

| Flag | Equivalent env var | Purpose |
|---|---|---|
| `-m` / `--model <model>` | `JACKY_INFERENCE_MODEL` | Override the model for this run |
| `--provider <provider>` | _(none)_ | Override the provider for this run |

```bash
jacky -z "…" --provider openrouter --model openai/gpt-5.5
# or:
JACKY_INFERENCE_MODEL=anthropic/claude-sonnet-4.6 jacky -z "…"
```

Same agent, same tools, same skills — just strips every interactive / cosmetic layer. If you need tool output in the transcript too, use `jacky chat -q` instead; `-z` is explicitly for "I only want the final answer".

## `jacky model`

Interactive provider + model selector. **This is the command for adding new providers, setting up API keys, and running OAuth flows.** Run it from your terminal — not from inside an active Jacky chat session.

```bash
jacky model
```

Use this when you want to:
- **add a new provider** (OpenRouter, Anthropic, Copilot, DeepSeek, custom, etc.)
- log into OAuth-backed providers (Anthropic, Copilot, Codex, Nous Portal)
- enter or update API keys
- pick from provider-specific model lists
- configure a custom/self-hosted endpoint
- save the new default into config

:::warning jacky model vs /model — know the difference
**`jacky model`** (run from your terminal, outside any Jacky session) is the **full provider setup wizard**. It can add new providers, run OAuth flows, prompt for API keys, and configure endpoints.

**`/model`** (typed inside an active Jacky chat session) can only **switch between providers and models you've already set up**. It cannot add new providers, run OAuth, or prompt for API keys.

**If you need to add a new provider:** Exit your Jacky session first (`Ctrl+C` or `/quit`), then run `jacky model` from your terminal prompt.
:::

### `/model` slash command (mid-session)

Switch between already-configured models without leaving a session:

```
/model                              # Show current model and available options
/model claude-sonnet-4              # Switch model (auto-detects provider)
/model zai:glm-5                    # Switch provider and model
/model custom:qwen-2.5              # Use model on your custom endpoint
/model custom                       # Auto-detect model from custom endpoint
/model custom:local:qwen-2.5        # Use a named custom provider
/model openrouter:anthropic/claude-sonnet-4  # Switch back to cloud
```

By default, `/model` changes apply **to the current session only**. Add `--global` to persist the change to `config.yaml`:

```
/model claude-sonnet-4 --global     # Switch and save as new default
```

:::info What if I only see OpenRouter models?
If you've only configured OpenRouter, `/model` will only show OpenRouter models. To add another provider (Anthropic, DeepSeek, Copilot, etc.), exit your session and run `jacky model` from the terminal.
:::

Provider and base URL changes are persisted to `config.yaml` automatically. When switching away from a custom endpoint, the stale base URL is cleared to prevent it leaking into other providers.

## `jacky gateway`

```bash
jacky gateway <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `run` | Run the gateway in the foreground. Recommended for WSL, Docker, and Termux. |
| `start` | Start the installed systemd/launchd background service. |
| `stop` | Stop the service (or foreground process). |
| `restart` | Restart the service. |
| `status` | Show service status. |
| `list` | List **all profiles** and whether each profile's gateway is currently running (with PID where available). Handy when you run multiple profiles side-by-side and want a single overview. |
| `install` | Install as a systemd (Linux) or launchd (macOS) background service. |
| `uninstall` | Remove the installed service. |
| `setup` | Interactive messaging-platform setup. |
| `migrate-legacy` | Remove legacy `jacky.service` units left over from pre-rename installs. Profile units (`jacky-gateway-<profile>.service`) and unrelated services are never touched. Flags: `--dry-run`, `-y`/`--yes`. |
| `enroll` | Experimental: enroll this gateway with a relay connector and save relay credentials for connector-backed platforms. |

Options:

| Option | Description |
|--------|-------------|
| `--all` | On `start` / `restart` / `stop`: act on **every profile's** gateway, not just the active `JACKY_HOME`. Useful if you run multiple profiles side-by-side and want to restart them all after `jacky update`. |
| `--no-supervise` | On `run`: inside the s6-overlay Docker image, opt out of auto-supervision and use pre-s6 foreground semantics — gateway runs as the container's main process with no auto-restart. No-op outside the s6 image. Equivalent to setting `JACKY_GATEWAY_NO_SUPERVISE=1`. |

`jacky gateway enroll` accepts `--token`, `--connector-url`, `--gateway-id`, and `--wake-url`. It exchanges the enrollment token with the connector and writes the resulting `GATEWAY_RELAY_ID`, `GATEWAY_RELAY_SECRET`, `GATEWAY_RELAY_DELIVERY_KEY`, optional `GATEWAY_RELAY_URL`, and (when `--wake-url` is given) `GATEWAY_RELAY_WAKE_URL` values to the active profile's `.env`.

:::tip WSL users
Use `jacky gateway run` instead of `jacky gateway start` — WSL's systemd support is unreliable. Wrap it in tmux for persistence: `tmux new -s jacky 'jacky gateway run'`. See [WSL FAQ](/reference/faq#wsl-gateway-keeps-disconnecting-or-jacky-gateway-start-fails) for details.
:::

## `jacky lsp`

```bash
jacky lsp <subcommand>
```

Manage the Language Server Protocol integration. LSP runs real
language servers (pyright, gopls, rust-analyzer, …) in the
background and feeds their diagnostics into the post-write check
used by `write_file` and `patch`. Gated on git workspace detection
— LSP only runs when the cwd or edited file is inside a git
worktree.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `status` | Show service state, configured servers, install status. |
| `list` | Print the registry of supported servers. Pass `--installed-only` to skip missing ones. |
| `install <id>` | Eagerly install one server's binary. |
| `install-all` | Install every server with a known auto-install recipe. |
| `restart` | Tear down running clients so the next edit re-spawns. |
| `which <id>` | Print the resolved binary path for one server. |

See [LSP — Semantic Diagnostics](/user-guide/features/lsp) for
the full guide, supported languages, and configuration knobs.

## `jacky setup`

```bash
jacky setup [model|tts|terminal|gateway|tools|agent] [--non-interactive] [--reset] [--quick] [--reconfigure] [--portal]
```

**Easiest path:** `jacky setup --portal` — OAuth into Nous Portal and opt into the [Tool Gateway](../user-guide/features/tool-gateway.md) in one shot.

**First run:** launches the first-time wizard.

**Returning user (already configured):** drops straight into the full reconfigure wizard — every prompt shows your current value as its default, press Enter to keep or type a new value. No menu.

Jump into one section instead of the full wizard:

| Section | Description |
|---------|-------------|
| `model` | Provider and model setup. |
| `terminal` | Terminal backend and sandbox setup. |
| `gateway` | Messaging platform setup. |
| `tools` | Enable/disable tools per platform. |
| `agent` | Agent behavior settings. |

Options:

| Option | Description |
|--------|-------------|
| `--quick` | On returning-user runs: only prompt for items that are missing or unset. Skip items you already have configured. |
| `--non-interactive` | Use defaults / environment values without prompts. |
| `--reset` | Reset configuration to defaults before setup. |
| `--reconfigure` | Backwards-compat alias — bare `jacky setup` on an existing install now does this by default. |
| `--portal` | One-shot Nous Portal setup: log in via OAuth, set Nous as the inference provider, and opt into the [Tool Gateway](../user-guide/features/tool-gateway.md). Skips the rest of the wizard. |

## `jacky portal`

```bash
jacky portal [status|open|tools]
```

Inspect Nous Portal auth, Tool Gateway routing, and reach the subscription page. Subcommand-less invocation runs `status`.

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Portal auth state + per-tool Tool Gateway routing summary. Also shown when no subcommand is given. |
| `open` | Open `portal.nousresearch.com/manage-subscription` in your default browser. |
| `tools` | List every Tool Gateway partner (Firecrawl, FAL, OpenAI TTS, Browser Use, Modal) and which are routed via Nous. |

For configuration of the gateway itself, see [Tool Gateway](../user-guide/features/tool-gateway.md). For the one-shot setup path, see `jacky setup --portal` above.

## `jacky whatsapp`

```bash
jacky whatsapp
```

Runs the WhatsApp pairing/setup flow, including mode selection and QR-code pairing.

## `jacky slack`

```bash
jacky slack manifest              # print manifest to stdout
jacky slack manifest --write      # write to ~/.jacky/slack-manifest.json
jacky slack manifest --slashes-only  # just the features.slash_commands array
```

Generates a Slack app manifest that registers every gateway command in
`COMMAND_REGISTRY` (`/btw`, `/stop`, `/model`, …) as a first-class
Slack slash command — matching Discord and Telegram parity. Paste the
output into your Slack app config at
[https://api.slack.com/apps](https://api.slack.com/apps) → your app →
**Features → App Manifest → Edit**, then **Save**. Slack prompts for
reinstall if scopes or slash commands changed.

| Flag | Default | Purpose |
|------|---------|---------|
| `--write [PATH]` | stdout | Write to a file instead of stdout. Bare `--write` writes `$JACKY_HOME/slack-manifest.json`. |
| `--name NAME` | `Jacky` | Bot display name in Slack. |
| `--description DESC` | default blurb | Bot description shown in the Slack app directory. |
| `--slashes-only` | off | Emit only `features.slash_commands` for merging into a manually-maintained manifest. |

Run `jacky slack manifest --write` again after `jacky update` to pick
up any new commands.


## `jacky send`

```bash
jacky send --to <target> "message text"
jacky send --to <target> --file <path>
echo "message" | jacky send --to <target>
jacky send --list [platform]
```

Send a one-shot message to a configured messaging platform without spinning up an agent or gateway loop. Reuses the gateway's already-configured credentials (`~/.jacky/.env` + `~/.jacky/config.yaml`) so ops scripts, cron jobs, CI hooks, and monitoring daemons can post status updates without reimplementing each platform's REST client.

For bot-token platforms (Telegram, Discord, Slack, Signal, SMS, WhatsApp-CloudAPI) no running gateway is required — `jacky send` talks directly to the platform's REST endpoint. Plugin platforms that need a persistent adapter still require a live gateway.

| Option | Description |
|--------|-------------|
| `-t`, `--to <TARGET>` | Delivery target. Formats: `platform` (uses home channel), `platform:chat_id`, `platform:chat_id:thread_id`, or `platform:#channel-name`. Examples: `telegram`, `telegram:-1001234567890`, `discord:#ops`, `slack:C0123ABCD`, `signal:+15551234567`. |
| `-f`, `--file <PATH>` | Read the message body from `PATH` (text files only — logs, reports, markdown). Pass `-` to force reading from stdin. To send an image or other binary file, use `MEDIA:<path>` (see below). |
| `-s`, `--subject <LINE>` | Prepend a subject/header line before the message body. |
| `-l`, `--list [platform]` | List configured targets across all platforms (or only the given platform). |
| `-q`, `--quiet` | Suppress stdout on success — useful in scripts (rely on exit code only). |
| `--json` | Emit raw JSON result instead of human-readable output. |

If neither a positional `message` argument nor `--file` is provided, `jacky send` reads from stdin when it is not a TTY. Exit codes: `0` on success, `1` on delivery/backend failure, `2` on usage errors.

### Sending images and other media

`--file` is for *text* bodies only. To deliver an image, document, video, or audio file as a native platform attachment, reference it inside the message text with the `MEDIA:<local_path>` directive:

```bash
jacky send --to telegram "MEDIA:/tmp/screenshot.png"
jacky send --to telegram "Build chart for today MEDIA:/tmp/chart.png"   # with caption
jacky send --to discord:#ops "MEDIA:/tmp/report.pdf"
```

By default, image files are sent as photos (platforms like Telegram recompress these). Add `[[as_document]]` to the message to deliver them as uncompressed file attachments instead:

```bash
jacky send --to telegram "[[as_document]] MEDIA:/tmp/screenshot.png"
```

Examples:

```bash
jacky send --to telegram "deploy finished"
echo "RAM 92%" | jacky send --to telegram:-1001234567890
jacky send --to discord:#ops --file /tmp/report.md
jacky send --to slack:#eng --subject "[CI]" --file build.log
jacky send --list                  # all platforms
jacky send --list telegram         # filter by platform
```


## `jacky secrets`

```bash
jacky secrets bitwarden <subcommand>
jacky secrets bw <subcommand>          # short alias
```

Pull API keys from an external secret manager at process startup instead of storing them in `~/.jacky/.env`. Currently supports **Bitwarden Secrets Manager**. See the full guide: [Bitwarden integration](../user-guide/secrets/bitwarden.md).

`bitwarden` (alias `bw`) subcommands:

| Subcommand | Description |
|------------|-------------|
| `setup` | Interactive wizard: install the pinned `bws` binary, store an access token, and pick a project. Accepts `--project-id`, `--access-token`, and `--server-url` for non-interactive use. |
| `status` | Show current config, binary path/version, and last fetch info. |
| `sync` | Fetch secrets now and report what changed. Add `--apply` to actually export the secrets into the current shell's environment (default is dry-run). |
| `install` | Download and verify the pinned `bws` binary. `--force` re-downloads even if a managed copy already exists. |
| `disable` | Turn off the Bitwarden integration. |


## `jacky migrate`

```bash
jacky migrate <type>
```

Diagnose and (optionally) rewrite the active `config.yaml` to replace references to retired models or deprecated settings. A timestamped backup of the original `config.yaml` is taken before any rewrite (skip with `--no-backup`).

| Subcommand | Description |
|------------|-------------|
| `xai` | Scan `config.yaml` for references to xAI models scheduled for retirement on May 15, 2026 and (with `--apply`) rewrite them in-place to the official replacements per the xAI migration guide. Defaults to dry-run. |

Common flags for migration subcommands:

| Flag | Description |
|------|-------------|
| `--apply` | Rewrite `config.yaml` in-place (default: dry-run, no writes). |
| `--no-backup` | Skip the timestamped backup of `config.yaml` when applying. |

> Not to be confused with `jacky claw migrate` (one-shot import of OpenClaw configuration into Jacky) — `jacky migrate` is the top-level config-rewrite command.


## `jacky proxy`

```bash
jacky proxy <subcommand>
```

Run a local OpenAI-compatible HTTP server that forwards requests to an OAuth-authenticated upstream provider (e.g. Nous Portal, xAI). External apps can point at the proxy with any bearer token; the proxy attaches your real OAuth credentials on the way out. See [Subscription Proxy](../user-guide/features/subscription-proxy.md) for the full guide.

| Subcommand | Description |
|------------|-------------|
| `start` | Run the proxy in the foreground. Flags: `--provider <nous\|xai>` (default `nous`), `--host <addr>` (default `127.0.0.1`; use `0.0.0.0` to expose on LAN), `--port <int>` (default `8645`). |
| `status` | Show which proxy upstreams are ready (credentials present, OAuth valid). |
| `providers` | List available proxy upstream providers. |


## `jacky security`

```bash
jacky security <subcommand>
```

On-demand vulnerability scan against [OSV.dev](https://osv.dev). Covers the Jacky venv (installed PyPI distributions), Python dependencies declared by plugins under `~/.jacky/plugins/`, and pinned `npx`/`uvx` MCP servers in `config.yaml`. Does NOT scan globally-installed packages or editor/browser extensions.

| Subcommand | Description |
|------------|-------------|
| `audit` | Run a one-shot supply-chain audit. |

`audit` flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | off | Emit machine-readable JSON instead of human-readable text. |
| `--fail-on <level>` | `critical` | Exit non-zero when any finding meets this severity (`low`, `moderate`, `high`, `critical`). |
| `--skip-venv` | off | Skip scanning the Jacky Python venv. |
| `--skip-plugins` | off | Skip scanning plugin requirements files. |
| `--skip-mcp` | off | Skip scanning pinned MCP servers in `config.yaml`. |


## `jacky login` / `jacky logout` *(Deprecated)*

:::caution
`jacky login` has been removed. Use `jacky auth` to manage OAuth credentials, `jacky model` to select a provider, or `jacky setup` for full interactive setup.
:::

## `jacky auth`

Manage credential pools for same-provider key rotation. See [Credential Pools](/user-guide/features/credential-pools) for full documentation.

```bash
jacky auth                                              # Interactive wizard
jacky auth list                                         # Show all pools
jacky auth list openrouter                              # Show specific provider
jacky auth add openrouter --api-key sk-or-v1-xxx        # Add API key
jacky auth add anthropic --type oauth                   # Add OAuth credential
jacky auth remove openrouter 2                          # Remove by index
jacky auth reset openrouter                             # Clear cooldowns
jacky auth status anthropic                             # Show auth status for a provider
jacky auth logout anthropic                             # Log out and clear stored auth state
jacky auth spotify                                      # Authenticate Jacky with Spotify via PKCE
```

Subcommands: `add`, `list`, `remove`, `reset`, `status`, `logout`, `spotify`. When called with no subcommand, launches the interactive management wizard.

## `jacky status`

```bash
jacky status [--all] [--deep]
```

| Option | Description |
|--------|-------------|
| `--all` | Show all details in a shareable redacted format. |
| `--deep` | Run deeper checks that may take longer. |

## `jacky cron`

```bash
jacky cron <list|create|edit|pause|resume|run|remove|status|tick>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show scheduled jobs. |
| `create` / `add` | Create a scheduled job from a prompt, optionally attaching one or more skills via repeated `--skill`. |
| `edit` | Update a job's schedule, prompt, name, delivery, repeat count, or attached skills. Supports `--clear-skills`, `--add-skill`, and `--remove-skill`. |
| `pause` | Pause a job without deleting it. |
| `resume` | Resume a paused job and compute its next future run. |
| `run` | Trigger a job on the next scheduler tick. |
| `remove` | Delete a scheduled job. |
| `status` | Check whether the cron scheduler is running. |
| `tick` | Run due jobs once and exit. |

The cron **trigger** is pluggable via the `cron.provider` config key. Empty
(the default) uses the built-in in-process ticker. Set it to `chronos` (the
NAS-managed provider for scale-to-zero hosted gateways) — configured via the
`cron.chronos.*` keys (`portal_url`, `callback_url`, `expected_audience`,
`nas_jwks_url`) — or name a custom provider under `plugins/cron/<name>/` or
`$JACKY_HOME/plugins/<name>/`. An unknown or unavailable provider falls back to
the built-in, so cron is never left without a trigger. See the
[cron internals](../developer-guide/cron-internals.md#gateway-integration) doc.

## `jacky kanban`

```bash
jacky kanban [--board <slug>] <action> [options]
```

Multi-profile, multi-project collaboration board. Each install can host many boards (one per project, repo, or domain); each board is a standalone queue with its own SQLite DB and dispatcher scope. New installs start with one board called `default`, whose DB is `~/.jacky/kanban.db` for back-compat; additional boards live at `~/.jacky/kanban/boards/<slug>/kanban.db`. The gateway-embedded dispatcher sweeps every board per tick.

**Global flags (apply to every action below):**

| Flag | Purpose |
|------|---------|
| `--board <slug>` | Operate on a specific board. Defaults to the current board (set via `jacky kanban boards switch`, the `JACKY_KANBAN_BOARD` env var, or `default`). |

**This is the human / scripting surface.** Agent workers spawned by the dispatcher drive the board through a dedicated `kanban_*` [toolset](/user-guide/features/kanban#how-workers-interact-with-the-board) (`kanban_show`, `kanban_complete`, `kanban_block`, `kanban_create`, `kanban_link`, `kanban_comment`, `kanban_heartbeat`; orchestrator profiles also get `kanban_list` and `kanban_unblock`) instead of shelling to `jacky kanban`. Workers have `JACKY_KANBAN_BOARD` pinned in their env so they physically cannot see other boards.

| Action | Purpose |
|--------|---------|
| `init` | Create `kanban.db` if missing. Idempotent. |
| `boards list` / `boards ls` | List all boards with task counts. `--json`, `--all` (include archived). |
| `boards create <slug>` | Create a new board. Flags: `--name`, `--description`, `--icon`, `--color`, `--switch` (make active). Slug is kebab-case, auto-downcased. |
| `boards switch <slug>` / `boards use` | Persist `<slug>` as the active board (writes `~/.jacky/kanban/current`). |
| `boards show` / `boards current` | Print the currently-active board's name, DB path, and task counts. |
| `boards rename <slug> "<name>"` | Change a board's display name. Slug is immutable. |
| `boards rm <slug>` | Archive (default) or hard-delete a board. `--delete` skips the archive step. Archived boards move to `boards/_archived/<slug>-<ts>/`. Refused for `default`. |
| `create "<title>"` | Create a new task on the active board. Flags: `--body`, `--assignee`, `--parent` (repeatable), `--workspace scratch\|worktree\|dir:<path>`, `--tenant`, `--priority`, `--triage`, `--idempotency-key`, `--max-runtime`, `--max-retries`, `--skill` (repeatable). |
| `list` / `ls` | List tasks on the active board. Filter with `--mine`, `--assignee`, `--status`, `--tenant`, `--archived`, `--json`. |
| `show <id>` | Show a task with comments and events. `--json` for machine output. |
| `assign <id> <profile>` | Assign or reassign. Use `none` to unassign. Refused while task is running. |
| `link <parent> <child>` | Add a dependency. Cycle-detected. Both tasks must be on the same board. |
| `unlink <parent> <child>` | Remove a dependency. |
| `claim <id>` | Atomically claim a ready task. Prints resolved workspace path. |
| `comment <id> "<text>"` | Append a comment. The next worker that claims the task reads it as part of its `kanban_show()` response. |
| `complete <id>` | Mark task done. Flags: `--result`, `--summary`, `--metadata`. |
| `block <id> "<reason>"` | Mark task blocked for human input. Also appends the reason as a comment. |
| `schedule <id> "<reason>"` | Park time-delay/follow-up work in `scheduled` so it is not shown as a human blocker. |
| `unblock <id>` | Return a blocked or scheduled task to ready (or `todo` if dependencies are still open). |
| `archive <id>` | Hide from default list. `gc` will remove scratch workspaces. |
| `tail <id>` | Follow a task's event stream. |
| `dispatch` | One dispatcher pass on the active board. Flags: `--dry-run`, `--max N`, `--failure-limit N`, `--json`. |
| `context <id>` | Print the full context a worker would see (title + body + parent results + comments). |
| `specify <id>` / `specify --all` | Flesh out a triage-column task into a concrete spec (title + body with goal, approach, acceptance criteria) via the auxiliary LLM, then promote it to `todo`. Flags: `--tenant` (scope `--all` to one tenant), `--author`, `--json`. Configure the model under `auxiliary.triage_specifier` in `config.yaml`. |
| `decompose <id>` / `decompose --all` | Fan a triage-column task out into a graph of child tasks routed to specialist profiles by description. Falls back to specify-style single-task promotion when the LLM decides the task doesn't benefit from fan-out. Same flags as `specify`. Configure the decomposer model under `auxiliary.kanban_decomposer` in `config.yaml`; `kanban.orchestrator_profile` only controls who owns the root/orchestration task after fan-out. Also runs automatically every dispatcher tick when `kanban.auto_decompose: true` (the default). See [Auto vs Manual orchestration](/user-guide/features/kanban#auto-vs-manual-orchestration). |
| `gc` | Remove scratch workspaces for archived tasks. |

Examples:

```bash
# Create a second board and put a task on it without switching away.
jacky kanban boards create atm10-server --name "ATM10 Server" --icon 🎮
jacky kanban --board atm10-server create "Restart server" --assignee ops

# Switch the active board for subsequent calls.
jacky kanban boards switch atm10-server
jacky kanban list                  # shows atm10-server tasks

# Archive a board (recoverable) or hard-delete it.
jacky kanban boards rm atm10-server
jacky kanban boards rm atm10-server --delete
```

Board resolution order (highest precedence first): `--board <slug>` flag → `JACKY_KANBAN_BOARD` env var → `~/.jacky/kanban/current` file → `default`.

All actions are also available as a slash command in the gateway (`/kanban …`), with the same argument surface — including `boards` subcommands and the `--board` flag.

For the full design — comparison with Cline Kanban / Paperclip / NanoClaw / Gemini Enterprise, eight collaboration patterns, four user stories, concurrency correctness proof — see `docs/jacky-kanban-v1-spec.pdf` in the repository or the [Kanban user guide](/user-guide/features/kanban).

## `jacky project`

```bash
jacky project <create|list|show|add-folder|remove-folder|rename|set-primary|use|archive|restore|bind-board>
```

Projects are human-named workspaces that can span multiple folders / repos. They anchor desktop session grouping and, when bound to a kanban board, give tasks a deterministic worktree + branch convention. State is per-profile.

| Subcommand | Description |
|------------|-------------|
| `create` | Create a new project. |
| `list` (alias `ls`) | List projects. |
| `show` | Show a project's details. |
| `add-folder` | Add a folder / repo to a project. |
| `remove-folder` | Remove a folder from a project. |
| `rename` | Rename a project. |
| `set-primary` | Set the primary folder. |
| `use` | Set the active project. |
| `archive` | Archive a project (recoverable). |
| `restore` | Restore an archived project. |
| `bind-board` | Bind a kanban board to this project. |

## `jacky webhook`

```bash
jacky webhook <subscribe|list|remove|test>
```

Manage dynamic webhook subscriptions for event-driven agent activation. Requires the webhook platform to be enabled in config — if not configured, prints setup instructions.

| Subcommand | Description |
|------------|-------------|
| `subscribe` / `add` | Create a webhook route. Returns the URL and HMAC secret to configure on your service. |
| `list` / `ls` | Show all agent-created subscriptions. |
| `remove` / `rm` | Delete a dynamic subscription. Static routes from config.yaml are not affected. |
| `test` | Send a test POST to verify a subscription is working. |

### `jacky webhook subscribe`

```bash
jacky webhook subscribe <name> [options]
```

| Option | Description |
|--------|-------------|
| `--prompt` | Prompt template with `{dot.notation}` payload references. |
| `--events` | Comma-separated event types to accept (e.g. `issues,pull_request`). Empty = all. |
| `--description` | Human-readable description. |
| `--skills` | Comma-separated skill names to load for the agent run. |
| `--deliver` | Delivery target: `log` (default), `telegram`, `discord`, `slack`, `github_comment`. |
| `--deliver-chat-id` | Target chat/channel ID for cross-platform delivery. |
| `--secret` | Custom HMAC secret. Auto-generated if omitted. |
| `--deliver-only` | Skip the agent — deliver the rendered `--prompt` as the literal message. Zero LLM cost, sub-second delivery. Requires `--deliver` to be a real target (not `log`). |
| `--script` | Filter/transform script under `~/.jacky/scripts/`. The webhook payload is passed as JSON on stdin; JSON stdout replaces the payload, and empty stdout, `[SILENT]`, or a nonzero exit code ignores the webhook. See [Script Filters and Transforms](../user-guide/messaging/webhooks.md#script-filters-and-transforms). |

Subscriptions persist to `~/.jacky/webhook_subscriptions.json` and are hot-reloaded by the webhook adapter without a gateway restart.

## `jacky doctor`

```bash
jacky doctor [--fix]
```

| Option | Description |
|--------|-------------|
| `--fix` | Attempt automatic repairs where possible. |

## `jacky dump`

```bash
jacky dump [--show-keys]
```

Outputs a compact, plain-text summary of your entire Jacky setup. Designed to be copy-pasted into Discord, GitHub issues, or Telegram when asking for support — no ANSI colors, no special formatting, just data.

| Option | Description |
|--------|-------------|
| `--show-keys` | Show redacted API key prefixes (first and last 4 characters) instead of just `set`/`not set`. |

### What it includes

| Section | Details |
|---------|---------|
| **Header** | Jacky version, release date, git commit hash |
| **Environment** | OS, Python version, OpenAI SDK version |
| **Identity** | Active profile name, JACKY_HOME path |
| **Model** | Configured default model and provider |
| **Terminal** | Backend type (local, docker, ssh, etc.) |
| **API keys** | Presence check for all 22 provider/tool API keys |
| **Features** | Enabled toolsets, MCP server count, memory provider |
| **Services** | Gateway status, configured messaging platforms |
| **Workload** | Cron job counts, installed skill count |
| **Config overrides** | Any config values that differ from defaults |

### Example output

```
--- jacky dump ---
version:          0.8.0 (2026.4.8) [af4abd2f]
os:               Linux 6.14.0-37-generic x86_64
python:           3.11.14
openai_sdk:       2.24.0
profile:          default
jacky_home:      ~/.jacky
model:            anthropic/claude-opus-4.6
provider:         openrouter
terminal:         local

api_keys:
  openrouter           set
  openai               not set
  anthropic            set
  nous                 not set
  firecrawl            set
  ...

features:
  toolsets:           all
  mcp_servers:        0
  memory_provider:    built-in
  gateway:            running (systemd)
  platforms:          telegram, discord
  cron_jobs:          3 active / 5 total
  skills:             42

config_overrides:
  agent.max_turns: 250
  compression.threshold: 0.85
  display.streaming: True
--- end dump ---
```

### When to use

- Reporting a bug on GitHub — paste the dump into your issue
- Asking for help in Discord — share it in a code block
- Comparing your setup to someone else's
- Quick sanity check when something isn't working

:::tip
`jacky dump` is specifically designed for sharing. For interactive diagnostics, use `jacky doctor`. For a visual overview, use `jacky status`.
:::

## `jacky debug`

```bash
jacky debug share [options]
```

Upload a debug report (system info + recent logs) to a paste service and get a shareable URL. Useful for quick support requests — includes everything a helper needs to diagnose your issue.

| Option | Description |
|--------|-------------|
| `--lines <N>` | Number of log lines to include per log file (default: 200). |
| `--expire <days>` | Paste expiry in days (default: 7). |
| `--nous` | Upload to Nous-internal diagnostics storage instead of a public paste service. Use this when Nous support asks for a private diagnostic bundle. |
| `--local` | Print the report locally instead of uploading. |
| `--no-redact` | Disable upload-time secret redaction. By default, uploads are redacted. |

The report includes system info (OS, Python version, Jacky version), recent agent, gateway, GUI/dashboard, and desktop logs (512 KB limit per file), and redacted API key status. By default, uploads are redacted so secrets are not included.

Default uploads use public paste services tried in order: paste.rs, dpaste.com. `--nous` uploads the same debug bundle to private Nous diagnostics storage instead; the returned viewer link is for the Nous team and auto-deletes after 14 days.

### Examples

```bash
jacky debug share              # Upload debug report, print URL
jacky debug share --lines 500  # Include more log lines
jacky debug share --expire 30  # Keep paste for 30 days
jacky debug share --nous       # Upload a private diagnostics bundle for Nous support
jacky debug share --local      # Print report to terminal (no upload)
```

## `jacky backup`

```bash
jacky backup [options]
```

Create a zip archive of your Jacky configuration, skills, sessions, and data. The backup excludes the jacky-agent codebase itself.

| Option | Description |
|--------|-------------|
| `-o`, `--output <path>` | Output path for the zip file (default: `~/jacky-backup-<timestamp>.zip`). |
| `-q`, `--quick` | Quick snapshot: only critical state files (config.yaml, state.db, .env, auth, cron jobs). Much faster than a full backup. |
| `-l`, `--label <name>` | Label for the snapshot (only used with `--quick`). |

The backup uses SQLite's `backup()` API for safe copying, so it works correctly even when Jacky is running (WAL-mode safe).

**What's excluded from the zip:**

- `*.db-wal`, `*.db-shm`, `*.db-journal` — SQLite's WAL / shared-memory / journal sidecars. The `*.db` file already got a consistent snapshot via `sqlite3.backup()`; shipping the live sidecars alongside it would let a restore see a half-committed state.
- `checkpoints/` — per-session trajectory caches. Hash-keyed and regenerated per session; wouldn't port cleanly to another install anyway.
- The `jacky-agent` code itself (this is a user-data backup, not a repo snapshot).

### Examples

```bash
jacky backup                           # Full backup to ~/jacky-backup-*.zip
jacky backup -o /tmp/jacky.zip        # Full backup to specific path
jacky backup --quick                   # Quick state-only snapshot
jacky backup --quick --label "pre-upgrade"  # Quick snapshot with label
```

## `jacky checkpoints`

```bash
jacky checkpoints [COMMAND]
```

Inspect and manage the shadow git store at `~/.jacky/checkpoints/` — the storage layer behind the in-session `/rollback` command. Safe to run any time; does not require the agent to be running.

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Show total size, project count, and per-project breakdown. Bare `jacky checkpoints` is equivalent. |
| `list` | Alias for `status`. |
| `prune` | Force a cleanup sweep — delete orphan and stale projects, GC the store, enforce the size cap. Ignores the 24h idempotency marker. |
| `clear` | Delete the entire checkpoint base. Irreversible; asks for confirmation unless `-f`. |
| `clear-legacy` | Delete only the `legacy-<timestamp>/` archives produced by the v1→v2 migration. |

### Options

| Option | Subcommand | Description |
|--------|------------|-------------|
| `--limit N` | `status`, `list` | Max projects to list (default 20). |
| `--retention-days N` | `prune` | Drop projects whose `last_touch` is older than N days (default 7). |
| `--max-size-mb N` | `prune` | After the orphan/stale pass, drop the oldest commit per project until total store size ≤ N MB (default 500). |
| `--keep-orphans` | `prune` | Skip deleting projects whose working directory no longer exists. |
| `-f`, `--force` | `clear`, `clear-legacy` | Skip the confirmation prompt. |

### Examples

```bash
jacky checkpoints                                  # status overview
jacky checkpoints prune --retention-days 3         # aggressive cleanup
jacky checkpoints prune --max-size-mb 200          # tighten size cap once
jacky checkpoints clear-legacy -f                  # drop v1 archive dirs
jacky checkpoints clear -f                         # wipe everything
```

See [Checkpoints and `/rollback`](../user-guide/checkpoints-and-rollback.md) for the full architecture and the in-session commands.

## `jacky import`

```bash
jacky import <zipfile> [options]
```

Restore a previously created Jacky backup into your Jacky home directory. All files in the archive overwrite existing files in your Jacky home; `--force` only skips the confirmation prompt that fires when the target already has a Jacky installation.

| Option | Description |
|--------|-------------|
| `-f`, `--force` | Skip the existing-installation confirmation prompt. |

:::warning
Stop the gateway before importing to avoid conflicts with running processes.
:::

### Examples
```bash
jacky import ~/jacky-backup-20260423.zip           # Prompts before overwriting existing config
jacky import ~/jacky-backup-20260423.zip --force   # Overwrite without prompting
```

## `jacky logs`

```bash
jacky logs [log_name] [options]
```

View, tail, and filter Jacky log files. All logs are stored in `~/.jacky/logs/` (or `<profile>/logs/` for non-default profiles).

### Log files

| Name | File | What it captures |
|------|------|-----------------|
| `agent` (default) | `agent.log` | All agent activity — API calls, tool dispatch, session lifecycle (INFO and above) |
| `errors` | `errors.log` | Warnings and errors only — a filtered subset of agent.log |
| `gateway` | `gateway.log` | Messaging gateway activity — platform connections, message dispatch, webhook events |
| `gui` | `gui.log` | Dashboard / TUI-gateway / PTY-bridge / websocket events |
| `desktop` | `desktop.log` | Electron desktop app — boot, backend spawn output, and recent Python tracebacks |

### Options

| Option | Description |
|--------|-------------|
| `log_name` | Which log to view: `agent` (default), `errors`, `gateway`, or `list` to show available files with sizes. |
| `-n`, `--lines <N>` | Number of lines to show (default: 50). |
| `-f`, `--follow` | Follow the log in real time, like `tail -f`. Press Ctrl+C to stop. |
| `--level <LEVEL>` | Minimum log level to show: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `--session <ID>` | Filter lines containing a session ID substring. |
| `--since <TIME>` | Show lines from a relative time ago: `30m`, `1h`, `2d`, etc. Supports `s` (seconds), `m` (minutes), `h` (hours), `d` (days). |
| `--component <NAME>` | Filter by component: `gateway`, `agent`, `tools`, `cli`, `cron`. |

### Examples

```bash
# View the last 50 lines of agent.log (default)
jacky logs

# Follow agent.log in real time
jacky logs -f

# View the last 100 lines of gateway.log
jacky logs gateway -n 100

# Show only warnings and errors from the last hour
jacky logs --level WARNING --since 1h

# Filter by a specific session
jacky logs --session abc123

# Follow errors.log, starting from 30 minutes ago
jacky logs errors --since 30m -f

# List all log files with their sizes
jacky logs list
```

### Filtering

Filters can be combined. When multiple filters are active, a log line must pass **all** of them to be shown:

```bash
# WARNING+ lines from the last 2 hours containing session "tg-12345"
jacky logs --level WARNING --since 2h --session tg-12345
```

Lines without a parseable timestamp are included when `--since` is active (they may be continuation lines from a multi-line log entry). Lines without a detectable level are included when `--level` is active.

### Log rotation

Jacky uses Python's `RotatingFileHandler`. Old logs are rotated automatically — look for `agent.log.1`, `agent.log.2`, etc. The `jacky logs list` subcommand shows all log files including rotated ones.


## `jacky prompt-size`

```bash
jacky prompt-size [--platform <name>] [--json]
```

Reports the fixed prompt budget for a fresh session — what gets sent on every
API call *before* any conversation content. Useful when a downstream adapter or
proxy has a tighter prompt budget than the model's context window, or when you
want to see which block (skills index, memory, profile) dominates.

It builds the same system prompt the agent would, then breaks it down:

- **System prompt total** — full assembled prompt (identity, guidance, skills
  index, context files, memory, profile, timestamp).
- **Skills index** — the `<available_skills>` block. This is often the largest
  single block when many skills are installed.
- **Memory** and **user profile** — your `MEMORY.md` / `USER.md` snapshots.
- **Prompt tiers** — stable / context / volatile, matching how Jacky layers
  the prompt for cache-friendliness.
- **Tool schemas** — the JSON for all enabled tools (the other half of the
  fixed per-call payload).

Runs entirely offline — no API call, works with no credentials configured.

```bash
# Human-readable breakdown for the CLI platform (default)
jacky prompt-size

# Simulate a messaging platform's prompt (different platform hint)
jacky prompt-size --platform telegram

# Machine-readable output for scripts
jacky prompt-size --json
```

:::tip
The skills index and tool schemas scale with how many skills and tools you have
enabled. To shrink the prompt, disable unused toolsets (`jacky tools`) or
uninstall skills you don't need (`jacky skills`). Context files (AGENTS.md,
.cursorrules) in your current directory also count toward the total.
:::

## `jacky config`

```bash
jacky config <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `show` | Show current config values. |
| `edit` | Open `config.yaml` in your editor. |
| `set <key> <value>` | Set a config value. |
| `path` | Print the config file path. |
| `env-path` | Print the `.env` file path. |
| `check` | Check for missing or stale config. |
| `migrate` | Add newly introduced options interactively. |

## `jacky pairing`

```bash
jacky pairing <list|approve|revoke|clear-pending>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show pending and approved users. |
| `approve <platform> <code>` | Approve a pairing code. |
| `revoke <platform> <user-id>` | Revoke a user's access. |
| `clear-pending` | Clear pending pairing codes. |

## `jacky skills`

```bash
jacky skills <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `browse` | Paginated browser for skill registries. |
| `search` | Search skill registries. |
| `install` | Install a skill. |
| `inspect` | Preview a skill without installing it. |
| `list` | List installed skills. |
| `check` | Check installed hub skills for upstream updates. |
| `update` | Reinstall hub skills with upstream changes when available. |
| `audit` | Re-scan installed hub skills. |
| `uninstall` | Remove a hub-installed skill. |
| `reset` | Un-stick a bundled skill flagged as `user_modified` by clearing its manifest entry. With `--restore`, also replaces the user copy with the bundled version. |
| `opt-out` | Stop bundled skills from being seeded into the active profile. Writes a `.no-bundled-skills` marker so the installer, `jacky update`, and any sync skip bundled-skill seeding. Safe by default — nothing on disk is touched. With `--remove`, also deletes already-present bundled skills that are **unmodified** (user-edited, hub-installed, and hand-written skills are never removed; previews and confirms first, `--yes` to skip). |
| `opt-in` | Undo `opt-out` by removing the `.no-bundled-skills` marker so bundled skills are seeded again on the next `jacky update`. With `--sync`, re-seed immediately. |
| `publish` | Publish a skill to a registry. |
| `snapshot` | Export/import skill configurations. |
| `tap` | Manage custom skill sources. |
| `config` | Interactive enable/disable configuration for skills by platform. |

Common examples:

```bash
jacky skills browse
jacky skills browse --source official
jacky skills search react --source skills-sh
jacky skills search https://mintlify.com/docs --source well-known
jacky skills inspect official/security/1password
jacky skills inspect skills-sh/vercel-labs/json-render/json-render-react
jacky skills install official/migration/openclaw-migration
jacky skills install skills-sh/anthropics/skills/pdf --force
jacky skills install https://sharethis.chat/SKILL.md                     # Direct URL (single-file SKILL.md)
jacky skills install https://example.com/SKILL.md --name my-skill        # Override name when frontmatter has none
jacky skills check
jacky skills update
jacky skills config
jacky skills reset google-workspace
jacky skills reset google-workspace --restore --yes
jacky skills opt-out                  # stop future bundled-skill seeding (nothing deleted)
jacky skills opt-out --remove --yes   # also delete UNMODIFIED bundled skills
jacky skills opt-in --sync            # undo: remove marker and re-seed now
```

Notes:
- `--force` can override non-dangerous policy blocks for third-party/community skills.
- `--force` does not override a `dangerous` scan verdict.
- `--source skills-sh` searches the public `skills.sh` directory.
- `--source well-known` lets you point Jacky at a site exposing `/.well-known/skills/index.json`.
- `--source browse-sh` searches [browse.sh](https://browse.sh)'s catalog of 200+ site-specific browser-automation skills. Identifiers look like `browse-sh/airbnb.com/search-listings-ddgioa`.
- Passing an `http(s)://…/*.md` URL installs a single-file SKILL.md directly. When frontmatter has no `name:` and the URL slug isn't a valid identifier, an interactive terminal prompts for a name; non-interactive surfaces (`/skills install` inside the TUI, gateway platforms) require `--name <x>` instead.

## `jacky bundles`

```bash
jacky bundles <subcommand>
```

Skill bundles group several skills under one `/<bundle-name>` slash command. Invoking the bundle loads every referenced skill into a single combined user message. Storage: `~/.jacky/skill-bundles/<slug>.yaml`. See [Skill Bundles](../user-guide/features/skills.md#skill-bundles) for the YAML schema and behavior.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `list` | List installed bundles (default when no subcommand given) |
| `show <name>` | Show one bundle's name, description, skills, and file path |
| `create <name>` | Create a new bundle. Pass `--skill <id>` (repeat) or omit for interactive entry. `--description`, `--instruction`, `--force` available. |
| `delete <name>` | Remove a bundle file |
| `reload` | Re-scan `~/.jacky/skill-bundles/` and report added/removed bundles |

Examples:

```bash
jacky bundles create backend-dev \
  --skill github-code-review \
  --skill test-driven-development \
  --skill github-pr-workflow \
  -d "Backend feature work"

jacky bundles list
jacky bundles show backend-dev
jacky bundles delete backend-dev
```

In a chat session, `/bundles` lists installed bundles and `/<bundle-name>` loads one.

## `jacky curator`

```bash
jacky curator <subcommand>
```

The curator is an auxiliary-model background task that periodically reviews agent-created skills, prunes stale ones, consolidates overlaps, and archives obsolete skills. Bundled and hub-installed skills are never touched. Archives are recoverable; auto-deletion never happens.

| Subcommand | Description |
|------------|-------------|
| `status` | Show curator status and skill stats |
| `run` | Trigger a curator review now (blocks until the LLM pass finishes) |
| `run --background` | Start the LLM pass in a background thread and return immediately |
| `run --dry-run` | Preview only — produce the review report with no mutations |
| `backup` | Take a manual tar.gz snapshot of `~/.jacky/skills/` (curator also snapshots automatically before every real run) |
| `rollback` | Restore `~/.jacky/skills/` from a snapshot (defaults to newest) |
| `rollback --list` | List available snapshots |
| `rollback --id <ts>` | Restore a specific snapshot by id |
| `rollback -y` | Skip the confirmation prompt |
| `pause` | Pause the curator until resumed |
| `resume` | Resume a paused curator |
| `pin <skill>` | Pin a skill so the curator never auto-transitions it |
| `unpin <skill>` | Unpin a skill |
| `restore <skill>` | Restore an archived skill |
| `archive <skill>` | Archive a skill manually |
| `prune` | Manually prune skills the curator would normally clean up |
| `list-archived` | List archived skills (recoverable via `restore`) |

On a fresh install the first scheduled pass is deferred by one full `interval_hours` (7 days by default) — the gateway will not curate immediately on the first tick after `jacky update`. Use `jacky curator run --dry-run` to preview before that happens.

See [Curator](../user-guide/features/curator.md) for behavior and config.

## `jacky moa`

Configure named Mixture of Agents presets. Presets appear as selectable models under a `Mixture of Agents` provider in every model picker; `/moa <prompt>` runs one prompt through the default preset.

```bash
jacky moa list
jacky moa configure [name]
jacky moa delete <name>
```

`jacky moa configure` reuses Jacky' provider → model picker for each reference model and the aggregator. A preset is an execution-mode configuration, not a primary model or provider.

## `jacky fallback`

```bash
jacky fallback <subcommand>
```

Manage the fallback provider chain. Fallback providers are tried in order when the primary model fails with rate-limit, overload, or connection errors.

| Subcommand | Description |
|------------|-------------|
| `list` (alias: `ls`) | Show the current fallback chain (default when no subcommand) |
| `add` | Pick a provider + model (same picker as `jacky model`) and append to the chain |
| `remove` (alias: `rm`) | Pick an entry to delete from the chain |
| `clear` | Remove all fallback entries |

See [Fallback Providers](../user-guide/features/fallback-providers.md).

## `jacky hooks`

```bash
jacky hooks <subcommand>
```

Inspect shell-script hooks declared in `~/.jacky/config.yaml`, test them against synthetic payloads, and manage the first-use consent allowlist at `~/.jacky/shell-hooks-allowlist.json`.

| Subcommand | Description |
|------------|-------------|
| `list` (alias: `ls`) | List configured hooks with matcher, timeout, and consent status |
| `test <event>` | Fire every hook matching `<event>` against a synthetic payload |
| `revoke` (aliases: `remove`, `rm`) | Remove a command's allowlist entries (takes effect on next restart) |
| `doctor` | Check each configured hook: exec bit, allowlist, mtime drift, JSON validity, and synthetic run timing |

See [Hooks](../user-guide/features/hooks.md) for event signatures and payload shapes.

## `jacky memory`

```bash
jacky memory <subcommand>
```

Set up and manage external memory provider plugins. Available providers: honcho, openviking, mem0, hindsight, holographic, retaindb, byterover, supermemory. Only one external provider can be active at a time. Built-in memory (MEMORY.md/USER.md) is always active.

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `setup` | Interactive provider selection and configuration. |
| `status` | Show current memory provider config. |
| `off` | Disable external provider (built-in only). |

:::info Provider-specific subcommands
When an external memory provider is active, it may register its own top-level `jacky <provider>` command for provider-specific management (e.g. `jacky honcho` when Honcho is active). Inactive providers do not expose their subcommands. Run `jacky --help` to see what's currently wired in.
:::

## `jacky acp`

```bash
jacky acp
```

Starts Jacky as an ACP (Agent Client Protocol) stdio server for editor integration.

Related entrypoints:

```bash
jacky-acp
python -m acp_adapter
```

Install support first:

```bash
cd ~/.jacky/jacky-agent && uv pip install -e '.[acp]'
```

See [ACP Editor Integration](../user-guide/features/acp.md) and [ACP Internals](../developer-guide/acp-internals.md).

## `jacky mcp`

```bash
jacky mcp <subcommand>
```

Manage MCP (Model Context Protocol) server configurations and run Jacky as an MCP server.

| Subcommand | Description |
|------------|-------------|
| *(none)* or `picker` | Interactive catalog picker — browse Nous-approved MCPs and install/enable/disable. |
| `catalog` | List Nous-approved MCPs (plain text, scriptable). |
| `install <name>` | Install a catalog entry (e.g. `jacky mcp install n8n`). |
| `serve [-v\|--verbose]` | Run Jacky as an MCP server — expose conversations to other agents. |
| `add <name> [--url URL] [--command CMD] [--auth oauth\|header] [--args ...]` | Add a custom MCP server with automatic tool discovery. `--args` passes the remaining argv to the stdio command, so put it last. |
| `remove <name>` (alias: `rm`) | Remove an MCP server from config. |
| `list` (alias: `ls`) | List configured MCP servers. |
| `test <name>` | Test connection to an MCP server. |
| `configure <name>` (alias: `config`) | Toggle tool selection for a server. |
| `login <name>` | Force re-authentication for an OAuth-based MCP server. |

See [MCP Config Reference](./mcp-config-reference.md), [Use MCP with Jacky](../guides/use-mcp-with-jacky.md), and [MCP Server Mode](../user-guide/features/mcp.md#running-jacky-as-an-mcp-server).

## `jacky plugins`

```bash
jacky plugins [subcommand]
```

Unified plugin management — general plugins, memory providers, and context engines in one place. Running `jacky plugins` with no subcommand opens a composite interactive screen with two sections:

- **General Plugins** — multi-select checkboxes to enable/disable installed plugins
- **Provider Plugins** — single-select configuration for Memory Provider and Context Engine. Press ENTER on a category to open a radio picker.

| Subcommand | Description |
|------------|-------------|
| *(none)* | Composite interactive UI — general plugin toggles + provider plugin configuration. |
| `install <identifier> [--force]` | Install a plugin from a Git URL or `owner/repo`. |
| `update <name>` | Pull latest changes for an installed plugin. |
| `remove <name>` (aliases: `rm`, `uninstall`) | Remove an installed plugin. |
| `enable <name>` | Enable a disabled plugin. |
| `disable <name>` | Disable a plugin without removing it. |
| `list` (alias: `ls`) | List installed plugins with enabled/disabled status. |

Provider plugin selections are saved to `config.yaml`:
- `memory.provider` — active memory provider (empty = built-in only)
- `context.engine` — active context engine (`"compressor"` = built-in default)

General plugin disabled list is stored in `config.yaml` under `plugins.disabled`.

See [Plugins](../user-guide/features/plugins.md) and [Build a Jacky Plugin](../developer-guide/plugins/index.md).

## `jacky tools`

```bash
jacky tools [--summary]
```

| Option | Description |
|--------|-------------|
| `--summary` | Print the current enabled-tools summary and exit. |

Without `--summary`, this launches the interactive per-platform tool configuration UI.

## `jacky computer-use`

```bash
jacky computer-use <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `install` | Run the upstream cua-driver installer (macOS, Windows, and Linux). |
| `install --upgrade` | Re-run the installer even if cua-driver is already on PATH. The upstream script always pulls the latest release, so this performs an in-place upgrade. |
| `status` | Print whether `cua-driver` is on `$PATH` and which version is installed. |

`jacky computer-use install` is the stable entry point for installing the
[cua-driver](https://github.com/trycua/cua) binary used by the
`computer_use` toolset. It runs the same upstream installer that
`jacky tools` invokes when you first enable Computer Use, so it's safe
to use for re-running the install if the toolset toggle didn't trigger
it (for example, on returning-user setups).

`jacky update` automatically re-runs the upstream installer at the end
of the update if cua-driver is on PATH, so most users will not need to
call `--upgrade` manually. Use it when upstream ships a fix you want
right now without waiting for the next Jacky update.

## `jacky pets`

```bash
jacky pets <list|install|select|show|off|scale|remove|doctor>
```

[Petdex](https://github.com/crafter-station/petdex) is a public gallery of animated sprite pets for coding agents. Install one and Jacky shows it reacting to agent activity across the CLI, TUI, and desktop app.

| Subcommand | Description |
|------------|-------------|
| `list` | Browse the petdex gallery. |
| `install` | Install a pet from the gallery. |
| `select` | Set the active pet (writes `display.pet.*`). |
| `show` | Animate the active pet in the terminal. |
| `off` | Disable the pet display. |
| `scale` | Resize the pet everywhere (`display.pet.scale`). |
| `remove` | Delete an installed pet. |
| `doctor` | Check pet setup + terminal graphics support. |

You can also generate a brand-new pet from a text description with the `/hatch` slash command. See [Pets](../user-guide/features/pets.md).

## `jacky sessions`

```bash
jacky sessions <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `list` | List recent sessions. |
| `browse` | Interactive session picker with search and resume. |
| `export <output> [--session-id ID]` | Export sessions to JSONL. |
| `delete <session-id>` | Delete one session. |
| `prune` | Delete sessions matching filters: time bounds `--older-than`/`--newer-than`/`--before`/`--after` (durations like `5h`/`2d`, bare days, or ISO timestamps); attributes `--source`, `--title`, `--model`, `--provider`, `--branch`, `--end-reason`, `--user`, `--chat-id`, `--chat-type`, `--cwd`; numeric bounds `--min/--max-messages`, `--min/--max-tokens`, `--min/--max-cost`, `--min/--max-tool-calls`; plus `--include-archived`, `--dry-run`, `--yes`. Default: older than 90 days. |
| `archive` | Bulk-archive (soft-hide, no deletion) sessions matching the same filters as `prune`. Requires at least one filter. |
| `stats` | Show session-store statistics. |
| `rename <session-id> <title>` | Set or change a session title. |

## `jacky insights`

```bash
jacky insights [--days N] [--source platform]
```

| Option | Description |
|--------|-------------|
| `--days <n>` | Analyze the last `n` days (default: 30). |
| `--source <platform>` | Filter by source such as `cli`, `telegram`, or `discord`. |

## `jacky claw`

```bash
jacky claw migrate [options]
```

Migrate your OpenClaw setup to Jacky. Reads from `~/.openclaw` (or a custom path) and writes to `~/.jacky`. Automatically detects legacy directory names (`~/.clawdbot`, `~/.moltbot`) and config filenames (`clawdbot.json`, `moltbot.json`).

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview what would be migrated without writing anything. |
| `--preset <name>` | Migration preset: `full` (all compatible settings) or `user-data` (excludes infrastructure config). Neither preset imports secrets — pass `--migrate-secrets` explicitly. |
| `--overwrite` | Overwrite existing Jacky files on conflicts (default: refuse to apply when the plan has conflicts). |
| `--migrate-secrets` | Include API keys in migration. Required even under `--preset full`. |
| `--no-backup` | Skip the pre-migration zip snapshot of `~/.jacky/` (by default a single restore-point archive is written to `~/.jacky/backups/pre-migration-*.zip` before apply; restorable with `jacky import`). |
| `--source <path>` | Custom OpenClaw directory (default: `~/.openclaw`). |
| `--workspace-target <path>` | Target directory for workspace instructions (AGENTS.md). |
| `--skill-conflict <mode>` | Handle skill name collisions: `skip` (default), `overwrite`, or `rename`. |
| `--yes` | Skip the confirmation prompt. |

### What gets migrated

The migration covers 30+ categories across persona, memory, skills, model providers, messaging platforms, agent behavior, session policies, MCP servers, TTS, and more. Items are either **directly imported** into Jacky equivalents or **archived** for manual review.

**Directly imported:** SOUL.md, MEMORY.md, USER.md, AGENTS.md, skills (4 source directories), default model, custom providers, MCP servers, messaging platform tokens and allowlists (Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost), agent defaults (reasoning effort, compression, human delay, timezone, sandbox), session reset policies, approval rules, TTS config, browser settings, tool settings, exec timeout, command allowlist, gateway config, and API keys from 3 sources.

**Archived for manual review:** Cron jobs, plugins, hooks/webhooks, memory backend (QMD), skills registry config, UI/identity, logging, multi-agent setup, channel bindings, IDENTITY.md, TOOLS.md, HEARTBEAT.md, BOOTSTRAP.md.

**API key resolution** checks three sources in priority order: config values → `~/.openclaw/.env` → `auth-profiles.json`. All token fields handle plain strings, env templates (`${VAR}`), and SecretRef objects.

For the complete config key mapping, SecretRef handling details, and post-migration checklist, see the **[full migration guide](../guides/migrate-from-openclaw.md)**.

### Examples

```bash
# Preview what would be migrated
jacky claw migrate --dry-run

# Full migration (all compatible settings, no secrets)
jacky claw migrate --preset full

# Full migration including API keys
jacky claw migrate --preset full --migrate-secrets

# Migrate user data only (no secrets), overwrite conflicts
jacky claw migrate --preset user-data --overwrite

# Migrate from a custom OpenClaw path
jacky claw migrate --source /home/user/old-openclaw
```

## `jacky serve`

```bash
jacky serve [options]
```

Start the Jacky **backend server** — the JSON-RPC/WebSocket gateway the [desktop app](/user-guide/desktop) and remote clients connect to. It is the same server `jacky dashboard` runs, but **headless**: it never opens a browser UI. The desktop app launches its own `jacky serve` backend; use this command directly when you want a headless backend on a remote host. Accepts the same `--host` / `--port` / `--insecure` / `--skip-build` / `--stop` / `--status` options as `jacky dashboard` below (a non-loopback bind engages the same auth gate). Requires the `[web]` extra; the embedded Chat socket additionally needs `[pty]` on a POSIX host.

## `jacky dashboard`

```bash
jacky dashboard [options]
```

Launch the web dashboard — a browser-based UI for managing configuration, API keys, and monitoring sessions. (For a headless backend with no browser UI — e.g. what the desktop app spawns — use [`jacky serve`](#jacky-serve) above.) Requires `cd ~/.jacky/jacky-agent && uv pip install -e ".[web]"` (FastAPI + Uvicorn). The embedded browser Chat tab is always available and additionally needs the `pty` extra (`cd ~/.jacky/jacky-agent && uv pip install -e ".[web,pty]"`) plus a POSIX PTY environment such as Linux, macOS, or WSL2. See [Web Dashboard](/user-guide/features/web-dashboard) for full documentation.

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `9119` | Port to run the web server on |
| `--host` | `127.0.0.1` | Bind address |
| `--no-open` | — | Don't auto-open the browser |
| `--insecure` | off | **Deprecated / no-op.** Formerly bypassed auth on a non-loopback bind. Since the June 2026 hardening a public bind *always* requires an auth provider (password or OAuth). Bind `127.0.0.1` and tunnel to keep it local. |
| `--skip-build` | off | Skip the web UI build step and serve the existing `dist` directly. Useful for non-interactive contexts (Windows Scheduled Tasks, CI) where npm isn't available. Pre-build with `cd web && npm run build`. |
| `--isolated` | off | When launched from a named profile (`worker dashboard`), run a dedicated per-profile server instead of routing to the machine dashboard. |
| `--stop` | — | Stop running `jacky dashboard` processes and exit. |
| `--status` | — | List running `jacky dashboard` processes and exit. |

### `jacky dashboard register`

Register this install as a self-hosted dashboard with your Nous Portal account. Creates an OAuth client, writes `JACKY_DASHBOARD_OAUTH_CLIENT_ID` into `~/.jacky/.env`, and prints how to engage the login gate. Requires being logged in (`jacky setup`).

| Option | Description |
|--------|-------------|
| `--name` | Human-readable label for the dashboard (default: auto-generated). |
| `--redirect-uri` | Public HTTPS OAuth redirect URI (e.g. `https://jacky.example.com/auth/callback`). Omit for localhost-only use. |
| `--portal-url` | Override the Nous Portal base URL for registration (default: the portal you logged into). Also settable via `JACKY_DASHBOARD_PORTAL_URL`. |

```bash
# Default — opens browser to http://127.0.0.1:9119
jacky dashboard

# Custom port, no browser
jacky dashboard --port 8080 --no-open

# From a profile alias — routes to the machine dashboard with the
# profile preselected in the sidebar switcher (attach if running)
worker dashboard
```

## `jacky profile`

```bash
jacky profile <subcommand>
```

Manage profiles — multiple isolated Jacky instances, each with its own config, sessions, skills, and home directory.

| Subcommand | Description |
|------------|-------------|
| `list` | List all profiles. |
| `use <name>` | Set a sticky default profile. |
| `create <name> [--clone] [--clone-all] [--clone-from <source>] [--no-alias]` | Create a new profile. `--clone` copies config, `.env`, `SOUL.md`, and skills from the active profile. `--clone-all` copies all state. `--clone-from` specifies a source profile and implies config clone unless paired with `--clone-all`. |
| `delete <name> [-y]` | Delete a profile. |
| `show <name>` | Show profile details (home directory, config, etc.). |
| `alias <name> [--remove] [--name NAME]` | Manage wrapper scripts for quick profile access. |
| `rename <old> <new>` | Rename a profile. |
| `export <name> [-o FILE]` | Export a profile to a `.tar.gz` archive (local backup). |
| `import <archive> [--name NAME]` | Import a profile from a `.tar.gz` archive (local restore). |
| `install <source> [--name N] [--alias] [--force] [-y]` | Install a profile distribution from a git URL or local directory. |
| `update <name> [--force-config] [-y]` | Re-pull a distribution; preserves user data (memories, sessions, auth). |
| `info <name>` | Show a profile's distribution manifest (version, requirements, source). |

Examples:

```bash
jacky profile list
jacky profile create work --clone
jacky profile use work
jacky profile alias work --name h-work
jacky profile export work -o work-backup.tar.gz
jacky profile import work-backup.tar.gz --name restored
jacky profile install github.com/user/my-distro --alias
jacky profile update work
jacky -p work chat -q "Hello from work profile"
```

## `jacky completion`

```bash
jacky completion [bash|zsh|fish]
```

Print a shell completion script to stdout. Source the output in your shell profile for tab-completion of Jacky commands, subcommands, and profile names.

Examples:

```bash
# Bash
jacky completion bash >> ~/.bashrc

# Zsh
jacky completion zsh >> ~/.zshrc

# Fish
jacky completion fish > ~/.config/fish/completions/jacky.fish
```

## `jacky update`

```bash
jacky update [--gateway] [--check] [--no-backup] [--backup] [--yes]
```

Pulls the latest `jacky-agent` code and reinstalls dependencies in the managed venv, then re-runs the post-install hooks (MCP servers, skills sync, completion install). Safe to run on a live install. Use `--check` to see whether your checkout is behind `origin/main` without installing.

`jacky update` pulls the configured update branch (default: `main`). If your checkout is on another branch, Jacky may check out the update branch before pulling. Commit branch work before updating when you want to keep it outside the update autostash flow.

| Option | Description |
|--------|-------------|
| `--gateway` | Internal mode used by the messaging `/update` command. Uses file-based IPC for prompts and progress streaming instead of reading from terminal stdin. Not a gateway restart flag. |
| `--check` | Check whether an update is available without pulling, installing dependencies, or restarting anything. |
| `--no-backup` | Skip the pre-update backup for this run, even if `updates.pre_update_backup` is enabled in `config.yaml`. |
| `--backup` | Create a labeled pre-update snapshot of `JACKY_HOME` (config, auth, sessions, skills, pairing data) before pulling. Default is **off** — the previous always-backup behavior was adding minutes to every update on large homes. Flip it on permanently via `updates.pre_update_backup: true` in `config.yaml`. |
| `--yes`, `-y` | Assume yes for interactive prompts such as config migration and stash restore. API-key entry is skipped; run `jacky config migrate` separately for those. |

Additional behavior:

- **Gateway restart.** After a successful update, Jacky attempts to restart all running gateway profiles automatically so they pick up the new code. Use `jacky gateway restart` when you want to restart a gateway without applying an update.
- **Local source changes.** For git installs, dirty tracked files and untracked files are auto-stashed before branch checkout or pull (`git stash push --include-untracked`). Interactive terminal updates ask before restoring the stash. Non-interactive updates restore it by default; set `updates.non_interactive_local_changes: discard` only on managed installs where local source edits should be thrown away after a successful pull. If stash restore conflicts or the pull fails, the stash is left in place for manual recovery.
- **npm lockfile churn.** Before stashing or switching branches, Jacky makes a best-effort cleanup of tracked `package-lock.json` diffs produced by npm install/build steps. Commit or manually stash intentional lockfile edits before running `jacky update`.
- **Pairing data snapshot.** Even when `--backup` is off, `jacky update` takes a lightweight snapshot of `~/.jacky/pairing/` and the Feishu comment rules before `git pull`. You can roll it back with `jacky backup restore --state pre-update` if a pull rewrites a file you were editing.
- **Legacy `jacky.service` warning.** If Jacky detects a pre-rename `jacky.service` systemd unit (instead of the current `jacky-gateway.service`), it prints a one-time migration hint so you can avoid flap-loop issues.
- **Exit codes.** `0` on success, `1` on pull/install/post-install errors, `2` on unexpected working-tree changes that block `git pull`.

## Maintenance commands

| Command | Description |
|---------|-------------|
| `jacky version` | Print version information. |
| `jacky update` | Pull latest changes and reinstall dependencies. |
| `jacky postinstall` | Internal bootstrap. Runs once after the install script provisions Jacky (or after `jacky update`) to install non-Python dependencies that pip cannot provide — Node.js runtime, headless browser, ripgrep, ffmpeg — and then trigger `jacky setup` if the profile has not been configured yet. Safe to re-run idempotently. |
| `jacky uninstall [--full] [--gui] [--yes]` | Remove Jacky, optionally deleting all config/data. `--gui` removes only the desktop Chat GUI, leaving the agent intact; `--full` also deletes config/data; `--yes` skips prompts. |

## See also

- [Slash Commands Reference](./slash-commands.md)
- [CLI Interface](../user-guide/cli.md)
- [Sessions](../user-guide/sessions.md)
- [Skills System](../user-guide/features/skills.md)
- [Skins & Themes](../user-guide/features/skins.md)
