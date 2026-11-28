"""Klip başına inceleme görüntüsü: spektrogram + perde eğrisi + kelime sınırları (Claude'un görsel incelemesi için).

Kullanım (Colab): python3 spektrogram.py <klip-klasörü> <klip_bilgi.json> <çıktı-klasörü>
klip_bilgi.json: [{no, metin, kelime_zaman: [[kelime, baş, son], ...]}, ...]
Her klip için <çıktı>/<no>.png: üstte 0-5 kHz spektrogram (ünlü formantları, uzunlukları ve duraklar görünür), ortasında
perde (F0, parselmouth), altta kelimeler zaman ekseninde. Uzatılmış hece spektrogramda uzun, düz formant bandı olarak,
yersiz durak kelimeler arası boşluk olarak görünür.
"""
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

try:
    import parselmouth
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "praat-parselmouth"], check=False)
    import parselmouth

klasor, bilgi_yol, cikti = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cikti.mkdir(parents=True, exist_ok=True)
SR = 16000


def oku(f):
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, dtype=np.float32).copy()


for b in json.loads(bilgi_yol.read_text()):
    no = f"{b['no']:02d}"
    x = oku(klasor / f"{no}.mp3")
    t_son = len(x) / SR
    snd = parselmouth.Sound(x.astype(np.float64), SR)
    perde = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400)
    f0 = perde.selected_array["frequency"]
    f0[f0 == 0] = np.nan
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(max(8, t_son * 1.1), 5.2), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1.3, 0.9]})
    a1.specgram(x, NFFT=512, Fs=SR, noverlap=384, cmap="magma", vmin=-110)
    a1.set_ylim(0, 5000)
    a1.set_ylabel("Hz")
    a1.set_title(f"{no}: {b['metin'][:140]}", fontsize=8, loc="left")
    a2.plot(perde.xs(), f0, ".", ms=2, color="tab:blue")
    a2.set_ylabel("F0")
    a3.set_yticks([])
    for w, s, e in b.get("kelime_zaman") or []:
        for a in (a1, a2):
            a.axvline(s, color="w" if a is a1 else "0.7", lw=0.4, alpha=0.6)
        a3.axvspan(s, e, color="0.9")
        a3.text((s + e) / 2, 0.5, w, ha="center", va="center", fontsize=6, rotation=35)
    a3.set_xlabel("sn")
    a3.set_xlim(0, t_son)
    fig.tight_layout()
    fig.savefig(cikti / f"{no}.png", dpi=80)
    plt.close(fig)
print("TAMAM", len(list(cikti.glob("*.png"))), "görüntü")
