# Changelog

Tum onemli degisiklikler bu dosyada.

Format: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/)
Surumleme: [SemVer](https://semver.org/lang/tr/)

## [0.1.0] - 2026-10-05

Ilk surum.

### Eklenen

- `agent_edit.py` -- geri donus garantili dosya duzenleme araci
  - Zaman damgali otomatik yedekleme, `~/.gemini/backups/` altinda
  - Atomik yazma (gecici dosya + `os.replace` + `fsync`)
  - Statik dogrulama: parantez dengesi, `.py`/`.json` gercek syntax kontrolu
  - `--verify-cmd` ile harici dogrulama (derleme, test)
  - Dogrulama basarisizsa otomatik geri alma
  - Elle geri alma (`--rollback`) ve yedek listeleme
  - Yedek temizleme (`--prune`)
- Kodlama korumasi
  - UTF-8 BOM algilama ve koruma
  - CRLF / LF satir sonu koruma
  - UTF-8 degilse `cp1254` fallback (Turkce Windows)
  - `surrogateescape` ile gecersiz bayt koruma
- Giris modlari
  - `--find` / `--replace` / `--all` / `--count`
  - `--gsub` (regex)
  - `--content-file`
  - `--stdin` (bayt-kesin aktarim)
  - `--patch-file` (JSON toplu duzenleme)
- Cikis kodlari: `0` basari, `1` dogrulama/geri alindi, `2` arguman, `3` yazma
- `rules/agent-edit-safe.md` -- Antigravity global kurali (`trigger: always_on`)
- `skills/agent-edit-safe/SKILL.md` -- ajan beceri paketi
- Kurulum betikleri: `install.ps1` (Windows), `install.sh` (Linux/macOS)
- Dokumanlar: Turkce ve Ingilizce README, kullanim, gelistirme, sorun giderme

### Duzeltilen

Gelistirme sirasinda bulunan ve duzeltilen hatalar:

- **CRLF satir sonlari bozuluyordu.** Python'un `open(path, "r")` metin modu
  CRLF'yi LF'e ceviriyordu. Bu arac her C++ dosyasinin tum satir sonlarini
  degistirirdi. Okuma ikili moda alindi, kodlama ve satir sonu elle yonetiliyor.
- **UTF-8 BOM kayboluyordu.** Yazma sirasinda BOM eklenmiyordu. Artik algilanip
  geri yaziliyor.
- **`--replace -\1` hata veriyordu.** `argparse` `-` ile baslayan degeri secenek
  saniyordu. `normalize_argv` ile `--opt=value` bicimine cevriliyor.
- **`--patch-file` regex girdileri calismiyordu.** Eslesme kontrolu `count()` ile
  yapiliyordu ve regex desenini duz metin sayiyordu, her regex girdisinde hata
  veriyordu. Artik regex girdileri `rx.search()` ile kontrol ediliyor.
- **`import time` eksikti.** Yedek kimligi uretimi sirasinda `NameError`.
- **Kurulum betigi `irm | iex` ile calismiyordu.** Betik boruya zorlandiginda
  `$PSScriptRoot` ve `$MyInvocation.MyCommand.Path` null oluyor, `Join-Path`
  "Cannot bind argument to parameter Path" hatasi veriyordu. `$SrcDir` artik
  savunmaci sekilde turetiliyor ve her kullanimi korumali.

## [Kisa surum gecmisi]

Bu arac, buyuk bir C++ projesinde bir ajanin yazdigi dosyalari korumak icin
gelistirildi. Baslangicta sadece --find/--replace vardi; Windows tirnak kacisi
ve satir sonu sorunlari cikinca `--patch-file`, `--stdin` ve kodlama korumasi
eklendi.
