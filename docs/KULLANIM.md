# Tüm seçenekler (Türkçe)

## Söz dizimi

```
python agent_edit.py --path <dosya> <işlem> [seçenekler]
```

`--path` her zaman zorunludur (geri alma modları hariç).

## Dört mod

Araç dört farklı iş yapar. Hangisini istediğini seçenekler belirler.

---

## 1. Metin değiştirme

### `--find` / `--replace`

```powershell
python agent_edit.py --path src/main.cpp --find "eski" --replace "yeni"
```

Varsayılan: sadece **ilk** eşleşmeyi değiştirir.

### `--all`

Tüm eşleşmeleri değiştirir.

```powershell
python agent_edit.py --path src/main.cpp --find "eski" --replace "yeni" --all
```

> Dikkat: `--all` kullanmadan önce eşleşme sayısını kontrol et. `grep -c` veya
> dosyada arama yap. Körlemesine `--all` ilgisiz kodları sessizce değiştirebilir.

### `--count N`

Kaç eşleşme değiştirileceğini sınırlar. `--all` ile birlikte kullanılamaz.

```powershell
python agent_edit.py --path src/main.cpp --find "TODO" --replace "DONE" --count 3
```

### `--gsub` (regex)

```powershell
python agent_edit.py --path src/main.cpp --gsub "\s*//\s*TODO:.*" --replace "" --all
```

`--gsub` ile birlikte `--regex` gerekmez, `--gsub` zaten regex'tir.
Regex'te `\1` gibi geri referanslar `--replace` değerinde kullanılabilir.

---

## 2. Tam dosya yazma

### `--content-file`

```powershell
python agent_edit.py --path src/main.cpp --content-file C:\tmp\yeni.cpp
```

Dosyanın tamamını yeni içerikle değiştirir. Mevcut dosya olmasa `--create` gerekir.

### `--stdin`

```powershell
cmd /c "type C:\tmp\yeni.cpp | python agent_edit.py --path src\main.cpp --stdin"
```

Bayt-kesin aktarım. Kodlama ve satır sonları korunur.

**`cmd /c type` kullan, PowerShell `Get-Content` değil.** `Get-Content` pipeline'da
kodlamayı bozar (test edilmiştir).

Linux/macOS'ta:
```bash
cat /tmp/yeni.cpp | python3 agent_edit.py --path src/main.cpp --stdin
```

---

## 3. Toplu düzenleme

### `--patch-file`

```powershell
python agent_edit.py --path src/main.cpp --patch-file patch.json
```

JSON dosyasındaki işlemleri sırayla uygular. Format için
[examples/README.md](../examples/README.md) dosyasına bak.

Herhangi bir işlem eşleşmezse hiçbir şey değişmez ve `2` çıkış kodu verilir.

---

## 4. Geri alma ve bakım

### `--rollback-list`

```powershell
python agent_edit.py --rollback-list
```

Yedekleri listeler (en yeni üstte):

```
Yedekler (12):
  20260101_143012_001  2026-01-01T14:30:12  src/main.cpp
  20260101_143008_000  2026-01-01T14:30:08  src/header.h
```

### `--rollback <id>`

```powershell
python agent_edit.py --rollback 20260101_143012_001
```

Belirtilen yedeği geri yükler.

Geri alma mantığı:
- Dosya düzenlemeden önce **vardıysa** → eski içerik geri yazılır
- Dosya **yoktuysa** (yeni oluşturulmuşsa) → dosya silinir
- Dosya o arada başka biri tarafından değiştirildiyse → **silinmez**, hata verir
  (veri kaybını önler)

### `--prune N`

```powershell
python agent_edit.py --prune 100
```

En son 100 yedeği bırakır, eskileri siler. Disk dolmasını önler.

---

## Doğrulama seçenekleri

### `--verify-cmd "<komut>"`

Yazma işleminden sonra çalıştırılacak doğrulama komutu. Başarısız olursa
değişiklik otomatik geri alınır ve komutun çıktısı gösterilir.

```powershell
--verify-cmd "cmake --build build --parallel"
--verify-cmd "npm run build"
--verify-cmd "python -m pytest -q"
--verify-cmd "cargo build"
--verify-cmd "go build ./..."
--verify-cmd "tsc --noEmit"
```

Komut, proje kökünde çalıştırılır. Varsayılan zaman aşımı 1800 saniyedir.

### `--skip-verify`

Statik doğrulamayı atlar. **Kullanma.** Sadece acil durumlar için.

Statik doğrulama araç dışında da bir şey yapmaz; sadece metin kontrolü yapar
(parantez dengesi, `.py`/`.json` syntax). `--skip-verify` bunu da kapatır.

---

## Dosya oluşturma

### `--create`

Hedef dosya yoksa hata verir (kod `2`). Oluşturabilmek için `--create` gerekir:

```powershell
python agent_edit.py --path src/yeni.cpp --content-file yeni.cpp --create
```

`--create` verilmeden var olmayan bir dosyaya yazmaya çalışırsan araç hiçbir şeye
dokunmaz.

---

## Proje kökü

### `--project-root <yol>`

Yedeklerin nereye yazılacağını belirler. Verilmezse otomatik bulunur: hedef
dosyanın üstündeki ilk `.git` klasörü aranır. Bulunamazsa dosyanın bulunduğu
dizin kullanılır.

```powershell
python agent_edit.py --path src/main.cpp --find "a" --replace "b" --project-root C:\proj
```

Yedekler her zaman `~/.gemini/backups/<proje-adı>-<hash>/` altına gider, proje
klasörünün **içine** değil. Böylece proje klasörü kirlenmez.

---

## Çıkış kodları

| Kod | Anlam | Dosya durumu |
|---|---|---|
| `0` | Başarılı | Değişti |
| `1` | Doğrulama başarısız, geri alındı | **Eski halinde** |
| `2` | Argüman hatası / eşleşme yok / dosya yok | Değişmedi |
| `3` | Yedekleme veya yazma hatası | Değişmedi veya geri alınamadı |

---

## Tam seçenek listesi

`python agent_edit.py --help` çalıştır.

```
--path PATH              düzenlenecek dosya
--content-file FILE      tam yeni içerik bu dosyadan
--stdin                  tam yeni içerik STDIN'den
--patch-file FILE        JSON: toplu find/replace
--find TEXT              aranacak metin
--replace TEXT           değiştirilecek metin
--gsub PATTERN           regex deseni
--all                    tüm eşleşmeleri değiştir
--count N                ilk N eşleşmeyi değiştir
--create                 dosya yoksa oluştur
--verify-cmd CMD         yazma sonrası doğrulama komutu
--skip-verify            statik doğrulamayı atla
--project-root PATH      proje kökünü elle ver
--rollback ID            yedek id ile geri al
--rollback-list          yedekleri listele
--prune N                son N yedeği bırak
```

---

## Sık yapılan hatalar

**`--find` eşleşmiyor, kod 2.**
Metin birebir aynı değil. Boşluk, satır sonu veya büyük/küçük harf farkı olabilir.
Önce dosyada arama yapıp metni kopyala.

**Tırnaklı kod bozuldu.**
`--find`/`--replace` yerine `--patch-file` kullan.

**`--all` beklediğinden fazla değiştirdi.**
Önce say: `python -c "print(open(r'src\main.cpp',encoding='utf-8').read().count('eski'))"`
veya `--count` kullan.

**Türkçe karakterler bozuldu.**
Araç kodlamayı korur. Eğer bozulduysa dosya zaten UTF-8 değildi ve `cp1254`
fallback'i devreye girmiştir. Dosyayı UTF-8'e çevirmek istersen bunu ayrı bir
işlem olarak yap.

**Yedek klasörü şişti.**
`--prune 100`
