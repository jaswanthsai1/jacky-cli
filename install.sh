#!/usr/bin/env bash
# ============================================================================
# Jacky CLI — one-line remote installer
# ============================================================================
# This is the script fetched by:
#
#   curl -fsSL https://raw.githubusercontent.com/jaswanthsai1/jacky-cli/main/install.sh | bash
#
# Unlike setup.sh (which assumes you've already `git clone`d the repo and are
# running it from inside the checkout), this script has no local repo to work
# from — it's read from stdin, so $BASH_SOURCE / $0 point nowhere useful. Its
# only job is: clone the repo somewhere sensible, then hand off to the real
# setup.sh from inside that checkout. Kept deliberately tiny and easy to read
# before you pipe it into bash, on purpose, for a security-focused tool.
#
# Safe to re-run: if ~/.jacky-cli already exists, it's updated in place
# (git pull) rather than re-cloned.
# ============================================================================

set -euo pipefail

REPO_URL="https://github.com/jaswanthsai1/jacky-cli.git"
INSTALL_DIR="${JACKY_INSTALL_DIR:-$HOME/.jacky-cli}"

if [ -t 1 ]; then
  GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
else
  GREEN=''; CYAN=''; RED=''; BOLD=''; NC=''
fi
info() { echo -e "${CYAN}==>${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗ $*${NC}" >&2; }

if ! command -v git >/dev/null 2>&1; then
  fail "git is required but not found. Install git, then re-run this command."
  exit 1
fi

echo -e "${BOLD}Jacky CLI — installer${NC}"
echo

if [ -d "$INSTALL_DIR/.git" ]; then
  info "Existing install found at $INSTALL_DIR — updating..."
  git -C "$INSTALL_DIR" fetch --quiet origin main
  git -C "$INSTALL_DIR" reset --quiet --hard origin/main
  ok "Updated to latest main"
else
  info "Cloning Jacky CLI into $INSTALL_DIR ..."
  git clone --quiet --depth 1 "$REPO_URL" "$INSTALL_DIR"
  ok "Cloned"
fi

info "Handing off to setup.sh ..."
echo
exec bash "$INSTALL_DIR/setup.sh"
