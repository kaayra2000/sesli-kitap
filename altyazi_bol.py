#!/usr/bin/env python3
"""
Uzun alt yazı satırlarını (40 kelimelik okuma parçaları) cümle ve en çok ~14 kelimelik satırlara böler; süre parçanın
içinde harf sayısına göre paylaştırılır. Kullanım: python3 altyazi_bol.py girdi.srt cikti.srt
"""
import re
import sys


def zaman(s: str) -> float:
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def yaz(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def bol(metin: str, en_cok: int = 14) -> list[str]:
    cumleler = [c for c in re.split(r"(?<=[.!?:;])\s+", metin) if c]
    satirlar = []
    for c in cumleler:
        w = c.split()
        while len(w) > en_cok:
            # en_cok'a yakın bir virgülden, yoksa tam en_cok'tan böl
            virgul = [i for i in range(en_cok // 2, en_cok) if w[i - 1].endswith(",")]
            k = virgul[-1] if virgul else en_cok
            satirlar.append(" ".join(w[:k]))
            w = w[k:]
        satirlar.append(" ".join(w))
    return satirlar


girdi = open(sys.argv[1], encoding="utf-8").read().strip().split("\n\n")
cikti, n = [], 1
for blok in girdi:
    satir = blok.split("\n")
    bas, son = (zaman(x.strip()) for x in satir[1].split("-->"))
    parcalar = bol(" ".join(satir[2:]))
    toplam = sum(len(p) for p in parcalar)
    t = bas
    for p in parcalar:
        d = (son - bas) * len(p) / toplam
        cikti.append(f"{n}\n{yaz(t)} --> {yaz(t + d)}\n{p}\n")
        t += d
        n += 1
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(cikti))
print(f"{len(girdi)} blok -> {n - 1} satır")
