#!/usr/bin/env python3
"""
Ünlü süresi ölçümü: Montreal Forced Aligner (Türkçe turkish_mfa akustik modeli + G2P sözlüğü) ile her kelimenin
ünlüleri 10 ms çözünürlükte hizalanır. CTC hizalaması tepeli (peaky) olduğundan ünlü süresinde güvenilir değildi.

MFA ortamında çalışır. Kullanım: python mfa_olc.py <is klasörü>  -> cikti/mfa.json
  {parça: [[kelime, [ünlü süreleri sn], [uzun mu]], ...]}  (ünlü sayısı tutmayan kelime atlanır)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

UNLU_FON = set("aeiouyɯøɛœʏɪʊɑæə")


def main():
    kok = Path(sys.argv[1])
    cikti = kok / "cikti"
    is_ = json.loads((kok / "is.json").read_text(encoding="utf-8"))
    def ses(p):
        return next((f for f in (cikti / "secilen" / f"{p['id']}.wav", cikti / "secilen" / f"{p['id']}.opus") if f.exists()),
                    None)
    parcalar = [p for p in is_["parcalar"] if p.get("mfa_kelimeler") and ses(p)]
    korpus, out = Path("/tmp/mfa_korpus"), Path("/tmp/mfa_out")
    subprocess.run(["rm", "-rf", str(korpus), str(out)])
    korpus.mkdir(parents=True)
    kelimeler = set()
    for p in parcalar:
        import librosa
        x, sr = librosa.load(ses(p), sr=None, mono=True)
        sf.write(korpus / f"{p['id']}.wav", librosa.resample(x, orig_sr=sr, target_sr=16000), 16000)
        (korpus / f"{p['id']}.lab").write_text(" ".join(p["mfa_kelimeler"]), encoding="utf-8")
        kelimeler.update(p["mfa_kelimeler"])
    (Path("/tmp/mfa_kelimeler.txt")).write_text("\n".join(sorted(kelimeler)), encoding="utf-8")
    def calis(*a):
        r = subprocess.run(["mfa", *a], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"mfa {a[0]} başarısız: " + (r.stdout + r.stderr)[-1500:])
    calis("g2p", "/tmp/mfa_kelimeler.txt", "turkish_mfa", "/tmp/mfa_sozluk.txt", "--clean")
    calis("align", str(korpus), "/tmp/mfa_sozluk.txt", "turkish_mfa", str(out), "--clean", "--single_speaker",
          "-j", "4", "--beam", "100", "--retry_beam", "400")
    from praatio import textgrid
    sonuc = {}
    for p in parcalar:
        tg_yol = out / f"{p['id']}.TextGrid"
        if not tg_yol.exists():
            continue
        tg = textgrid.openTextgrid(str(tg_yol), includeEmptyIntervals=False)
        kel = [e for e in tg.getTier("words").entries if e.label.strip()]
        fon = [e for e in tg.getTier("phones").entries if e.label.strip() and e.label != "spn"]
        satir = []
        for (w, uzun), e in zip(zip(p["mfa_kelimeler"], p["mfa_uzun"]), kel):
            if e.label != w:
                continue
            sureler = [round(f.end - f.start, 3) for f in fon if f.start >= e.start - 1e-4 and f.end <= e.end + 1e-4
                       and f.label.rstrip("ːˑ").lower() in UNLU_FON]
            if len(sureler) == len(uzun):
                satir.append([w, sureler, uzun])
        sonuc[p["id"]] = satir
    (cikti / "mfa.json").write_text(json.dumps(sonuc, ensure_ascii=False), encoding="utf-8")
    n = sum(len(v) for v in sonuc.values())
    print(f"MFA ÖLÇÜLDÜ: {len(sonuc)} parça, {n} kelime, ortanca kısa ünlü "
          f"{np.median([s for v in sonuc.values() for _, ss, uu in v for s, u in zip(ss, uu) if not u] or [0]):.3f} sn")


if __name__ == "__main__":
    main()
