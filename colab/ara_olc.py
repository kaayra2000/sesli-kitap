"""Yersiz durak ölçüsü: metinde noktalama olmayan kelime sınırında sessizlik (ör. "bir zümre-i ‖ makbûlân").

Whisper kelime zamanları sessizliği sonraki kelimeye katar, o yüzden sessizlik enerjiden bulunur; kelime sınırına
Whisper zamanlarıyla, noktalamaya da metin kelimeleriyle (difflib hizası) bağlanır. Aday seçiminde ve testte kullanılır.
"""
import difflib
import re

import numpy as np

NOKTALAMA = ",.;:!?)]\"'’”—–-…"


def _norm(k: str) -> str:
    return re.sub(r"[^a-zçğıöşüâîû]", "", k.lower().replace("İ", "i").replace("I", "ı"))


def sessizlikler(x: np.ndarray, sr: int, en_az: float = 0.2, esik_db: float = -35) -> list:
    """10 ms karelerde tepeye göre esik_db altı ve en_az saniyeden uzun aralıklar (baş ve son hariç)."""
    h = int(sr * 0.01)
    n = len(x) // h
    if n < 3:
        return []
    e = np.sqrt((x[: n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(e / (e.max() + 1e-12))
    sessiz = db < esik_db
    ses = np.flatnonzero(~sessiz)
    if len(ses) == 0:
        return []
    ilk, son = ses[0], ses[-1]
    out, i = [], ilk
    while i <= son:
        if sessiz[i]:
            j = i
            while j <= son and sessiz[j]:
                j += 1
            if (j - i) * 0.01 >= en_az:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


IZAFET = re.compile(r"-(i|ı|yi|yı|u|ü|yu|yü)$")


def yersiz_aralar(x: np.ndarray, sr: int, kelimeler: list, hedef: str, en_az: float = 0.2,
                  yalniz_tamlama: bool = True) -> list:
    """kelimeler: [(kelime, başla, bitiş)] Whisper zamanları. Dönüş: [(önceki kelime, sonraki kelime, süre)].

    yalniz_tamlama: yalnız izafet içi (zümre-i ‖ makbûlân) sayılır; noktalamasız ama doğal nefes durakları
    (ör. "ve" öncesi) insan okumasında da var, onlar sayılmaz."""
    if not kelimeler:
        return []
    hk = hedef.split()
    hn = [_norm(k) for k in hk]
    wn = [_norm(k[0]) for k in kelimeler]
    eslem = {}
    for blok in difflib.SequenceMatcher(None, wn, hn, autojunk=False).get_matching_blocks():
        for d in range(blok.size):
            eslem[blok.a + d] = blok.b + d
    # eşleşmeyen kelime (zümreyi / zümre-i): iki yanındaki eşleşmeler arası aralık eşitse konumdan eşle
    es = sorted(eslem.items())
    for (a0, b0), (a1, b1) in zip(es, es[1:]):
        if a1 - a0 == b1 - b0 > 1:
            for d in range(1, a1 - a0):
                eslem[a0 + d] = b0 + d
    out = []
    for a, b in sessizlikler(x, sr, en_az):
        orta = (a + b) / 2
        # sessizliği izleyen ilk kelime (Whisper sessizliği sonraki kelimenin başına katar)
        k = next((i for i, w in enumerate(kelimeler) if w[2] > orta), None)
        if k is None or k == 0:
            continue
        onceki = k - 1
        if onceki not in eslem:
            continue
        ok = hk[eslem[onceki]]
        if ok[-1] in NOKTALAMA:
            continue
        if not yalniz_tamlama or IZAFET.search(ok):
            out.append((kelimeler[onceki][0].strip(), kelimeler[k][0].strip(), round(b - a, 2)))
    return out
