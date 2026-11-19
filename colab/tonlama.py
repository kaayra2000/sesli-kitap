"""
Tonlama (prosodi) ölçümü: perde (F0) eğrisinden ve kelime zamanlarından sayısal özellikler.

ASR hakemleri kelimenin doğru olup olmadığını söyler, tonlamayı ölçmez. Bu modül şunları ölçer:
  perde_std   cümle içi perde oynaklığı (yarım ton std). Çok düşük = tekdüze, çok yüksek = abartılı.
  son_egim    son 0.45 sn'deki perde eğimi (yarım ton/sn). Düz cümle sonunda düşmeli, soru (?) sonunda yükselmeli.
  alcalma     cümle başı ile sonu arasındaki perde farkı (yarım ton); doğal okumada cümle boyunca perde iner.
  virgul_ara  virgüldeki ortalama duraklama (sn); okuyucu virgülde nefes alır.
  hiz_cv      kelime sürelerinin değişkenlik katsayısı; robot gibi eşit tempo düşük çıkar.
Bu özellikler insan anlatıcı kayıtlarından çıkarılan dağılımla (insan_profil.json) karşılaştırılır.
"""
import re

import numpy as np


def f0_egrisi(x16: np.ndarray):
    import librosa

    f0, voiced, _ = librosa.pyin(x16, fmin=60, fmax=350, sr=16000, frame_length=1024, hop_length=160)
    t = np.arange(len(f0)) * 160 / 16000
    m = voiced & ~np.isnan(f0)
    return t[m], f0[m]


def ozellikler(x16: np.ndarray, kelimeler: list, metin: str) -> dict:
    """kelimeler: faster-whisper Word nesneleri (start, end, word)."""
    t, f0 = f0_egrisi(x16)
    if len(f0) < 20:
        return {}
    st = 12 * np.log2(f0 / np.median(f0))
    sonuc = {"perde_std": round(float(st.std()), 2)}
    son = t >= t[-1] - 0.45
    if son.sum() >= 5:
        sonuc["son_egim"] = round(float(np.polyfit(t[son], st[son], 1)[0]), 2)
    uc = max(1, len(st) // 3)
    sonuc["alcalma"] = round(float(np.median(st[:uc]) - np.median(st[-uc:])), 2)
    if len(kelimeler) >= 3:
        sure = np.array([w.end - w.start for w in kelimeler])
        sonuc["hiz_cv"] = round(float(sure.std() / max(1e-3, sure.mean())), 2)
    # Virgül duraklaması: Whisper kelime sayısı metinle tutuyorsa, virgülden sonraki boşluk.
    hedef = metin.split()
    if len(hedef) == len(kelimeler):
        aralar = [kelimeler[i + 1].start - kelimeler[i].end for i, w in enumerate(hedef[:-1]) if w.endswith((",", ";"))]
        if aralar:
            sonuc["virgul_ara"] = round(float(np.mean(aralar)), 3)
    sonuc["bitis"] = "soru" if metin.rstrip().endswith("?") else (
        "virgul" if re.search(r"[,;]$", metin.rstrip()) else "duz")
    return sonuc


def profil(kayitlar: list[dict]) -> dict:
    """Özellik başına 10. / 50. / 90. yüzdelik (bitiş türüne göre ayrı son_egim)."""
    p = {}
    for ad in ("perde_std", "alcalma", "hiz_cv", "virgul_ara"):
        v = [k[ad] for k in kayitlar if ad in k]
        if len(v) >= 5:
            p[ad] = [round(float(np.percentile(v, q)), 3) for q in (10, 50, 90)]
    for bitis in ("duz", "soru", "virgul"):
        v = [k["son_egim"] for k in kayitlar if k.get("bitis") == bitis and "son_egim" in k]
        if len(v) >= 5:
            p[f"son_egim_{bitis}"] = [round(float(np.percentile(v, q)), 3) for q in (10, 50, 90)]
    return p


def puan(o: dict, prof: dict) -> dict:
    """Her özellik insan dağılımının 10-90 aralığında mı? Oran = aralıkta kalan özellik / ölçülen özellik."""
    sonuc = {}
    for ad, aralik in prof.items():
        anahtar = "son_egim" if ad.startswith("son_egim_") else ad
        if anahtar not in o or (ad.startswith("son_egim_") and ad != f"son_egim_{o.get('bitis')}"):
            continue
        sonuc[ad] = aralik[0] <= o[anahtar] <= aralik[2]
    return {"tonlama_uyum": round(sum(sonuc.values()) / len(sonuc), 3) if sonuc else None,
            "tonlama_disinda": [k for k, v in sonuc.items() if not v]}
