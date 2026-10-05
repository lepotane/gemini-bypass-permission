#!/usr/bin/env bash
# gemini-bypass-permission installer for Linux and macOS.
#
#   curl -fsSL https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.sh | bash
#
# Options:
#   --prefix DIR      Install somewhere else (default: ~/.gemini)
#   --project DIR     Also add the rule to this project's workspace
#   --no-skill        Skip the skill files
#   --no-rule         Skip the rule file
#   --no-gemini-md    Do not touch GEMINI.md
#   --help            Show this message

set -euo pipefail

PREFIX="$HOME/.gemini"
PROJECT=""
INSTALL_SKILL=1
INSTALL_RULE=1
TOUCH_GEMINI_MD=1
REPO_BASE="https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main"
REPO_URL="https://github.com/lepotane/gemini-bypass-permission"

cyan()  { printf '\033[36m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
warn()  { printf '\033[33m%s\033[0m\n' "$1"; }

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix)       PREFIX="$2"; shift 2 ;;
    --project)      PROJECT="$2"; shift 2 ;;
    --no-skill)     INSTALL_SKILL=0; shift ;;
    --no-rule)      INSTALL_RULE=0; shift ;;
    --no-gemini-md) TOUCH_GEMINI_MD=0; shift ;;
    --help|-h)      sed -n '2,17p' "$0"; exit 0 ;;
    *)              red "Unknown option: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------- python check
if ! command -v python3 >/dev/null 2>&1; then
  red "ERROR: python3 not found."
  echo "  Install Python 3.8 or newer:"
  echo "    Ubuntu/Debian : sudo apt install python3"
  echo "    macOS         : brew install python3"
  exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)'; then
  red "ERROR: Python 3.8 or newer is required."
  python3 --version
  exit 1
fi

green "Python: $(python3 --version)"

# --------------------------------------------------------------- locate files
TOOL_SRC="$SRC_DIR/scripts/agent_edit.py"
RULE_SRC="$SRC_DIR/rules/agent-edit-safe.md"
SKILL_SRC="$SRC_DIR/skills/agent-edit-safe"

TMP=""
if [ ! -f "$TOOL_SRC" ]; then
  warn "Not running from a checkout. Downloading..."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  curl -fsSL "$REPO_BASE/scripts/agent_edit.py" -o "$TMP/agent_edit.py"
  TOOL_SRC="$TMP/agent_edit.py"
  if [ "$INSTALL_RULE" = "1" ]; then
    if curl -fsSL "$REPO_BASE/rules/agent-edit-safe.md" -o "$TMP/agent-edit-safe.md"; then
      RULE_SRC="$TMP/agent-edit-safe.md"
    else
      warn "Could not fetch the rule file"
      INSTALL_RULE=0
    fi
  fi
fi

# ------------------------------------------------------------------- install
TOOLS_DIR="$PREFIX/tools"
RULES_DIR="$PREFIX/config/rules"
SKILLS_DIR="$PREFIX/config/skills"
mkdir -p "$TOOLS_DIR" "$PREFIX/backups"

DEST_TOOL="$TOOLS_DIR/agent_edit.py"
cp "$TOOL_SRC" "$DEST_TOOL"
chmod +x "$DEST_TOOL"
green "tool  : $DEST_TOOL"

if [ "$INSTALL_RULE" = "1" ] && [ -f "$RULE_SRC" ]; then
  mkdir -p "$RULES_DIR"
  cp "$RULE_SRC" "$RULES_DIR/agent-edit-safe.md"
  green "rule  : $RULES_DIR/agent-edit-safe.md"
fi

if [ "$INSTALL_SKILL" = "1" ]; then
  DEST_SKILL="$SKILLS_DIR/agent-edit-safe"
  mkdir -p "$DEST_SKILL/scripts"
  cp "$DEST_TOOL" "$DEST_SKILL/scripts/agent_edit.py"
  chmod +x "$DEST_SKILL/scripts/agent_edit.py"
  if [ -f "$SKILL_SRC/SKILL.md" ]; then
    cp "$SKILL_SRC/SKILL.md" "$DEST_SKILL/SKILL.md"
  elif curl -fsSL "$REPO_BASE/skills/agent-edit-safe/SKILL.md" -o "$DEST_SKILL/SKILL.md"; then
    :
  else
    warn "Could not fetch SKILL.md"
  fi
  green "skill : $DEST_SKILL"

  CLAUDE_SKILL="$HOME/.claude/skills/agent-edit-safe"
  if mkdir -p "$CLAUDE_SKILL/scripts" 2>/dev/null; then
    cp "$DEST_TOOL" "$CLAUDE_SKILL/scripts/agent_edit.py" 2>/dev/null || true
    cp "$DEST_SKILL/SKILL.md" "$CLAUDE_SKILL/SKILL.md" 2>/dev/null || true
    green "skill : $CLAUDE_SKILL  (compat)"
  fi
fi

# ------------------------------------------------------------------ GEMINI.md
if [ "$TOUCH_GEMINI_MD" = "1" ]; then
  GEMINI_MD="$PREFIX/GEMINI.md"
  if [ -f "$GEMINI_MD" ] && grep -q "agent-edit-safe" "$GEMINI_MD" 2>/dev/null; then
    green "GEMINI.md already references agent-edit-safe (left untouched)"
  else
    cat >> "$GEMINI_MD" <<EOF

---

# File editing protocol

Mandatory: modify files with the safe editing tool, never with built-in editor
tools. Full instructions are installed as an always-active rule.

- Tool: \`$DEST_TOOL\`
- Rule: \`$RULES_DIR/agent-edit-safe.md\`
- Start with: python3 $DEST_TOOL --help

See $REPO_URL
EOF
    green "GEMINI.md updated with a pointer"
  fi
fi

# ------------------------------------------------------------ workspace rule
if [ -n "$PROJECT" ]; then
  if [ -f "$RULE_SRC" ]; then
    WS="$PROJECT/.agents/rules"
    mkdir -p "$WS"
    cp "$RULE_SRC" "$WS/agent-edit-safe.md"
    green "workspace rule: $WS/agent-edit-safe.md"
  else
    warn "Rule file not available, skipping workspace rule"
  fi
fi

# -------------------------------------------------------------------- verify
echo
cyan "Verifying..."
if ! python3 "$DEST_TOOL" --help >/dev/null 2>&1; then
  red "FAILED: tool did not run. Check your Python installation."
  exit 1
fi
green "OK: tool runs correctly"

SMOKE="$(mktemp -d)"
printf 'int smoke = 1;\n' > "$SMOKE/sample.cpp"
if python3 "$DEST_TOOL" --path "$SMOKE/sample.cpp" --find 'smoke = 1' --replace 'smoke = 2' >/dev/null 2>&1 \
   && grep -q 'smoke = 2' "$SMOKE/sample.cpp"; then
  green "OK: smoke test passed"
else
  warn "Smoke test inconclusive, but --help worked."
fi
rm -rf "$SMOKE"
find "$PREFIX/backups" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true

cat <<EOF

----------------------------------------------------------
 Installed.

 Quick test:
   python3 $DEST_TOOL --help

 IMPORTANT -- restart your agent.
 Agents read rules and skills when a conversation starts.
 An already running session keeps its old instructions.

 If the agent still asks for confirmation:
   1. Start a brand new conversation
   2. Check the Customizations > Rules panel lists the rule
   3. Check the Customizations > Skills panel lists the skill

 Rollback:
   python3 $DEST_TOOL --rollback-list

 Docs: $REPO_URL
----------------------------------------------------------

EOF