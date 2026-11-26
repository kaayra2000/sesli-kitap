# Kanal tarzı: Sesli Sayfalar

YouTube kanalı: **Sesli Sayfalar** (`@SesliSayfalarTR`). Kanal yalnızca tasavvuf kitapları için değil. Telifsiz, eski ya da yeni her türlü kitabı yapay zekâyla seslendirir. Her yeni kitap aşağıdaki görsel ve metin düzenini izlemelidir. Böylece kanalın tek bir tarzı olur.

İlk örnek: `kitaplar/mektuplar/gorsel/` (kapaklar) ve `video/kanal/` (profil resmi ve banner).

## Renkler

| Ad | RGB | Kullanım |
|---|---|---|
| `ZEMIN` | (14, 38, 40) | Koyu yeşil-lacivert zemin |
| Pano | (9, 26, 28), saydamlık 225 | Yazıların durduğu orta dikdörtgen |
| Kenar karartısı | (5, 16, 18) | Kenarlara doğru koyulaşan hâle |
| `ALTIN` | (201, 164, 92) | Çerçeve, yıldızlar, yazar adı, bölüm sırası |
| `KREM` | (240, 228, 200) | Kitap adı ve bölüm adı |

## Yazı tipleri

Hepsi Noto ailesinden (`/usr/share/fonts/truetype/noto/`):

- Kitap adı: `NotoSerifDisplay-Bold`, büyük harf, harf aralığı geniş.
- Alt başlık: `NotoSerifDisplay-Italic`.
- Bölüm adı: `NotoSerifDisplay-Regular`. Uzun adlar `sigdir()` ile küçültülür.
- Yazar adı, bölüm sırası ("BİRİNCİ BÖLÜM") ve alt satır ("SESLİ KİTAP"): `NotoSerif-Regular`, büyük harf, harf aralığı geniş, altın renkte.

Özgün imlâ korunur: â, î, û, ‘ ve ’ işaretleri başlıklardan atılmaz.

## Kapak düzeni (1920×1080, küçük resim 1280×720)

1. Zemin: döşenmiş sekiz köşeli yıldız deseni, kenarlarda karartı (`desen()`).
2. Ortada koyu bir pano: altın renkli çift çerçeve, köşelerinde küçük yıldızlar.
3. Yukarıdan aşağıya:
   - Yazar adı.
   - Kitap adı.
   - Alt başlık.
   - Ayraç: iki çizgi, ortalarında bir yıldız.
   - Bölüm sırası.
   - Bölüm adı.
   - "SESLİ KİTAP".
4. Tam kitap videosunda bölüm satırlarının yerine "SESLİ KİTABIN TAMAMI" / "Altı Bölüm Bir Arada" gibi bir metin gelir.

Desen kitabın konusuna göre değişebilir. Örneğin Batı kaynaklı bir eserde geometrik yıldız yerine sade bir çerçeve kullanılabilir. Renkler, yazı tipleri ve yerleşim ise aynı kalır.

Görseller fotoğraf, gerçek kişi portresi ya da başka bir eserden alınmış resim içermez. Hepsi kodla üretilir.

## Kanal görselleri

- `video/kanal/profil.png` (800×800): altın çift daire içinde açık kitap.
- `video/kanal/banner.jpg` (2560×1440): sade koyu geçişli zemin, çerçeve içinde "SESLİ SAYFALAR" ve altında "Eski ve yeni kitaplar, sesli olarak".

Bu iki görsel yeni kitaplarda değişmez.

## Başlık ve açıklama

Şablon: `kitaplar/mektuplar/yukleme-bilgileri.md` (`video/aciklama.py` üretir).

- Bölüm başlığı: `<Kitap> <n>. Bölüm: <Bölüm adı> | Sesli Kitap`
- Tam kitap başlığı: `<Kitap> (Tamamı) – <Yazar> | Sesli Kitap`
- Açıklama sırası:
  1. Eser ve bölüm.
  2. Yazar hakkında bir cümle.
  3. ⚠️ Yapay zekâ notu: model adı, gerçek kişinin okuması olmadığı, okunuş hatası olabileceği, altyazının bulunduğu.
  4. Bölüm listesi. Tam kitap videosunda bunun yerine `00:00` ile başlayan zaman damgaları gelir.
  5. Etiket satırı.
- Videonun kendi içinde yapay zekâ notu olmaz. Not yalnızca açıklamada ve YouTube'un "değiştirilmiş içerik: Evet" bildiriminde yer alır.
- Yükleme ayarları:
  - Türkçe altyazı (`.srt`, zamanlamalı).
  - Video dili Türkçe.
  - "Çocuklara özel değil".
  - Ücretli tanıtım: Hayır.
  - Kitabın oynatma listesine eklenir, liste eskiden yeniye sıralanır.

## Video

Durağan kapak ile ses birleştirilir (`video/uret.py`):

- Görüntü: libx264, `-tune stillimage`, 1 fps.
- Ses: AAC 192k, 48 kHz.
- Video ses uzunluğunda kesilir (`-t`).
- Tam kitapta bölümler arasında 3 sn sessizlik bulunur.
