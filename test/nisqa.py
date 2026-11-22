#!/usr/bin/env python3
"""
Doğallık / robotiklik bekçisi: NISQA (Mittag ve ark. 2021, torchmetrics) MOS ve alt boyutlar
(gürültü, kesinti, renklenme, yükseklik; 1-5). Deney (2026-11-22): sonradan işlem (perde PSOLA ×1.25, ünlü periyot
kopyalama, sessizlik ekleme) kullanıcıya "robotik, telefon çekmiyor" geldi; jitter/HNR bunu göstermedi, NISQA gösterdi
(işlenmemiş ornek07 MOS 4.73 / kesinti 4.69; işlenmiş 4.47-4.53 / 4.19-4.37). Kural: değişiklik NISQA'yı düşürmemeli.

Kullanım: python3 test/nisqa.py <klasör|dosya> ...   (opus/wav; klasörde tüm dosyaların ortalaması)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from torchmetrics.functional.audio.nisqa import non_intrusive_speech_quality_assessment as nisqa

ADLAR = ["MOS", "gürültü", "kesinti", "renklenme", "yükseklik"]


def oku(f):
    with tempfile.NamedTemporaryFile(suffix=".wav") as t:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-ac", "1", "-ar", "16000", t.name], check=True)
        x, sr = sf.read(t.name, dtype="float32")
    return x, sr


def puan_dizi(x, sr):
    """20 sn'lik dilimlerin süre ağırlıklı ortalaması (NISQA uzun sesi kabul etmiyor)."""
    d = 20 * sr
    parca = [x[i:i + d] for i in range(0, len(x), d) if len(x[i:i + d]) > sr]
    return np.average([nisqa(torch.from_numpy(p), sr).numpy() for p in parca], 0, weights=[len(p) for p in parca])


def puan(f):
    return puan_dizi(*oku(f))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        p = Path(a)
        dosyalar = sorted(list(p.glob("*.opus")) + list(p.glob("*.wav"))) if p.is_dir() else [p]
        m = np.mean([puan(f) for f in dosyalar], 0)
        print(f"{p.name:30} " + "  ".join(f"{n} {v:.2f}" for n, v in zip(ADLAR, m)) + f"  ({len(dosyalar)} dosya)")
