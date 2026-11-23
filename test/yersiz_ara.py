"""Bölümde yersiz durakları listeler (metinde noktalama olmayan kelime sınırında >=0.2 s sessizlik).
Kullanım: python3 test/yersiz_ara.py iterasyonlar/ornek12 [en_az_sn]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "colab"))
from ara_olc import yersiz_aralar  # noqa: E402


def oku(yol):
    b = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(yol), "-ac", "1", "-ar", "24000", "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype=np.float32), 24000


d = Path(sys.argv[1])
en_az = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
s = json.loads((d / "sonuc.json").read_text(encoding="utf-8"))
top, kelime = 0, 0
for p in s["parcalar"]:
    ses = next(iter(sorted((d / "secilen").glob(p["id"] + ".*"))), None)
    if ses is None or not p.get("kelime_zaman"):
        continue
    x, sr = oku(ses)
    y = yersiz_aralar(x, sr, p["kelime_zaman"], p["metin"], en_az)
    kelime += len(p["metin"].split())
    top += len(y)
    for a, b, t in y:
        print(f"{p['id']}  {a} ‖ {b}  {t:.2f} s")
print(f"\nToplam yersiz durak {top}, 100 kelimede {100 * top / max(1, kelime):.2f}")
