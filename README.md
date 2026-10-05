# gemini-bypass-permission

**Yapay zeka ajanlarının dosyaları bozmasını engelleyen, geri alınabilir dosya düzenleme aracı.**

[English](README.en.md) · [Kurulum](#kurulum) · [Sorun Giderme](docs/SORUN_GIDERME.md)

---

## Bu araç ne işe yarar?

Yapay zeka ajanları (Antigravity, Claude Code, Gemini CLI, Cursor, Copilot, Aider, ...)
kod yazarken iki sorun çıkarır.

### Sorun 1: Her degisiklik icin onay ister

Ajan bir dosyayi degistirdiginde ekranda "Accept all / Reject all" karti cikar.
Sen de her seferinde tiklamak zorunda kalirsin. 30 dosya degisikliginde 30 kez tiklarsin.

### Sorun 2: Hatali yazarsa dosya bozulur

Ajan genelde editorun kendi araciyla dosya yazar. Yanlis yazarsa veya yazarken hata
olursa dosya bozulur ve geri donusun olmaz.

### Bu arac ikisini birden cozer

| | Normal ajan davranisi | Bu aracla |
|---|---|---|
| Onay karti | Her degisiklikte cikar | **Hiç cikmaz** |
| Yanlis yazma | Dosya kalici bozulur | Otomatik geri alinir |
| Derleme hatasi | Dosyada kalir, fark etmezsin | Geri alinir, hatayi sana gosterir |
| Kodlama bozulmasi | Satir sonlari ve Turkce karakterler degisir | Otomatik korunur |

**Kisacasi:** Ajan istedigini yapar, sen hicbir seye tiklamazsin. Hata olursa dosya
eskisinde kalir.

---

## Nasil calisiyor: kural + beceri + arac

Bu, uc parcadan olusur ve **ucu de sart**:

| Parca | Ne yapar | Neden sart |
|---|---|---|
| **Arac** (`agent_edit.py`) | Asil isi yapar: yedek, atomik yazma, dogrulama, geri alma | Guvenligi saglar |
| **Kural** (`agent-edit-safe.md`) | Ajani "editor araci kullanma, sunu kullan" diye zorlar | Ajanin **davranisini** degistirir |
| **Beceri** (`SKILL.md`) | Cok adimli karar agaci, cikis kodlari | Ajanin **yontemini** ogretir |

Sadece araci kurmak **yetmez**. Ajan editor aracini kullanmayi bilmiyor, o yuzden
her degisiklik icin yine onay ister. Kural olmadan hicbir fark yaratmaz.

### Kural mi, beceri mi?

Antigravity bu ikisini farkli yerlerden ve farkli yollardan yukler:

| | Kural | Beceri |
|---|---|---|
| Ne icin | Kisitlar, degismezler ("asla sunu yapma") | Cok adimli is akislari |
| Yukleme | Diskten, `~/.gemini/` | Backend servisinden |
| Her zaman aktif | `trigger: always_on` | Model kararina bagli |
| Guvenilirlik | **Yuksek** -- dosya senin makinende | Dusuk -- sunucu tarafinda |

Senin durumun icin **kural sart**, beceri ise ustune konan bir katman. Ikisini de
kurariz.

Kurulum betigi dort yere birden yazar:

```
~/.gemini/tools/agent_edit.py                        <- arac
~/.gemini/config/rules/agent-edit-safe.md            <- global kural (always_on)
~/.gemini/config/skills/agent-edit-safe/             <- Antigravity 2.0 becerisi
~/.claude/skills/agent-edit-safe/                    <- Claude Code / eski Antigravity uyumu
```

Ayrica `~/.gemini/GEMINI.md` dosyasina bir yonlendirme ekler ve istersen proje
klasorune de kural kurar (bkz. `-ProjectRoot`).

### Neden bu kadar cok yere kuruyoruz?

Cunku ajanlarin kurulum yolu farkli:

- **Antigravity IDE (eski surum)** -- `~/.gemini/GEMINI.md` ve `.claude/skills/`
- **Antigravity 2.0** -- `~/.gemini/config/rules/` ve `~/.gemini/config/skills/`
- **Claude Code** -- `~/.claude/skills/`
- **Gemini CLI** -- `~/.gemini/GEMINI.md`

Hepsini kurmak en guvenlisi. Tek satir, birkac yuz bayt. Sorun cikarsa silersin.

---

## Kurulum

### Windows (PowerShell)

Asagidaki tek satiri PowerShell'e yapistirip Enter'a bas:

```powershell
irm https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.ps1 | iex
```

Bu komut betigi indirip calistirir. Tarayicida acmadan dogrudan calisir.

> **Windows uyarisi:** Betigi indirip dosyadan calistirmaya calisirsan PowerShell
> *"not digitally signed"* hatasi verebilir. Bu Windows'un guvenlik ayari.
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File .\install.ps1
> ```
>
> Kalici cozum (sadece bu klasor icin):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> `irm | iex` yontemi bu sorunu yasamaz. **Yeniysen `irm | iex` ile basla.**

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/lepotane/gemini-bypass-permission/main/install.sh | bash
```

### Manuel kurulum (istege bagli)

Betik dosyayi iki yere kopyalar. Bunları elle de yapabilirsin:

```
~/.gemini/
├── tools/
│   └── agent_edit.py            <- ana arac
├── backups/                     <- yedekler (otomatik olusur)
└── config/
    ├── rules/
    │   └── agent-edit-safe.md   <- global kural
    └── skills/
        └── agent-edit-safe/     <- ajanin okudugu beceri
            ├── SKILL.md
            └── scripts/agent_edit.py
```

Windows'da `~` yerine `%USERPROFILE%` yaz.

### Python gereksinimi

Python **3.8 veya ustu** gerekiyor. Windows'ta kurarken mutlaka
**"Add python.exe to PATH"** kutusunu isaretle.

Kontrolu:

```powershell
python --version
```

`Python was not found` diyorsa [python.org](https://www.python.org/downloads/) adresinden
indirip kur, sonra PowerShell'i kapatip yeniden ac.

---

## Kurulum ne yapar?

1. Python 3.8+ var mi kontrol eder (yoksa durur, nehir yonlendirmesi gosterir)
2. Araci `~/.gemini/tools/agent_edit.py` konumuna kopyalar
3. Kurali `~/.gemini/config/rules/agent-edit-safe.md` konumuna kurar
4. Beceriyi iki konuma kurar
5. `GEMINI.md` dosyasina yonlendirme ekler
6. Araci calistirip gercek bir duzenleme testi yapar

Kurulumdan sonra **ajanini yeniden baslat**. Kural ve beceriler konusma
baslangicinda okunur, acik bir oturumda guncellenmez.

---

## Kullanim

### Ajan ile kullanmak (onerilen)

Kurulumdan sonra bir sey yapmana gerek yok. Ajan bu beceriyi kendi bulur ve
kendisi uygular. Sen sadece isini tarif et.

> "mapeditorview.cpp icindeki eski menu kodunu yeni menu sistemiyle degistir"

Ajan artik her degisiklikte senin onayini beklemez.

### Elle kullanmak

```powershell
# Basit degisiklik
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --find "eski" --replace "yeni"

# Tum eslesmeleri degistir
python ~/.gemini/tools/agent_edit.py --path src/main.cpp --find "eski" --replace "yeni" --all

# Tum secenekler
python ~/.gemini/tools/agent_edit.py --help
```

---

## Nasil calisir?

Her duzenlemede dort adim:

```
1. YEDEK AL    ->  ~/.gemini/backups/<proje>/<zaman-damgasi>/
2. ATOMIK YAZ ->  gecici dosyaya yaz, sonra tasi
3. DOGRULA    ->  parantez dengesi, .py/.json syntax kontrolu
4. GERI AL    ->  dogrulama basarisizsa eski hale otomatik doner
```

### Cikis kodlari

| Kod | Anlami | Ne yapmalisin |
|---|---|---|
| `0` | Basarili, dosya degisti | Devam et |
| `1` | Dogrulama basarisiz, **geri alindi** | Hatayi oku, duzelt, tekrar dene |
| `2` | Arguman hatasi / eslesme yok | Hicbir sey degismedi, komutu duzelt |
| `3` | Yedekleme/yazma hatasi | **Dur ve kullaniciya bildir** |

### Geri alma

Her basarili islem bir yedek kimligi yazdirir:

```
Edited: src/main.cpp (backup: 20260101_143012_001)
```

Listele ve geri al:

```powershell
python ~/.gemini/tools/agent_edit.py --rollback-list
python ~/.gemini/tools/agent_edit.py --rollback 20260101_143012_001
```

Dogrulama hatasinda geri alma **otomatik** olur.

---

## Windows'ta tirnak sorunu

C++ kodu tirnak, ters bolu ve satir sonu icerir. Bunlari komut satirindan gecirmek
kodu bozar. Iki guvenli yol var.

### 1. Patch dosyasi (onerilen)

Once bir JSON dosyasi yaz, sonra yolunu ver:

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

### 2. STDIN (tum dosyayi yeniden yazmak)

```powershell
cmd /c "type C:\tmp\new.cpp | python ~/.gemini/tools/agent_edit.py --path src/main.cpp --stdin"
```

**`cmd /c type` kullan, PowerShell `Get-Content` degil.** `Get-Content` pipeline'da
kodlamayi bozar.

---

## Kodlama ve satir sonlari

Arac otomatik olarak korur:

- UTF-8 BOM var mi yok mu
- CRLF mi LF mi
- UTF-8 degilse `cp1254` (Turkce Windows)

Test edildi: 56 baytlik Turkce karakterli bir dosyada sadece hedeflenen karakter
degisti, diger 55 bayt birebir ayni kaldi.

---

## Sik sorulan sorular

**Ajanim hala onay istiyor?**
Once ajani **yeniden baslat**. Sonra sorun giderme belgesindeki kontrol listesini
izle: [docs/SORUN_GIDERME.md](docs/SORUN_GIDERME.md)

**Yedekler birikir mi?**
Her duzenlemede bir klasor olusur. Temizlemek icin:

```powershell
python ~/.gemini/tools/agent_edit.py --prune 100
```

**Kaldirmak istiyorum.**
Kurulum betigini silmen yeterli. Elle kurduysan `~/.gemini/tools/agent_edit.py` ve
`~/.gemini/config/` altindaki `rules/` ve `skills/` klasorlerini sil.

**Baska ajanlarla calisir mi?**
Evet. Arac sadece bir Python betigi. `SKILL.md` dosyasi Antigravity, Claude Code ve
Gemini CLI tarafindan okunur. Diger ajanlarda `GEMINI.md` veya `AGENTS.md` icindeki
kurallari kullanabilirsin.

---

## Proje yapisi

```
gemini-bypass-permission/
├── README.md                    <- bu dosya (Turkce)
├── README.en.md                 <- Ingilizce
├── CHANGELOG.md
├── LICENSE                      <- MIT
├── install.ps1                  <- Windows kurulum
├── install.sh                   <- Linux/macOS kurulum
├── scripts/
│   └── agent_edit.py            <- ana arac
├── rules/
│   └── agent-edit-safe.md       <- global kural (trigger: always_on)
├── skills/
│   └── agent-edit-safe/
│       ├── SKILL.md             <- ajan becerisi
│       └── scripts/agent_edit.py
├── examples/
│   ├── README.md                <- patch dosyasi formati
│   ├── demo.cpp                 <- ornek dosya
│   └── patch.example.json       <- demo.cpp ile calisan ornek patch
└── docs/
    ├── KULLANIM.md              <- tum secenekler (TR)
    ├── USAGE.md                 <- tum secenekler (EN)
    ├── GELISTIRME.md            <- araci genisletme
    ├── SORUN_GIDERME.md         <- hata cozumleri
    └── GEMINI_RULES.md          <- elle kurulum icin kural metni
```

### Kurulum secenekleri

```powershell
.\install.ps1 -Prefix C:\tools\gemini     # farkli klasore kur
.\install.ps1 -ProjectRoot C:\src\proj     # projeye de kural ekle
.\install.ps1 -NoSkill                     # sadece arac + kural
.\install.ps1 -NoRule                      # sadece arac + beceri
.\install.ps1 -NoGeminiMd                  # GEMINI.md'ye dokunma
```

---

## Katki

Begendiysen katkida bulun. Ozellikle:
- Yeni dogrulama tipleri (Rust, Go, C# icin)
- Yeni dosya formatlari
- Gelişmis geri alma stratejileri

## Lisans

MIT. Istedigin gibi kullan, degistir, dagit.