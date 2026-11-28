"""Ölçüm araçlarının puanlarını kulak testi puanlarıyla karşılaştırır (Spearman sıra uyumu).

Kullanım: python3 video/olcum_karsilastir.py <olcum.csv> <puanlar-klasörü> [gizli_anahtar.json]
puanlar-klasörü: ArtifactData ile indirilen k01.json ... k40.json (alanlar: no, puan, uzama, okuma).
Çıktı: her ölçüm için tüm klipler, yalnız nesir ve "yanlış uzatma" işaretiyle uyum; en uyumludan en aza.
"""
import csv
import json
import math
import statistics as st
import sys
from pathlib import Path


def sira(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for k in range(i, j + 1):
            r[s[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = sira(a), sira(b)
    ma, mb = st.mean(ra), st.mean(rb)
    pay = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    payda = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return pay / payda if payda else float("nan")


def main():
    csv_yol, puan_kls = Path(sys.argv[1]), Path(sys.argv[2])
    siir = set()
    if len(sys.argv) > 3:  # şiir mi: metinde Osmanlıca/Farsça mısra işaretleri (gizli anahtardan elle verilir)
        siir = {int(x) for x in json.loads(Path(sys.argv[3]).read_text()).get("siir", [])}
    P = {}
    for f in puan_kls.glob("*.json"):
        d = json.loads(f.read_text())
        d = d.get("data", d)
        P[int(d["no"])] = d
    satir = list(csv.DictReader(csv_yol.open()))
    olcumler = [k for k in satir[0] if k != "klip"]
    sonuc = []
    for o in olcumler:
        cift = [(float(r[o]), P[int(r["klip"])]) for r in satir
                if r[o] not in ("", "nan") and int(r["klip"]) in P and P[int(r["klip"])].get("puan")]
        if len(cift) < 10:
            continue
        hep = spearman([c[0] for c in cift], [c[1]["puan"] for c in cift])
        nes = [(x, p) for (x, p), r in zip(cift, satir) if int(r["klip"]) not in siir]
        nesir = spearman([x for x, _ in nes], [p["puan"] for _, p in nes]) if len(nes) >= 10 else float("nan")
        uz = spearman([-c[0] for c in cift], [1 if c[1].get("uzama") else 0 for c in cift])
        aralik = (min(c[0] for c in cift), max(c[0] for c in cift))
        sonuc.append((hep, o, nesir, uz, aralik, len(cift)))
    print(f"{'ölçüm':<18} {'uyum (hepsi)':>12} {'uyum (nesir)':>12} {'uzatmayı yakalama':>18}  aralık")
    for hep, o, nesir, uz, (a, b), n in sorted(sonuc, key=lambda s: -s[0] if not math.isnan(s[0]) else 9):
        print(f"{o:<18} {hep:>12.3f} {nesir:>12.3f} {uz:>18.3f}  {a:.2f}–{b:.2f} (n={n})")


if __name__ == "__main__":
    main()
