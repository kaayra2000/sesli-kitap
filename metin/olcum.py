"""
Hakem metin karşılaştırması: hedef okunuş ile ASR çıktısı arasındaki karakter / kelime hatası.

Colab'de (seslendir.py) ve yerelde (degerlendir.py, eski turları yeniden puanlama) aynı kod kullanılır.
Whisper duyduğunu günümüz imlâsıyla yazar; iki taraf da aynı biçime getirilir (esitle), böylece yalnız gerçek
seslendirme hatası sayılır. CTC çıktısı eşitlenmeden (harfi harfine) karşılaştırılır.
"""
import re

from okunus import GUNUMUZ, okunus, sayi_yazi


def normalize(text: str) -> str:
    text = re.sub(r"\d+", lambda m: " " + sayi_yazi(int(m.group(0))) + " " if len(m.group(0)) <= 6 else m.group(0), text)
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = text.translate(str.maketrans("îâû", "iau"))
    text = re.sub(r"[’'`‘]", "", text)
    return " ".join(re.sub(r"[^\wçğıöşü ]+", " ", text).split())


def esitle(metin: str) -> str:
    """Günümüz imlâsı + yazım farkları: çift ünsüz (Hakk/hak, hâssdır/hastır), izafet ünlüsü (huzurı/huzuru),
    eklerin kesme ve tireyle ayrılması (Ekber'den, daire-i)."""
    metin = re.sub(r"\b[Hh]z\.\s*", "Hazret-i ", metin)   # Whisper "Hazret-i"yi "Hz." diye kısaltıyor
    t = normalize(okunus(metin, [], GUNUMUZ))
    t = re.sub(r"([bcçdfgğhjklmnprsştvyz])\1", r"\1", t)   # çift ünsüz: hâssdır/hastır, Hakk/hak
    t = re.sub(r"(?<=\w)[ıiuü]\b", "i", t)
    return t


def distance(a, b) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def hata(ref: str, hyp: str, esit: bool = False) -> dict:
    r, h = (esitle(ref), esitle(hyp)) if esit else (normalize(ref), normalize(hyp))
    rn, hn = r.replace(" ", ""), h.replace(" ", "")
    return {"cer": round(distance(rn, hn) / max(1, len(rn)), 4),   # boşluksuz: "fil hakika" = "filhakika"
            "wer": round(distance(r.split(), h.split()) / max(1, len(r.split())), 4)}


def yerel_hata(ifade: str, hyp: str, esit: bool = True) -> float:
    """İfadenin (ör. bir tamlama) duyulan metin içindeki en iyi eşleşmesinin karakter hatası (yarı-global hizalama:
    duyulan metinde başlangıç ve bitiş serbest). Boşluklar yok sayılır."""
    # İzafet ünlüsü (ı/i/u/ü) yazımı duyana göre değişir (Babı Ali / Babıali / Bab-ı Ali); dar ünlüler eşitlenir.
    dar = str.maketrans("ıuü", "iii")
    r = (esitle(ifade) if esit else normalize(ifade)).replace(" ", "").translate(dar)
    h = (esitle(hyp) if esit else normalize(hyp)).replace(" ", "").translate(dar)
    if not r:
        return 0.0
    onceki = [0] * (len(h) + 1)          # duyulan metnin her yerinden başlanabilir
    for i, x in enumerate(r, 1):
        simdi = [i] + [0] * len(h)
        for j, y in enumerate(h, 1):
            simdi[j] = min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + (x != y))
        onceki = simdi
    return round(min(onceki) / len(r), 4)


IZAFET = r"[\wâîûÂÎÛ‘’']+-(?:[ıiuü]|yı|yi)\s+[\wâîûÂÎÛ‘’']+"


def tamlamalar(metin: str) -> list[str]:
    import re as _re
    return _re.findall(IZAFET, metin)
