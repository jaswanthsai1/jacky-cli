<p align="center">
  <img src="https://raw.githubusercontent.com/jaswanthsai1/jacky-cli/main/assets/banner.jpeg" alt="Jacky CLI" width="600">
</p>

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:00FF41,50:00E5FF,100:9D00FF&height=120&section=header&animation=fadeIn" alt="divider"/>

<h1 align="center">jacky-cli-agent</h1>
<p align="center"><i>npm install shim for Jacky CLI — AI CLI, Automate.</i></p>

<p align="center">
  <a href="https://github.com/jaswanthsai1/jacky-cli/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-00FF41?style=for-the-badge&logo=opensourceinitiative&logoColor=black" alt="License: MIT"></a>
  <a href="https://github.com/jaswanthsai1"><img src="https://img.shields.io/badge/Author-jaswanthsai1-9D00FF?style=for-the-badge&logo=github&logoColor=white" alt="Author"></a>
  <img src="https://img.shields.io/badge/status-ONLINE-00FF41?style=for-the-badge&logo=statuspage&logoColor=black" alt="status">
</p>

**Designer / Author:** [Maturi Jaswanth Sai Madhu Mohan](https://github.com/jaswanthsai1)

Jacky is an AI agent CLI built to run wherever you want it — local model or
cloud, your choice of provider — with a bug-bounty/offensive-security
hunt-loop methodology built in from day one. One-command install, a full
tool-calling agent loop, a self-improving skill system, and live visibility
into every background agent it spawns.

**What this package actually is:** `jacky-cli-agent` is a small Node.js
bootstrap shim, not Jacky itself. On install it downloads the real
[`jacky-cli`](https://pypi.org/project/jacky-cli/) Python package into a
managed virtual environment under `~/.jacky`, exposes the `jacky` command on
your `PATH`, and keeps that managed install current on later
`npm install -g` runs. Prefer installing the Python package directly, or
building from source? See [Other install methods](#other-install-methods)
below.

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00E5FF,100:9D00FF" alt="divider"/>

## Install

```bash
npm install -g jacky-cli-agent
```

Then run:

```bash
jacky
```

Jacky checks for updates on startup and tells you when
`npm update -g jacky-cli-agent` is worth running.

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:9D00FF,100:00FF41" alt="divider"/>

## Requirements

- **Node.js** >= 16, to run this shim
- **Python** 3.11, 3.12, or 3.13 — installed automatically by the shim on
  supported platforms if missing
- **OS**: Linux, macOS, or Windows (native, or WSL)
- **Optional, for local models**: [Ollama](https://ollama.com) or another
  OpenAI-compatible local server, plus a GPU for anything beyond small models
  (CPU-only inference works, just slower)
- **Optional, for cloud models**: an API key for any OpenAI-compatible or
  Anthropic-compatible provider (OpenRouter, OpenAI, Anthropic, Google AI
  Studio, and others — bring your own key)

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00FF41,100:00E5FF" alt="divider"/>

## What Jacky can do

<table>
<tr><td><b>Dual local + cloud model support</b></td><td>Run entirely offline against <a href="https://ollama.com">Ollama</a> and any GGUF model — zero API cost, nothing leaves your machine — or point it at any OpenAI-compatible cloud provider (OpenRouter, direct OpenAI/Anthropic, Google AI Studio, and more). Switch providers any time with <code>jacky model</code>, no code changes.</td></tr>
<tr><td><b>Bundled offensive-security methodology</b></td><td>Ships with a real bug-bounty / red-team hunt-loop doctrine under <code>skills/</code>: scope → recon → rank → enumerate → test → validate → chain → report, plus finding-validation gates, evidence-hygiene discipline, and report-writing formulas.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks — skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Tool-calling and agentic by default</b></td><td>40+ built-in tools, an MCP client for connecting any MCP server, and a toolset system for scoping what's available per session.</td></tr>
<tr><td><b>Runs anywhere</b></td><td>Six terminal backends — local, Docker, SSH, Singularity, Modal, and Daytona. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand.</td></tr>
</table>

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00E5FF,100:9D00FF" alt="divider"/>

## Local model (Ollama) vs. cloud provider setup

Jacky supports both, and switching between them is a one-line config change.

**Local, zero API cost, fully offline:**

```bash
curl -fsSL https://ollama.com/install.sh | sh   # install Ollama
ollama pull qwen3:8b                            # or any tool-calling-capable model
jacky model                                     # pick Ollama + the model you pulled
```

**Cloud, any OpenAI-compatible provider:**

```bash
jacky model            # pick your provider, then paste its API key when prompted
# supports OpenRouter, OpenAI, Anthropic, Google AI Studio, z.ai, Kimi,
# MiniMax, Hugging Face, or your own OpenAI-compatible endpoint
```

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:9D00FF,100:00FF41" alt="divider"/>

## Getting Started

```bash
jacky              # Interactive CLI — start a conversation
jacky model        # Choose your LLM provider and model
jacky tools        # Configure which tools are enabled
jacky config set   # Set individual config values
jacky gateway      # Start the messaging gateway (Telegram, Discord, etc.)
jacky setup        # Run the full setup wizard (configures everything at once)
jacky update       # Update to the latest version
jacky doctor       # Diagnose any issues
```

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00FF41,100:00E5FF" alt="divider"/>

## CLI vs Messaging Quick Reference

Jacky has two entry points: start the terminal UI with `jacky`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | ---------------------------------------------------------------------------------- |
| Start chatting                 | `jacky`                                       | Run `jacky gateway setup` + `jacky gateway start`, then send the bot a message   |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                                |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                 |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:9D00FF,100:00FF41" alt="divider"/>

## Other install methods

**Native from source (Linux/macOS):**

```bash
curl -fsSL https://raw.githubusercontent.com/jaswanthsai1/jacky-cli/main/install.sh | bash
```

**Via pip (any OS with Python 3.11–3.13):**

```bash
pip install jacky-cli
```

**Windows (native, PowerShell):**

```powershell
git clone https://github.com/jaswanthsai1/jacky-cli.git
cd jacky-cli
powershell -ExecutionPolicy ByPass -File scripts\install.ps1
```

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00E5FF,100:9D00FF" alt="divider"/>

## Documentation

| Section                                                                                                                  | What's Covered                                                |
| ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [Quickstart](https://jaswanthsai1.github.io/jacky-cli/getting-started/quickstart)                                       | Install → setup → first conversation in 2 minutes             |
| [CLI Usage](https://jaswanthsai1.github.io/jacky-cli/user-guide/cli)                                                    | Commands, keybindings, personalities, sessions                |
| [Configuration](https://jaswanthsai1.github.io/jacky-cli/user-guide/configuration)                                      | Config file, providers, models, all options                   |
| [Messaging Gateway](https://jaswanthsai1.github.io/jacky-cli/user-guide/messaging/)                                     | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant     |
| [Security](https://jaswanthsai1.github.io/jacky-cli/user-guide/security)                                                | Command approval, DM pairing, container isolation              |
| [Tools & Toolsets](https://jaswanthsai1.github.io/jacky-cli/user-guide/features/tools)                                  | 40+ tools, toolset system, terminal backends                   |
| [Skills System](https://jaswanthsai1.github.io/jacky-cli/user-guide/features/skills)                                    | Procedural memory, Skills Hub, creating skills                 |
| [Memory](https://jaswanthsai1.github.io/jacky-cli/user-guide/features/memory)                                           | Persistent memory, user profiles, best practices               |
| [MCP Integration](https://jaswanthsai1.github.io/jacky-cli/user-guide/features/mcp)                                     | Connect any MCP server for extended capabilities               |
| [Cron Scheduling](https://jaswanthsai1.github.io/jacky-cli/user-guide/features/cron)                                    | Scheduled tasks with platform delivery                         |
| [Providers](https://jaswanthsai1.github.io/jacky-cli/integrations/providers)                                            | Local (Ollama) and cloud (OpenAI-compatible) providers         |
| [Architecture](https://jaswanthsai1.github.io/jacky-cli/developer-guide/architecture)                                   | Project structure, agent loop, key classes                     |
| [CLI Reference](https://jaswanthsai1.github.io/jacky-cli/reference/cli-commands)                                        | All commands and flags                                         |
| [Environment Variables](https://jaswanthsai1.github.io/jacky-cli/reference/environment-variables)                       | Complete env var reference                                     |
| **[Hunt-Loop Methodology](https://github.com/jaswanthsai1/jacky-cli/blob/main/docs/METHODOLOGY.md)**                     | **Bundled bug-bounty/offensive-security doctrine and skills**  |

Full docs site: **<https://jaswanthsai1.github.io/jacky-cli/>**

<img width="100%" height="4" src="https://capsule-render.vercel.app/api?type=rect&color=0:00FF41,100:00E5FF" alt="divider"/>

## Community & Links

- 💻 [Source repository](https://github.com/jaswanthsai1/jacky-cli)
- 🐛 [Issues](https://github.com/jaswanthsai1/jacky-cli/issues)
- 📦 [PyPI package](https://pypi.org/project/jacky-cli/)
- 🚀 [Releases](https://github.com/jaswanthsai1/jacky-cli/releases)
- 📚 [Skills Hub (agentskills.io)](https://agentskills.io)
- 🤝 [Contributing guide](https://github.com/jaswanthsai1/jacky-cli/blob/main/.github/CONTRIBUTING.md)

## About

Jacky is an AI agent CLI built to run wherever you want it — local model or
cloud, your choice of provider — with a bug-bounty/offensive-security
hunt-loop methodology built in from day one, not bolted on. It ships with a
one-command install, a full tool-calling agent loop, a self-improving skill
system, and live visibility into every background agent it spawns.

**Designed and maintained by [Maturi Jaswanth Sai Madhu Mohan](https://github.com/jaswanthsai1).**

## License

MIT — see [LICENSE](https://github.com/jaswanthsai1/jacky-cli/blob/main/LICENSE) for full attribution details.

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:9D00FF,50:00E5FF,100:00FF41&height=100&section=footer" alt="footer"/>
