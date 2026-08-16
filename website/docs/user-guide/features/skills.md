---
sidebar_position: 2
title: "Skills System"
description: "On-demand knowledge documents — progressive disclosure, agent-managed skills, and the Skills Hub"
---

# Skills System

Skills are on-demand knowledge documents the agent can load when needed. They follow a **progressive disclosure** pattern to minimize token usage and are compatible with the [agentskills.io](https://agentskills.io/specification) open standard.

All skills live in **`~/.jacky/skills/`** — the primary directory and source of truth. On fresh install, bundled skills are copied from the repo. Hub-installed and agent-created skills also go here. The agent can modify or delete any skill.

You can also point Jacky at **external skill directories** — additional folders scanned alongside the local one. See [External Skill Directories](#external-skill-directories) below.

See also:

- [Bundled Skills Catalog](/reference/skills-catalog)
- [Official Optional Skills Catalog](/reference/optional-skills-catalog)

## Starting with a blank slate

By default every profile is seeded with the bundled skill catalog, and each `jacky update` adds any newly bundled skills. If you want a profile with **no bundled skills** — and that stays empty across updates — you have two paths:

**At install time** (applies to the default `~/.jacky` profile):

```bash
curl -fsSL https://jacky-agent.nousresearch.com/install.sh | bash -s -- --no-skills
```

**At profile-create time** (named profiles):

```bash
jacky profile create research --no-skills
```

**On an already-installed profile** (default or named), toggle it at runtime:

```bash
jacky skills opt-out            # stop future seeding — nothing on disk is touched
jacky skills opt-out --remove   # also delete UNMODIFIED bundled skills (confirms first)
jacky skills opt-in --sync      # undo: remove the marker and re-seed now
```

All three paths write a `.no-bundled-skills` marker into the profile directory. While the marker is present, the installer, `jacky update`, and any skill sync all skip bundled-skill seeding for that profile. Delete the marker (or run `jacky skills opt-in`) to re-enable.

:::note Safe by default
`jacky skills opt-out` only stops *future* seeding — it never deletes anything already on disk. The optional `--remove` flag deletes bundled skills **only** when they are unmodified (byte-identical to the version Jacky installed). Skills you have edited, skills installed from the hub, and skills you wrote yourself are always kept.
:::

## Using Skills

Every installed skill is automatically available as a slash command:

```bash
# In the CLI or any messaging platform:
/gif-search funny cats
/axolotl help me fine-tune Llama 3 on my dataset
/github-pr-workflow create a PR for the auth refactor
/plan design a rollout for migrating our auth provider

# Just the skill name loads it and lets the agent ask what you need:
/excalidraw
```

### Stacking multiple skills in one command

You can invoke several skills in a single message by chaining slash commands
at the start — every leading `/skill` token (up to 5) is loaded, and the rest
becomes your instruction:

```bash
/github-pr-workflow /test-driven-development fix issue #123 and open a PR
```

Parsing stops at the first token that isn't an installed skill, so arguments
that happen to start with `/` (like file paths) are never swallowed:

```bash
/ocr-and-documents /tmp/scan.pdf extract the tables   # loads one skill; /tmp/scan.pdf is the argument
```

For combinations you use repeatedly, prefer a [skill bundle](#skill-bundles) —
same effect under one short command.

The bundled `plan` skill is a good example. Running `/plan [request]` loads the skill's instructions, telling Jacky to inspect context if needed, write a markdown implementation plan instead of executing the task, and save the result under `.jacky/plans/` relative to the active workspace/backend working directory.

You can also interact with skills through natural conversation:

```bash
jacky chat --toolsets skills -q "What skills do you have?"
jacky chat --toolsets skills -q "Show me the axolotl skill"
```

## Learning a skill from sources (`/learn`)

`/learn` is the fast way to turn something you already know — or a pile of
reference material — into a reusable skill, without hand-writing the
`SKILL.md`. It is open-ended: point it at *anything you can describe* and the
agent gathers the material with the tools it already has, then authors a skill
that follows the [house authoring standards](#skillmd-format) (≤60-char
description, the standard section order, Jacky-tool framing, no invented
commands).

```bash
# A local SDK or doc directory — read with read_file / search_files
/learn the REST client in ~/projects/acme-sdk, focus on auth + pagination

# An online doc page — fetched with web_extract
/learn https://docs.example.com/api/quickstart

# The workflow you just walked the agent through in this conversation
/learn how I just deployed the staging server

# Pasted notes / a described procedure
/learn filing an expense: open the portal, New > Expense, attach the receipt, submit
```

Because the live agent does the sourcing, `/learn` works the same in the CLI,
the messaging gateway, the TUI, and the dashboard — and on any terminal backend
(local, Docker, remote), since there is no separate ingestion engine. In the
**dashboard**, the Skills page has a **Learn a skill** button that opens a panel
with a directory field, a URL field, and an open-ended text box; it composes a
`/learn` request and runs it in chat.

There is no model-tool footprint: `/learn` builds a standards-guided prompt and
hands it to the agent as a normal turn. The agent saves the result with the
`skill_manage` tool, so the [write-approval gate](#gating-agent-skill-writes-skillswrite_approval)
applies if you have it on.

## Progressive Disclosure

Skills use a token-efficient loading pattern:

```
Level 0: skills_list()           → [{name, description, category}, ...]   (~3k tokens)
Level 1: skill_view(name)        → Full content + metadata       (varies)
Level 2: skill_view(name, path)  → Specific reference file       (varies)
```

The agent only loads the full skill content when it actually needs it.

## SKILL.md Format

```markdown
---
name: my-skill
description: Brief description of what this skill does
version: 1.0.0
platforms: [macos, linux]     # Optional — restrict to specific OS platforms
metadata:
  jacky:
    tags: [python, automation]
    category: devops
    fallback_for_toolsets: [web]    # Optional — conditional activation (see below)
    requires_toolsets: [terminal]   # Optional — conditional activation (see below)
    config:                          # Optional — config.yaml settings
      - key: my.setting
        description: "What this controls"
        default: "value"
        prompt: "Prompt for setup"
---

# Skill Title

## When to Use
Trigger conditions for this skill.

## Procedure
1. Step one
2. Step two

## Pitfalls
- Known failure modes and fixes

## Verification
How to confirm it worked.
```

### Platform-Specific Skills

Skills can restrict themselves to specific operating systems using the `platforms` field:

| Value | Matches |
|-------|---------|
| `macos` | macOS (Darwin) |
| `linux` | Linux |
| `windows` | Windows |

```yaml
platforms: [macos]            # macOS only (e.g., iMessage, Apple Reminders, FindMy)
platforms: [macos, linux]     # macOS and Linux
```

When set, the skill is automatically hidden from the system prompt, `skills_list()`, and slash commands on incompatible platforms. If omitted, the skill loads on all platforms.

## Skill output and media delivery

When a skill response (or any agent response) includes a bare absolute path to a media file — for example `/home/user/screenshots/diagram.png` — the gateway auto-detects it, strips it from the visible text, and delivers the file natively to the user's chat (Telegram photo, Discord attachment, etc.) instead of leaving the raw path in the message.

For audio specifically, the `[[audio_as_voice]]` directive promotes audio files to native voice-message bubbles on platforms that support them (Telegram, WhatsApp).

### Forcing document-style delivery: `[[as_document]]`

Sometimes you want the **opposite** of inline preview: you want the file delivered as a downloadable attachment, not a re-compressed image bubble. The classic example is a high-resolution screenshot or chart — Telegram's `sendPhoto` recompresses it to ~200 KB at 1280 px, destroying readability. A 1-2 MB PNG sent via `sendDocument` keeps the original bytes intact.

If a response (or any text inside it — typically the last line) contains the literal directive `[[as_document]]`, every media path extracted from that response is delivered as a document/file attachment rather than an image bubble:

```
Here is your rendered chart:

/home/user/.jacky/cache/chart-q4-2025.png

[[as_document]]
```

The directive is stripped before delivery, so users never see it. Granularity is intentionally all-or-nothing per response: emit `[[as_document]]` once and every image path in the same response is delivered as a document. This mirrors the scope of `[[audio_as_voice]]`.

Use it from a skill when:

- You produce screenshots or charts the user needs as files (for editing in another tool, archiving, sharing intact).
- The default lossy preview would obscure detail (small text, pixel-accurate diagrams, color-sensitive renders).

Platforms without a separate document path (e.g. SMS) fall back to whatever attachment mechanism they have.

### Conditional Activation (Fallback Skills)

Skills can automatically show or hide themselves based on which tools are available in the current session. This is most useful for **fallback skills** — free or local alternatives that should only appear when a premium tool is unavailable.

```yaml
metadata:
  jacky:
    fallback_for_toolsets: [web]      # Show ONLY when these toolsets are unavailable
    requires_toolsets: [terminal]     # Show ONLY when these toolsets are available
    fallback_for_tools: [web_search]  # Show ONLY when these specific tools are unavailable
    requires_tools: [terminal]        # Show ONLY when these specific tools are available
```

| Field | Behavior |
|-------|----------|
| `fallback_for_toolsets` | Skill is **hidden** when the listed toolsets are available. Shown when they're missing. |
| `fallback_for_tools` | Same, but checks individual tools instead of toolsets. |
| `requires_toolsets` | Skill is **hidden** when the listed toolsets are unavailable. Shown when they're present. |
| `requires_tools` | Same, but checks individual tools. |

**Example:** The built-in `duckduckgo-search` skill uses `fallback_for_toolsets: [web]`. When you have `FIRECRAWL_API_KEY` set, the web toolset is available and the agent uses `web_search` — the DuckDuckGo skill stays hidden. If the API key is missing, the web toolset is unavailable and the DuckDuckGo skill automatically appears as a fallback.

Skills without any conditional fields behave exactly as before — they're always shown.

## Secure Setup on Load

Skills can declare required environment variables without disappearing from discovery:

```yaml
required_environment_variables:
  - name: TENOR_API_KEY
    prompt: Tenor API key
    help: Get a key from https://developers.google.com/tenor
    required_for: full functionality
```

When a missing value is encountered, Jacky asks for it securely only when the skill is actually loaded in the local CLI. You can skip setup and keep using the skill. Messaging surfaces never ask for secrets in chat — they tell you to use `jacky setup` or `~/.jacky/.env` locally instead.

Once set, declared env vars are **automatically passed through** to `execute_code` and `terminal` sandboxes — the skill's scripts can use `$TENOR_API_KEY` directly. For non-skill env vars, use the `terminal.env_passthrough` config option. See [Environment Variable Passthrough](/user-guide/security#environment-variable-passthrough) for details.

### Skill Config Settings

Skills can also declare non-secret config settings (paths, preferences) stored in `config.yaml`:

```yaml
metadata:
  jacky:
    config:
      - key: myplugin.path
        description: Path to the plugin data directory
        default: "~/myplugin-data"
        prompt: Plugin data directory path
```

Settings are stored under `skills.config` in your config.yaml. `jacky config migrate` prompts for unconfigured settings, and `jacky config show` displays them. When a skill loads, its resolved config values are injected into the context so the agent knows the configured values automatically.

See [Skill Settings](/user-guide/configuration#skill-settings) and [Creating Skills — Config Settings](/developer-guide/creating-skills#config-settings-configyaml) for details.

## Skill Directory Structure

```text
~/.jacky/skills/                  # Single source of truth
├── mlops/                         # Category directory
│   ├── axolotl/
│   │   ├── SKILL.md               # Main instructions (required)
│   │   ├── references/            # Additional docs
│   │   ├── templates/             # Output formats
│   │   ├── scripts/               # Helper scripts callable from the skill
│   │   └── assets/                # Supplementary files
│   └── vllm/
│       └── SKILL.md
├── devops/
│   └── deploy-k8s/                # Agent-created skill
│       ├── SKILL.md
│       └── references/
├── .hub/                          # Skills Hub state
│   ├── lock.json
│   ├── quarantine/
│   └── audit.log
└── .bundled_manifest              # Tracks seeded bundled skills
```

## External Skill Directories

If you maintain skills outside of Jacky — for example, a shared `~/.agents/skills/` directory used by multiple AI tools — you can tell Jacky to scan those directories too.

Add `external_dirs` under the `skills` section in `~/.jacky/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
    - /home/shared/team-skills
    - ${SKILLS_REPO}/skills
```

Paths support `~` expansion and `${VAR}` environment variable substitution.

### How it works

- **Create locally, update in place**: New agent-created skills are written to `~/.jacky/skills/`. Existing skills are modified where they are found, including skills under `external_dirs`, when the agent uses `skill_manage` actions such as `patch`, `edit`, `write_file`, `remove_file`, or `delete`.
- **External dirs are not a write-protection boundary**: If an external skill directory is writable by the Jacky process, agent-managed skill updates can change files in that directory. Use filesystem permissions or a separate profile/toolset setup if shared external skills must stay read-only.
- **Local precedence**: If the same skill name exists in both the local dir and an external dir, the local version wins.
- **Full integration**: External skills appear in the system prompt index, `skills_list`, `skill_view`, and as `/skill-name` slash commands — no different from local skills.
- **Non-existent paths are silently skipped**: If a configured directory doesn't exist, Jacky ignores it without errors. Useful for optional shared directories that may not be present on every machine.

### Example

```text
~/.jacky/skills/               # Local (primary, read-write)
├── devops/deploy-k8s/
│   └── SKILL.md
└── mlops/axolotl/
    └── SKILL.md

~/.agents/skills/               # External (shared, mutable if writable)
├── my-custom-workflow/
│   └── SKILL.md
└── team-conventions/
    └── SKILL.md
```

All four skills appear in your skill index. If you create a new skill called `my-custom-workflow` locally, it shadows the external version.

## Skill Bundles

Skill bundles are tiny YAML files that group several skills under a single slash command. When you run `/<bundle-name>`, every skill listed in the bundle loads at once — useful when a particular task always benefits from the same set of skills together.

### Quick example

```bash
# Create a bundle for backend feature work
jacky bundles create backend-dev \
  --skill github-code-review \
  --skill test-driven-development \
  --skill github-pr-workflow \
  -d "Backend feature work — review, test, PR workflow"
```

Then in the CLI or any gateway platform:

```
/backend-dev refactor the auth middleware
```

The agent receives all three skills loaded into one user message, with any text after the slash command attached as a user instruction.

### YAML schema

Bundles live in **`~/.jacky/skill-bundles/<slug>.yaml`** and look like this:

```yaml
name: backend-dev
description: Backend feature work — review, test, PR workflow.
skills:
  - github-code-review
  - test-driven-development
  - github-pr-workflow
instruction: |
  Always start by writing failing tests, then implement.
  Open the PR through the standard workflow with co-author tags.
```

Fields:
- `name` (optional — defaults to the filename stem) — the bundle's display name. Normalized to a hyphen slug for the slash command (`Backend Dev` → `/backend-dev`).
- `description` (optional) — short text shown in `/bundles` and `jacky bundles list`.
- `skills` (required, non-empty list) — skill names or paths relative to your skills directory. Use the same identifier you'd pass to `/<skill-name>`.
- `instruction` (optional) — extra guidance prepended to the loaded skill content. Useful for codifying "how we always use these together."

### Managing bundles

```bash
# List all installed bundles
jacky bundles list

# Inspect one bundle
jacky bundles show backend-dev

# Create a bundle interactively (omit --skill flags to enter them one per line)
jacky bundles create research

# Overwrite an existing bundle
jacky bundles create backend-dev --skill ... --force

# Delete a bundle
jacky bundles delete backend-dev

# Re-scan ~/.jacky/skill-bundles/ and report changes
jacky bundles reload
```

From inside a chat session, `/bundles` lists every installed bundle and its skills.

### Behavior

- **Bundles take precedence over individual skills** when slugs collide. If you name a bundle `research` and you also have a skill called `research`, `/research` invokes the bundle. This is intentional — you opted into the bundle by naming it.
- **Missing skills are skipped, not fatal.** If a bundle lists `skill-foo` and you haven't installed it, the bundle still loads the skills that do resolve, and the agent gets a note listing what was skipped.
- **Bundles work in every surface** — interactive CLI, TUI, dashboard chat, and every gateway platform (Telegram, Discord, Slack, …) — because dispatch is centralized in the same place as individual skill commands.
- **Bundles do not invalidate the prompt cache.** They generate a fresh user message at invocation time, the same way `/<skill-name>` does — no system prompt mutation.

### When bundles beat installing each skill manually

Use a bundle when:
- You always pair the same skills for a recurring task (`/backend-dev`, `/release-prep`, `/incident-response`).
- You want a one-character-shorter mental model than typing several `/skill` invocations in a row.
- You want to ship a team-wide "task profile" by checking the bundle YAML into a shared dotfiles repo and symlinking it into `~/.jacky/skill-bundles/`.

A bundle is just a YAML alias — it doesn't install skills for you. The skills themselves must already be present (in `~/.jacky/skills/` or an external skill directory). Otherwise the bundle invocation just skips the missing ones.

## Agent-Managed Skills (skill_manage tool)

The agent can create, update, and delete its own skills via the `skill_manage` tool. This is the agent's **procedural memory** — when it figures out a non-trivial workflow, it saves the approach as a skill for future reuse.

Skills and memory work together in the self-improvement loop: memory stores
small durable facts that should always be in context, while skills store longer
procedures that should load only when relevant. The background review can
suggest or stage skill changes after a session, but the write-approval gate
below lets you require human review before those changes land.

### When the Agent Creates Skills

- After completing a complex task (5+ tool calls) successfully
- When it hit errors or dead ends and found the working path
- When the user corrected its approach
- When it discovered a non-trivial workflow

### Actions

| Action | Use for | Key params |
|--------|---------|------------|
| `create` | New skill from scratch | `name`, `content` (full SKILL.md), optional `category` |
| `patch` | Targeted fixes (preferred) | `name`, `old_string`, `new_string` |
| `edit` | Major structural rewrites | `name`, `content` (full SKILL.md replacement) |
| `delete` | Remove a skill entirely | `name` |
| `write_file` | Add/update supporting files | `name`, `file_path`, `file_content` |
| `remove_file` | Remove a supporting file | `name`, `file_path` |

:::tip
The `patch` action is preferred for updates — it's more token-efficient than `edit` because only the changed text appears in the tool call.
:::

### Gating agent skill writes (`skills.write_approval`)

By default the agent writes skills freely — including from the [background
self-improvement review](/user-guide/features/memory#controlling-memory-writes-write_approval)
that runs after a turn. If you'd rather approve every skill write first
(small models that misjudge what they learned, secure environments, or just
wanting eyes on the self-improvement loop), turn on the write-approval gate:

```yaml
skills:
  write_approval: false     # false = write freely (default) | true = require approval
```

When `write_approval: true`, every `skill_manage` write (create / edit /
patch / delete / write_file / remove_file) is **staged** instead of committed —
a SKILL.md is too large to review inline, so staging applies regardless of
whether the write came from a foreground turn or the background review.
Staged writes survive restarts under `~/.jacky/pending/skills/` and are
reviewed with the same familiar approve/deny flow as dangerous commands:

```
/skills pending             # list staged skill writes + a one-line gist each
/skills diff <id>           # full unified diff (best viewed in CLI or dashboard)
/skills approve <id>        # apply it (or 'all')
/skills reject <id>         # drop it (or 'all')
/skills approval on         # turn the gate on (or 'off') and persist it
```

The review surface works in the interactive CLI and on messaging platforms
(diff output is truncated for chat bubbles — read the full diff on the CLI or
in the pending JSON file). Memory writes have the same gate under
`memory.write_approval` — see [Controlling memory writes](/user-guide/features/memory#controlling-memory-writes-write_approval).

> The separate `skills.guard_agent_created` setting is a content scanner
> (dangerous-pattern heuristics), not an approval gate — the two are
> independent. See [Guard on agent-created skill writes](/user-guide/configuration#guard-on-agent-created-skill-writes).

## Skills Hub

Browse, search, install, and manage skills from online registries, `skills.sh`, direct well-known skill endpoints, and official optional skills.

### Common commands

```bash
jacky skills browse                              # Browse all hub skills (official first)
jacky skills browse --source official            # Browse only official optional skills
jacky skills search kubernetes                   # Search all sources
jacky skills search react --source skills-sh     # Search the skills.sh directory
jacky skills search https://mintlify.com/docs --source well-known
jacky skills inspect openai/skills/k8s           # Preview before installing
jacky skills install openai/skills/k8s           # Install with security scan
jacky skills install official/security/1password
jacky skills install skills-sh/vercel-labs/json-render/json-render-react --force
jacky skills install well-known:https://mintlify.com/docs/.well-known/skills/mintlify
jacky skills install https://sharethis.chat/SKILL.md              # Direct URL (single-file SKILL.md)
jacky skills install https://example.com/SKILL.md --name my-skill # Override name when frontmatter has none
jacky skills list --source hub                   # List hub-installed skills
jacky skills check                               # Check installed hub skills for upstream updates
jacky skills update                              # Reinstall hub skills with upstream changes when needed
jacky skills audit                               # Re-scan all hub skills for security
jacky skills uninstall k8s                       # Remove a hub skill
jacky skills reset google-workspace              # Un-stick a bundled skill from "user-modified" (see below)
jacky skills reset google-workspace --restore    # Also restore the bundled version, deleting your local edits
jacky skills publish skills/my-skill --to github --repo owner/repo
jacky skills snapshot export setup.json          # Export skill config
jacky skills tap add myorg/skills-repo           # Add a custom GitHub source
```

### Supported hub sources

| Source | Example | Notes |
|--------|---------|-------|
| `official` | `official/security/1password` | Optional skills shipped with Jacky. |
| `skills-sh` | `skills-sh/vercel-labs/agent-skills/vercel-react-best-practices` | Searchable via `jacky skills search <query> --source skills-sh`. Jacky resolves alias-style skills when the skills.sh slug differs from the repo folder. |
| `well-known` | `well-known:https://mintlify.com/docs/.well-known/skills/mintlify` | Skills served directly from `/.well-known/skills/index.json` on a website. Search using the site or docs URL. |
| `url` | `https://sharethis.chat/SKILL.md` | Direct HTTP(S) URL to a single-file `SKILL.md`. Name resolution: frontmatter → URL slug → interactive prompt → `--name` flag. |
| `github` | `openai/skills/k8s` | Direct GitHub repo/path installs and custom taps. |
| `clawhub`, `lobehub`, `browse-sh` | Source-specific identifiers | Community or marketplace integrations. |

### Integrated hubs and registries

Jacky currently integrates with these skills ecosystems and discovery sources:

#### 1. Official optional skills (`official`)

These are maintained in the Jacky repository itself and install with built-in trust.

- Catalog: [Official Optional Skills Catalog](../../reference/optional-skills-catalog)
- Source in repo: `optional-skills/`
- Example:

```bash
jacky skills browse --source official
jacky skills install official/security/1password
```

#### 2. skills.sh (`skills-sh`)

This is Vercel's public skills directory. Jacky can search it directly, inspect skill detail pages, resolve alias-style slugs, and install from the underlying source repo.

- Directory: [skills.sh](https://skills.sh/)
- CLI/tooling repo: [vercel-labs/skills](https://github.com/vercel-labs/skills)
- Official Vercel skills repo: [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
- Example:

```bash
jacky skills search react --source skills-sh
jacky skills inspect skills-sh/vercel-labs/json-render/json-render-react
jacky skills install skills-sh/vercel-labs/json-render/json-render-react --force
```

#### 3. Well-known skill endpoints (`well-known`)

This is URL-based discovery from sites that publish `/.well-known/skills/index.json`. It is not a single centralized hub — it is a web discovery convention.

- Example live endpoint: [Mintlify docs skills index](https://mintlify.com/docs/.well-known/skills/index.json)
- Reference server implementation: [vercel-labs/skills-handler](https://github.com/vercel-labs/skills-handler)
- Example:

```bash
jacky skills search https://mintlify.com/docs --source well-known
jacky skills inspect well-known:https://mintlify.com/docs/.well-known/skills/mintlify
jacky skills install well-known:https://mintlify.com/docs/.well-known/skills/mintlify
```

#### 4. Direct GitHub skills (`github`)

Jacky can install directly from GitHub repositories and GitHub-based taps. This is useful when you already know the repo/path or want to add your own custom source repo.

Default taps (browsable without any setup):
- [openai/skills](https://github.com/openai/skills)
- [anthropics/skills](https://github.com/anthropics/skills)
- [huggingface/skills](https://github.com/huggingface/skills)
- [NVIDIA/skills](https://github.com/NVIDIA/skills) — NVIDIA-verified skills (signed `skill.oms.sig` + governance `skill-card.md`)
- [garrytan/gstack](https://github.com/garrytan/gstack)

- Example:

```bash
jacky skills install openai/skills/k8s
jacky skills tap add myorg/skills-repo
```

**Category groupings (`skills.sh.json`).** A GitHub tap may ship a
`skills.sh.json` file at its repo root following the
[skills.sh schema](https://skills.sh/schemas/skills.sh.schema.json). Its
`groupings` (each with a `title` and a list of skill names) are read at index
time and become the category labels shown in the
[Skills Hub](https://jacky-agent.nousresearch.com/docs) page — instead of a
tag-derived guess. This is generic: any tap that ships the file gets real
categorization, no Jacky-side changes required.

```json
{
  "$schema": "https://skills.sh/schemas/skills.sh.schema.json",
  "groupings": [
    { "title": "Inference AI", "skills": ["dynamo-recipe-runner", "dynamo-router-sla"] },
    { "title": "Decision Optimization", "skills": ["cuopt-developer", "cuopt-install"] }
  ]
}
```

#### 5. ClawHub (`clawhub`)

A third-party skills marketplace integrated as a community source.

- Site: [clawhub.ai](https://clawhub.ai/)
- Jacky source id: `clawhub`

#### 6. Claude marketplace-style repos (`claude-marketplace`)

Jacky supports marketplace repos that publish Claude-compatible plugin/marketplace manifests.

Known integrated sources include:
- [anthropics/skills](https://github.com/anthropics/skills)
- [aiskillstore/marketplace](https://github.com/aiskillstore/marketplace)

Jacky source id: `claude-marketplace`

#### 7. LobeHub (`lobehub`)

Jacky can search and convert agent entries from LobeHub's public catalog into installable Jacky skills.

- Site: [LobeHub](https://lobehub.com/)
- Public agents index: [chat-agents.lobehub.com](https://chat-agents.lobehub.com/)
- Backing repo: [lobehub/lobe-chat-agents](https://github.com/lobehub/lobe-chat-agents)
- Jacky source id: `lobehub`

#### 8. browse.sh (`browse-sh`)

Jacky integrates with [browse.sh](https://browse.sh), Browserbase's catalog of 200+ site-specific browser-automation SKILL.md files (Airbnb, Amazon, arXiv, 12306.cn, Etsy, Xero, and many more). Each skill describes how to drive one website end-to-end and is suitable for use with Jacky' browser tools and any browser-automation skills you already have installed.

- Site: [browse.sh](https://browse.sh/)
- Catalog API: `https://browse.sh/api/skills`
- Jacky source id: `browse-sh`
- Trust level: `community`

```bash
jacky skills search airbnb --source browse-sh
jacky skills inspect browse-sh/airbnb.com/search-listings-ddgioa
jacky skills install browse-sh/airbnb.com/search-listings-ddgioa
```

Identifiers use the form `browse-sh/<hostname>/<task-id>` and match the slug exposed by the browse.sh catalog. Content is resolved through the per-skill detail endpoint (`/api/skills/<slug>` → `skillMdUrl`), not through the catalog's GitHub `sourceUrl`.

#### 9. Direct URL (`url`)

Install a single-file `SKILL.md` directly from any HTTP(S) URL — useful when an author hosts a skill on their own site (no hub listing, no GitHub path to type). Jacky fetches the URL, parses the YAML frontmatter, security-scans it, and installs.

- Jacky source id: `url`
- Identifier: the URL itself (no prefix needed)
- Scope: **single-file `SKILL.md`** only. Multi-file skills with `references/` or `scripts/` need a manifest and should be published via one of the other sources above.

```bash
jacky skills install https://sharethis.chat/SKILL.md
jacky skills install https://example.com/my-skill/SKILL.md --category productivity
```

Name resolution, in order:
1. `name:` field in the SKILL.md YAML frontmatter (recommended — every well-formed skill has one).
2. Parent directory name from the URL path (e.g. `.../my-skill/SKILL.md` → `my-skill`, or `.../my-skill.md` → `my-skill`), when it's a valid identifier (`^[a-z][a-z0-9_-]*$`).
3. Interactive prompt on a terminal with a TTY.
4. On non-interactive surfaces (the `/skills install` slash command inside the TUI, gateway platforms, scripts), a clean error pointing at the `--name` override.

```bash
# Frontmatter has no name and the URL slug is unhelpful — supply one:
jacky skills install https://example.com/SKILL.md --name sharethis-chat

# Or inside a chat session:
/skills install https://example.com/SKILL.md --name sharethis-chat
```

Trust level is always `community` — the same security scan runs as for every other source. The URL is stored as the install identifier, so `jacky skills update` re-fetches from the same URL automatically when you want to refresh.

### Security scanning and `--force`

All hub-installed skills go through a **security scanner** that checks for data exfiltration, prompt injection, destructive commands, supply-chain signals, and other threats.

`jacky skills inspect ...` now also surfaces upstream metadata when available:
- repo URL
- skills.sh detail page URL
- install command
- weekly installs
- upstream security audit statuses
- well-known index/endpoint URLs

Use `--force` when you have reviewed a third-party skill and want to override a non-dangerous policy block:

```bash
jacky skills install skills-sh/anthropics/skills/pdf --force
```

Important behavior:
- `--force` can override policy blocks for caution/warn-style findings.
- `--force` does **not** override a `dangerous` scan verdict.
- Official optional skills (`official/...`) are treated as built-in trust and do not show the third-party warning panel.

### Trust levels

| Level | Source | Policy |
|-------|--------|--------|
| `builtin` | Ships with Jacky | Always trusted |
| `official` | `optional-skills/` in the repo | Built-in trust, no third-party warning |
| `trusted` | Trusted registries/repos such as `openai/skills`, `anthropics/skills`, `huggingface/skills`, `NVIDIA/skills` | More permissive policy than community sources |
| `community` | Everything else (`skills.sh`, well-known endpoints, custom GitHub repos, most marketplaces) | Non-dangerous findings can be overridden with `--force`; `dangerous` verdicts stay blocked |

### Update lifecycle

The hub now tracks enough provenance to re-check upstream copies of installed skills:

```bash
jacky skills check          # Report which installed hub skills changed upstream
jacky skills update         # Reinstall only the skills with updates available
jacky skills update react   # Update one specific installed hub skill
```

This uses the stored source identifier plus the current upstream bundle content hash to detect drift.

:::tip GitHub rate limits
Skills hub operations use the GitHub API, which has a rate limit of 60 requests/hour for unauthenticated users. If you see rate-limit errors during install or search, set `GITHUB_TOKEN` in your `.env` file to increase the limit to 5,000 requests/hour. The error message includes an actionable hint when this happens.
:::

### Publishing a custom skill tap

If you want to share a curated set of skills — for your team, your org, or publicly — you can publish them as a **tap**: a GitHub repository other Jacky users add with `jacky skills tap add <owner/repo>`. No server, no registry sign-up, no release pipeline. Just a directory of `SKILL.md` files.

#### Repo layout

A tap is any GitHub repo (public or private — private needs `GITHUB_TOKEN`) laid out like this:

```
owner/repo
├── skills/                       # default path; configurable per-tap
│   ├── my-workflow/
│   │   ├── SKILL.md              # required
│   │   ├── references/           # optional supporting files
│   │   ├── templates/
│   │   └── scripts/
│   ├── another-skill/
│   │   └── SKILL.md
│   └── third-skill/
│       └── SKILL.md
└── README.md                     # optional but helpful
```

Rules:
- Each skill lives in its own directory under the tap's root path (default `skills/`).
- The directory name becomes the skill's install slug.
- Each skill directory must contain a `SKILL.md` with standard [SKILL.md frontmatter](#skillmd-format) (`name`, `description`, plus optional `metadata.jacky.tags`, `version`, `author`, `platforms`, `metadata.jacky.config`).
- Subdirectories like `references/`, `templates/`, `scripts/`, `assets/` are downloaded alongside `SKILL.md` at install time.
- Skills whose directory name starts with `.` or `_` are ignored.

Jacky discovers skills by listing every subdirectory of the tap path and probing each for `SKILL.md`.

#### Minimal tap example

```
my-org/jacky-skills
└── skills/
    └── deploy-runbook/
        └── SKILL.md
```

`skills/deploy-runbook/SKILL.md`:

```markdown
---
name: deploy-runbook
description: Our deployment runbook — services, rollback, Slack channels
version: 1.0.0
author: My Org Platform Team
metadata:
  jacky:
    tags: [deployment, runbook, internal]
---

# Deploy Runbook

Step 1: ...
```

After pushing that to GitHub, any Jacky user can subscribe and install:

```bash
jacky skills tap add my-org/jacky-skills
jacky skills search deploy
jacky skills install my-org/jacky-skills/deploy-runbook
```

#### Non-default paths

If your skills don't live under `skills/` (common when you're adding a `skills/` subtree to an existing project), edit the tap entry in `~/.jacky/.hub/taps.json`:

```json
{
  "taps": [
    {"repo": "my-org/platform-docs", "path": "internal/skills/"}
  ]
}
```

The `jacky skills tap add` CLI defaults new taps to `path: "skills/"`; edit the file directly if you need a different path. `jacky skills tap list` shows the effective path per tap.

#### Installing individual skills directly (without adding a tap)

Users can also install a single skill from any public GitHub repo without adding the whole repo as a tap:

```bash
jacky skills install owner/repo/skills/my-workflow
```

Useful when you want to share one skill without asking the user to subscribe to your whole registry.

#### Trust levels for taps

New taps are assigned `community` trust by default. Skills installed from them run through the standard security scan and show the third-party warning panel on first install. If your org or a widely-trusted source should get higher trust, add its repo to `TRUSTED_REPOS` in `tools/skills_hub.py` (requires a Jacky core PR).

#### Tap management

```bash
jacky skills tap list                                # show all configured taps
jacky skills tap add myorg/skills-repo               # add (default path: skills/)
jacky skills tap remove myorg/skills-repo            # remove
```

Inside a running session:

```
/skills tap list
/skills tap add myorg/skills-repo
/skills tap remove myorg/skills-repo
```

Taps are stored in `~/.jacky/.hub/taps.json` (created on demand).

## Bundled skill updates (`jacky skills reset`)

Jacky ships with a set of bundled skills in `skills/` inside the repo. On install and on every `jacky update`, a sync pass copies those into `~/.jacky/skills/` and records a manifest at `~/.jacky/skills/.bundled_manifest` mapping each skill name to the content hash at the time it was synced (the **origin hash**).

On each sync, Jacky recomputes the hash of your local copy and compares it to the origin hash:

- **Unchanged** → safe to pull upstream changes, copy the new bundled version in, record the new origin hash.
- **Changed** → treated as **user-modified** and skipped forever, so your edits never get stomped.

The protection is good, but it has one sharp edge. If you edit a bundled skill and then later want to abandon your changes and go back to the bundled version by just copy-pasting from `~/.jacky/jacky-agent/skills/`, the manifest still holds the *old* origin hash from whenever the last successful sync ran. Your fresh copy-paste contents (current bundled hash) won't match that stale origin hash, so sync keeps flagging it as user-modified.

`jacky skills reset` is the escape hatch:

```bash
# Safe: clears the manifest entry for this skill. Your current copy is preserved,
# but the next sync re-baselines against it so future updates work normally.
jacky skills reset google-workspace

# Full restore: also deletes your local copy and re-copies the current bundled
# version. Use this when you want the pristine upstream skill back.
jacky skills reset google-workspace --restore

# Non-interactive (e.g. in scripts or TUI mode) — skip the --restore confirmation.
jacky skills reset google-workspace --restore --yes
```

The same command works in chat as a slash command:

```text
/skills reset google-workspace
/skills reset google-workspace --restore
```

:::note Profiles
Each profile has its own `.bundled_manifest` under its own `JACKY_HOME`, so `jacky -p coder skills reset <name>` only affects that profile.
:::

### Slash commands (inside chat)

All the same commands work with `/skills`:

```text
/skills browse
/skills search react --source skills-sh
/skills search https://mintlify.com/docs --source well-known
/skills inspect skills-sh/vercel-labs/json-render/json-render-react
/skills install openai/skills/skill-creator --force
/skills check
/skills update
/skills reset google-workspace
/skills list
```

Official optional skills still use identifiers like `official/security/1password` and `official/migration/openclaw-migration`.
