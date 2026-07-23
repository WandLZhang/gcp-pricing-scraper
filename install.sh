#!/usr/bin/env bash
# Canonical installer for the `gcp-pricing` CLI. Idempotent. No credentials.
# Setup repos call this with one line:
#   curl -fsSL https://raw.githubusercontent.com/WandLZhang/gcp-pricing-scraper/main/install.sh | bash
set -euo pipefail

REPO="git+https://github.com/WandLZhang/gcp-pricing-scraper@main"
RAW="https://raw.githubusercontent.com/WandLZhang/gcp-pricing-scraper/main"
echo "[gcp-pricing] installing CLI..."

if command -v pipx >/dev/null 2>&1; then
  pipx install --force "$REPO"
elif python3 -c 'import ensurepip' >/dev/null 2>&1; then
  APP="$HOME/.local/share/gcp-pricing"
  rm -rf "$APP/venv"
  python3 -m venv "$APP/venv"
  "$APP/venv/bin/pip" install --quiet --upgrade pip
  "$APP/venv/bin/pip" install --quiet "$REPO"
  mkdir -p "$HOME/.local/bin"
  ln -sf "$APP/venv/bin/gcp-pricing" "$HOME/.local/bin/gcp-pricing"
else
  # Debian/PEP-668 externally-managed fallback
  python3 -m pip install --user --break-system-packages --quiet "$REPO"
fi

# ensure ~/.local/bin is on PATH for future shells
mkdir -p "$HOME/.local/bin"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) : ;;
  *) echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" ;;
esac
# some setups (claude-code) use ~/bin — mirror the launcher there if that dir exists
if [ -d "$HOME/bin" ] && command -v gcp-pricing >/dev/null 2>&1; then
  ln -sf "$(command -v gcp-pricing)" "$HOME/bin/gcp-pricing" 2>/dev/null || true
fi

# if Claude Code is present, drop the skill so the agent auto-discovers the tool
if [ -d "$HOME/.claude" ]; then
  mkdir -p "$HOME/.claude/skills/gcp-pricing"
  curl -fsSL "$RAW/SKILL.md" -o "$HOME/.claude/skills/gcp-pricing/SKILL.md" 2>/dev/null || true
fi

echo "[gcp-pricing] done. Try: gcp-pricing tpu --filter Trillium"
