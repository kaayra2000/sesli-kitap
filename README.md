# Sesli Kitap

Telifsiz ve tasavvufî kitapları Türkçe sesli kitap olarak seslendirip YouTube'a yüklemek için araçlar. İlk kitap:
Salâhuddîn b. Sirâcuddîn, *Mektûblar ve Ba‘zı Mesâ’il-i Mühimme* (Osmanlı Türkçesinden Latin harflerine aktarım,
`bedri_gencer` reposu).

Ses yerelde hazırlanan iş paketiyle ücretsiz Google Colab'de (T4 GPU) üretilir. Model: `kaanhgunay/pocket-tts-tr`
(CC BY 4.0, atıf: "pocket-tts-tr, kaanhgunay, CC BY 4.0").

## Akış

```
kitap.md ──hazirla.py──> parçalar (metin + okunuş) ──paketle.py──> is-<konu>.zip
   ──Colab: calistir.sh / seslendir.py──> cikti-<konu>.zip ──degerlendir.py──> rapor + gecmis.tsv
```

| Dosya | İş |
|---|---|
| `metin/okunus.py` | Eski imlâyı okunuşa çevirir: `etdim` → `ettim`, `içün` → `için`, `sebeb` → `sebep`, `ma‘lûm` → `malum`, `fi’l-hakîka` → `filhakika`, sayılar yazıya. Arap harfli ibare okunmaz |
| `metin/okunus.tsv` | Kural dışı kelimeler için sözlük (yazılan, okunacak) |
| `metin/hazirla.py` | Kitap Markdown'unu parçalara böler; sayfa imi, fihrist, dipnot tanımı atlanır; âyet ve hadîsin Türkçe meali okunur |
| `test/test_kumesi_olustur.py` | Test kümesi: kitaptan katmanlı 38 cümle + 12 zor durum (sayı, hemze, ayın, izafet, soru, ünlem, isim) |
| `paketle.py` | Colab iş paketi (`test` ya da `ornek`) |
| `colab/sesli_kitap.ipynb` | Colab defteri: zip'i yükler, `calistir.sh`'ı çalıştırır, çıktıyı indirir |
| `colab/seslendir.py` | Her parça için en çok 6 aday üretir; Whisper large-v3, wav2vec2 CTC ve UTMOS ile ölçer; en iyisini seçer |
| `degerlendir.py` | Başarı ölçütleri, en kötü parçalar, önceki turla fark |

## Öz yinelemeli test

Her tur: `paketle.py test --tur N` → Colab → `degerlendir.py cikti-turNN.zip`. Rapordaki en kötü parçalara bakılır.
Hata okunuş kuralındaysa `okunus.py` ya da `okunus.tsv`, sesteyse `ayarlar.json` (sıcaklık, referans, aday) düzeltilir
ve tur tekrarlanır. Bütün ölçütler geçince kitaptan bir örnek (`paketle.py ornek`) üretilir ve insan dinler.

Ölçütler (`degerlendir.py`): yanlış kelimeli parça yok (Whisper CER > %3), ortalama CER ≤ %1.5, cümle sonunda ses
artığı yok, cümle içinde 0.9 sn'den uzun takılma yok, kırpılma yok, UTMOS ≥ 3.3, hız 11-15.5 harf/sn.

Sınır: ASR hakemleri doğru kelimeyi duyar ama vurgu ve tonlamayı ölçmez; son karar dinleyerek verilir.

## Kitap metni: aktarım ve sadeleştirme

Kitabın metni bu repoda, her kitap için ayrı bir klasörde tutulur:

```
kitaplar/<kitap>/
  kitap.json              # künye, telif dayanağı, kaynak, seslendirilecek sürüm
  kaynak/                 # orijinal baskının taraması (kamu malı)
  aktarim/NN-<bolum>.md   # sadeleştirilmemiş aktarım (kurallar/AKTARIM.md)
  sadelestirilmis/NN-<bolum>.md  # günümüz Türkçesi (kurallar/SADELESTIRME.md)
  sozluk.tsv              # terim -> sadeleştirmedeki karşılığı / açıklaması
  rapor.md                # bölüm bölüm yöntem, [?] listesi, kararlar
  ses/                    # Opus ses + altyazı;  gorsel/  kapaklar
```

Bölüm bölüm ilerlenir: aktar, sadeleştir, gözden geçir, seslendir, yükle. Kitap bitince bölümler tek
parça baskıya hazır metinde birleştirilir ve sesin tamamı yüklenir.

Telif: yazar ve (tercümeyse) çevirmen ölümünden itibaren 70 yılın sonunda kamu malı olur; dayanak
`kitap.json`'da kaynaklı yazılır. Modern hazırlayanın (aktaran/sadeleştiren) baskısı kaynak alınmaz.
