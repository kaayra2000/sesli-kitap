#!/usr/bin/env python3
"""
MFA ile ünlü süresi ölçümü ve düzeltmesi (Montreal Forced Aligner, turkish_mfa, 10 ms).

CTC hizalaması tepeli olduğundan ünlü süresinde yanıltıyordu (birâder'in â'sını 2.0 uzun ölçtü, MFA 1.0; kullanıcı da
kısa duydu). Bu betik:
  olc     -> cikti/mfa.json   {parça: [[kelime, [[baş, son] ...], [uzun mu ...]], ...]}
  duzelt  -> uzun ünlü (â î û, sakin ayn öncesi) bölümün kelime içi kısa ünlü ortancasının HEDEF katına uzatılır,
             kelime içi kısa ünlü SINIR katını aşıyorsa kısaltılır (perde periyodu çoğaltma/silme); secilen/*.wav
             güncellenir, yeniden hizalanıp ölçülür (mfa.json = düzeltme sonrası, mfa_once.json = öncesi); örnek
             modunda bölüm sesi ve alt yazı yeniden birleştirilir.
MFA ortamında çalışır: python mfa_duzelt.py <iş klasörü> olc|duzelt
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uzatma  # noqa: E402

UNLU_FON = set("aeiouyɯøɛœʏɪʊɑæə")
HEDEF, SINIR, EN_COK = 2.0, 1.6, 2.6


def ses_yolu(cikti, pid):
    return next((f for f in (cikti / "secilen" / f"{pid}.wav", cikti / "secilen" / f"{pid}.opus") if f.exists()), None)


def mfa(*a):
    r = subprocess.run(["mfa", *a], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"mfa {a[0]} başarısız: " + (r.stdout + r.stderr)[-1500:])


def hizala(cikti, parcalar):
    import librosa
    from praatio import textgrid
    korpus, out = Path("/tmp/mfa_korpus"), Path("/tmp/mfa_out")
    subprocess.run(["rm", "-rf", str(korpus), str(out)])
    korpus.mkdir(parents=True)
    kelimeler = set()
    for p in parcalar:
        x, sr = librosa.load(ses_yolu(cikti, p["id"]), sr=16000, mono=True)
        sf.write(korpus / f"{p['id']}.wav", x, 16000)
        (korpus / f"{p['id']}.lab").write_text(" ".join(p["mfa_kelimeler"]), encoding="utf-8")
        kelimeler.update(p["mfa_kelimeler"])
    Path("/tmp/mfa_kelimeler.txt").write_text("\n".join(sorted(kelimeler)), encoding="utf-8")
    if not Path("/tmp/mfa_sozluk.txt").exists() or set(Path("/tmp/mfa_sozluk_kelimeler.txt").read_text().split()
                                                         if Path("/tmp/mfa_sozluk_kelimeler.txt").exists() else []) != kelimeler:
        mfa("g2p", "/tmp/mfa_kelimeler.txt", "turkish_mfa", "/tmp/mfa_sozluk.txt", "--clean")
        Path("/tmp/mfa_sozluk_kelimeler.txt").write_text("\n".join(sorted(kelimeler)))
    mfa("align", str(korpus), "/tmp/mfa_sozluk.txt", "turkish_mfa", str(out), "--clean", "--single_speaker", "-j", "4",
        "--beam", "100", "--retry_beam", "400")
    sonuc = {}
    for p in parcalar:
        yol = out / f"{p['id']}.TextGrid"
        if not yol.exists():
            continue
        tg = textgrid.openTextgrid(str(yol), includeEmptyIntervals=False)
        kel = [e for e in tg.getTier("words").entries if e.label.strip()]
        fon = [e for e in tg.getTier("phones").entries if e.label.strip() and e.label != "spn"]
        satir = []
        for (w, uzun), e in zip(zip(p["mfa_kelimeler"], p["mfa_uzun"]), kel):
            if e.label != w:
                continue
            aralik = [[round(f.start, 3), round(f.end, 3)] for f in fon
                      if f.start >= e.start - 1e-4 and f.end <= e.end + 1e-4 and f.label.rstrip("ːˑ").lower() in UNLU_FON]
            if len(aralik) == len(uzun):
                satir.append([w, aralik, uzun])
        sonuc[p["id"]] = satir
    return sonuc


def kisa_ortanca(M):
    k = [b - a for v in M.values() for w, ar, uu in v for j, ((a, b), u) in enumerate(zip(ar, uu))
         if not u and j < len(ar) - 1]
    return float(np.median(k)) if k else 0.08


def ozet(M, m):
    uz = [(b - a) / m for v in M.values() for w, ar, uu in v for (a, b), u in zip(ar, uu) if u]
    ks = [(b - a) / m for v in M.values() for w, ar, uu in v for j, ((a, b), u) in enumerate(zip(ar, uu))
          if not u and j < len(ar) - 1]
    return {"kisa_ortanca_ms": round(1000 * m), "uzun_oran_ortanca": round(float(np.median(uz)), 2) if uz else None,
            "uzamamis": round(float(np.mean([r < 1.4 for r in uz])), 3) if uz else None,
            "yersiz_uzun": round(float(np.mean([r > 1.8 for r in ks])), 3) if ks else None}


def duzelt(cikti, M, m):
    islem_say = {"uzatilan": 0, "kisaltilan": 0}
    for pid, v in M.items():
        f = cikti / "secilen" / f"{pid}.wav"
        if not f.exists():
            continue
        x, sr = sf.read(f, dtype="float32")
        islem = []
        for w, ar, uu in v:
            for j, ((a, b), u) in enumerate(zip(ar, uu)):
                d = b - a
                if u and d < HEDEF * m:
                    islem.append((a, b, min(EN_COK, HEDEF * m / max(d, 1e-3))))
                elif not u and j < len(ar) - 1 and d > SINIR * m:
                    islem.append((a, b, SINIR * m / d))
        Ps = [uzatma.periyot(x[int((a + b) / 2 * sr) - sr // 40: int((a + b) / 2 * sr) + sr // 40], sr) for a, b, _ in islem]
        Ps = [q for q in Ps if q]
        yedek = int(np.median(Ps)) if Ps else None
        for a, b, kat in sorted(islem, key=lambda z: -z[0]):
            if kat > 1:
                y = uzatma.uzat(x, sr, [(a, b)], kat, yedek)
                islem_say["uzatilan"] += len(y) != len(x)
            else:
                orta = int((a + b) / 2 * sr)
                P = uzatma.periyot(x[orta - sr // 40: orta + sr // 40], sr) or yedek
                y = uzatma.periyot_sil(x, sr, a, b, int(round((1 - kat) * (b - a) * sr / P))) if P else x
                islem_say["kisaltilan"] += len(y) != len(x)
            x = y
        sf.write(f, x, sr)
    return islem_say


def birlestir(kok, cikti, parcalar):
    SR = 48000
    seg, simdi, srt = [], 0.0, []

    def z(t):
        ms = round(t * 1000)
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    for n, p in enumerate(parcalar, 1):
        x, sr = sf.read(cikti / "secilen" / f"{p['id']}.wav", dtype="float32")
        seg.append(x)
        srt.append(f"{n}\n{z(simdi)} --> {z(simdi + len(x) / SR)}\n{p['metin']}\n")
        simdi += len(x) / SR
        ara = np.zeros(int(p.get("ara", 0.5) * SR), np.float32)
        seg.append(ara)
        simdi += len(ara) / SR
    sf.write(cikti / "ham.wav", np.concatenate(seg), SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cikti / "ham.wav"), "-af", "loudnorm=I=-16:TP=-1:LRA=11",
                    "-ar", str(SR), "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(cikti / "ornek.mp3")], check=True)
    (cikti / "ham.wav").unlink()
    (cikti / "altyazi.srt").write_text("\n".join(srt), encoding="utf-8")


def main():
    kok, mod = Path(sys.argv[1]), sys.argv[2]
    cikti = kok / "cikti"
    is_ = json.loads((kok / "is.json").read_text(encoding="utf-8"))
    parcalar = [p for p in is_["parcalar"] if p.get("mfa_kelimeler") and ses_yolu(cikti, p["id"])]
    M = hizala(cikti, parcalar)
    m = kisa_ortanca(M)
    if mod == "duzelt":
        (cikti / "mfa_once.json").write_text(json.dumps(M), encoding="utf-8")
        once = ozet(M, m)
        say = duzelt(cikti, M, m)
        M = hizala(cikti, parcalar)
        print("MFA DÜZELTME:", json.dumps({"once": once, "sonra": ozet(M, kisa_ortanca(M)), **say}, ensure_ascii=False))
        if is_.get("mod") == "ornek" and (cikti / "ornek.mp3").exists():
            sira = [p for p in is_["parcalar"] if (cikti / "secilen" / f"{p['id']}.wav").exists()]
            birlestir(kok, cikti, sira)
    (cikti / "mfa.json").write_text(json.dumps(M), encoding="utf-8")
    print(f"MFA ÖLÇÜLDÜ: {len(M)} parça, {sum(len(v) for v in M.values())} kelime", json.dumps(ozet(M, kisa_ortanca(M))))


if __name__ == "__main__":
    main()
