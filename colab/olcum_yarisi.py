"""Doğallık ölçüm araçları yarışı: klasördeki her sesi bütün adaylarla puanlar, CSV'ye yazar.

Kullanım (Colab, GPU): python3 olcum_yarisi.py <klip-klasörü> <çıktı.csv>
Her araç kendi try bloğunda çalışır; kurulamayan ya da hata veren araç sütunsuz kalır, diğerleri sürer.
Sonuç, kullanıcının kulak testi puanlarıyla (Spearman) karşılaştırılır: video/olcum_karsilastir.py.
"""
import csv
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

DEV = "cuda" if torch.cuda.is_available() else "cpu"
klasor, cikti = Path(sys.argv[1]), Path(sys.argv[2])
dosyalar = sorted(klasor.glob("*.mp3")) + sorted(klasor.glob("*.wav"))


def oku16(f):
    """Sesi 16 kHz mono float32 olarak okur (ffmpeg ile)."""
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, dtype=np.float32).copy()


def pip(*paket):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *paket], check=False)


sesler = {f.stem: oku16(f) for f in dosyalar}
puan = {k: {} for k in sesler}


def calistir(ad, fn):
    try:
        fn()
        print(f"[tamam] {ad}", flush=True)
    except Exception:  # noqa: BLE001
        print(f"[HATA] {ad}\n{traceback.format_exc()[-1500:]}", flush=True)


def utmos_v1():
    from huggingface_hub import hf_hub_download
    m = torch.jit.load(hf_hub_download("balacoon/utmos", "utmos.jit"), map_location=DEV).eval()
    with torch.inference_mode():
        for k, x in sesler.items():
            puan[k]["utmos_v1"] = float(m(torch.from_numpy(x).unsqueeze(0).to(DEV)).item())


def utmos_v2():
    pip("git+https://github.com/sarulab-speech/UTMOSv2.git")
    import utmosv2
    m = utmosv2.create_model(pretrained=True, device=DEV)
    for k, f in zip(sesler, dosyalar):
        tmp = f"/tmp/{k}.wav"
        sf.write(tmp, sesler[k], 16000)
        puan[k]["utmos_v2"] = float(m.predict(input_path=tmp))


def dnsmos():
    pip("speechmos")
    from speechmos import dnsmos as d
    for k, x in sesler.items():
        r = d.run(x / max(1e-6, np.abs(x).max()), sr=16000)
        puan[k]["dnsmos_ovrl"] = float(r["ovrl_mos"])
        puan[k]["dnsmos_sig"] = float(r["sig_mos"])
        puan[k]["dnsmos_p808"] = float(r["p808_mos"])


def nisqa():
    pip("torchmetrics>=1.6", "librosa")
    from torchmetrics.functional.audio.nisqa import non_intrusive_speech_quality_assessment as n
    for k, x in sesler.items():
        r = n(torch.from_numpy(x), 16000)
        puan[k]["nisqa_mos"], puan[k]["nisqa_noi"], puan[k]["nisqa_dis"], puan[k]["nisqa_col"], puan[k]["nisqa_loud"] = \
            [float(v) for v in r]


def distill_mos():
    pip("distillmos")
    import distillmos
    m = distillmos.ConvTransformerSQAModel().to(DEV).eval()
    with torch.inference_mode():
        for k, x in sesler.items():
            puan[k]["distill_mos"] = float(m(torch.from_numpy(x).unsqueeze(0).to(DEV)).item())


def audiobox():
    pip("audiobox_aesthetics")
    from audiobox_aesthetics.infer import initialize_predictor
    m = initialize_predictor()
    for k, x in sesler.items():
        r = m.forward([{"path": torch.from_numpy(x).unsqueeze(0), "sample_rate": 16000}])[0]
        for a in ("CE", "CU", "PC", "PQ"):
            puan[k][f"audiobox_{a.lower()}"] = float(r[a])


def scoreq():
    pip("scoreq")
    import scoreq
    m = scoreq.Scoreq(data_domain="synthetic", mode="nr")
    for k in sesler:
        tmp = f"/tmp/{k}.wav"
        sf.write(tmp, sesler[k], 16000)
        puan[k]["scoreq"] = float(m.predict(test_path=tmp, ref_path=None))


def squim():
    import torchaudio
    m = torchaudio.pipelines.SQUIM_OBJECTIVE.get_model().to(DEV).eval()
    with torch.inference_mode():
        for k, x in sesler.items():
            stoi, pesq, sisdr = m(torch.from_numpy(x).unsqueeze(0).to(DEV))
            puan[k]["squim_pesq"], puan[k]["squim_stoi"] = float(pesq), float(stoi)


for ad, fn in [("UTMOS v1 (şimdiki)", utmos_v1), ("UTMOSv2", utmos_v2), ("DNSMOS", dnsmos), ("NISQA", nisqa),
               ("Distill-MOS", distill_mos), ("Audiobox Aesthetics", audiobox), ("SCOREQ", scoreq), ("SQUIM", squim)]:
    calistir(ad, fn)

sutun = sorted({s for p in puan.values() for s in p})
with open(cikti, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["klip", *sutun])
    for k in sorted(puan):
        w.writerow([k, *[round(puan[k].get(s, float("nan")), 4) for s in sutun]])
print("SONUÇ", cikti, len(puan), "klip", len(sutun), "ölçüm:", ", ".join(sutun))
