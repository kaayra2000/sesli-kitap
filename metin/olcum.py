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
    """Günümüz imlâsı + yazım farkları: kelime sonu çift ünsüz (Hakk/hak, hâss/has), izafet ünlüsü (huzurı/huzuru),
    eklerin kesme ve tireyle ayrılması (Ekber'den, daire-i)."""
    t = normalize(okunus(metin.replace("-", ""), [], GUNUMUZ))
    t = re.sub(r"([bcçdfgğhjklmnprsştvyz])\1\b", r"\1", t)
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
