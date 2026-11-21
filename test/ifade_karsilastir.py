#!/usr/bin/env python3
"""Deney varyantlarının ifade ölçülerini (ortanca) insan ve referans hedefleriyle yan yana yazar.
Kullanım: python3 test/ifade_karsilastir.py iterasyonlar/deney20 [iterasyonlar/deney19 (insan ölçüsü için)]"""
import collections
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metin"))
from olcum import hata  # noqa: E402

d = Path(sys.argv[1])
insan_yol = next((Path(a) / "ifade_insan.json" for a in sys.argv[1:] if (Path(a) / "ifade_insan.json").exists()), None)
I = json.loads((d / "ifade.json").read_text())
S = {p["id"]: p for p in json.loads((d / "sonuc.json").read_text())["parcalar"]}
K = ["canlilik", "olumluluk", "CE", "PQ", "perde_aralik", "perde_sapma", "enerji_sapma", "duraklama_10kelime",
     "kelime_hiz_cv", "vurgu_sapma", "vurgulu_oran", "vurgu_perde_sapma"]
print("ölçü".ljust(20) + "".join(k[:10].rjust(11) for k in K) + "    W%   CTC%  yanlış")
if insan_yol:
    H = json.loads(insan_yol.read_text())
    print("insan (ortanca)".ljust(20) + "".join(f"{H['fleurs'][k][1]:11.3f}" if k in H["fleurs"] else " " * 11 for k in K))
    r = H["referans"].get("kitap-sesi-yeni-c.wav", {})
    print("referans ses".ljust(20) + "".join(f"{r[k]:11.3f}" if k in r else " " * 11 for k in K))
g = collections.defaultdict(list)
for pid, v in I.items():
    g[pid.split("--")[1] if "--" in pid else "bölüm"].append((pid, v))
for var, L in g.items():
    row = [st.median([v[k] for _, v in L if k in v]) for k in K]
    w = [hata(S[p]["metin"], S[p]["duyulan"], esit=True)["cer"] for p, _ in L]
    c = [hata(S[p]["metin"], S[p].get("ctc_duyulan", ""), esit=True)["cer"] for p, _ in L]
    print(var[:20].ljust(20) + "".join(f"{x:11.3f}" for x in row) +
          f"  {100 * st.mean(w):5.2f} {100 * st.mean(c):5.2f} {sum(a > .03 and b > .06 for a, b in zip(w, c)):4d}")
