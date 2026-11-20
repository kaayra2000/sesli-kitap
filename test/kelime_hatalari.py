#!/usr/bin/env python3
"""
Kelime düzeyinde okuma hataları: her parçada metnin kelimeleri Whisper ve CTC dökümüyle hizalanır (eşitlenmiş);
iki hakemin de farklı duyduğu kelime "yanlış okunan" sayılır. Tekrar eden hatalar sözlük/kural adayıdır.

Kullanım: python3 test/kelime_hatalari.py iterasyonlar/ornek04 [iterasyonlar/...]
"""
import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metin"))
from okunus import GUNUMUZ, okunus  # noqa: E402
from olcum import distance, esitle, normalize  # noqa: E402

UNLU = str.maketrans("ıuü", "iii")


def kelimeler(metin: str, kaynak: bool = False) -> list[str]:
    """Eşitlenmiş kelimeler; kaynak metin önce günümüz okunuşuna (tire birleşik, izafet bitişik) çevrilir."""
    if kaynak:
        metin = okunus(metin, None, {**GUNUMUZ, "harf_ayir": "yok"})
    return esitle(normalize(metin)).split()


def yanlislar(ref: str, hyp: str) -> dict[int, str]:
    """ref kelime indeksi -> duyulan (yanlış duyulanlar). Küçük fark (1 harf, 6+ harfli kelimede) tolere edilir."""
    r, h = kelimeler(ref, True), kelimeler(hyp)
    sonuc = {}
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, r, h, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        duyulan = " ".join(h[b1:b2])
        bitisik = "".join(r[a1:a2])
        if bitisik == duyulan.replace(" ", ""):
            continue  # yalnız boşluk farkı
        for i in range(a1, a2):
            w = r[i]
            if op == "replace" and a2 - a1 == 1 and (w.translate(UNLU) == duyulan.translate(UNLU) or
                                                     len(w) >= 6 and distance(w, duyulan) <= 1):
                continue
            sonuc[i] = duyulan
    return sonuc


def main() -> None:
    sayac, ornek = Counter(), defaultdict(list)
    toplam = 0
    for d in sys.argv[1:]:
        for p in json.loads((Path(d) / "sonuc.json").read_text(encoding="utf-8"))["parcalar"]:
            ref = p.get("hedef") or p["metin"]
            w, c = yanlislar(ref, p.get("duyulan", "")), yanlislar(ref, p.get("ctc_duyulan", ""))
            kel = kelimeler(ref, True)
            toplam += len(kel)
            for i in w.keys() & c.keys():
                sayac[kel[i]] += 1
                ornek[kel[i]].append(f"{w[i]} / {c[i]}  [{p['id']}]")
    print(f"{toplam} kelime, {sum(sayac.values())} iki hakemce yanlış ({sum(sayac.values()) / max(1, toplam):.2%})")
    for k, n in sayac.most_common(60):
        print(f"{n:3} {k:22} -> {ornek[k][0]}")


if __name__ == "__main__":
    main()
