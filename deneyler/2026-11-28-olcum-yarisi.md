# Ölçüm araçları ve hakem yarışı (2026-11-28)

Amaç: aday seçiminde kullanılan otomatik ölçümlerin hangisinin kullanıcının kulağıyla uyuştuğunu bulmak.

## Sınav seti

- Mârifetnâme 02 ve 03'ten 40 cümle (`2026-11-28-kulak-testi-puanlari.json`).
  - 15 cümle: yanlış uzatma kuralının şüphelendikleri
  - 10 cümle: UTMOS puanı en düşük olanlar
  - 15 cümle: rastgele
- Kullanıcı her cümleyi körlemesine dinledi: 1–5 doğallık puanı, "yanlış uzatma var" ve "yanlış okuma var" işaretleri.
- Uyum ölçüsü: Spearman sıra uyumu (1 tam uyum, 0 ilişki yok).
- Sınır: tek dinleyici, 40 cümle. Sıralamalar yol gösterir, sayıların kesinliği düşüktür.

## Kullanıcı puanlarından çıkanlar

- Aslıyla okunan Osmanlıca/Farsça şiirler: ortalama 2,82 (11 cümle). Sadeleştirilmiş nesir: 3,66 (29 cümle).
- Kullanıcının 6 "yanlış uzatma" işaretinin hepsi şiirde, nesirde hiç yok.
- Karar: şiirlerin aslı okunmaya devam eder (kullanıcı kararı, `kurallar/SADELESTIRME.md` karar günlüğü).

## Sonuçlar (kullanıcı puanıyla uyum)

| Ölçüm | Uyum | Not |
|---|---|---|
| Whisper doğruluğu + Audiobox PQ | 0,53 | Seçilen birleşim |
| Claude'un spektrogram incelemesi | 0,53 (nesirde 0,40) | Kör değil: Claude kullanıcı puanlarını daha önce görmüştü |
| Whisper doğruluğu | 0,44 | |
| Audiobox Aesthetics PQ | 0,41 | En iyi tek doğallık aracı |
| Audiobox CU | 0,39 | |
| İfade: vurgu sapması | 0,29 | |
| İfade: canlılık | 0,27 | |
| Audiobox CE | 0,25 | |
| İfade: perde aralığı | 0,22 | |
| SQUIM STOI | 0,22 | |
| UTMOS v1 (eski hakem) | 0,16 | 40 klibe 3,36–3,43 arası puan verdi |
| NISQA | 0,04 | |
| Distill-MOS | −0,04 | |
| DNSMOS | −0,07 | |
| UTMOSv2 | −0,09 | |
| SCOREQ | −0,16 | |
| Qwen2.5-Omni 3B (JSON cevap) | — | Her klibe doğallık 1, uzatma 0 verdi; şablonu kopyaladı |
| Qwen2.5-Omni 3B tonlama | −0,27 | |
| Fonem modeli (wav2vec2 XLSR-53 espeak) | −0,23 | Türkçe espeak fonemleriyle taban hatası %35 |
| Türkçe noktalama modeliyle durak | 0,12–0,19 | Whisper kelime zamanları durakları göstermiyor |
| Yanlış uzatma kuralı (CTC süreleri) | — | 15 işaretin 3'ü kullanıcıyla örtüştü; kapatıldı |

## Uygulanan değişiklikler

- Aday seçiminde doğallık hakemi UTMOS yerine Audiobox Aesthetics PQ (`colab/seslendir.py`).
- Yanlış uzatma kuralı kapatıldı (`ayarlar.json` `uzama_sinir: 0`).
- `ñ` seslendirmede `n` okunur (`metin/okunus.py`).

## Spektrogram incelemesinden gözlem

Düşük puanlı cümlelerde (08, 11, 12, 38) perde eğrisi baştan sona ~100 Hz'de düz: tekdüze okuma. Yüksek puanlılarda
(02, 27, 29, 32) perde 120–200 Hz arasında iniş çıkış yapıyor, sayma ve soru tonlaması belirgin. 30'da soru cümlesi
("erdirmeyecek misiniz?") sonda yükselmiyor, düşüyor. Görüntüler `colab/spektrogram.py` ile üretilir.

## Dosyalar

- `2026-11-28-olcum-araclari.csv`: her klip için bütün ölçüm araçlarının puanı
- `2026-11-28-kucuk-hakemler.csv`: fonem ve durak hakemleri
- `2026-11-28-claude-spektrogram-puanlari.json`: Claude'un spektrogramdan verdiği puanlar
- Betikler: `colab/olcum_yarisi.py`, `colab/hakem_deneme.py`, `colab/spektrogram.py`, `video/olcum_karsilastir.py`
