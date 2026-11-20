#!/usr/bin/env python3
"""
Gerçek insan sesinden uzun referans: Google FLEURS Türkçe (CC BY 4.0) erkek kayıtları ECAPA ses kimliğine göre
kümelenir, her küme bir konuşmacı sayılır. Kaydı çok olan kümeler arasından temel sese (Fahrettin) en yakın olanların
temiz kayıtları birleştirilip 30 ve 60 sn'lik referanslar yapılır; VoxCPM2 bu referanslarla test cümlelerini okur.

VoxCPM ortamında (Python 3.12). Kullanım: python gercek_ses.py is.json
Atıf: FLEURS (Conneau vd., 2022), CC BY 4.0.
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seslendir  # noqa: E402
import tonlama  # noqa: E402
from voxcpm import VoxCPM  # noqa: E402

URL = "https://huggingface.co/api/datasets/google/fleurs/parquet/tr_tr/{}/0.parquet"
KUME_ESIK = 0.62       # aynı konuşmacı sayılacak en düşük ECAPA kosinüs benzerliği (ortalamaya göre)
EN_AZ_KAYIT = 12
SURELER = (30, 60)
ADAY_KUME = 3

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ayar = {**seslendir.VARSAYILAN, **is_.get("ayar", {})}
cikti = HERE / "cikti" / "gercek"
cikti.mkdir(parents=True, exist_ok=True)

from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": seslendir.DEV})


def gomme(x16):
    with torch.no_grad():
        e = ecapa.encode_batch(torch.from_numpy(x16.astype(np.float32)).unsqueeze(0).to(seslendir.DEV)).squeeze()
    return (e / e.norm()).cpu().numpy()


def snr(x16):
    """Kaba gürültü tahmini: 20 ms pencerelerin en sessiz %10'u ile en yüksek %10'u arasındaki fark (dB)."""
    n = len(x16) // 320
    if n < 20:
        return 0.0
    e = np.sort((x16[: n * 320].reshape(n, 320) ** 2).mean(1) + 1e-10)
    return float(10 * np.log10(e[-n // 10:].mean() / e[: n // 10].mean()))


kayitlar = []
for bolum in ("train", "validation", "test"):
    yol = Path(f"/tmp/fleurs-tr-{bolum}.parquet")
    if not yol.exists():
        urllib.request.urlretrieve(URL.format(bolum), yol)
    df = pd.read_parquet(yol)
    df = df[df["gender"] == 0] if df["gender"].dtype != object else df[df["gender"].astype(str).str.lower().isin(["0", "male"])]
    for _, r in df.iterrows():
        x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
        x = x.mean(1) if x.ndim > 1 else x
        x16 = seslendir.resample(x, sr, 16000)
        if not (3 <= len(x16) / 16000 <= 20):
            continue
        kayitlar.append({"id": f"{bolum}-{r['id']}", "x16": x16, "metin": str(r["raw_transcription"]).strip(),
                         "e": gomme(x16), "snr": snr(x16)})
    print(f"{bolum}: {len(kayitlar)} erkek kayıt", flush=True)

# Açgözlü kümeleme: her kayıt en yakın küme merkezine (benzerlik >= eşik) ya da yeni kümeye
kumeler = []
for k in sorted(kayitlar, key=lambda k: -k["snr"]):
    if kumeler:
        merkez = np.stack([c["m"] / np.linalg.norm(c["m"]) for c in kumeler])
        b = merkez @ k["e"]
        i = int(b.argmax())
        if b[i] >= KUME_ESIK:
            kumeler[i]["uye"].append(k)
            kumeler[i]["m"] = kumeler[i]["m"] + k["e"]
            continue
    kumeler.append({"uye": [k], "m": k["e"].copy()})
x, s = sf.read(str(HERE / "referans/referans-temel-ses.wav"), dtype="float32")
temel = gomme(seslendir.resample(x, s, 16000))
x, s = sf.read(str(HERE / "referans/referans-canli.wav"), dtype="float32")
canli = gomme(seslendir.resample(x, s, 16000))
buyuk = [c for c in kumeler if len(c["uye"]) >= EN_AZ_KAYIT]
for c in buyuk:
    m = c["m"] / np.linalg.norm(c["m"])
    c["temel"], c["canli"] = float(m @ temel), float(m @ canli)
    c["snr"] = float(np.median([u["snr"] for u in c["uye"]]))
buyuk.sort(key=lambda c: -(c["temel"] + c["canli"]))
print(f"{len(kumeler)} küme, {len(buyuk)} büyük küme", flush=True)
for i, c in enumerate(buyuk[:8]):
    print(f"küme {i}: {len(c['uye'])} kayıt, {sum(len(u['x16']) for u in c['uye']) / 16000:.0f} sn, temel {c['temel']:.2f}, "
          f"canlı {c['canli']:.2f}, snr {c['snr']:.1f} dB", flush=True)

vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = vox.tts_model.sample_rate
hakem = seslendir.Hakem(ayar)
prof = {k: v for k, v in json.loads((HERE / "referans/insan_profil.json").read_text()).items() if not k.startswith("_")}
sonuc = {"kumeler": [], "sinav": {}}
for ki, c in enumerate(buyuk[:ADAY_KUME]):
    # Kendi merkezine en yakın (kesin aynı kişi) ve en temiz kayıtlar
    m = c["m"] / np.linalg.norm(c["m"])
    uyeler = sorted(c["uye"], key=lambda u: -(float(u["e"] @ m) + u["snr"] / 60))
    for hedef in SURELER:
        parca, metin, toplam = [], [], 0.0
        for u in uyeler:
            if float(u["e"] @ m) < 0.7:
                continue
            parca += [u["x16"], np.zeros(int(0.4 * 16000), np.float32)]
            metin.append(u["metin"])
            toplam += len(u["x16"]) / 16000
            if toplam >= hedef:
                break
        ad = f"kume{ki}-{hedef}sn"
        ref = np.concatenate(parca)
        ref = ref / max(1e-6, np.abs(ref).max()) * 0.9
        ref_yol = cikti / f"{ad}.wav"
        sf.write(ref_yol, ref, 16000)
        ref_metin = " ".join(metin)
        sonuc["kumeler"].append({"ad": ad, "kayit": len(metin), "sure": round(toplam, 1), "temel": round(c["temel"], 3),
                                 "canli": round(c["canli"], 3), "metin": ref_metin})
        sonuc["sinav"][ad] = {}
        (cikti / "sinav" / ad).mkdir(parents=True, exist_ok=True)
        for p in is_["parcalar"]:
            en_iyi = None
            for tohum in range(3):
                torch.manual_seed(tohum)
                y = seslendir.kirp(np.asarray(vox.generate(text=p["okunus"], prompt_wav_path=str(ref_yol), prompt_text=ref_metin,
                                                           reference_wav_path=str(ref_yol), cfg_value=2.0,
                                                           inference_timesteps=10), dtype=np.float32), sr)
                o = hakem.olc(y, sr, p["okunus"])
                t = tonlama.ozellikler(seslendir.resample(y, sr, 16000), o.pop("_kelimeler"), p["okunus"])
                o.update(tonlama_sapma=tonlama.sapma(t, prof), perde=t.get("perde_std"),
                         benzerlik_ref=round(float(gomme(seslendir.resample(y, sr, 16000)) @ m), 3))
                k = (seslendir.yanlis(o, ayar), o["whisper"]["cer"] + 0.5 * o["ctc_esit"]["cer"], o["tonlama_sapma"])
                if en_iyi is None or k < en_iyi[0]:
                    en_iyi = (k, y, o)
            _, y, o = en_iyi
            sf.write(cikti / "sinav" / ad / f"{p['id']}.wav", y / max(1e-6, np.abs(y).max()) * 0.9, sr)
            sonuc["sinav"][ad][p["id"]] = o
            print(f"SINAV {ad:14} {p['id']:10} CER {o['whisper']['cer']:.3f} CTC {o['ctc_esit']['cer']:.3f} "
                  f"ref benzerlik {o['benzerlik_ref']:.2f} tonlama {o['tonlama_sapma']:.2f} perde {o['perde']} "
                  f"| {o['duyulan']}", flush=True)
(HERE / "cikti" / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "gercek"}, **sonuc}, ensure_ascii=False,
                                                      indent=1, default=seslendir.jsonla), encoding="utf-8")
print("GERÇEK SES BİTTİ")
