#!/usr/bin/env python3
"""
VoxCPM2 ses tasarımı: kimsenin sesi kopyalanmadan, tarifle (parantez içinde) yeni bir ses üretilir. Doğal ve
profesyonel anlatıcı tarzları denenir; her tarif için birkaç tohum, en doğru okunan iki aday dinlemeye çıkar.
Beğenilen klip sonra sabit ses referansı yapılır (tam klon).

VoxCPM ortamında. Kullanım: python ses_tasarimi.py is.json -> cikti/tasarim/<tarz>-<tohum>.wav, sonuc.json
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

TARZLAR = {
    "haber-spikeri": "A professional Turkish male news anchor in his thirties, clear, confident and warm voice, natural "
                     "conversational delivery, steady pace, studio quality recording",
    "radyo-sunucusu": "A friendly professional Turkish male radio host, energetic, warm and smiling voice, natural and "
                      "smooth delivery, studio microphone",
    "maskot": "A young Turkish male voice actor with a bright, cheerful and friendly voice, lively and expressive like "
              "an animated character, professional studio recording",
    "anlatici": "A calm professional Turkish male narrator, warm medium-low voice, natural unhurried pace, intimate "
                "audiobook narration, studio quality",
}
METIN = ("Merhaba, ben Cezerî. Bugün size yeni sistemimizi anlatacağım. Hazırsanız birlikte bakalım; "
         "göreceksiniz, çok kolay!")
TOHUM = 4
CIKAR = 2

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ayar = {**seslendir.VARSAYILAN, **is_.get("ayar", {})}
cikti = HERE / "cikti" / "tasarim"
cikti.mkdir(parents=True, exist_ok=True)
vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = vox.tts_model.sample_rate
hakem = seslendir.Hakem(ayar)
prof = {k: v for k, v in json.loads((HERE / "referans/insan_profil.json").read_text()).items() if not k.startswith("_")}
okunus = METIN.replace("î", "i")
sonuc = {}
for tarz, tarif in TARZLAR.items():
    adaylar = []
    for tohum in range(TOHUM):
        torch.manual_seed(tohum)
        y = seslendir.kirp(np.asarray(vox.generate(text=f"({tarif}){okunus}", cfg_value=2.0, inference_timesteps=10),
                                      dtype=np.float32), sr)
        p = hakem.olc(y, sr, okunus)
        t = tonlama.ozellikler(seslendir.resample(y, sr, 16000), p.pop("_kelimeler"), okunus)
        p.update(tonlama=t, tonlama_sapma=tonlama.sapma(t, prof), tohum=tohum)
        adaylar.append((p, y))
        print(f"{tarz:15} tohum {tohum} CER {p['whisper']['cer']:.3f} CTC {p['ctc_esit']['cer']:.3f} perde "
              f"{t.get('perde_std')} MOS {p['mos']:.2f} | {p['duyulan']}", flush=True)
    adaylar.sort(key=lambda a: (a[0]["whisper"]["cer"] + 0.5 * a[0]["ctc_esit"]["cer"], a[0]["tonlama_sapma"]))
    sonuc[tarz] = []
    for p, y in adaylar[:CIKAR]:
        ad = f"{tarz}-t{p['tohum']}"
        sf.write(cikti / f"{ad}.wav", y / max(1e-6, np.abs(y).max()) * 0.9, sr)
        sonuc[tarz].append({"ad": ad, "tarif": tarif, "metin": METIN, **{k: v for k, v in p.items() if k != "tonlama"}})
(HERE / "cikti" / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "tasarim"}, "tasarim": sonuc}, ensure_ascii=False,
                                                      indent=1, default=seslendir.jsonla), encoding="utf-8")
print("TASARIM BİTTİ")
