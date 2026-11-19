#!/usr/bin/env python3
"""
Model yarışının hakemi: her sistemin her cümlesini aynı ölçülerle puanlar ve sıralar.

  kelime    Whisper large-v3 (eşitlenmiş CER) ve wav2vec2 CTC (eşitlenmiş CER)
  doğallık  UTMOS-v2 (Türkçe TTS değerlendirmesinde gerçekçiliğe en uyumlu ölçü; arXiv 2610.06057) ve UTMOS22
  ses       ECAPA konuşmacı benzerliği: standarttaki temel sese (referans) ne kadar benziyor
  tonlama   insan profiline (FLEURS tr) göre sapma
Kalibrasyon: aynı ölçülerle FLEURS'ten gerçek insan kayıtları da puanlanır ("insan").

Kullanım: python hakem_yaris.py is.json cikti/yaris  -> cikti/yaris/yaris.json, özet tablo
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import seslendir  # noqa: E402
import tonlama  # noqa: E402

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
kok = Path(sys.argv[2])
prof = {k: v for k, v in json.loads((HERE.parent / "referans/insan_profil.json").read_text()).items()
        if not k.startswith("_")}
hakem = seslendir.Hakem({**seslendir.VARSAYILAN})

import utmosv2  # noqa: E402
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

utmos2 = utmosv2.create_model(pretrained=True)
ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": seslendir.DEV})


def gomme(x16: np.ndarray) -> torch.Tensor:
    with torch.no_grad():
        e = ecapa.encode_batch(torch.from_numpy(x16).unsqueeze(0).to(seslendir.DEV)).squeeze()
    return e / e.norm()


def oku(yol: Path) -> tuple[np.ndarray, int]:
    x, sr = sf.read(str(yol), dtype="float32")
    return (x.mean(1) if x.ndim > 1 else x), sr


x, sr = oku(HERE.parent / is_["referans"]["yol"])
ref_gomme = gomme(seslendir.resample(x, sr, 16000))


def puanla(yol: Path, metin: str) -> dict:
    x, sr = oku(yol)
    p = hakem.olc(x, sr, metin)
    x16 = seslendir.resample(x, sr, 16000)
    o = tonlama.ozellikler(x16, p.pop("_kelimeler"), metin)
    tmp = Path("/tmp/utmos2.wav")
    sf.write(tmp, x16, 16000)
    return {"cer": p["whisper"]["cer"], "ctc": p.get("ctc_esit", {}).get("cer"), "utmos22": p["mos"],
            "utmos2": round(float(utmos2.predict(input_path=str(tmp))), 3),
            "benzerlik": round(float(gomme(x16) @ ref_gomme), 3), "tonlama_sapma": tonlama.sapma(o, prof),
            "son_kelime": o.get("son_kelime"), "perde_std": o.get("perde_std"), "sure": p["sure"],
            "duyulan": p["duyulan"]}


sonuc = {}
for sistem in sorted(d.name for d in kok.iterdir() if d.is_dir()):
    sonuc[sistem] = {}
    for c in is_["cumleler"]:
        yol = kok / sistem / f"{c['id']}.wav"
        if yol.exists():
            try:
                sonuc[sistem][c["id"]] = puanla(yol, c["okunus"])
            except Exception as e:  # noqa: BLE001
                print(f"{sistem} {c['id']} puanlanamadı: {e}", flush=True)
    print(f"{sistem}: {len(sonuc[sistem])} cümle puanlandı", flush=True)

# İnsan kalibrasyonu: FLEURS tr test, 12 kayıt
import pandas as pd  # noqa: E402

yol = Path("/tmp/fleurs-tr.parquet")
if not yol.exists():
    urllib.request.urlretrieve(seslendir.INSAN_VERI, yol)
df = pd.read_parquet(yol).sample(12, random_state=1)
(kok / "_insan").mkdir(exist_ok=True)
sonuc["insan"] = {}
for _, r in df.iterrows():
    x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
    p = kok / "_insan" / f"{r['id']}.wav"
    sf.write(p, x, sr)
    sonuc["insan"][str(r["id"])] = puanla(p, str(r["raw_transcription"]))

ozet = {}
for sistem, d in sonuc.items():
    v = list(d.values())
    if not v:
        continue
    ort = lambda k: round(float(np.mean([x[k] for x in v if x.get(k) is not None])), 3)  # noqa: E731
    ozet[sistem] = {k: ort(k) for k in ("cer", "ctc", "utmos2", "utmos22", "benzerlik", "tonlama_sapma", "son_kelime",
                                         "perde_std")}
    ozet[sistem]["yanlis"] = sum(x["cer"] > 0.03 and (x["ctc"] or 1) > 0.06 for x in v)
    ozet[sistem]["n"] = len(v)
(kok / "yaris.json").write_text(json.dumps({"ozet": ozet, "ayrinti": sonuc}, ensure_ascii=False, indent=1),
                                encoding="utf-8")
print("YARIŞ ÖZET")
for s, o in sorted(ozet.items(), key=lambda kv: -kv[1]["utmos2"]):
    print(s, json.dumps(o, ensure_ascii=False), flush=True)
