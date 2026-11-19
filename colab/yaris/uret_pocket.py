#!/usr/bin/env python3
"""pocket-tts-tr (mevcut standart) ile yarış cümleleri; seslendir.py'deki Ses sınıfı, tek tohum, aday seçimi yok."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import seslendir  # noqa: E402

is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cikti = Path(sys.argv[2])
for bicim, ref in (("pocket-canli", "canli"), ("pocket-temel", "temel")):
    (cikti / bicim).mkdir(parents=True, exist_ok=True)
    ayar = {**seslendir.VARSAYILAN, "referans": ref}
    ses = seslendir.Ses(ayar, cikti)
    ses.state = ses.model.get_state_for_audio_prompt(
        str(HERE.parent / ("referans/referans-canli.wav" if ref == "canli" else "referans/referans-temel-ses.wav")))
    ses.model.temp = 0.5
    for c in is_["cumleler"]:
        x = ses.soyle(c["okunus"], 0)
        seslendir.wav_yaz(cikti / bicim / f"{c['id']}.wav", x, ses.sr)
        print(f"{bicim} {c['id']}", flush=True)
    del ses
