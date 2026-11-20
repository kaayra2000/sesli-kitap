#!/usr/bin/env python3
"""
Daha canlı sabit ses referansı arar (VoxCPM ortamında, Python 3.12).

1. Aday üret: şu anki canlı referansın (D) sesiyle VoxCPM2'ye canlı / sıcak metinler okutulur (metin x cfg x tohum).
2. Ele: Whisper CER <= %2, temel sese (Piper Fahrettin) ECAPA benzerliği >= BENZERLIK_ALT (tını korunur).
3. Sırala: canlılık = perde oynaklığı (insan 90. yüzdeliğini aşmadan) + tempo değişkenliği; tonlama insan aralığında.
4. Sına: en iyi FINALIST aday referans olarak kullanılıp test cümleleri (düz + Osmanlıca) klonlanır; asıl ölçü budur.

Kullanım: python referans_ara.py is.json -> cikti/referans/<aday>.wav, cikti/referans/sinav/<aday>/<cümle>.wav, sonuc.json
"""
import json
import sys
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
METINLER = {
    "haber": seslendir.CANLI_METIN,
    "hikaye": "Hiç düşündünüz mü, bir kitap insanın hayatını nasıl değiştirir? Bugün size çok güzel bir hikâye "
              "anlatacağım. Hazırsanız, başlayalım!",
    "yolculuk": "Merhaba dostlar! Bugün birlikte çok keyifli bir yolculuğa çıkıyoruz. Sonunda ne bulacağımızı merak "
                "ediyor musunuz?",
}
CFG = (1.8, 2.2)
TOHUM = 6
BENZERLIK_ALT = 0.55
FINALIST = 4

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ayar = {**seslendir.VARSAYILAN, **is_.get("ayar", {})}
cikti = HERE / "cikti" / "referans"
(cikti / "sinav").mkdir(parents=True, exist_ok=True)
vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = vox.tts_model.sample_rate
hakem = seslendir.Hakem(ayar)
prof = {k: v for k, v in json.loads((HERE / "referans/insan_profil.json").read_text()).items() if not k.startswith("_")}
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": seslendir.DEV})


def gomme(x, s):
    x16 = seslendir.resample(x, s, 16000)
    with torch.no_grad():
        e = ecapa.encode_batch(torch.from_numpy(x16).unsqueeze(0).to(seslendir.DEV)).squeeze()
    return e / e.norm()


x, s = sf.read(TEMEL, dtype="float32")
temel_e = gomme(x, s)


def olc(y, metin):
    p = hakem.olc(y, sr, metin)
    o = tonlama.ozellikler(seslendir.resample(y, sr, 16000), p.pop("_kelimeler"), metin)
    return {"cer": p["whisper"]["cer"], "ctc": p["ctc_esit"]["cer"], "duyulan": p["duyulan"], "tonlama": o,
            "tonlama_sapma": tonlama.sapma(o, prof), "benzerlik": round(float(gomme(y, sr) @ temel_e), 3)}


adaylar = []
for ad, metin in METINLER.items():
    for cfg in CFG:
        for tohum in range(TOHUM):
            torch.manual_seed(tohum)
            y = seslendir.kirp(np.asarray(vox.generate(text=metin, prompt_wav_path=CANLI, prompt_text=seslendir.CANLI_METIN,
                                                       reference_wav_path=CANLI, cfg_value=cfg, inference_timesteps=10),
                                          dtype=np.float32), sr)
            p = olc(y, metin)
            o = p["tonlama"]
            canlilik = min(o.get("perde_std", 0), prof["perde_std"][2]) + 3 * o.get("hiz_cv", 0)
            kimlik = f"{ad}-cfg{cfg}-t{tohum}"
            gecer = p["cer"] <= 0.02 and p["benzerlik"] >= BENZERLIK_ALT and p["tonlama_sapma"] <= 0.2
            adaylar.append({"id": kimlik, "metin": metin, "canlilik": round(canlilik, 3), "gecer": gecer, **p})
            if gecer:
                sf.write(cikti / f"{kimlik}.wav", y / max(1e-6, np.abs(y).max()) * 0.9, sr)
            print(f"{kimlik:22} CER {p['cer']:.3f} benzerlik {p['benzerlik']:.2f} perde {o.get('perde_std')} "
                  f"tempo {o.get('hiz_cv')} canlılık {canlilik:.2f} {'GEÇER' if gecer else '-'}", flush=True)

finalist = sorted([a for a in adaylar if a["gecer"]], key=lambda a: -a["canlilik"])
# Her metinden en fazla iki aday: tek metne yığılmasın
secilen, sayac = [], {}
for a in finalist:
    m = a["id"].split("-")[0]
    if sayac.get(m, 0) < 2:
        secilen.append(a)
        sayac[m] = sayac.get(m, 0) + 1
    if len(secilen) == FINALIST:
        break

# Sınav: her finalist (ve şu anki canlı referans) referans olarak test cümlelerini klonlar
sinav = {}
for a in [{"id": "simdiki-canli", "metin": seslendir.CANLI_METIN, "yol": CANLI}] + \
         [{**a, "yol": str(cikti / f"{a['id']}.wav")} for a in secilen]:
    sinav[a["id"]] = {}
    (cikti / "sinav" / a["id"]).mkdir(exist_ok=True)
    for c in is_["parcalar"]:
        en_iyi = None
        for tohum in range(3):
            torch.manual_seed(tohum)
            y = seslendir.kirp(np.asarray(vox.generate(text=c["okunus"], prompt_wav_path=a["yol"], prompt_text=a["metin"],
                                                       reference_wav_path=a["yol"], cfg_value=2.0, inference_timesteps=10),
                                          dtype=np.float32), sr)
            p = olc(y, c["okunus"])
            k = (p["cer"] > 0.03 and p["ctc"] > 0.06, p["cer"] + 0.5 * p["ctc"], p["tonlama_sapma"])
            if en_iyi is None or k < en_iyi[0]:
                en_iyi = (k, y, p)
        _, y, p = en_iyi
        sf.write(cikti / "sinav" / a["id"] / f"{c['id']}.wav", y / max(1e-6, np.abs(y).max()) * 0.9, sr)
        sinav[a["id"]][c["id"]] = p
        print(f"SINAV {a['id']:22} {c['id']:10} CER {p['cer']:.3f} CTC {p['ctc']:.3f} benzerlik {p['benzerlik']:.2f} "
              f"tonlama {p['tonlama_sapma']:.2f} perde {p['tonlama'].get('perde_std')} | {p['duyulan']}", flush=True)
if (cikti.parent / "secilen").exists():
    pass
(HERE / "cikti" / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "referans"}, "adaylar": adaylar,
                                                       "finalist": [a["id"] for a in secilen], "sinav": sinav},
                                                      ensure_ascii=False, indent=1, default=seslendir.jsonla),
                                           encoding="utf-8")
print("REFERANS ARAMA BİTTİ", [a["id"] for a in secilen])
