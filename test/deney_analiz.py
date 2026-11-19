#!/usr/bin/env python3
"""
Uzun ünlü deneyinin sonucu: her şapka biçimi için doğruluk (Whisper / CTC, eşitlenmiş) ve süre oranı.

Süre oranı = biçimin cümle süresi (adayların medyanı) / şapkasız biçimin süresi. Uzun ünlü doğru verilirse oran > 1.
Kullanım: python3 test/deney_analiz.py iterasyonlar/deney01
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metin"))
from olcum import hata  # noqa: E402

d = json.loads((Path(sys.argv[1]) / "sonuc.json").read_text(encoding="utf-8"))
sure, cer, ctc, yanlis = defaultdict(dict), defaultdict(list), defaultdict(list), defaultdict(int)
for r in d["parcalar"]:
    cumle, bicim = r["id"].rsplit("-", 1)
    sure[cumle][bicim] = statistics.median(a["sure"] for a in r["adaylar"])
    w = hata(r["metin"], r["duyulan"], esit=True)["cer"]
    c = hata(r["metin"], r.get("ctc_duyulan", ""), esit=True)["cer"]
    cer[bicim].append(w)
    ctc[bicim].append(c)
    yanlis[bicim] += w > 0.03 and c > 0.06
bicimler = sorted(cer, key=["kaldir", "koru", "cift"].index)
print(f"{'biçim':8} {'Whisper CER':>12} {'CTC CER':>8} {'yanlış':>7} {'süre oranı':>11}")
for b in bicimler:
    oran = [sure[c][b] / sure[c]["kaldir"] for c in sure if b in sure[c] and "kaldir" in sure[c]]
    print(f"{b:8} {statistics.mean(cer[b]):12.4f} {statistics.mean(ctc[b]):8.4f} {yanlis[b]:7d} "
          f"{statistics.mean(oran):11.3f}")
print("\ncümle başına süre (sn):")
for c in sorted(sure):
    print(c, "  ".join(f"{b} {sure[c].get(b, 0):.2f}" for b in bicimler))
