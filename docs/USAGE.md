# All options (English)

## Syntax

```
python agent_edit.py --path <file> <operation> [options]
```

`--path` is always required, except in rollback mode.

## Four modes

The tool does four things. Options decide which.

---

## 1. Text replacement

### `--find` / `--replace`

```bash
python3 agent_edit.py --path src/main.cpp --find "old" --replace "new"
```

Default: replaces the **first** match only.

### `--all`

Replaces every match.

```bash
python3 agent_edit.py --path src/main.cpp --find "old" --replace "new" --all
```

> Warning: check the match count before using `--all`. A blind `--all` can
> silently rewrite unrelated code.

### `--count N`

Limits how many matches are replaced. Cannot be combined with `--all`.

```bash
python3 agent_edit.py --path src/main.cpp --find "TODO" --replace "DONE" --count 3
```

### `--gsub` (regex)

```bash
python3 agent_edit.py --path src/main.cpp --gsub "\s*//\s*TODO:.*" --replace "" --all
```

Backreferences like `\1` work in the `--replace` value.

---

## 2. Whole-file writes

### `--content-file`

```bash
python3 agent_edit.py --path src/main.cpp --content-file /tmp/new.cpp
```

Replaces the entire file. If the file does not exist, `--create` is required.

### `--stdin`

```bash
cat /tmp/new.cpp | python3 agent_edit.py --path src/main.cpp --stdin
```

Byte-exact transfer. Encoding and line endings preserved.

On Windows, use `cmd /c type`. PowerShell `Get-Content` mangles encoding in a
pipeline (tested).

---

## 3. Batch editing

### `--patch-file`

```bash
python3 agent_edit.py --path src/main.cpp --patch-file patch.json
```

Applies a list of operations from JSON in order. See
[examples/README.md](../examples/README.md) for the format.

If any operation fails to match, nothing is changed and the tool exits `2`.
No partial application.

---

## 4. Rollback and maintenance

### `--rollback-list`

```bash
python3 agent_edit.py --rollback-list
```

Lists backups, newest first:

```
Yedekler (12):
  20260101_143012_001  2026-01-01T14:30:12  src/main.cpp
  20260101_143008_000  2026-01-01T14:30:08  src/header.h
```

### `--rollback <id>`

```bash
python3 agent_edit.py --rollback 20260101_143012_001
```

Restores a backup.

Logic:
- File **existed** before the edit → original content restored
- File **did not exist** (was newly created) → file deleted
- File was **changed by someone else** since → **not deleted**, error raised
  (prevents data loss)

### `--prune N`

```bash
python3 agent_edit.py --prune 100
```

Keeps the newest 100 backups, deletes older ones. Prevents disk bloat.

---

## Validation options

### `--verify-cmd "<command>"`

A validation command run after the write. If it fails, the change is
automatically rolled back and the command output is printed.

```bash
--verify-cmd "cmake --build build --parallel"
--verify-cmd "npm run build"
--verify-cmd "python -m pytest -q"
--verify-cmd "cargo build"
--verify-cmd "go build ./..."
--verify-cmd "tsc --noEmit"
```

The command runs in the project root. Default timeout is 1800 seconds.

### `--skip-verify`

Skips static validation. **Do not use this.** Only for emergencies.

Static validation is cheap: bracket balance, and real syntax checks for `.py`
and `.json`. `--skip-verify` turns it off too.

---

## Creating files

### `--create`

Without `--create`, writing to a non-existent file is an error (code `2`).

```bash
python3 agent_edit.py --path src/new.cpp --content-file new.cpp --create
```

---

## Project root

### `--project-root <path>`

Overrides where backups are written. By default the tool walks up from the
target file looking for a `.git` directory. If none is found, it uses the
file's own directory.

```bash
python3 agent_edit.py --path src/main.cpp --find "a" --replace "b" --project-root /path/to/proj
```

Backups always go to `~/.gemini/backups/<project-name>-<hash>/`, never inside the
project directory, so your repo stays clean.

---

## Exit codes

| Code | Meaning | File state |
|---|---|---|
| `0` | Success | Changed |
| `1` | Validation failed, rolled back | **Original** |
| `2` | Bad arguments / no match / file missing | Unchanged |
| `3` | Backup or write failure | Unchanged, or rollback failed |

---

## Full option list

Run `python3 agent_edit.py --help`.

```
--path PATH              file to edit
--content-file FILE      full new content from this file
--stdin                  full new content from STDIN
--patch-file FILE        JSON: batch find/replace
--find TEXT              text to search for
--replace TEXT           replacement text
--gsub PATTERN           regex pattern
--all                    replace all matches
--count N                replace first N matches
--create                 create the file if missing
--verify-cmd CMD         validation command after write
--skip-verify            skip static validation
--project-root PATH      set the project root manually
--rollback ID            restore a backup by id
--rollback-list          list backups
--prune N                keep only the newest N backups
```

---

## Common mistakes

**`--find` does not match, code 2.**
The text is not byte-identical. Check whitespace, newlines, and letter case.
Search the file first and copy the exact text.

**Quoted code got corrupted.**
Use `--patch-file` instead of `--find` / `--replace`.

**`--all` changed more than expected.**
Count first:
`python3 -c "print(open('src/main.cpp',encoding='utf-8').read().count('old'))"`
or use `--count`.

**Non-ASCII characters got mangled.**
The tool preserves encoding. If it happened, the file was not UTF-8 to begin
with and the `cp1254` fallback kicked in. Convert the file to UTF-8 as a
separate, deliberate step.

**Backups folder is huge.**
`--prune 100`
