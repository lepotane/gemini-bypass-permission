# Patch dosyası formatı

Bu dosya `examples/patch.example.json` içindeki düzenlemelerin ne yaptığını açıklar.
Bu örnek, aynı klasördeki `demo.cpp` dosyasına uygulanmak üzere yazıldı.

## Format

Patch dosyası bir **JSON dizisi** veya **tek bir JSON nesnesi** olmalıdır.
Dizi kullanman önerilir, çünkü birden fazla işlemi sırayla uygular.

```json
[
  {"find": "eski", "replace": "yeni"},
  {"find": "başka", "replace": "başka2"}
]
```

## Alanlar

| Alan | Zorunlu | Açıklama |
|---|---|---|
| `find` | Evet | Aranacak metin veya regex deseni |
| `replace` | Hayır | Yerine yazılacak metin. Yoksa boş string (yani silme) |
| `all` | Hayır | `true` ise tüm eşleşmeleri değiştirir. Varsayılan: sadece ilki |
| `count` | Hayır | `all` yoksa kaç eşleşme değiştirileceği |
| `regex` | Hayır | `true` ise `find` regex olarak yorumlanır |

## Örnekler ve açıklamaları

### 1. Basit renk değişikliği

```json
{"find": "QColor(255, 0, 0)", "replace": "QColor(0, 255, 0)"}
```

Tek bir eşleşmeyi değiştirir.

### 2. C++ çift tırnaklı metin

```json
{"find": "setToolTip(\"hello\")", "replace": "setToolTip(QStringLiteral(\"hello\"))", "all": true}
```

JSON içinde `"` karakteri `\"` şeklinde yazılır. Bu, **kilit konu** — C++ kodunu
komut satırından geçirmek yerine JSON dosyası kullanmak, tırnak kaçışı hatalarını
tamamen ortadan kaldırır.

### 3. İç içe tırnak ve ters bölü

```json
{"find": "\\\"q\\\"", "replace": "q"}
```

C++ kaynakta şöyle görünen metin:

```cpp
QString s = "a \"q\" b";
```

Burada kaynaktaki karakterler şunlar: `\"q\"`. JSON içinde bunu yazmak için
her ters bölü iki kez yazılır: `\\\"q\\\"`.

Kural basit: **kaynakta kaç tane ters bölü varsa JSON'da iki katını yaz.**

### 4. Regex ile toplu temizlik

```json
{"find": "[ \\t]*//[ \\t]*TODO:.*", "replace": "", "regex": true, "all": true}
```

Tüm `TODO:` yorum satırlarını siler. `\\t` JSON'da bir tab karakteridir
(`\t` yazsan hata alırsın çünkü `\t` geçerli bir kaçış dizisi değil).

### 5. Sınırlı sayıda değişiklik

```json
{"find": "TODO", "replace": "DONE", "all": false, "count": 3}
```

İlk 3 eşleşmeyi değiştirir, gerisine dokunmaz.

## Davranış kuralları

**Sıralama:** İşlemler verilen sırayla uygulanır. Yani 2. işlem 1. işlemin
ürettiği metni görebilir. Buna dikkat et, sıralamayı bilinçli seç.

**Hata durumu:** Herhangi bir işlem eşleşmezse araç `2` çıkış koduyla durur ve
**hiçbir değişiklik yapılmaz**. Kısmi uygulama olmaz — ya hepsi ya hiçbiri.

Bu güvenlik özelliğidir: yarım uygulanmış bir patch yarım bozuk dosya demektir.

**`replace` verilmezse:** Boş string ile değiştirilir, yani metin silinir.

## Ne zaman patch dosyası kullan

| Durum | Yöntem |
|---|---|
| Kısa, tırnaksız tek kelime | `--find` / `--replace` yeterli |
| Tırnak veya ters bölü içeren metin | `--patch-file` |
| Çok satırlı kod bloğu | `--stdin` |
| 3'ten fazla düzenleme | `--patch-file` |
| Regex ile toplu değişiklik | `--patch-file` |

## Çok satırlı kod değiştirmek

JSON içinde çok satırlı metin kullanmak kaotiktir. Onun yerine:

1. Yeni içeriği geçici bir dosyaya yaz
2. `--stdin` ile uygula

```powershell
cmd /c "type C:\tmp\new.cpp | python agent_edit.py --path src\main.cpp --stdin"
```

Bu yöntem bayt-kesindir, kodlama ve satır sonları bozulmaz.