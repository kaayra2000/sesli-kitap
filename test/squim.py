"""İnsan kulağıyla daha uyumlu kalite ölçüleri (TTSDS2 makalesi, arXiv 2506.19441: modern TTS'te insan puanıyla
Spearman SQUIM-MOS 0.57, DNSMOS 0.29, NISQA ~-0.24).

- SQUIM-MOS (torchaudio SQUIM_SUBJECTIVE): eşleşmeyen temiz insan kaydını referans alır (ölçüm için insan okuması).
- DNSMOS P.835 (speechmos): SIG (konuşma sinyali), BAK (arka plan), OVRL.
Kullanım: python test/squim.py --ref referans/insan-okuma-1.wav <klasör|dosya> ...   (klasörde ilk 30 dosya)
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
from torchaudio.pipelines import SQUIM_SUBJECTIVE
from speechmos import dnsmos


def oku(yol, sr=16000):
    b = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(yol), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype=np.float32).copy()


args = sys.argv[1:]
ref_yol = args[args.index("--ref") + 1]
args = [a for i, a in enumerate(args) if a != "--ref" and (i == 0 or args[i - 1] != "--ref")]
model = SQUIM_SUBJECTIVE.get_model().eval()
ref = torch.from_numpy(oku(ref_yol)[: 16000 * 20]).unsqueeze(0)


def olc(x):
    sq = []
    for i in range(0, max(1, len(x) - 16000 * 3), 16000 * 10):  # 10 s dilimler
        p = torch.from_numpy(x[i:i + 16000 * 10]).unsqueeze(0)
        with torch.inference_mode():
            sq.append(model(p, ref).item())
    d = dnsmos.run(x / (np.abs(x).max() + 1e-9) * 0.9, 16000)
    return np.mean(sq), d["sig_mos"], d["bak_mos"], d["ovrl_mos"]


for a in args:
    p = Path(a)
    ds = sorted(x for x in p.iterdir() if x.suffix in (".opus", ".wav", ".mp3"))[:30] if p.is_dir() else [p]
    r = np.array([olc(oku(d)) for d in ds]).mean(0)
    print(f"{a}: SQUIM-MOS {r[0]:.3f}  DNSMOS SIG {r[1]:.3f} BAK {r[2]:.3f} OVRL {r[3]:.3f}  (n={len(ds)})", flush=True)
