#!/usr/bin/env python3
"""
Kesinti (takılma) ölçüsü: konuşmanın ortasında ani ses kesilmesi ya da ani başlaması ("internet çekmiyor" etkisi).
5 ms çerçevede enerji, konuşma düzeyinden (parçanın %95 düzeyi - 20 dB üstü) bir çerçevede 30 dB'den fazla düşüyor
ya da sessizlikten bir çerçevede 30 dB'den fazla yükseliyorsa ve iki yanında da konuşma varsa (cümle başı/sonu
değil) kesinti sayılır. Doğal durak ünsüzleri ve ünlü sonları enerjiyi 10-30 ms'de bırakır; dijital ekleme/kesme anlıktır.

Kullanım: python3 test/kesinti.py <ses.wav|opus> ...   ya da  python3 test/kesinti.py --klasor iterasyonlar/ornek10/secilen
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

ESIK = 24.0


def oku(yol):
    if str(yol).endswith(".wav"):
        x, sr = sf.read(yol, dtype="float32")
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav") as t:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(yol), "-ac", "1", "-ar", "16000", t.name], check=True)
            x, sr = sf.read(t.name, dtype="float32")
    return (x.mean(1) if x.ndim > 1 else x), sr


def kesintiler(x, sr):
    h = int(0.005 * sr)
    n = len(x) // h
    if n < 20:
        return []
    e = 10 * np.log10((x[: n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    ust = np.percentile(e, 95)
    konusma = e > ust - 20
    ilk, son = np.argmax(konusma), n - np.argmax(konusma[::-1])
    sonuc = []
    for i in range(max(1, ilk + 4), min(n - 1, son - 4)):
        dus = e[i - 1] - e[i]
        yuksel = e[i] - e[i - 1]
        if (dus > ESIK and konusma[i - 1]) or (yuksel > ESIK and konusma[i]):
            sonuc.append(round(i * 0.005, 3))
    return sonuc


def main():
    if sys.argv[1] == "--klasor":
        dosyalar = sorted(Path(sys.argv[2]).glob("*.opus")) + sorted(Path(sys.argv[2]).glob("*.wav"))
    else:
        dosyalar = [Path(a) for a in sys.argv[1:]]
    toplam = 0
    for f in dosyalar:
        k = kesintiler(*oku(f))
        toplam += len(k)
        if k:
            print(f"{f.stem}: {len(k)} kesinti {k[:8]}")
    print(f"TOPLAM: {len(dosyalar)} dosya, {toplam} kesinti")


if __name__ == "__main__":
    main()
