# Aracı genişletme

Bu belge, `agent_edit.py`'ye yeni yetenekler eklemek isteyenler içindir.

## Mimari

Araç tek dosya, harici bağımlılık yok (sadece Python standart kütüphanesi).
Bu bilinçli bir tercih: kullanıcının `pip install` yapmasına gerek kalmaz.

```
agent_edit.py
├── yardımcılar      sha256, proje kökü bulma, yedek yolu hesaplama
├── kodlama          BOM algılama, satır sonu algılama, atomik yazma
├── yedekleme        create_backup, restore_backup, list_backups, prune
├── doğrulama        verify_static (metin), verify_cmd (komut)
├── yazma            write_atomic, read_file_raw
├── CLI              build_parser, normalize_argv, main
└── çıkış kodları    0 başarı, 1 geri alındı, 2 argüman, 3 hata
```

## Yeni doğrulama tipi ekleme

`verify_static` fonksiyonuna yeni bir dal ekle. Örneğin Rust için:

```python
elif ext == ".rs":
    if text.count("{") != text.count("}"):
        return False, "süslü parantez dengesiz"
    if text.count("(") != text.count(")"):
        return False, "parantez dengesiz"
```

Sonra `CRITICAL_EXT` veya benzeri listeye eklemek gerekmez, `verify_static`
içindeki `elif` zinciri yeterlidir.

### Daha güçlü doğrulama istiyorsan

Derleme tabanlı doğrulama `--verify-cmd` ile gelir ve araçtan bağımsızdır:

```bash
--verify-cmd "cargo build"
--verify-cmd "go vet ./..."
--verify-cmd "dotnet build"
```

Bunlar her dil için çalışır, araçta özel kod gerekmez.

## Yeni işlem modu ekleme

`main()` içinde `if/elif` zinciri var. Yeni bir mod eklemek için:

1. `build_parser()` içine argüman ekle
2. `main()` içinde `elif args.yeni_mod:` dalı ekle
3. `new_text` üret, geri kalan akış (yedekle, yaz, doğrula, geri al) aynen çalışır

Önemli: dal düşse bile `new_text == old_text` kontrolü geçerli olmalı, yoksa
`2` dönmelisin.

## Yeni kritik dosya kalıbı

```python
CRITICAL_NAMES = {
    "cmakelists.txt", "makefile", "package.json", ...
}
CRITICAL_EXT = {".cmake", ".pem", ".key", ...}
```

Bu listeler `is_critical()` tarafından kullanılır. Bir dosya kritikse, başarılı
işlem sonrası ek bir uyarı yazdırılır. Amaçı **uyarı**, engel değil — araç yine
de yazmaya izin verir çünkü senin kararın.

## Atomik yazma neden bu şekilde

```python
tmp = os.path.join(d, "." + os.path.basename(path) + ".agent_edit.tmp")
with open(tmp, "wb") as f:
    f.write(text.encode(enc, errors="surrogateescape"))
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, path)
```

Üç kritik nokta:

**Geçici dosya hedefle aynı diskte olmalı.** Farklı diskte olursa `os.replace`
atomik olmaz.

**`fsync` çağrısı.** Veri diske inmeden rename edilirse, güç kesintisinde
boş dosya kalabilir.

**`os.replace` atomik.** Hedef üzerine yazma atomik bir işlemdir, yarım dosya
görünmez.

**`errors="surrogateescape"`** — dosyada geçersiz bayt varsa okuma hata vermez,
yazma sırasında aynen korunur. Bu sayede araç bozuk dosyayı da "onar" değil,
olduğu gibi korur.

## Satır sonu ve kodlama: dokunma

Bu kısım en çok hata yapılan yer. Kural:

**Python'un `open()` fonksiyonunu metin modunda `newline` vermeden kullanma.**

```python
YANLIŞ:  open(path, "r")            # CRLF -> LF çevirir, yazınca bozar
YANLIŞ:  open(path, "w")            # LF yazar, BOM siler
DOĞRU:  open(path, "rb")            # bayt düzeyinde çalış
```

Aracın `read_file_raw` fonksiyonu bu yüzden binary modda okuyup manuel decode
ediyor. Sen de yeni okuma yolu ekliyorsan aynısını yap.

## Yedekleme formatı

```
~/.gemini/backups/<proje-adı>-<hash8>/
└── 20260101_143012_001/
    ├── manifest.json
    └── files/
        └── <rel-yol>
```

`manifest.json` içeriği:

```json
{
  "id": "20260101_143012_001",
  "project_root": "C:\\proj",
  "path": "C:\\proj\\src\\main.cpp",
  "rel": "src\\main.cpp",
  "existed": true,
  "created": "2026-01-01T14:30:12",
  "hash_before": "abc123..."
}
```

`hash_before` geri alma sırasında kullanılır: dosya sonradan başka biri
tarafından değiştirilmişse geri alma **reddeder** ve veri kaybını önler.

## Yeni çıkış kodu ekleme

`main()` sonundaki `return` değerleri. Mevcut kodlar:

| Kod | Anlam |
|---|---|
| `0` | Başarılı |
| `1` | Doğrulama başarısız, geri alındı |
| `2` | Argüman hatası / eşleşme yok |
| `3` | Yedekleme/yazma hatası |

Yeni kod eklerken `SKILL.md` ve `docs/` dosyalarını da güncelle — ajan bu
tabloya bakarak karar veriyor.

## Test yazma

Araç için otomatik test dosyası yok. Elle test şablonu:

```python
import subprocess, os, tempfile, sys

TOOL = "scripts/agent_edit.py"

def run(*args, **kw):
    return subprocess.run([sys.executable, TOOL, *args],
                          capture_output=True, text=True, **kw)

def test_crlf_preserved():
    d = tempfile.mkdtemp()
    f = os.path.join(d, "a.cpp")
    with open(f, "wb") as fh:
        fh.write(b"int a = 1;\r\nint b = 2;\r\n")
    r = run("--path", f, "--find", "1", "--replace", "9")
    assert r.returncode == 0
    with open(f, "rb") as fh:
        assert fh.read().count(b"\r\n") == 2, "CRLF kayboldu!"

def test_rollback_on_bad_syntax():
    d = tempfile.mkdtemp()
    f = os.path.join(d, "a.cpp")
    with open(f, "w") as fh:
        fh.write("int a = 1;")
    r = run("--path", f, "--find", "1;", "--replace", "1; ((((")
    assert r.returncode == 1, "doğrulama yakalamalıydı"
    assert open(f).read() == "int a = 1;", "geri alınmalıydı"
```

Çalıştırmak için pytest kullan veya basit `assert` dosyası yazıp `python` ile
çalıştır.

## CLI kaçış tuzağı

`argparse` `--replace -\1` gibi `-` ile başlayan değerleri seçenek sanar.
Bu yüzden `normalize_argv` fonksiyonu `--opt=value` biçimine çeviriyor.

Yeni bir değer alan seçenek eklersen `takes_value` kümesine ekle. Aksi halde
`--yeni -1` gibi bir çağrı hata verir.

## Tip ipucu

`python` ile `-c "import ast; ast.parse(open('scripts/agent_edit.py').read())"`
yazarak sözdizimi hatasını anında yakalayabilirsin.

## Katkı gönderme

1. Değişikliği yap
2. Yukarıdaki testleri çalıştır
3. `SKILL.md` ve `docs/` güncelle (yeni seçenek eklediysen)
4. `CHANGELOG.md` güncelle
5. Pull request aç

`SKILL.md` dosyasını güncellemeyi unutma — ajan davranışı buradan öğreniyor,
README'den değil.
