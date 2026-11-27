# Aktarım kuralları (sadeleştirilmemiş metin)

Bu dosya, Arap harfli Osmanlı Türkçesi bir baskının Latin harflerine **aslına sadık** aktarımını tanımlar. Kurallar `bedri_gencer` reposundaki `AGENTS.md`'den alındı. Bu repoda da kitap üretimi için standart kabul edilir.

Aktarımın amacı, metni değiştirmeden okunabilir kılmaktır. Kelime, cümle yapısı ve imlâ aslındaki gibi kalır, yalnızca alfabe değişir. Günümüz Türkçesine çeviri ayrı bir iştir: [`SADELESTIRME.md`](SADELESTIRME.md).

## Temel ilke

- Metin özetlenmez, sadeleştirilmez, günümüz Türkçesine çevrilmez. Kelimesi kelimesine aktarılır.
- Paragraf yapısı, başlıklar ve dipnotlar korunur.
- Sayfa başları `[s. N]` ile işaretlenir. N, matbu sayfa numarasıdır. PDF sayfasından farklıysa raporda belirtilir.
- Okunuşu kesin olmayan yer boş bırakılmaz: görüntü yeniden incelenir, cümlenin akışına ve bağlama en uygun okuma yazılır. Metinde `[?]` bırakılmaz. Tahmini okuma, baskıdaki yazılışı ve varsa öbür ihtimallerle birlikte bölüm raporundaki **Tahmini okumalar** listesine sayfa numarasıyla eklenir (2026-11-27, kullanıcı kararı).
- Kaynağı bulunamayan âyet dışı söz için dipnota "Kaynağı tespit edilemedi." yazılır.
- Aktaranın her eki (açıklama, kaynak, tamamlanan harf) `[Aktaran notu]` dipnotu ya da `[köşeli ayraç]` ile ayrılır. Yazarın sözüyle karışmaz.
- Kenar notları, okuyucu el yazıları, mühür ve damgalar aktarılmaz, raporda anılır.

## Transliterasyon ve imlâ

- **Uzun ünlüler:** düzeltme işaretiyle yazılır: `â`, `î`, `û` (ör. `Kulûb`, `Ezmân`, `Hanîfe`).
- **Ayın ve hemze:** Ayın `‘` (U+2018) ile yazılır. Hemze ve harf-i tarif birleşimi `’` (U+2019) ile yazılır: `‘Akâid`, `Bâ‘is`, `Fevâkihü’l-Kulûb`.
- **Harf-i tarif:**
  - Önceki kelimeye i‘râb ünlüsüyle bağlanır, kesme ve kısa tireyle yazılır: `Usûlü’l-Fıkh`.
  - Şemsî harflerde idgam gösterilir (`’n-`, `’s-`, `’t-`, `’r-` …).
  - Başta gelen harf-i tarif küçük yazılır: `el-Fevâyih`.
- **Farsça izafet:** `-i` / `-ı` ile, kısa tireyle yazılır ve büyük ünlü uyumuna uyar: `Feverân-ı Ezmân`, `Mekteb-i Tıbbiyye`.
- **Arapça kelimeler:** aslına göre yazılır: `Ebû Hanîfe`, cer hâlinde `li-Ebî Hanîfe`.
- **Ünlüler:** Kalın ve ince ünlü ayrımına dikkat edilir: `hıfz`, `sıhhat`.
- **Eski Türkçe ekler:** metinde nasıl yazılmışsa öyle kalır: `etdim`, `içün`, `olub`. Okunuşa çevirmek seslendirme betiğinin işidir (`metin/okunus.py`).

## Düzeltme adımı (II. adım)

Bu düzeltmeler aktarımdan sonra yapılır:

1. **Yazım ve OCR hataları** düzeltilir: `delvet` → `devlet`.
2. **Büyük harf:** Dil, din ve millet adları büyük harfle yazılır: `İslâm`, `Müslüman`, `Arap`.
3. **Kesme:** Özel isimlere gelen ekler kesmeyle (`’`) ayrılır: `İstanbul’un`.
4. **İtalik:** Kitap ve dergi adları, yabancı kavramlar italik yazılır.
5. **Kitap adları:**
   - Harf-i tarif, harf-i cer, bağlaç ve edatlar küçük yazılır.
   - Asıl kelimelerin ilk harfi büyük yazılır.
   - i‘râba uygun yazılır: `el-Fevâyihü’l-Münîfe fî Tercemeti’n-Nesâyih`.
6. **Yabancı kitap adları:** aslıyla yazılır, Türkçesi ayraç içinde verilir.
7. **Türkçe telaffuzla yazılmış yabancı adlar:** aslıyla yazılır, ilk geçtiği yerde doğum–ölüm yılları verilir. Kesin değilse `[?]` konur.
8. **Yabancı terimler:** dipnotta açıklanır.
9. **Âyet, hadîs ve Arapça/Farsça sözler:**
   - Asıl harfleriyle, **tam harekeli** ve «…» içinde yazılır.
   - Türkçe meali hemen altında “…” içinde ya da `[Aktaran notu]` dipnotunda verilir.
   - Âyetin sûre ve âyet numarası, hadîsin kaynağı dipnotta gösterilir.

## Seslendirme ile ilişkisi

Seslendirme bu metinden yapılır. `metin/hazirla.py` sayfa imlerini, dipnot tanımlarını ve fihristi okumaz. Arap harfli ibarenin yerine meali okunur. Eski imlâ okunuşa `metin/okunus.py` ve `metin/okunus.tsv` ile çevrilir. Aktarımda okunuş için değişiklik yapılmaz. Okunuş sorunu okunuş katmanında çözülür.
