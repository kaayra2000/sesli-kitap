#!/usr/bin/env python3
"""
MFA ünlü süresi raporu (Montreal Forced Aligner, 10 ms): mfa.json {parça: [[kelime, [süreler], [uzun mu]]]}.
Oran = ünlü süresi / bölümün kelime içi kısa ünlü ortancası (kelime sonu ünlü hariç: öbek sonu uzaması).
- Uzamamış uzun ünlü: oran < 1.4
- Yersiz uzamış kısa ünlü (kelime sonu değil): oran > 1.8
Kullanım: python3 test/mfa_raporu.py iterasyonlar/ornek09 [kelime ...]   (kelime verilirse yalnız onlar yazılır)
"""
import json
import statistics as st
import sys
from pathlib import Path

d = Path(sys.argv[1])
ara = set(sys.argv[2:])
M = json.loads((d / "mfa.json").read_text())
# yeni biçim: [[baş, son] ...] -> süre
M = {k: [[w, [b - a if isinstance(x, list) else x for x in ss for a, b in ([x] if isinstance(x, list) else [(0, x)])], uu]
         for w, ss, uu in v] for k, v in M.items()}
srt = {}
kisa = [s for v in M.values() for w, ss, uu in v for j, (s, u) in enumerate(zip(ss, uu)) if not u and j < len(ss) - 1]
m = st.median(kisa)
uz, yer, uzun_n, kisa_n = [], [], 0, 0
oranlar = []
for pid, v in M.items():
    for w, ss, uu in v:
        for j, (s, u) in enumerate(zip(ss, uu)):
            r = s / m
            if u:
                uzun_n += 1
                oranlar.append(r)
                if r < 1.4:
                    uz.append((pid, w, j, round(r, 2)))
            elif j < len(ss) - 1:
                kisa_n += 1
                if r > 1.8:
                    yer.append((pid, w, j, round(r, 2)))
        if ara and w in ara:
            print(pid, w, " ".join(f"{'*' if u else ''}{s / m:.1f}" for s, u in zip(ss, uu)))
if ara:
    sys.exit()
print(f"# MFA ünlü süresi: {d.name}\n\n- Kısa ünlü ortancası {m * 1000:.0f} ms; uzun ünlü oran ortancası {st.median(oranlar):.2f}")
print(f"- Uzun ünlü {uzun_n}, uzamamış {len(uz)} (%{100 * len(uz) / max(1, uzun_n):.0f})")
print(f"- Kelime içi kısa ünlü {kisa_n}, yersiz uzamış {len(yer)} (%{100 * len(yer) / max(1, kisa_n):.1f})\n")
print("## Uzamamış uzun ünlüler (parça, kelime, kaçıncı ünlü, oran)\n")
for x in uz:
    print(f"- {x[0]} {x[1]} #{x[2] + 1} ({x[3]})")
print("\n## Yersiz uzamış kısa ünlüler\n")
for x in yer:
    print(f"- {x[0]} {x[1]} #{x[2] + 1} ({x[3]})")
