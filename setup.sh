#!/usr/bin/env bash
# ============================================================================
# Jacky CLI — first-time setup
# ============================================================================
# Guarantees a working `jacky` command from a fresh `git clone`, with no
# manual steps beyond editing .env for your provider of choice.
#
# Usage:
#   ./setup.sh
#
# What it does:
#   1. Finds a usable Python 3.11-3.13 interpreter
#   2. Creates a virtual environment at .venv/
#   3. Installs Jacky CLI (editable) + core dependencies into it
#   4. Copies .env.example -> .env if you don't already have one
#   5. Symlinks the `jacky` command into ~/.local/bin so it's on your PATH
#   6. Actually runs `jacky --help` to PROVE the install works before
#      declaring success — if that fails, this script exits non-zero with
#      a clear error, it does not silently report success.
#
# For advanced setups (uv-managed environment, Termux/Android, Windows
# native) see setup-jacky.sh instead, which this script's simple path is a
# subset of.
# ============================================================================

set -euo pipefail

# ---- colors -----------------------------------------------------------
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; CYAN=''; RED=''; BOLD=''; NC=''
fi

info()  { echo -e "${CYAN}==>${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✗ $*${NC}" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${BOLD}${CYAN}Jacky CLI — Setup${NC}"
echo ""

# ---- 1. Find a Python interpreter (>=3.11, <3.14) ----------------------
info "Looking for a Python 3.11-3.13 interpreter..."
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
    case "$ver" in
      3.11|3.12|3.13) PYTHON_BIN="$candidate"; break ;;
    esac
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  fail "No usable Python interpreter found (need 3.11, 3.12, or 3.13)."
  echo "  Install one, e.g.:"
  echo "    Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
  echo "    macOS (brew):  brew install python@3.11"
  exit 1
fi
ok "Using $($PYTHON_BIN --version) at $(command -v "$PYTHON_BIN")"

# ---- 2. Create the virtual environment ---------------------------------
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  info "Creating virtual environment at .venv/ ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  ok "Virtual environment created"
else
  ok "Virtual environment already exists at .venv/"
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
if [ ! -x "$VENV_PY" ]; then
  # Windows-style venv layout (Git Bash / MSYS)
  VENV_PY="$VENV_DIR/Scripts/python.exe"
  VENV_PIP="$VENV_DIR/Scripts/pip.exe"
fi

# ---- 3. Install Jacky CLI ------------------------------------------------
info "Upgrading pip..."
"$VENV_PY" -m pip install --upgrade pip -q

info "Installing Jacky CLI (editable) + core dependencies..."
if ! "$VENV_PIP" install -e . -q; then
  fail "pip install -e . failed. See the output above for details."
  exit 1
fi
ok "Jacky CLI installed into .venv/"

echo ""
warn "The base install covers core functionality (chat, tools, skills, cron,"
warn "dashboard). Optional integrations (Telegram/Discord/Slack, voice/TTS,"
warn "the Anthropic provider, cloud memory providers, etc.) are pip extras."
warn "Install what you need, e.g.: .venv/bin/pip install -e '.[web,messaging]'"
warn "or everything with:          .venv/bin/pip install -e '.[all]'"
echo ""

# ---- 4. .env -------------------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    ok "Created .env from .env.example — edit it with your provider keys"
  else
    warn ".env.example not found — skipping .env creation"
  fi
else
  ok ".env already exists — leaving it as-is"
fi

# ---- 5. Put `jacky` on PATH ----------------------------------------------
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

VENV_JACKY="$VENV_DIR/bin/jacky"
if [ ! -x "$VENV_JACKY" ]; then
  VENV_JACKY="$VENV_DIR/Scripts/jacky.exe"
fi

if [ -x "$VENV_JACKY" ]; then
  ln -sf "$VENV_JACKY" "$BIN_DIR/jacky"
  ok "Linked $BIN_DIR/jacky -> $VENV_JACKY"
else
  fail "Expected jacky launcher not found at $VENV_JACKY after install."
  exit 1
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) PATH_OK=1 ;;
  *) PATH_OK=0 ;;
esac

# ---- 6. Prove it actually works ------------------------------------------
info "Verifying the install by running 'jacky --help'..."
if "$VENV_JACKY" --help >/tmp/jacky-setup-help.$$ 2>&1; then
  ok "'jacky --help' ran successfully"
  rm -f /tmp/jacky-setup-help.$$
else
  fail "'jacky --help' FAILED. Setup did not complete successfully."
  echo "---- output ----"
  cat /tmp/jacky-setup-help.$$ >&2
  echo "----------------"
  rm -f /tmp/jacky-setup-help.$$
  exit 1
fi

echo ""
echo -e "${BOLD}${GREEN}Setup complete.${NC}"
echo ""
if [ "$PATH_OK" -eq 0 ]; then
  warn "$BIN_DIR is not on your PATH yet."
  echo "  Add it, then reload your shell:"
  echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc   # or ~/.zshrc"
  echo "    source ~/.bashrc                                          # or: source ~/.zshrc"
fi
echo "Next steps:"
echo "  1. Edit .env with your provider configuration (local Ollama and/or"
echo "     a cloud API key — see README.md for both paths)."
echo "  2. Run: jacky"
echo "     (or, without touching PATH: .venv/bin/jacky)"
echo "  3. Using Claude Code, Codex, or another coding agent? This repo"
echo "     ships METHODOLOGY.md and skills/ with a bundled offensive-"
echo "     security hunt-loop methodology — see METHODOLOGY.md."
echo ""
