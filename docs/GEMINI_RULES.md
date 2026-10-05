# Ajan kuralları (beceri desteklemeyen ajanlar için)

`SKILL.md` becerisi olan ajanlar (Antigravity 2.0, Claude Code, Gemini CLI)
kurulumda otomatik bu talimatları alır.

Ama bazı ajanlar beceri sistemi kullanmaz veya eski sürümdedir. Onlar için aşağıdaki
kuralları `GEMINI.md`, `AGENTS.md`, `.cursorrules` veya ajanın kural dosyasına
elle kopyala.

Yol değişikliklerini kendi sistemine göre düzenle.

---

## GEMINI.md / AGENTS.md için

```markdown
# File Editing Rules

## NEVER

- Do NOT use the IDE's built-in file editor or diff tool to modify files. Every
  edit raises a confirmation card that the user must click.
- Do NOT write files directly via `>`, `Set-Content`, `Out-File`,
  `open(path,'w')`, `Path.write_text()`, or any raw write.
- Do NOT change a file's encoding, BOM, or line endings as a side effect.
- Do NOT batch-modify multiple files and validate afterwards.

## ALWAYS

Modify files only with:

    python ~/.gemini/tools/agent_edit.py --path <file> --find "..." --replace "..."

This tool backs up every file, writes atomically, validates, and rolls back
automatically if validation fails.

### Operations

- Short plain text:
  `--find "old" --replace "new"`
- All occurrences: add `--all`
- Complex or multi-line edits: write a JSON file and use `--patch-file FILE`
- Whole-file rewrite: `cmd /c "type new.txt | python ~/.gemini/tools/agent_edit.py --path FILE --stdin"`
  (use `cmd /c type`, not PowerShell `Get-Content`, which mangles encoding)
- New file: add `--create`

### Validation

For compiled languages always pass `--verify-cmd`:

    --verify-cmd "cmake --build build --parallel"

Others: `npm run build`, `python -m pytest -q`, `cargo build`, `go build ./...`

### Exit codes -- check every time

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | Success | Continue |
| 1 | Validation failed, rolled back | Read the error, fix, retry. Do not continue the task |
| 2 | Bad arguments / no match | Nothing changed. Fix the command |
| 3 | Backup or write failed | Stop and tell the user |

### Rollback

    python ~/.gemini/tools/agent_edit.py --rollback-list
    python ~/.gemini/tools/agent_edit.py --rollback <backup_id>

Rollback is automatic on validation failure. Use manually only when the user
asks you to undo something.

### Reporting

After each edit report:

    Edited: <path> (backup: <backup_id>)
```

---

## Sadece Windows'ta çalışıyorsan

Yol `~` yerine tam yazılmalı çünkü PowerShell `~` genişletmez:

```markdown
    python C:\Users\SEN\.gemini\tools\agent_edit.py --path <file> ...
```

Kendi kullanıcı adını yaz.

---

## C++ / CMake projeleri için ek kurallar

```markdown
## C++ project rules

- Always validate with `--verify-cmd "cmake --build build --parallel"`
- If CMakeLists.txt or a *.cmake file changed, reconfigure first:
  `--verify-cmd "cmake -S . -B build && cmake --build build --parallel"`
- Never modify `third_party/**` -- those are vendored libraries
- Never modify `build/**` -- those are generated outputs
- Header files (*.h, *.hpp) affect every translation unit. Always validate.
```

---

## Sadece basit metin değişikliği yapan ajanlar için (minimal)

Ajan çok basit bir modelse, tüm kuralları vermek yerine şu yeter:

```markdown
# File Editing

Modify files only with this command, never with built-in editor tools:

    python ~/.gemini/tools/agent_edit.py --path <file> --find "old" --replace "new"

For code containing quotes or newlines, use --patch-file (JSON) or --stdin.

If it exits 1 or 3, the change was NOT applied. Report the error and stop.
```

---

## Neden `GEMINI.md` gerekli olabilir

| Durum | Yapman gereken |
|---|---|
| Antigravity 2.0 | Kurulum yeterli, beceri otomatik bulunur |
| Claude Code | Kurulum yeterli |
| Gemini CLI | Kurulum yeterli |
| Cursor | `SKILL.md`'yi `.cursor/rules/` altına kopyala veya kuralları yapıştır |
| Aider | `GEMINI.md` veya `CONVENTIONS.md` içine yapıştır |
| Copilot | `.github/copilot-instructions.md` içine yapıştır |
| Eski ajan sürümleri | `GEMINI.md` içine yapıştır |

Beceri sistemi olan ama çalışmayan ajanlarda da bu dosya işe yarar.
