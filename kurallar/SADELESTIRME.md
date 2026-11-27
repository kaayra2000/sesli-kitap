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
   - Paragraflar aktarımla birebir eşleşir: aynı sayıda paragraf, aynı `[s. N]` imleri, aynı dipnot numaraları.
   - Şiirlerin altına eklenen italik anlam paragrafları bu sayıma girmez.
3. **Âyet ve hadîs:**
   - Arapça aslı aktarımdaki gibi, tam harekeli kalır.
   - Meali günümüz Türkçesiyle, ibarenin hemen ardından metin içinde “…” olarak verilir. Dinleyici meali duyar.
   - Dipnotta yalnız kaynak kalır (sûre:âyet, hadîs kaynağı). Kaynak yoksa "Kaynak gösterilmemiş." yazılır.
   - Bir dipnotta Arap harfi ile “…” birlikte bulunmaz. `metin/hazirla.py` dipnottaki meali de okur, meal iki kez okunmuş olur.
   - Yaygın bir meale dayanılmaz, aktarımdaki meal sadeleştirilir.
4. **Tasavvuf terimleri:**
   - Karşılığı tek kelimeyle verilemeyen terimler korunur: nefs, kalp, ruh, sır, zikir, fikir, marifet, fena, beka, seyrüsülûk, mürşit, mürit, tevekkül, teslim, rıza, tecelli, vahdet. Yazımda TDK esas alınır (2.3).
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
   - Düzeltme işareti TDK'nin kullandığı yerlerde kullanılır:
     - anlam ayıran yerlerde (âlem/alem, hâl/hal),
     - k, g, l'den sonraki inceltmede (kâmil, mekân, lâzım),
     - nispet î'sinde (ebedî, ilahî, zatî).
   - Özel adlar ve sure adları TDV İslâm Ansiklopedisi'ndeki (DİA) biçimiyle, ayın ve hemze işaretleri kaldırılarak yazılır: Araf, Enam, Muhyiddin İbnü'l-Arabî.
   - Ayın ve hemze işaretleri (‘ ’) kaldırılır. Kesme işareti olarak düz `'` değil `’` kullanılır.
4. **Eski ekler:** "etdim, içün, olub" gibi eski ek ve yazımlar günümüz biçimine çevrilir: "ettim, için, olup".
5. **Hitap ve kalıp sözler:** "Ey azîz!", "Ma‘lûm ola ki" gibi kalıplar günümüz karşılığıyla korunur ("Ey aziz dost!", "Bilinsin ki"). Üslubun sıcaklığı silinmez.
6. **Tarih ve ölçüler:** Hicrî tarihin yanına ayraç içinde Milâdî karşılığı eklenir. Eski ölçüler (zirâ, fersah, dirhem) korunur, ilk geçtiği yerde yaklaşık karşılığı verilir.

## 3. Sadeleştirenin ekleri

- Açıklama gerektiren her ek, yazarın sözünden ayrılır: kısa açıklamalar `(…)` içinde, uzun olanlar `[Sadeleştiren notu]` dipnotunda.
- Metinde `[?]` bırakılmaz. Aktarımdaki tahmini okuma esas alınır, sadeleştirme cümlenin akışına göre yapılır (bkz. AKTARIM.md, Temel ilke).

## 4. Seslendirme

İki metin de seslendirilebilir. Hangisinin seslendirileceği kitap bazında `kitap.json`'da belirtilir (`"seslendirme": "aktarim" | "sadelestirilmis"`). Sadeleştirilmiş metinde okunuş katmanının işi azalır, ama özel adlar ve terimler için `metin/okunus.tsv` yine geçerlidir.

## 5. Kendi kendini iyileştirme

Her bölüm şu döngüyle işlenir:

1. **Aktar:** Taramadan aktarım yapılır ve bölüm raporuna tahmini okumalar listesi yazılır.
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
| 2026-11-26 | Mârifetnâme 01 | Her manzum bloğun (Türkçe, Farsça, Arapça) altına tek bir italik anlam paragrafı yazılır. Sayfa imiyle bölünen manzumede her parçanın anlamı kendi sayfasında verilir. Anlam paragrafları paragraf eşleşmesine sayılmaz. |
| 2026-11-26 | Mârifetnâme 01 | Meal, metin içinde «…» ibaresinin ardından verilir. Dipnotta yalnız kaynak kalır, numara korunur. |
| 2026-11-26 | Mârifetnâme 01 | Yazarın Türkçe hadîs tercümeleri “…” içinde doğrudan söz olur: "buyurmuşdur ki …" → "buyurmuştur: “…”". |
| 2026-11-26 | Mârifetnâme 01 | Kalıp sözlerin karşılıkları:<br>• "Ey ‘azîz" → "Ey aziz dost!"<br>• "Ma‘lûm olsun ki" → "Bilinsin ki"<br>• (Beyt), (Kıt‘a), (Mesnevî), (Nazm) → (Beyit), (Kıta), (Mesnevi), (Nazım)<br>• Başlık altı tanıtımlar → "Bu bâb/fasıl/tür … bildirir." |
| 2026-11-26 | Mârifetnâme 01 | Aktarımda [?] olan kelime aynen bırakılır. Raporda önerilen okuma varsa o yazılır ve ardına [?] konur. |
| 2026-11-26 | Mârifetnâme 01 | Sahabe ve sonraki kişilere ilk geçtiği yerde ölüm tarihi verilir: (ö. hicrî/milâdî). Peygamberlere ve meleklere tarih verilmez. |
| 2026-11-26 | Mârifetnâme 01 | Baskıdaki ✱ ayraçları korunur. |
| 2026-11-26 | Mârifetnâme 01 | Bir terime her yerde aynı karşılık verilir, sözlük (`sozluk.tsv`) bağlayıcıdır. Örnekler:<br>• "millet" fırka anlamında "fırka" olur.<br>• "hevâ" "nefsin arzusu" olur.<br>• "rükün" namazın içindeki farzlar, "şart" namazın dışındaki farzlar için kullanılır. |
| 2026-11-26 | Mârifetnâme 01 | Metinde fıkha aykırı görünen ya da baskı hatası olabilecek yerler değiştirilmez. Raporda not edilir. |
| 2026-11-26 | Mârifetnâme 02 | Dipnottaki Arapça ibarenin karşılığı “…” ile değil ayraçla verilir: «…» (ölmeden önce ölünüz). Okunuşu kesin olmayan Latin harfli okuma italik ve tırnaksız yazılır. |
| 2026-11-26 | Mârifetnâme 02 | Meali dipnotta verilmiş manzume için meal italik anlam paragrafına taşınır. Dipnotta yalnız nispet, kaynak ve baskı notu kalır. Tek mısralık bloğa da anlam paragrafı yazılır. Etiket (Mısra‘) → (Mısra). |
| 2026-11-26 | Mârifetnâme 02 | Sayfa imini aşan doğrudan söz tırnağa alınmaz, dolaylı anlatılır. Tırnak iki blok arasında açık kalmaz. |
| 2026-11-26 | Mârifetnâme 02 | fena, beka, huzur gibi kelimeler gündelik anlamda geçtiğinde çevrilir. Terim açıklaması yalnız tasavvufî anlamda geçtiği ilk yerde verilir. "hevâ" "hava" anlamındaysa terim sayılmaz. |
| 2026-11-26 | Mârifetnâme 02 | Eski para ve ölçüler (dirhem, dinar) korunur, ilk geçtiği yerde ayraç içinde açıklanır. |
| 2026-11-26 | Mârifetnâme 02 | Kişi ve yer adlarında metindeki biçim DİA'dan farklıysa DİA biçimi kullanılır: Gazâlî → Gazzâlî, Erzurûm → Erzurum. |
| 2026-11-26 | Mârifetnâme 02 | Aktaranın notundaki maddi hata sadeleştirmede düzeltilir, raporda belirtilir. Aktarım dosyası da aynı turda düzeltilir. |
| 2026-11-27 | Mârifetnâme 03 | Baskıda ayraç içindeki Arapça ibare sadeleştirmede ayraçsız yazılır: `«…»[^n] “meal”`. Aktarımda baskıdaki ayraç korunur. |
| 2026-11-27 | Mârifetnâme 03 | Sayfa imi bir Arapça ibarenin içine düşerse ibare aktarımdaki yerden bölünür. Meal ibarenin bittiği sayfada verilir. |
| 2026-11-27 | Mârifetnâme 03 | Esmâ-i hüsnâ (Vehhâb, Samed, Kahhâr …) korunur, ilk geçtiği yerde ayraç içinde anlamı verilir. TDK sözlüğünde olan TDK yazımıyla (Rahman, Cebbar), olmayan DİA biçimiyle (Deyyân) yazılır. |
| 2026-11-27 | Mârifetnâme 03 | Aktaranın mealinde [?] ile boş bırakılmış kelime, anlam paragrafında Latin harfli okunuşuyla ve [?] ile yazılır: serâyâ [?]. |
| 2026-11-27 | Mârifetnâme 03 | Arap harfi bulunan dipnotta anılan Türkçe kelime tırnakla değil italikle yazılır (*mümin*). |
| 2026-11-27 | Mârifetnâme 03 | "Hevâ" nefse değil başka bir şeye bağlıysa terim sayılmaz: "aşkın hevâsı" → "aşkın arzusu". |
| 2026-11-27 | Mârifetnâme 04 | Bağlamın açıkça gösterdiği dizgi hatası (ör. "zâhir" yerine "tâhir", "olmışdır" yerine "olmamışdır", nev‘ yerine yanlışlıkla "Fasl" başlığı) sadeleştirmede düzeltilmiş anlamıyla yazılır ve `[Sadeleştiren notu]` dipnotunda belirtilir. Aktarımda baskıdaki biçim kalır. Fıkhî ya da içerikle ilgili şüpheli yerler bu kurala girmez, değiştirilmez. |
| 2026-11-27 | — | Kullanıcı kararı: `[?]` metinde kalmaz. Okunamayan yer bağlama en uygun okumayla doldurulur, raporun "Tahmini okumalar" listesine yazılır. Önceki "[?] aynen bırakılır" kararlarının yerine geçer. Seste `[?]` soru tonlamasına yol açıyordu. |
| 2026-11-27 | Mârifetnâme 04 | Dizgi hatası için aktarımda zaten bir dipnot varsa sadeleştirmede yeni numara açılmaz, o dipnot `[Sadeleştiren notu]` olarak yeniden yazılır. |
| 2026-11-27 | Mârifetnâme 04 | Sözlükte açıklanmış terim, tür başlığının altındaki tanıtım cümlesinde yeniden açıklanmaz. Ad listeleri (ör. izafî ruhun adları) Türkçe karşılıklarıyla verilir. |
| 2026-11-27 | Mârifetnâme 04 | Dirhem ağırlık olarak geçtiğinde ilk yerde gram karşılığı verilir (1 dirhem ≈ 3,2 g). |
| 2026-11-27 | Mârifetnâme 05 | Dipnotu olmayan kısa Arapça sözün meali ibarenin hemen ardına “…” içinde yazılır. |
| 2026-11-27 | Mârifetnâme 05 | "✱ Rubâ‘iyyât ✱" → "✱ Rubailer ✱", "(Rubâ‘î)" → "(Rubai)". |
| 2026-11-27 | Mârifetnâme 05 | Baskıda öznesi düşmüş cümlede özne ayraç içinde tamamlanır. "Sâlik" ve "muhakkik" terim olarak korunur, "mübtedi" "yola yeni başlayan" diye çevrilir. |
| 2026-11-27 | Mârifetnâme 06 | Tan vakti anlamındaki "seher" korunur. Uyanıklık anlamındaki "sehar" (سهر) "uykusuzluk" ya da "gece uyanık kalmak" diye yazılır. |
| 2026-11-27 | Mârifetnâme 06 | Manzumede öznesi belirsiz redifte özne anlam paragrafında ayraç içinde tamamlanır: "(âşık)". |
| 2026-11-27 | Mârifetnâme 06 | Cinaslı sözde iki anlam da duyulacak biçimde verilir, gerekirse asıl kelime ayraçta kalır: "yok (lâ) … ancak Allah (illallah)". |
| 2026-11-27 | Mârifetnâme 07 | Dizgi hatasının olduğu cümlede dipnot yoksa yeni numara açılmaz. Not, aynı ya da bir önceki cümlenin dipnotunun sonuna `[Sadeleştiren notu]` olarak eklenir ve yeri belirtilir. |
| 2026-11-27 | Mârifetnâme 07 | Aynı terim başka bir ilimde başka anlamdaysa sözlüğe ayrı satır açılır: fıkıhta "ilm-i hâl", tasavvufta "hâl ilmi". |
| 2026-11-27 | Mârifetnâme 07 | Sayfa imini aşan söz tırnaksız, iki noktadan sonra düz verilebilir. Hadis dizilerinde "Yine buyurmuştur ki …" kalıbı kullanılır. Cinas kuralı ses benzerliğine dayanan ikililere de uygulanır (cirm/cürm). |
| 2026-11-27 | Mârifetnâme 08 | Metinde kişi adlarında "b." kısaltması yerine "bin" yazılır (seslendirmede nokta cümleyi böler). Dipnotlarda "b." kalabilir. |
| 2026-11-27 | Mârifetnâme 08 | Sözlükte tasavvufî karşılığı olan kelime gündelik anlamda geçerse çevrilir: "vahdet ve kesret" → "yalnızlık ve kalabalık". |
| 2026-11-27 | Mârifetnâme 08 | Yalnız vezin, redif ya da bağlamın tek okumaya zorladığı yer dizgi hatası sayılıp düzeltilir. "… kastedilmiş olabilir" türü okumalar içerik şüphesidir, değiştirilmez. |
| 2026-11-27 | Mârifetnâme 09 | Zikir cümlesi olarak geçen kısa Arapça (lâ ilâhe illallah, Allah, Hû) metinde Latin harfle yazılır, ilk geçişte anlamı ayraç içinde verilir. |
| 2026-11-27 | Mârifetnâme 09 | "Zikir, zâkir ve Mezkûr" → "zikir, zikreden ve Zikredilen"; Allah kastedildiğinde büyük harf. |
| 2026-11-27 | Mârifetnâme 09 | Aktarımdaki zayıf okuma dinleyiciye anlamsız geliyorsa ve bağlam bir okumayı açıkça istiyorsa sadeleştirmede o okuma yazılır, dipnotta belirtilir (ör. "evvel ve elyeddir" → "ilk ve ebedîdir"). Kullanıcı kararı: metin akışa göre doldurulur. |
