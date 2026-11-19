#!/usr/bin/env python3
"""VoxCPM2 (openbmb/VoxCPM2, Apache-2.0) ile yarış cümlelerini seslendirir. Ayrı Python 3.12 ortamında çalışır.

Kullanım: python uret_voxcpm.py is.json cikti/yaris
Biçimler: voxcpm-ref (yalnız referans sesi), voxcpm-tam (referans sesi + metni), voxcpm-sapka (tam + şapkalı metin).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from voxcpm import VoxCPM

HERE = Path(__file__).resolve().parent
is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cikti = Path(sys.argv[2])
ref = is_["referans"]
print("cuda:", torch.cuda.is_available(), flush=True)
model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = model.tts_model.sample_rate
print("VoxCPM2 hazır, sr", sr, flush=True)
for bicim in ("voxcpm-ref", "voxcpm-tam", "voxcpm-sapka"):
    (cikti / bicim).mkdir(parents=True, exist_ok=True)
    for c in is_["cumleler"]:
        metin = c["okunus_sapka"] if bicim == "voxcpm-sapka" else c["okunus"]
        arg = {"reference_wav_path": str(HERE.parent / ref["yol"])}
        if bicim != "voxcpm-ref":
            arg.update(prompt_wav_path=str(HERE.parent / ref["yol"]), prompt_text=ref["metin"])
        t = time.time()
        torch.manual_seed(0)
        wav = model.generate(text=metin, cfg_value=2.0, inference_timesteps=10, **arg)
        sf.write(cikti / bicim / f"{c['id']}.wav", np.asarray(wav, dtype=np.float32), sr)
        print(f"{bicim} {c['id']} {len(wav) / sr:.1f} sn ses, {time.time() - t:.1f} sn", flush=True)
