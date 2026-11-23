"""Bant genişliği / codec testi: "telefon hattı" tınısını yakalar (referans gerekmez).
Kullanım: python3 test/bant.py <ses|klasör> ...
Ölçüler (sesli kareler, 0.5 s üstü sinyal): %99 spektral rolloff (Hz), 4-8 kHz / 0-4 kHz ve 8-16 kHz / 0-4 kHz enerji oranı (dB).
"""
import sys
from pathlib import Path
import numpy as np
import librosa

def olc(yol):
    y, sr = librosa.load(str(yol), sr=44100, mono=True)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    e = S.sum(0)
    S = S[:, e > np.percentile(e, 50)]  # yalnız güçlü kareler
    toplam = S.sum(1)
    kum = np.cumsum(toplam) / toplam.sum()
    rolloff = f[np.searchsorted(kum, 0.99)]
    def band(a, b):
        return toplam[(f >= a) & (f < b)].sum()
    alt = band(80, 4000)
    return rolloff, 10*np.log10(band(4000, 8000)/alt), 10*np.log10(band(8000, 16000)/alt + 1e-12)

for a in sys.argv[1:]:
    p = Path(a)
    ds = sorted(x for x in p.iterdir() if x.suffix in (".opus", ".wav", ".mp3")) if p.is_dir() else [p]
    r = np.array([olc(d) for d in ds[:40]])
    m = r.mean(0)
    print(f"{a}: rolloff99 {m[0]:.0f} Hz, 4-8k {m[1]:.1f} dB, 8-16k {m[2]:.1f} dB  (n={len(r)})")
