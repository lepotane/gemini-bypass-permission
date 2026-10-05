# gemini-bypass-permission

**A reversible file editing tool that stops AI coding agents from corrupting your code.**

[English](README.en.md) · [Install](#install) · [Troubleshooting](docs/SORUN_GIDERME.md)

---

## What problem does this solve?

AI coding agents (Antigravity, Claude Code, Gemini CLI, Cursor, Copilot, Aider, ...)
have two problems when they write code:

### Problem 1: They ask for approval on every single change

Whenever the agent modifies a file, an "Accept all / Reject all" card appears.
You have to click it every time. Thirty file changes means thirty clicks.

### Problem 2: If they write wrong, the file breaks permanently

Agents normally write through the IDE's own editor tool. If the content is wrong,
or the process dies mid-write, the file is corrupted and there is no way back.

### This tool solves both

| | Normal agent behaviour | With this tool |
|---|---|---|
| Approval card | Appears on every edit | **Never appears** |
| Wrong edit | File stays broken | Automatically rolled back |
| Build error | Stays in the file, you may not notice | Rolled back, error shown to you |
| Encoding damage | Line endings, non-ASCII chars change | Automatically preserved |

**In short:** the agent does the work, you click nothing. If anything fails, the
file stays exactly as it was.

---

## How it works: rule + skill + tool

Three pieces, and **all three are required**:

| Piece | What it does | Why it is required |
|---|---|---|
| **Tool** (`agent_edit.py`) | Does the real work: backup, atomic write, validation, rollback | Provides the safety |
| **Rule** (`agent-edit-safe.md`) | Forces the agent to skip the IDE editor and use this tool | Changes agent **behaviour** |
| **Skill** (`SKILL.md`) | Multi-step decision tree, exit codes, quoting rules | Teaches agent **method** |

Installing only the tool does **nothing**. The agent does not know to use it, so
it keeps using the editor and keeps asking for approval. Without the rule there
is no effect at all.

### Rule or skill?

Antigravity loads these two from different places and by different mechanisms:

| | Rule | Skill |
|---|---|---|
| For | Constraints, invariants ("never do X") | Multi-step workflows |
| Loaded from | Disk, under `~/.gemini/` | Backend service |
| Always active | `trigger: always_on` | Model decision |
| Reliability | **High** -- file is on your machine | Low -- server side |

For your situation the **rule is the essential part**; the skill is an extra
layer. The installer sets up both.

The installer writes to four locations:

```
~/.gemini/tools/agent_edit.py                        <- the tool
~/.gemini/config/rules/agent-edit-safe.md            <- global rule (always_on)
~/.gemini/config/skills/agent-edit-safe/             <- Antigravity 2.0 skill
~/.claude/skills/agent-edit-safe/                    <- Claude Code / older Antigravity
```

It also appends a pointer to `~/.gemini/GEMINI.md` and can optionally install a
workspace rule (see `-ProjectRoot`).

### Why install to so many places?

Because different agents load from different paths:

- **Antigravity IDE (older builds)** -- `~/.gemini/GEMINI.md` and `.claude/skills/`
- **Antigravity 2.0** -- `~/.gemini/config/rules/` and `~/.gemini/config/skills/`
- **Claude Code** -- `~/.claude/skills/`
- **Gemini CLI** -- `~/.gemini/GEMINI.md`

Installing all of them is the safe option. It is one line and a few hundred
bytes. If something goes wrong, delete them.

---

## Install

### Windows (PowerShell)

Paste this single line into PowerShell and press Enter:

```powershell
irm https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.ps1 | iex
```

`irm` (Invoke-RestMethod) downloads and runs the script. Nothing to save first.

> **Windows gotcha:** If you download the script and try to run it from the file,
> PowerShell may refuse with *"is not digitally signed"*. That is a Windows
> security setting, not a bug in this project.
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File .\install.ps1
> ```
>
> Permanent fix (current user scope only):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> The `irm | iex` method above never hits this, because no file is loaded.
> **If you are new, start with `irm | iex`.**

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.sh | bash
```

### Manual install (optional)

The script copies files into several places. You can also do it by hand:

```
~/.gemini/
├── tools/
│   └── agent_edit.py            <- the tool
├── backups/                     <- created automatically
└── config/
    ├── rules/
    │   └── agent-edit-safe.md   <- global rule
    └── skills/
        └── agent-edit-safe/     <- the skill your agent reads
            ├── SKILL.md
            └── scripts/agent_edit.py
```

On Windows, write `%USERPROFILE%` instead of `~`.

### Python requirement

Python **3.8 or newer** is required. On Windows, make sure you tick
**"Add python.exe to PATH"** during setup.

```powershell
python --version
```

If you get `Python was not found`, install it from
[python.org](https://www.python.org/downloads/), then close and reopen
PowerShell.

---

## What the installer does

1. Checks that Python 3.8+ exists (stops with guidance if not)
2. Copies the tool to `~/.gemini/tools/agent_edit.py`
3. Installs the rule to `~/.gemini/config/rules/agent-edit-safe.md`
4. Installs the skill to two locations
5. Appends a pointer to `~/.gemini/GEMINI.md`
6. Runs the tool and performs a real edit as a smoke test

**Restart your agent afterwards.** Rules and skills are read when a conversation
starts; an open session does not refresh them.

---

## Usage

### With an AI agent (recommended)

Nothing to do after install. The agent finds the rule and applies it. Just
describe your task.

> "Replace the old menu code in mapeditorview.cpp with the new menu system"

The agent will no longer wait for your approval on every edit.

### Manually

```bash
# Simple edit
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --find "old" --replace "new"

# Replace every occurrence
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --find "old" --replace "new" --all

# All options
python ~/.gemini/tools/agent_edit.py --help
```

---

## How it works

Four steps on every edit:

```
1. BACK UP   ->  ~/.gemini/backups/<project>/<timestamp>/
2. WRITE     ->  write to a temp file, then move it into place
3. VALIDATE  ->  bracket balance, real syntax check for .py/.json
4. ROLL BACK ->  if validation fails, restore the original automatically
```

### Exit codes

| Code | Meaning | What to do |
|---|---|---|
| `0` | Success | Continue |
| `1` | Validation failed, **rolled back** | Read the error, fix, retry |
| `2` | Bad arguments / no match | Nothing changed, fix the command |
| `3` | Backup or write failed | **Stop and tell the user** |

### Rollback

Every successful operation prints a backup id:

```
Edited: src/main.cpp (backup: 20260101_143012_001)
```

```bash
python ~/.gemini/tools/agent_edit.py --rollback-list
python ~/.gemini/tools/agent_edit.py --rollback 20260101_143012_001
```

Rollback also happens automatically on validation failure.

---

## Quoting problems on Windows

C++ code contains double quotes, backslashes, and newlines. Passing that through
the command line corrupts it. Two safe options exist.

### 1. Patch file (recommended)

Write a JSON file first, then pass its path:

```json
[
  {"find": "QColor(255, 0, 0)", "replace": "QColor(0, 255, 0)"},
  {"find": "setToolTip(\"hello\")", "replace": "setToolTip(QStringLiteral(\"hello\"))", "all": true},
  {"find": "[ \\t]*//[ \\t]*TODO:.*", "replace": "", "regex": true, "all": true}
]
```

```powershell
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --patch-file patch.json
```

### 2. STDIN (whole-file rewrite)

```powershell
cmd /c "type C:\tmp\new.cpp | python ~/.gemini/tools/agent_edit.py --path src/main.cpp --stdin"
```

**Use `cmd /c type`, not PowerShell `Get-Content`** -- the latter mangles encoding
in a pipeline.

---

## Encoding and line endings

Automatically preserved:

- UTF-8 BOM present or absent
- CRLF or LF
- `cp1254` fallback for non-UTF-8 files (Turkish Windows)

Verified: in a 56-byte file with non-ASCII characters, only the targeted byte
changed. The other 55 bytes stayed identical.

---

## FAQ

**My agent still asks for approval.**
Restart it first, then work through the checklist in
[docs/SORUN_GIDERME.md](docs/SORUN_GIDERME.md).

**Do backups pile up?**
Each edit creates one folder. To clean up:

```bash
python ~/.gemini/tools/agent_edit.py --prune 100
```

**I want to uninstall.**
Delete `~/.gemini/tools/agent_edit.py` and the `rules/` and `skills/` folders
under `~/.gemini/config/`.

**Does it work with other agents?**
Yes. The tool is a plain Python script. `SKILL.md` is read by Antigravity,
Claude Code, and Gemini CLI. For other agents, put the instructions in
`GEMINI.md` or `AGENTS.md`.

---

## Project layout

```
gemini-bypass-permission/
├── README.md                    <- Turkish (main)
├── README.en.md                 <- this file (English)
├── CHANGELOG.md
├── LICENSE                      <- MIT
├── install.ps1                  <- Windows installer
├── install.sh                   <- Linux/macOS installer
├── scripts/
│   └── agent_edit.py            <- the tool
├── rules/
│   └── agent-edit-safe.md       <- global rule (trigger: always_on)
├── skills/
│   └── agent-edit-safe/
│       ├── SKILL.md             <- agent instructions
│       └── scripts/agent_edit.py
├── examples/
│   ├── README.md                <- patch format explained
│   ├── demo.cpp                 <- sample file
│   └── patch.example.json       <- example patch that works on demo.cpp
└── docs/
    ├── KULLANIM.md              <- all options (Turkish)
    ├── USAGE.md                 <- all options (English)
    ├── GELISTIRME.md            <- extending the tool
    ├── SORUN_GIDERME.md         <- troubleshooting
    └── GEMINI_RULES.md          <- rules to copy manually
```

### Installer options

```powershell
.\install.ps1 -Prefix C:\tools\gemini     # install elsewhere
.\install.ps1 -ProjectRoot C:\src\proj     # also add workspace rule
.\install.ps1 -NoSkill                     # tool + rule only
.\install.ps1 -NoRule                      # tool + skill only
.\install.ps1 -NoGeminiMd                  # do not touch GEMINI.md
```

---

## Contributing

Contributions welcome, especially:
- New validation types (Rust, Go, C#)
- New file formats
- Smarter rollback strategies

## License

MIT. Use it, change it, ship it.