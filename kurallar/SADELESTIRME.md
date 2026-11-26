# Sadeleştirme kuralları

Sadeleştirilmiş metin, aktarılmış metnin ([`AKTARIM.md`](AKTARIM.md)) **anlamını eksiksiz koruyarak** günümüz Türkçesiyle yeniden yazılmasıdır. Okur, aslındaki her fikri, sırasını ve ağırlığını bu metinde bulmalıdır. Değişen, söyleyiş biçimidir.

Sadeleştirme, aktarım bittikten sonra aynı bölüm için yapılır. Her zaman aktarımdan yola çıkılır, taramadan doğrudan sadeleştirilmez. İki metin paragraf paragraf karşılaştırılabilir kalır.

Bu dosya yaşayan bir standarttır. Her bölümden sonra yeni karşılaşılan durumlar karara bağlanır ve en alttaki **Karar günlüğü**ne eklenir (bkz. "Kendi kendini iyileştirme").

## 1. Değişmeyenler

1. **Anlam:**
   - Hiçbir fikir atılmaz, özetlenmez, yumuşatılmaz.
   - Yazarın görüşüne ekleme ya da yorum yapılmaz.
   - Bugün tuhaf gelen bilgiler (eski kozmoloji, tıp, astronomi) olduğu gibi aktarılır. Düzeltilmez, "yanlıştır" denmez.
2. **Sıra ve yapı:**
   - Bölüm, başlık ve paragraf sırası korunur.
   - Paragraflar aktarımla birebir eşleşir: aynı sayıda paragraf, aynı `[s. N]` imleri.
3. **Âyet ve hadîs:**
   - Arapça aslı aktarımdaki gibi, tam harekeli kalır.
   - Meali günümüz Türkçesiyle verilir. Yaygın bir meale dayanılmaz, aktarımdaki meal sadeleştirilir.
4. **Tasavvuf terimleri:**
   - Karşılığı tek kelimeyle verilemeyen terimler korunur: nefs, kalp, ruh, sır, zikir, fikir, marifet, fenâ, bekâ, seyr ü sülûk, mürşid, mürid, tevekkül, teslim, rızâ, tecellî, vahdet.
   - İlk geçtiği yerde ayraç içinde kısaca açıklanır. Ör. "fenâ (kulun kendi varlığını Hak'ta yok bilmesi)".
   - Açıklama kitabın sözlüğüne (`sozluk.tsv`) de yazılır. Sonraki geçişlerde tekrarlanmaz.
5. **Şiir:**
   - Manzumeler önce aktarımdaki hâliyle verilir, ölçü ve kafiye bozulmaz.
   - Altına italikle, düz yazı olarak sadeleştirilmiş anlamı yazılır.
6. **Özel adlar:** Kişi ve eser adları bilinen hâliyle yazılır. Ör. Muhyiddin İbnü'l-Arabî, İmâm-ı Rabbânî, *Fusûsu'l-Hikem*. İlk geçtiği yerde yaşadığı dönem verilir.

## 2. Değişenler

1. **Cümle yapısı:**
   - Uzun, iç içe Osmanlıca cümleler anlam birimlerine göre bölünür.
   - Yüklem sona alınır.
   - Bir cümlede tek ana fikir olması hedeflenir, ama düşünce zinciri kopartılmaz.
2. **Kelime seçimi:**
   - Günlük kullanımda karşılığı olan Arapça-Farsça kelime ve tamlamalar Türkçeleştirilir: "mezkûr" → "anılan", "ahvâl-i nâs" → "insanların hâlleri", "ber-vech-i âtî" → "aşağıdaki gibi".
   - Karşılık seçerken anlam kayması olmamalıdır. Tek kelime yetmiyorsa iki-üç kelimelik açıklama tercih edilir.
   - Bugün de yaşayan kelimeler ("sabır", "şükür", "hikmet", "ilim") olduğu gibi kalır. Gereksiz Öztürkçecilik yapılmaz.
3. **İmlâ:**
   - TDK'nın güncel yazım kurallarına uyulur.
   - Düzeltme işareti yalnız anlam ayırt ettiği yerde (kâr/kar, âlem/alem) ve özel adlarda kullanılır.
   - Ayın ve hemze işaretleri (‘ ’) kaldırılır.
4. **Eski ekler:** "etdim, içün, olub" gibi eski ek ve yazımlar günümüz biçimine çevrilir: "ettim, için, olup".
5. **Hitap ve kalıp sözler:** "Ey azîz!", "Ma‘lûm ola ki" gibi kalıplar günümüz karşılığıyla korunur ("Ey aziz dost!", "Bilinsin ki"). Üslubun sıcaklığı silinmez.
6. **Tarih ve ölçüler:** Hicrî tarihin yanına ayraç içinde Milâdî karşılığı eklenir. Eski ölçüler (zirâ, fersah, dirhem) korunur, ilk geçtiği yerde yaklaşık karşılığı verilir.

## 3. Sadeleştirenin ekleri

- Açıklama gerektiren her ek, yazarın sözünden ayrılır: kısa açıklamalar `(…)` içinde, uzun olanlar `[Sadeleştiren notu]` dipnotunda.
- Aktarımda `[?]` olan yer, sadeleştirmede de `[?]` olarak kalır. Tahminle doldurulmaz.

## 4. Seslendirme

İki metin de seslendirilebilir. Hangisinin seslendirileceği kitap bazında `kitap.json`'da belirtilir (`"seslendirme": "aktarim" | "sadelestirilmis"`). Sadeleştirilmiş metinde okunuş katmanının işi azalır, ama özel adlar ve terimler için `metin/okunus.tsv` yine geçerlidir.

## 5. Kendi kendini iyileştirme

Her bölüm şu döngüyle işlenir:

1. **Aktar:** Taramadan aktarım yapılır ve bölüm raporuna `[?]` listesi yazılır.
2. **Sadeleştir:** Aktarımdan sadeleştirilmiş metin üretilir. Yeni terimler `sozluk.tsv`'ye eklenir.
3. **Gözden geçir:** İki metin paragraf paragraf karşılaştırılır:
   - Atlanan ya da eklenen fikir var mı?
   - Anlam kayması var mı?
   - Aynı terime farklı karşılık verilmiş mi? (`sozluk.tsv` ile kontrol)
   - Cümleler gereğinden uzun mu, yüklem sonda mı?
4. **Karara bağla:** Gözden geçirmede çıkan genel bir sorun (ör. "‘hâl’ kelimesi bazen durum, bazen tasavvufî hâl anlamında") **Karar günlüğü**ne yazılır. Önceki bölümler bu karara göre düzeltilir.
5. **Seslendir:** Seçili metin seslendirilir. `degerlendir.py` raporundaki okunuş hataları `okunus.tsv`'ye geri beslenir.

## Karar günlüğü

| Tarih | Kitap / bölüm | Karar |
|---|---|---|
| 2026-11-26 | — | Standart ilk sürüm. |
