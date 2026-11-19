#!/usr/bin/env python3
"""Chatterbox Multilingual (resemble-ai, MIT; Ağustos 2026'dan beri bakımı yapılmıyor) ile yarış cümleleri.
Ayrı Python 3.11 ortamında çalışır. Kullanım: python uret_chatterbox.py is.json cikti/yaris"""
import json
import sys
import time
from pathlib import Path

import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

HERE = Path(__file__).resolve().parent
is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cikti = Path(sys.argv[2]) / "chatterbox"
cikti.mkdir(parents=True, exist_ok=True)
try:
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
except TypeError:
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
for c in is_["cumleler"]:
    t = time.time()
    torch.manual_seed(0)
    wav = model.generate(c["okunus"], language_id="tr", audio_prompt_path=str(HERE.parent / is_["referans"]["yol"]))
    ta.save(str(cikti / f"{c['id']}.wav"), wav.cpu() if hasattr(wav, "cpu") else wav, model.sr)
    print(f"chatterbox {c['id']} {time.time() - t:.1f} sn", flush=True)
