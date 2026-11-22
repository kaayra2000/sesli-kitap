#!/usr/bin/env python3
"""
İfade (duygu, tonlama, vurgu) ölçümü: seslendirmeden sonra ayrı ortamda çalışır, cikti/ifade.json yazar.

Ölçüler (parça başına):
- duygu: audEERING wav2vec2 MSP-Podcast boyutsal model (arousal = canlılık, dominance = kararlılık, valence = olumluluk,
  0-1). Lisans CC-BY-NC-SA 4.0: yalnız ölçüm için kullanılır, üretilen sese girmez.
- estetik: Meta Audiobox Aesthetics (CC-BY 4.0): CE içerik keyfi, CU yararlılık, PC karmaşıklık, PQ yapım kalitesi (1-10).
- prozodi (Praat/parselmouth): perde aralığı (yarım ton, %5-95), perde sapması, enerji sapması (dB), duraklama sıklığı ve
  süresi (kelime arası > 0.15 sn), kelime hızı değişkenliği.
- vurgu: kelime başına önem = z(perde tepe) + z(enerji) + z(harf başına süre) (Suni ve ark. 2017 dalgacık yöntemine
  yakın, sadeleştirilmiş). Önem sapması (karşıtlık) ve vurgulu kelime oranı (önem > 1.5).

Kullanım: python ifade_olc.py cikti            -> cikti/ifade.json (secilen/*.wav + sonuc.json kelime zamanları)
          python ifade_olc.py --insan cikti    -> cikti/ifade_insan.json (FLEURS tr insan okumaları + referans ses)
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn

DEV = "cuda" if torch.cuda.is_available() else "cpu"
HERE = Path(__file__).resolve().parent


def rs16(x, sr):
    import librosa
    x = x.mean(1) if x.ndim > 1 else x
    return librosa.resample(x.astype(np.float32), orig_sr=sr, target_sr=16000) if sr != 16000 else x.astype(np.float32)


class Duygu:
    ADI = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"

    def __init__(self):
        from transformers import Wav2Vec2Model, Wav2Vec2PreTrainedModel, Wav2Vec2Processor

        class Bas(nn.Module):
            def __init__(self, c):
                super().__init__()
                self.dense = nn.Linear(c.hidden_size, c.hidden_size)
                self.dropout = nn.Dropout(c.final_dropout)
                self.out_proj = nn.Linear(c.hidden_size, c.num_labels)

            def forward(self, x):
                return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))

        class Model(Wav2Vec2PreTrainedModel):
            def __init__(self, c):
                super().__init__(c)
                self.wav2vec2 = Wav2Vec2Model(c)
                self.classifier = Bas(c)
                self.post_init()

            def forward(self, x):
                h = self.wav2vec2(x)[0].mean(1)
                return self.classifier(h)

        self.proc = Wav2Vec2Processor.from_pretrained(self.ADI)
        self.model = Model.from_pretrained(self.ADI).to(DEV).eval()

    @torch.inference_mode()
    def __call__(self, x16):
        g = self.proc(x16, sampling_rate=16000, return_tensors="pt").input_values.to(DEV)
        a, d, v = self.model(g)[0].float().cpu().tolist()
        return {"canlilik": round(a, 3), "kararlilik": round(d, 3), "olumluluk": round(v, 3)}


class Estetik:
    def __init__(self):
        from audiobox_aesthetics.infer import initialize_predictor
        self.p = initialize_predictor()

    def __call__(self, x16):
        r = self.p.forward([{"path": torch.from_numpy(x16).unsqueeze(0), "sample_rate": 16000}])[0]
        return {k: round(float(v), 3) for k, v in r.items()}


def prozodi(x16, kelimeler):
    import parselmouth
    snd = parselmouth.Sound(x16, 16000)
    f0 = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400).selected_array["frequency"]
    t = np.arange(len(f0)) * 0.01 + 0.005
    v = f0 > 0
    sonuc = {}
    if v.sum() > 20:
        st = 12 * np.log2(f0[v] / np.median(f0[v]))
        sonuc["perde_aralik"] = round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2)
        sonuc["perde_sapma"] = round(float(st.std()), 2)
    en = snd.to_intensity(minimum_pitch=60, time_step=0.01)
    db = en.values[0]
    et = en.xs()
    if len(db) > 20:
        sonuc["enerji_sapma"] = round(float(db[db > db.max() - 40].std()), 2)
    if len(kelimeler) >= 3:
        # Duraklama enerjiden: Whisper kelime zamanları sessizliği kelimeye katıyor (iki nokta sonrası 0.48 sn sessizliği
        # 0.10 sn gösterdi). Ses tepe düzeyinin 40 dB altında 0.12 sn'den uzun iç bölümler sayılır.
        sessiz = db < (np.percentile(db, 95) - 40)
        konusma = np.where(~sessiz)[0]
        dur = []
        if len(konusma):
            i, bas = konusma[0], None
            for k in range(konusma[0], konusma[-1] + 1):
                if sessiz[k] and bas is None:
                    bas = k
                elif not sessiz[k] and bas is not None:
                    if (k - bas) * 0.01 >= 0.12:
                        dur.append((k - bas) * 0.01)
                    bas = None
        sonuc["duraklama_10kelime"] = round(10 * len(dur) / len(kelimeler), 2)
        sonuc["duraklama_ort"] = round(float(np.mean(dur)), 3) if dur else 0.0
        hiz = [(e - s) / max(1, len(w)) for w, s, e in kelimeler if e > s]
        sonuc["kelime_hiz_cv"] = round(float(np.std(hiz) / max(1e-6, np.mean(hiz))), 3)
        # vurgu
        oz = []
        for w, s, e in kelimeler:
            m = (t >= s) & (t <= e) & v
            me = (et >= s) & (et <= e)
            if m.sum() < 3 or me.sum() < 2:
                continue
            oz.append((float(12 * np.log2(f0[m].max() / np.median(f0[v]))), float(db[me].mean()),
                       (e - s) / max(1, len(w))))
        if len(oz) >= 4:
            o = np.array(oz)
            z = (o - o.mean(0)) / (o.std(0) + 1e-6)
            onem = z.sum(1)
            sonuc["vurgu_sapma"] = round(float(onem.std()), 3)
            sonuc["vurgulu_oran"] = round(float((onem > 1.5).mean()), 3)
            sonuc["vurgu_perde_sapma"] = round(float(o[:, 0].std()), 3)  # kelime tepe perdelerinin yayılımı
    return sonuc


def olc(araclar, x16, kelimeler):
    r = {**araclar["duygu"](x16), **prozodi(x16, kelimeler)}
    try:
        r.update(araclar["estetik"](x16))
    except Exception as e:  # noqa: BLE001
        r["estetik_hata"] = str(e)[:80]
    return r


def ozet(kayitlar):
    anahtarlar = sorted({k for r in kayitlar for k, v in r.items() if isinstance(v, (int, float))})
    return {k: [round(float(np.percentile([r[k] for r in kayitlar if k in r], q)), 3) for q in (10, 50, 90)]
            for k in anahtarlar if sum(k in r for r in kayitlar) >= 3}


def main():
    insan = sys.argv[1] == "--insan"
    cikti = Path(sys.argv[-1])
    araclar = {"duygu": Duygu(), "estetik": Estetik()}
    if insan:
        from faster_whisper import WhisperModel
        asr = WhisperModel("large-v3", device=DEV, compute_type="float16" if DEV == "cuda" else "int8")

        def kz(x16):
            seg, _ = asr.transcribe(x16, language="tr", word_timestamps=True, vad_filter=False)
            return [[w.word.strip(), w.start, w.end] for s in seg for w in (s.words or [])]
        import pandas as pd
        yol = Path("/tmp/fleurs-tr-test.parquet")
        if not yol.exists():
            urllib.request.urlretrieve("https://huggingface.co/api/datasets/google/fleurs/parquet/tr_tr/test/0.parquet", yol)
        df = pd.read_parquet(yol).sample(120, random_state=0)
        kayit = []
        for _, r in df.iterrows():
            x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
            x16 = rs16(x, sr)
            if 4 <= len(x16) / 16000 <= 20:
                kayit.append(olc(araclar, x16, kz(x16)))
        ref = {}
        for f in sorted((HERE / "referans").glob("kitap-sesi-*.wav")):
            x, sr = sf.read(f, dtype="float32")
            x16 = rs16(x, sr)
            ref[f.name] = olc(araclar, x16, kz(x16))
        (cikti / "ifade_insan.json").write_text(json.dumps({"fleurs": ozet(kayit), "fleurs_n": len(kayit),
                                                            "referans": ref}, ensure_ascii=False, indent=1))
        print("İNSAN İFADE ÖLÇÜLDÜ", len(kayit))
        return
    sonuc = json.loads((cikti / "sonuc.json").read_text(encoding="utf-8"))
    from faster_whisper import WhisperModel  # son ses (MFA düzeltmesi, perde vb. sonrası) yeniden yazıya dökülür
    asr = WhisperModel("large-v3", device=DEV, compute_type="float16" if DEV == "cuda" else "int8")
    out = {}
    for p in sonuc["parcalar"]:
        f = cikti / "secilen" / f"{p['id']}.wav"
        if not f.exists():
            continue
        x, sr = sf.read(f, dtype="float32")
        x16 = rs16(x, sr)
        seg, _ = asr.transcribe(x16, language="tr", beam_size=5, word_timestamps=True, vad_filter=False)
        seg = list(seg)
        kz = [[w.word.strip(), w.start, w.end] for s_ in seg for w in (s_.words or [])]
        out[p["id"]] = {**olc(araclar, x16, kz), "duyulan_son": "".join(s_.text for s_ in seg).strip()}
    (cikti / "ifade.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("İFADE ÖLÇÜLDÜ", len(out))


if __name__ == "__main__":
    main()
