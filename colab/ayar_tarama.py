#!/usr/bin/env python3
"""
VoxCPM2 ayar ve referans taraması: "robotik" ses ayardan mı (cfg, adım), klonlama biçiminden mi (tam klon / yalnız
tını), referans sesten mi (Piper temel ses / canlı referans / referanssız) geliyor? VoxCPM ortamında (Python 3.12) çalışır.

Kullanım: python ayar_tarama.py is.json  -> cikti/tarama/<biçim>/<cümle>.wav, cikti/sonuc.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seslendir  # noqa: E402
import tonlama  # noqa: E402
from voxcpm import VoxCPM  # noqa: E402

TEMEL = str(HERE / "referans/referans-temel-ses.wav")
CANLI = str(HERE / "referans/referans-canli.wav")
CANLI_METIN = "Size harika bir haberim var! Yeni sistemimiz hazır. Hadi, birlikte keşfedelim!"
BICIMLER = {
    "1-standart": dict(prompt_wav_path=TEMEL, prompt_text=seslendir.TEMEL_METIN, reference_wav_path=TEMEL, cfg_value=2.0, inference_timesteps=10),
    "2-cfg15": dict(prompt_wav_path=TEMEL, prompt_text=seslendir.TEMEL_METIN, reference_wav_path=TEMEL, cfg_value=1.5, inference_timesteps=10),
    "3-adim30": dict(prompt_wav_path=TEMEL, prompt_text=seslendir.TEMEL_METIN, reference_wav_path=TEMEL, cfg_value=2.0, inference_timesteps=30),
    "4-tini": dict(reference_wav_path=TEMEL, cfg_value=2.0, inference_timesteps=10),
    "5-tini-cfg15-adim30": dict(reference_wav_path=TEMEL, cfg_value=1.5, inference_timesteps=30),
    "6-canli-ref": dict(prompt_wav_path=CANLI, prompt_text=CANLI_METIN, reference_wav_path=CANLI, cfg_value=2.0, inference_timesteps=10),
    "7-referanssiz": dict(cfg_value=2.0, inference_timesteps=10),
}

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cikti = HERE / "cikti"
vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = vox.tts_model.sample_rate
ayar = {**seslendir.VARSAYILAN, **is_.get("ayar", {})}
hakem = seslendir.Hakem(ayar)
prof = {k: v for k, v in json.loads((HERE / "referans/insan_profil.json").read_text()).items() if not k.startswith("_")}

from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": seslendir.DEV})


def gomme(x, sr_):
    x16 = seslendir.resample(x, sr_, 16000)
    with torch.no_grad():
        e = ecapa.encode_batch(torch.from_numpy(x16).unsqueeze(0).to(seslendir.DEV)).squeeze()
    return e / e.norm()


x, s = sf.read(TEMEL, dtype="float32")
ref_e = gomme(x, s)
sonuc = {}
for bicim, arg in BICIMLER.items():
    (cikti / "tarama" / bicim).mkdir(parents=True, exist_ok=True)
    sonuc[bicim] = {}
    for c in is_["parcalar"]:
        en_iyi = None
        for tohum in range(ayar.get("aday", 2)):
            torch.manual_seed(tohum)
            t = time.time()
            y = np.asarray(vox.generate(text=c["okunus"], **arg), dtype=np.float32)
            y = seslendir.kirp(y, sr)
            p = hakem.olc(y, sr, c["okunus"])
            o = tonlama.ozellikler(seslendir.resample(y, sr, 16000), p.pop("_kelimeler"), c["okunus"])
            p.update(tonlama=o, tonlama_sapma=tonlama.sapma(o, prof), benzerlik=round(float(gomme(y, sr) @ ref_e), 3),
                     sure_uretim=round(time.time() - t, 1), tohum=tohum)
            anahtar = (seslendir.yanlis(p, ayar), p["whisper"]["cer"] + 0.5 * p["ctc_esit"]["cer"], p["tonlama_sapma"])
            if en_iyi is None or anahtar < en_iyi[0]:
                en_iyi = (anahtar, y, p)
        _, y, p = en_iyi
        sf.write(cikti / "tarama" / bicim / f"{c['id']}.wav", y / max(1e-6, np.abs(y).max()) * 0.9, sr)
        sonuc[bicim][c["id"]] = p
        print(f"{bicim:22} {c['id']:10} CER {p['whisper']['cer']:.3f} CTC {p['ctc_esit']['cer']:.3f} "
              f"benzerlik {p['benzerlik']:.2f} tonlama {p['tonlama_sapma']:.2f} son kelime {p['tonlama'].get('son_kelime')} "
              f"perde {p['tonlama'].get('perde_std')} | {p['duyulan']}", flush=True)
(cikti / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "ayar"}, "tarama": sonuc}, ensure_ascii=False, indent=1,
                                             default=seslendir.jsonla), encoding="utf-8")
print("TARAMA BİTTİ")
