# Sorun giderme

## Kurulum

### "Python was not found"

Python kurulu değil ya da PATH'te değil.

1. [python.org](https://www.python.org/downloads/) adresinden indir
2. Kurulumda **"Add python.exe to PATH"** kutusunu işaretle
3. PowerShell'i **kapat ve yeniden aç** (PATH değişikliği ancak yeni oturumda geçerli)

Kontrol:
```powershell
python --version
```

### "Python 3.8+ not found" ama Python kurulu

Sistemde Python 2.7 veya 3.7 var olabilir. `py -3 --version` dene. Sadece 3.8+
varsa kurulum betiği otomatik bulur.

Antigravity kuruluysa Python çoktan mevcuttur. Kurulum betiği
`C:\Users\<sen>\.gemini\` altına kurar, `python` komutu PATH'te olmasa bile
betik IDE'nin Python'ını kullanabilir.

### Kurulum "Download failed" hatası

İnternet bağlantısı ya da proxy sorunu olabilir. Betni indirip elle çalıştır:

```powershell
irm https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Dosya adı bozuk geliyor

`irm | iex` yerine indirip çalıştırmayı dene:
```powershell
irm https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.ps1 -OutFile install.ps1
```

### "cannot be loaded ... is not digitally signed"

Windows'un PowerShell execution politikası indirilen betiği engelliyor. Bu bir
Windows güvenlik ayarı, aracın hatası değil.

Geçici çözüm (tek çalıştırma):
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Kalıcı çözüm (sadece senin kullanıcı hesabın için):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Mevcut politikayı görmek için:
```powershell
Get-ExecutionPolicy -List
```

Not: `irm ... | iex` yöntemi bu sorunu yaşamaz, çünkü dosya yüklenmiyor.
Yeniysen o yöntemi kullan.

---

## Kullanım

### "HATA: dosya yok, --create kullan"

Hedef dosya yok. Ya mevcut bir dosyanın **yolunu yanlış yazdın**, ya da yeni
dosya oluşturuyorsun.

Yeni dosya için:
```powershell
python agent_edit.py --path src/yeni.cpp --content-file yeni.cpp --create
```

### "HATA: --find eslesmedi"

Metin birebir aynı değil. En sık nedenler:

- Boşluk farkı (1 yerine 2 boşluk)
- Sekme yerine boşluk
- Satır sonu farkı (LF vs CRLF)
- Büyük/küçük harf

Dosyada arama yap, metni kopyala yapıştır. Sorun devam ederse:

```powershell
python -c "import sys; d=open(r'src\main.cpp',encoding='utf-8').read(); print(repr(d[1000:1100]))"
```

Bu, o bölgeyi tırnaklı gösterir, görünmeyen karakterleri ortaya çıkarır.

### "HATA: yeni icerik eskisiyle ayni"

Değiştirmek istediğin metin zaten yazılı. Ya da `find` ve `replace` aynı
değer. Araç hiçbir şeye dokunmaz, bu doğru davranış.

### Çıkış kodu 3 — "Yedekleme basarisiz"

En tehlikeli kod çünkü dosya durumu belirsiz olabilir. Kontrol et:

1. Diskin dolu mu?
2. Hedef dosya **salt okunur** mu? (özellikle `third_party` altında)
3. Antivirüs veya izin engeli var mı?

Diskte yer yoksa `--prune 100` ile yedek temizle.

---

## Windows'a özel

### `~` çalışmıyor

PowerShell'de `~` genişlemez. Tam yol kullan:

```powershell
python "$env:USERPROFILE\.gemini\tools\agent_edit.py" --help
```

### Türkçe karakterler bozuldu

Araç kodlamayı korur, bu yüzden normalde olmaz. Şunları kontrol et:

1. Kaynak dosyanın kodlaması ne? Araç UTF-8 dener, olmazsa `cp1254` kullanır.
2. `cp1254` ile okunan bir dosyaya UTF-8 beklentisiyle yazmış olabilirsin

Doğrulamak için:
```powershell
python -c "print(open(r'src\main.cpp',encoding='utf-8').read()[:100])"
```
Türkçe karakterler düzgün görünüyorsa dosya UTF-8.

### Uzun satır "command too long" hatası

Uzun metni komut satırından geçirme. `--patch-file` veya `--stdin` kullan.

### `--find` içindeki `\"` bozuluyor

Bu, komut satırı kaçışının sınırı. `--patch-file` kullan:

```json
[{"find": "setToolTip(\"hello\")", "replace": "setToolTip(QStringLiteral(\"hello\"))"}]
```

```powershell
python agent_edit.py --path src/main.cpp --patch-file patch.json
```

### PowerShell `Get-Content` ile bozulan kodlama

`Get-Content | python` **kodlamayı bozar**. Test edilmiştir.

Doğrusu:
```powershell
cmd /c "type C:\tmp\new.cpp | python agent_edit.py --path src\main.cpp --stdin"
```

---

## Doğrulama

### `--verify-cmd` çok yavaş

Derleme her dosyada çalışıyor. Çözümler:

1. `--parallel` ekle: `--verify-cmd "cmake --build build --parallel"`
2. Hedefe özel derle: `--verify-cmd "cmake --build build --target mtr --parallel"`
3. Sadece sözdizimi kontrolü istersen `--verify-cmd` yerine `--skip-verify` kullan
   (ama gerçek derleme güvenliği sağlar, önermem)

### Derleme başarısız ama kod doğru

Projede **zaten** derleme hatası varsa araç her değişikliği geri alır.
Önce mevcut hatayı düzelt, sonra devam et.

Hatanın senden mi yoksa projeden mi olduğunu anlamak için: değişiklik yapmadan
`cmake --build build --parallel` çalıştır.

### Derleme çok uzun sürüyor / takılıyor

Varsayılan zaman aşımı 1800 saniye. Daha kısa istersen kaynak kodda
`verify_cmd` fonksiyonundaki `timeout=1800` değerini değiştir.

---

## Yedekler

### Yedek klasörü çok büyüdü

```powershell
python agent_edit.py --prune 100
```

Her düzenleme bir klasör bırakır. Yüzlerce düzenleme yaptıysan GB'ler olabilir.

### Yedekler nerede?

```
~/.gemini/backups/<proje-adı>-<hash>/
```

Windows:
```
C:\Users\<sen>\.gemini\backups\
```

Proje adı + proje yolunun kısa hash'i. Aynı isimli iki proje çakışmasın diye
hash eklenir.

### Geri alma "DOSYA DEGISTIRILMIS" hatası veriyor

Yedeklenen dosya sen bu yedeği aldıktan sonra **başka biri tarafından**
değiştirilmiş. Araç veri kaybını önlemek için geri almayı reddeder.

Ne yapmalı: yedekteki içeriğe elle bak, gerekirse dosyayı yedekten kopyala.

### Yedekten geri yükledim, hâlâ bozuk

`manifest.json` içindeki `path` değerini kontrol et. Belki başka bir yedek
tanımlı. `--rollback-list` ile listeye bak.

---

## Ajan davranışı

### Ajan hâlâ onay istiyor

Bu en sık sorulan soru. Sırayla kontrol et.

**1. Ajanı gerçekten yeniden başlattın mı?**

Kural ve beceriler **konuşma başında** okunur. Açık bir konuşmaya yeni mesaj
yazmak yetmez, yeni oturum açman gerekir. IDE'yi kapatıp açmak en garantisi.

**2. Kurulum gerçekten rule yazdı mı?**

```powershell
Test-Path "$env:USERPROFILE\.gemini\config\rules\agent-edit-safe.md"
```

`True` olmalı. Bu dosya şart. Sadece aracı kurmak hiçbir işe yaramaz.

**3. Boyut sınırı aşıldı mı?**

Antigravity dosya başına **24.000 bayt** sınırı koyar. Üstü varsa sessizce
kesilir.

```powershell
(Get-Item "$env:USERPROFILE\.gemini\config\rules\agent-edit-safe.md").Length
```

24000'den küçük olmalı (varsayılan ~5.5 KB).

**4. Frontmatter doğru mu?**

`config/rules/*.md` dosyaları **mutlaka** YAML frontmatter ile başlamalı:

```
---
trigger: always_on
description: "..."
---
```

`trigger` değeri şunlardan biri olmalı: `always_on`, `model_decision`, `glob`,
`manual`. Geçersiz değer olursa kural **sessizce atılır**, hata vermez.

Doğrulamak için:
```powershell
Get-Content "$env:USERPROFILE\.gemini\config\rules\agent-edit-safe.md" -TotalCount 5
```

**5. GEMINI.md çakışması var mı?**

`GEMINI.md` içinde eski bir "edit aracı kullan" ya da tersi yön bir kural varsa
çelişki olur. Kontrol et:

```powershell
Select-String -Path "$env:USERPROFILE\.gemini\GEMINI.md" -Pattern "edit|diff|Accept"
```

**6. Antigravity panelinde kural görünüyor mu?**

IDE'de **Settings > Customizations > Rules** sekmesini aç. Kuralın listelendiğini
gör. Görünmüyorsa dosya yolu yanlış veya frontmatter bozuk.

Aynı şekilde **Skills** sekmesinde beceri görünmeli.

**7. Token bütçesi taştı mı?**

Tüm global + `always_on` kurallar **20.000 jeton** paylaşır. Aşılırsa
Antigravity en büyük dosyaları otomatik olarak "pointer"a çevirir, yani içerik
yüklenmez.

Çözüm: `GEMINI.md`ni kısalt veya gereksiz kuralları sil.

### Kural yüklendi ama ajan yine de edit aracını kullanıyor

Bu, kuralın **çatışma** durumunda kaldığı anlamına gelir. Ajanın sistem
prompt'unda başka bir yönerge öncelikli olabilir.

Güçlendirmek için `GEMINI.md`ye şunu ekle (kurulum otomatik ekler ama daha net
olması için elle de yazabilirsin):

```markdown
# Dosya Duzenleme

Tum dosya degisiklikleri icin MUTLAKA su araci kullan:
python C:\Users\SEN\.gemini\tools\agent_edit.py --path <dosya> --find "..." --replace "..."

IDE'nin kendi edit/diff aracini KULLANMA.
Dogrudan Set-Content / redirection ile yazma.
```

Sonra **yeni konuşma** başlat.

### Çok eski Antigravity sürümü

Bazı çok eski sürümler `config/rules/` dizinini hiç okumaz. Bu durumda
`GEMINI.md` tek çalışan yoldur. Kurulum zaten onu güncelliyor. Doğrulamak için
Customizations > Rules panelinde kuralı gör.

### Skill görünüyor ama kural değil

Beklenen davranış değil bu. Skill tek başına yeterli değil, çünkü ajan önce
edit aracını kullanmayı tercih eder. Kural (`config/rules/`) şart.

### Ajan çıkış kodlarını kontrol etmiyor

`SKILL.md` içinde "Reading exit codes" bölümü var. Ajan oraya bakmalı.
Olmazsa ajana ayrıca söyle: "Her `agent_edit.py` çağrısından sonra çıkış kodunu
kontrol et. Kod 1 veya 3 ise dur ve bana bildir."

### "File was modified" uyarısı alıyorum

Ajan diske yazdı, senin editöründeki dosya bayatladı. Düzeltmek için:

1. Editörde dosyayı **kaydetmeden kapat** (kaydetme, ajanın yazdığını siler)
2. Yeniden aç

Ya da ajana "dosyayı şimdi diskte oku" de, `view_file`/`read` aracıyla tazelesin.

---

## Hâlâ çözülmediyse

1. `--help` çıktısını oku, seçenek doğru mu
2. Hata mesajındaki çıkış koduna bak, tabloda karşılığını bul
3. Sorunu [GitHub Issues](https://github.com/lepotane/gemini-bypass-permission/issues)'a yaz

Hata mesajını, kullandığın komutu ve işletim sistemini paylaş.
