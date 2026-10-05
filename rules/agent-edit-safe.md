---
trigger: always_on
description: "Mandatory file editing protocol. Always modify files with agent_edit.py instead of the IDE editor, so no confirmation dialogs appear and no write can corrupt a file."
---

# File Editing Protocol

## Absolute constraints

These are not suggestions. Violating them either blocks the user or risks
destroying their code.

1. **Never** modify file contents through the IDE's built-in file editor or
   diff tool. Every edit raises an "Accept all" card that the user must click.
   The user must never have to click anything.

2. **Never** write to disk directly. Forbidden: `>` redirection, `Set-Content`,
   `Out-File`, `>>`, `open(path,'w')`, `Path.write_text()`,
   `writeFileSync()`, `sed -i`, `echo > file`, `tee`. These have no safety net.

3. **Never** skip validation on compiled languages. No `--skip-verify`.

4. **Never** change a file's encoding, BOM, or line endings as a side effect.
   Do not rewrite an entire file just to make a small edit.

5. **Never** batch-modify multiple files and validate afterwards. One file at
   a time, stop at the first failure.

6. **Never** modify generated output (`build/**`, `dist/**`, `node_modules/**`)
   or vendored dependencies (`third_party/**`, `vendor/**`).

## The tool

```
python ~/.gemini/tools/agent_edit.py --path <file> <operation>
```

On Windows the home directory must be spelled out, since PowerShell does not
expand `~`:

```
python C:\Users\<user>\.gemini\tools\agent_edit.py --path <file> <operation>
```

Every call: backs up the file, writes atomically, validates, and **restores the
original automatically** if validation fails. You never manage backups
yourself.

Run `python ~/.gemini/tools/agent_edit.py --help` for the option list instead
of reading the source.

## Choosing the operation

```
More than one line changes?
  YES -> Do you have the complete new file content already?
           YES -> write it to a temp file, then use --stdin
           NO  -> break it into parts, write a JSON patch, use --patch-file
  NO  -> plain identifier or short literal with no quotes or backslashes?
           YES -> --find / --replace
           NO  -> --patch-file
```

### Short plain text

```
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --find "oldName" --replace "newName"
```

Add `--all` for every occurrence, `--count N` to limit to the first N.

### Complex, quoted, or multi-line edits

Never pass this through the shell. Windows escaping corrupts it silently.

Write a JSON file first:

```json
[
  {"find": "QColor(255, 0, 0)", "replace": "QColor(0, 255, 0)"},
  {"find": "setToolTip(\"hello\")", "replace": "setToolTip(QStringLiteral(\"hello\"))", "all": true},
  {"find": "[ \\t]*//[ \\t]*TODO:.*", "replace": "", "regex": true, "all": true}
]
```

```
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --patch-file patch.json
```

Each entry: `find` (required), `replace` (defaults to empty), optional `all`,
`count`, or `"regex": true`. In JSON, every backslash in the source must be
doubled. If any entry fails to match, nothing is applied.

### Whole-file rewrite

```
cmd /c "type C:\tmp\new.cpp | python ~/.gemini/tools/agent_edit.py --path src\main.cpp --stdin"
```

Use `cmd /c type`, **not** PowerShell `Get-Content`, which corrupts encoding in a
pipeline. This transfer is byte-exact.

### New file

Add `--create`, otherwise writing to a missing file is an error.

## Validation

Compiled languages must be validated on every edit:

```
--verify-cmd "cmake --build build --parallel"
--verify-cmd "npm run build"
--verify-cmd "python -m pytest -q"
--verify-cmd "cargo build"
--verify-cmd "go build ./..."
--verify-cmd "tsc --noEmit"
```

If a build system file changed, reconfigure first:
`--verify-cmd "cmake -S . -B build && cmake --build build --parallel"`.

If the project already fails to build before your change, fix that first and
report it.

## Exit codes -- mandatory to check

| Code | Meaning | Required action |
| --- | --- | --- |
| `0` | Success | Continue |
| `1` | Validation failed, **rolled back** | Read the error, fix the edit, retry. Do **not** continue the task |
| `2` | Bad arguments or no match | Nothing changed. Correct the command |
| `3` | Backup or write failed | **Stop and tell the user** |

Codes `1` and `3` mean the file is intact but your edit did not happen. Never
report an edit as done unless the exit code was `0`.

## Rollback

Automatic on validation failure. Manual use only when the user asks you to undo
something, or a later step reveals the edit was wrong:

```
python ~/.gemini/tools/agent_edit.py --rollback-list
python ~/.gemini/tools/agent_edit.py --rollback <backup_id>
```

For a multi-file task, collect every backup id as you go. If the user wants the
whole task reverted, roll them back in reverse order.

## Reporting

After each successful edit, state:

```
Edited: src/main.cpp (backup: 20260101_143012_001)
```

The backup id is how the user can undo your work, so always include it. At the
end of a task, list all changed files with their backup ids.

## Anti-patterns

- Patching the same file more than three times in a row. If you keep patching,
  your picture of the file is wrong. Read it again.
- Using `--all` without counting occurrences first. A blind `--all` rewrites
  unrelated code.
- Editing files open in the user's editor windows without mentioning it. Their
  buffer goes stale and saving it overwrites your write.
- Refactoring or reformatting code outside the scope of the task.
- Claiming success without checking the exit code.
