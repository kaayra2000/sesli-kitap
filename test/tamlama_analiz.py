#!/usr/bin/env python3
"""
Tamlama deneyi analizi: her biçim için genel doğruluk, tamlama doğruluğu ve uzun ünlü oranı.

Tamlama doğru sayılır: Whisper'da yerel hata <= %10 ve CTC'de (harfi harfine) <= %20.
Kullanım: python3 test/tamlama_analiz.py iterasyonlar/deney02
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metin"))
from olcum import hata, tamlamalar, yerel_hata  # noqa: E402

d = json.loads((Path(sys.argv[1]) / "sonuc.json").read_text(encoding="utf-8"))
g = defaultdict(lambda: defaultdict(list))
kotu = defaultdict(list)
for r in d["parcalar"]:
    cumle, bicim = r["id"].split("--")
    w = hata(r["metin"], r["duyulan"], esit=True)["cer"]
    c = hata(r["metin"], r.get("ctc_duyulan", ""), esit=True)["cer"]
    g[bicim]["cer"].append(w)
    g[bicim]["ctc"].append(c)
    g[bicim]["yanlis"].append(w > 0.03 and c > 0.06)
    if r.get("uzatma", {}).get("oran_sonra"):
        g[bicim]["oran"].append(r["uzatma"]["oran_sonra"])
    for t in tamlamalar(r["metin"]):
        tw, tc = yerel_hata(t, r["duyulan"]), yerel_hata(t, r.get("ctc_duyulan", ""))
        ok = tw <= 0.10 and tc <= 0.20
        g[bicim]["tamlama"].append(ok)
        if not ok:
            kotu[bicim].append((t, tw, tc, r["duyulan"][:90]))
print(f"{'biçim':22} {'CER':>6} {'CTC':>6} {'yanlış':>6} {'tamlama doğru':>14} {'uzun/kısa':>9}")
for b, v in g.items():
    print(f"{b:22} {st.mean(v['cer']):6.3f} {st.mean(v['ctc']):6.3f} {sum(v['yanlis']):6d} "
          f"{sum(v['tamlama'])}/{len(v['tamlama'])} ({sum(v['tamlama']) / max(1, len(v['tamlama'])):.0%})"
          f"{st.mean(v['oran']) if v['oran'] else 0:10.2f}")
for b, k in kotu.items():
    print(f"\n{b}: yanlış okunan tamlamalar ({len(k)})")
    for t, tw, tc, h in k[:12]:
        print(f"  {t:28} W {tw:.2f} C {tc:.2f} | {h}")
