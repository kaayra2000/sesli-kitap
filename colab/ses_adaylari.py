#!/usr/bin/env python3
"""
Maskot sesi adayları: Google FLEURS Türkçe (CC BY 4.0) bütün konuşmacıları ECAPA ile kümelenir; her konuşmacı için
perde (ortanca F0), perde oynaklığı, konuşma hızı ve kayıt temizliği ölçülür. Canlı, temiz ve tizliği farklı 8
konuşmacının gerçek kayıtları (sentez yok) 25-30 sn'lik dinleme dosyaları olarak çıkar; kullanıcı dinleyip seçer.

VoxCPM ortamında (speechbrain, pandas). Kullanım: python ses_adaylari.py is.json -> cikti/adaylar/*.wav, sonuc.json
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seslendir  # noqa: E402

URL = "https://huggingface.co/api/datasets/google/fleurs/parquet/tr_tr/{}/0.parquet"
KUME_ESIK = 0.62
EN_AZ_KAYIT = 6
ADAY = 8
HEDEF_SN = 28

cikti = HERE / "cikti" / "adaylar"
cikti.mkdir(parents=True, exist_ok=True)
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": seslendir.DEV})


def gomme(x16):
    with torch.no_grad():
        e = ecapa.encode_batch(torch.from_numpy(x16.astype(np.float32)).unsqueeze(0).to(seslendir.DEV)).squeeze()
    return (e / e.norm()).cpu().numpy()


def snr(x16):
    n = len(x16) // 320
    e = np.sort((x16[: n * 320].reshape(n, 320) ** 2).mean(1) + 1e-10)
    return float(10 * np.log10(e[-n // 10:].mean() / e[: n // 10].mean())) if n >= 20 else 0.0


kayitlar = []
for bolum in ("train", "validation", "test"):
    yol = Path(f"/tmp/fleurs-tr-{bolum}.parquet")
    if not yol.exists():
        urllib.request.urlretrieve(URL.format(bolum), yol)
    for _, r in pd.read_parquet(yol).iterrows():
        x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
        x = x.mean(1) if x.ndim > 1 else x
        x16 = seslendir.resample(x, sr, 16000)
        if not (3 <= len(x16) / 16000 <= 20):
            continue
        kayitlar.append({"id": f"{bolum}-{r['id']}", "x16": x16, "metin": str(r["raw_transcription"]).strip(),
                         "cins": int(r["gender"]) if str(r["gender"]).isdigit() else str(r["gender"]),
                         "e": gomme(x16), "snr": snr(x16)})
    print(f"{bolum}: toplam {len(kayitlar)} kayıt", flush=True)

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
print(f"{len(kumeler)} konuşmacı kümesi", flush=True)

ozet = []
for c in kumeler:
    if len(c["uye"]) < EN_AZ_KAYIT:
        continue
    m = c["m"] / np.linalg.norm(c["m"])
    uyeler = [u for u in sorted(c["uye"], key=lambda u: -(float(u["e"] @ m) + u["snr"] / 60)) if float(u["e"] @ m) >= 0.72]
    if len(uyeler) < 3:
        continue
    f0s, stds, hiz = [], [], []
    for u in uyeler[:8]:
        f0, v, _ = librosa.pyin(u["x16"], fmin=60, fmax=450, sr=16000, frame_length=1024, hop_length=160)
        f0 = f0[v & ~np.isnan(f0)]
        if len(f0) > 20:
            f0s.append(np.median(f0))
            stds.append(float((12 * np.log2(f0 / np.median(f0))).std()))
        hiz.append(len(u["metin"].replace(" ", "")) / (len(u["x16"]) / 16000))
    if not f0s:
        continue
    c.update(f0=float(np.median(f0s)), perde_std=float(np.median(stds)), hiz=float(np.median(hiz)),
             snr=float(np.median([u["snr"] for u in uyeler])), uyeler=uyeler,
             cins=max(set(u["cins"] for u in uyeler), key=[u["cins"] for u in uyeler].count))
    ozet.append(c)

# Canlılık ve temizlik puanı; çeşitlilik için tizlik aralıklarından seç (alçak, orta, yüksek)
for c in ozet:
    c["puan"] = c["perde_std"] + 0.05 * min(c["snr"], 60) + 0.1 * c["hiz"]
ozet.sort(key=lambda c: -c["puan"])
secilen, kovalar = [], {}
for c in ozet:
    kova = "alcak" if c["f0"] < 140 else ("orta" if c["f0"] < 210 else "yuksek")
    if kovalar.get(kova, 0) < 3 and c["snr"] >= 25:
        secilen.append(c)
        kovalar[kova] = kovalar.get(kova, 0) + 1
    if len(secilen) == ADAY:
        break

bilgi = []
for i, c in enumerate(sorted(secilen, key=lambda c: c["f0"]), 1):
    parca, metin, t = [], [], 0.0
    for u in c["uyeler"]:
        parca += [u["x16"], np.zeros(int(0.5 * 16000), np.float32)]
        metin.append(u["metin"])
        t += len(u["x16"]) / 16000
        if t >= HEDEF_SN:
            break
    ses = np.concatenate(parca)
    try:  # Arka plan gürültüsü (FLEURS stüdyo kaydı değil): spektral kapılama ile azaltılır
        import noisereduce as nr
        ses = nr.reduce_noise(y=ses, sr=16000, stationary=True, prop_decrease=0.85).astype(np.float32)
    except Exception as e:  # noqa: BLE001
        print("gürültü azaltılamadı:", e, flush=True)
    ses = ses / max(1e-6, np.abs(ses).max()) * 0.9
    ad = f"aday-{i}"
    sf.write(cikti / f"{ad}.wav", ses, 16000)
    bilgi.append({"ad": ad, "kayit_sayisi": len(c["uye"]), "cins": c["cins"], "f0_hz": round(c["f0"], 1),
                  "perde_std": round(c["perde_std"], 2), "hiz_harf_sn": round(c["hiz"], 1), "snr_db": round(c["snr"], 1),
                  "sure": round(t, 1), "metin": " ".join(metin), "kayitlar": [u["id"] for u in c["uyeler"]][:40]})
    print(f"{ad}: cins {c['cins']} f0 {c['f0']:.0f} Hz perde {c['perde_std']:.2f} hız {c['hiz']:.1f} snr {c['snr']:.0f} dB "
          f"({len(c['uye'])} kayıt)", flush=True)
(HERE / "cikti" / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "aday"}, "adaylar": bilgi}, ensure_ascii=False,
                                                      indent=1), encoding="utf-8")
print("ADAYLAR BİTTİ")
