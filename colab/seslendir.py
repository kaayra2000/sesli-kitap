#!/usr/bin/env python3
"""
Colab'de (T4 GPU) çalışır: iş paketindeki parçaları pocket-tts-tr ile seslendirir, her adayı üç hakemle ölçer, en iyi
adayı seçer ve raporlar.

Hakemler:
  - Whisper large-v3 (faster-whisper, fp16): duyulan metin, karakter hatası (CER). Metin ipucu verilmez.
  - wav2vec2 CTC (Türkçe, dil modeli yok, açgözlü çözme): Whisper kulağın duyduğunu günümüz imlâsına düzeltir
    (içün -> için); CTC harfi harfine yazar, okunuşun metne sadakatini o ölçer. Whisper ve hedef karşılaştırmadan
    önce aynı günümüz biçimine getirilir (esitle), CTC ham metinle karşılaştırılır.
  - UTMOS22: doğallık tahmini (1-5).
Ayrıca: cümle sonunda ses artığı (kuyruk), cümle içinde uzun sessizlik (takılma), konuşma hızı, kırpılma.

Kullanım: python3 seslendir.py is.json  (çıktı: cikti/)
is.json: {"konu", "mod": "test|ornek", "ayar": {...}, "parcalar": [{"id", "metin", "okunus", "ara"}]}
"""

import json
import math
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from olcum import hata, normalize  # noqa: E402
import tonlama  # noqa: E402
import uzatma  # noqa: E402

POCKET_REPO = "kaanhgunay/pocket-tts-tr"
SR_OUT = 48000
DEV = "cuda" if torch.cuda.is_available() else "cpu"
VARSAYILAN = {
    "aday": 6,             # en çok aday
    "erken_dur": 2,        # bu kadar temiz aday olunca dur
    "sicaklik": 0.5,
    "motor": "pocket",     # pocket (pocket-tts-tr) | voxcpm (VoxCPM2, standart 2026-11-19)
    "referans": "canli",   # canli | temel | sakin | referans/<dosya>.wav
    "hakem": "large-v3",
    "ctc": ["mpoyraz/wav2vec2-xls-r-300m-cv8-turkish", "m3hrdadfi/wav2vec2-large-xlsr-turkish"],
    "kuyruk_sinir": 0.35,
    "sessizlik_sinir": 0.9,
    "cer_sinir": 0.03,
    "ctc_sinir": 0.06,
    "kurtarma_aday": 8,       # hâlâ yanlış / kuyruklu cümleye düşük sıcaklıkta ek aday
    "kurtarma_sicaklik": 0.35,
    "bolum_kelime": 14,    # pocket-tts sınırı 50 jeton; şapkalı Osmanlıca kelimeler çok jeton tutar
    "bolum_ara": 0.18,
    "uzatma": 1.0,         # uzun ünlü (â î û) seste bu oranda uzatılır (uzatma.py); 1 = kapalı
}
SAKIN_METIN = ("Bilesin ki gönül, sevdiğinin yanında huzur bulur. Bu yol sabır ve muhabbet yoludur. "
               "Acele etmeden, adım adım yürünür.")
INSAN_SON_KELIME = 1.8   # insan okuyucuda düz cümle son kelime düşüşü (yarım ton); insan_profil.json varsa oradan


def log(*a):
    print(*a, flush=True)


def bol(metin: str, en_cok: int) -> list[str]:
    """en_cok kelimeden uzun metni ortaya en yakın virgülden (yoksa "ve"den, yoksa ortadan) böler."""
    w = metin.split()
    if len(w) <= en_cok:
        return [metin]
    orta = len(w) / 2
    adaylar = [i for i in range(3, len(w) - 2) if w[i - 1].endswith((",", ";", ":"))]
    adaylar = adaylar or [i for i in range(3, len(w) - 2) if w[i] in ("ve", "ile", "ki")]
    i = min(adaylar, key=lambda k: abs(k - orta)) if adaylar else round(orta)
    return bol(" ".join(w[:i]), en_cok) + bol(" ".join(w[i:]), en_cok)


def resample(x: np.ndarray, sr: int, hedef: int) -> np.ndarray:
    """torchaudio ile yeniden örnekleme (her aday için ffmpeg süreci açmak Colab'in 2 çekirdeğini dolduruyordu)."""
    import torchaudio.functional as F
    if sr == hedef:
        return x.astype(np.float32)
    return F.resample(torch.from_numpy(x.astype(np.float32)), sr, hedef).numpy()


def kirp(x: np.ndarray, sr: int, esik_db: float = -45) -> np.ndarray:
    """Baştaki ve sondaki sessizliği atar: 10 ms pencerelerde tepe -45 dB altındaysa sessiz."""
    pencere = max(1, sr // 100)
    n = len(x) // pencere
    if n == 0:
        return x
    tepe = np.abs(x[: n * pencere]).reshape(n, pencere).max(1)
    ses = np.where(tepe > 10 ** (esik_db / 20))[0]
    if len(ses) == 0:
        return x
    y = x[ses[0] * pencere: (ses[-1] + 1) * pencere]
    return y if len(y) > sr * 0.2 else x


def wav_yaz(yol: Path, x: np.ndarray, sr: int) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wav_oku(yol: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(yol)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768, w.getframerate()


TEMEL_METIN = ("Birimler ve yöneticiler artık düzenli kartlarda, net bir ağaç yapısında görünür. "
               "Bir isme ya da fotoğrafa tıkladığınızda, sağda kişi kartı açılır.")


CANLI_METIN = "Size harika bir haberim var! Yeni sistemimiz hazır. Hadi, birlikte keşfedelim!"


class VoxSes:
    """VoxCPM2 (openbmb/VoxCPM2, Apache-2.0), standarttaki sabit ses: canlı referans (temel ses Piper Fahrettin'in
    tınısında canlı okunmuş klip, standartlar tasarim/ses/referans-canli.wav) tam klon. 2026-11-20 kör dinlemede Piper'ın
    düz referansından (robotik) daha insansı bulundu.

    Referans klip + metni + tını referansı (prompt_wav_path, prompt_text, reference_wav_path); cfg 2.0, 10 adım.
    Sıcaklık yoktur; adaylar tohumla çeşitlenir. Kurtarma geçişinde (model.temp düşürülünce) cfg 2.5 kullanılır.
    """

    def __init__(self, ayar: dict, cikti: Path):
        from voxcpm import VoxCPM

        # Referans klip gürültülüyse (gerçek kayıt) VoxCPM'in ZipEnhancer temizleyicisi referansı temizler.
        self.denoise = bool(ayar.get("vox_denoise", False))
        try:
            self.vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=self.denoise)
        except Exception as e:  # noqa: BLE001
            log(f"temizleyici yüklenemedi ({e}); referans temizlenmeden kullanılacak")
            self.denoise = False
            self.vox = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
        self.sr = self.vox.tts_model.sample_rate
        self.ayar = ayar
        self.model = self  # seslendir döngüsü model.temp'e yazar
        self.temp = ayar["sicaklik"]
        self.ref = str(HERE / "referans" / ayar.get("vox_referans", "referans-canli.wav"))
        self.cikti = cikti
        self.etkin = "openbmb/VoxCPM2"
        self.ref_metin = ayar.get("vox_referans_metin", CANLI_METIN) or self.yaziya_dok(self.ref)
        self.refler = {Path(self.ref).name: self.ref_metin, **ayar.get("vox_referans_metinleri", {})}

    def yaziya_dok(self, yol: str) -> str:
        """Metni bilinmeyen referans kaydı Whisper ile yazıya dökülür."""
        import soundfile as sf
        from faster_whisper import WhisperModel
        w = WhisperModel("large-v3", device=DEV, compute_type="float16" if DEV == "cuda" else "int8")
        x, xsr = sf.read(yol, dtype="float32")  # PyAV sürümü faster-whisper ile uyumsuz: ses numpy verilir
        x = x.mean(1) if x.ndim > 1 else x
        seg, _ = w.transcribe(resample(x, xsr, 16000), language="tr", beam_size=5)
        metin = " ".join(s.text.strip() for s in seg)
        del w
        log(f"referans metni (Whisper) {Path(yol).name}: {metin}")
        with open(self.cikti / "referans_metin.txt", "a", encoding="utf-8") as f:
            f.write(f"{Path(yol).name}\t{metin}\n")
        return metin

    def referans_kur(self, hakem: "Hakem") -> str:
        return self.ref + " (VoxCPM2 tam klon)"

    def model_al(self, kimlik: str):
        """VoxCPM2 tabanı ya da ince ayarlı türevi (ör. Trendyol/Trendyol-TTS: VoxCPM2 + 20 sa Türkçe LoRA, MIT).
        Bellekte tek model tutulur (T4 15 GB iki modeli sığdırmıyor): başka model istenince öncekisi boşaltılır."""
        if kimlik == self.etkin:
            return self.vox
        import gc
        from voxcpm import VoxCPM
        self.vox = None
        gc.collect()
        torch.cuda.empty_cache()
        self.vox = VoxCPM.from_pretrained(kimlik, load_denoiser=False)
        self.etkin = kimlik
        log(f"model yüklendi: {kimlik}")
        return self.vox

    def soyle(self, metin: str, tohum: int, referans: str | None = None, mod: str | None = None,
              stil: str | None = None, model: str | None = None, cfg_d: float | None = None,
              adim_d: int | None = None) -> np.ndarray:
        """referans: parçaya özel referans dosyası. mod: "tam" (referans + metni; ritim de kopyalanır) ya da "kontrollu"
        (yalnız tını referansı; stil tarifi duyguyu/üslubu yönlendirir). stil: parantez içi üslup tarifi."""
        mod = mod or self.ayar.get("vox_mod", "tam")
        stil = stil if stil is not None else self.ayar.get("vox_stil", "")
        torch.manual_seed(tohum)
        np.random.seed(tohum)
        ref = str(HERE / "referans" / referans) if referans else self.ref
        if Path(ref).name not in self.refler:
            self.refler[Path(ref).name] = self.yaziya_dok(ref)
        ref_metin = self.refler[Path(ref).name]
        cfg = 2.5 if self.temp < self.ayar["sicaklik"] else float(cfg_d or self.ayar.get("vox_cfg", 2.0))
        adim = int(adim_d or self.ayar.get("vox_adim", 10))
        vox = self.model_al(model or self.ayar.get("vox_model", "openbmb/VoxCPM2"))
        parcalar = []
        bolumler = bol(metin, self.ayar["bolum_kelime"])
        iki_nokta = float(self.ayar.get("iki_nokta_ara", 0) or 0)
        if iki_nokta > 0:  # iki nokta üst üsteden sonra gerçek duraklama: ayrı üretilip sessizlikle birleştirilir
            bolumler = [b for parca in bolumler for b in re.split(r"(?<=:)\s+", parca) if b.strip()]
        for k, bolum in enumerate(bolumler):
            if k:
                ara = iki_nokta if iki_nokta > 0 and bolumler[k - 1].rstrip().endswith(":") else self.ayar["bolum_ara"]
                parcalar.append(np.zeros(int(ara * self.sr), np.float32))
            ek = {"prompt_wav_path": ref, "prompt_text": ref_metin} if mod == "tam" else {}
            x = vox.generate(text=f"({stil}){bolum}" if stil else bolum, **ek,
                                  reference_wav_path=ref, cfg_value=cfg, inference_timesteps=adim,
                                  **({"denoise": True} if self.denoise else {}))
            parcalar.append(kirp(np.asarray(x, dtype=np.float32), self.sr))
        return np.concatenate(parcalar)


class Ses:
    def __init__(self, ayar: dict, cikti: Path):
        from huggingface_hub import snapshot_download
        from pocket_tts import TTSModel

        repo = Path(snapshot_download(POCKET_REPO))
        config = Path("/tmp/pocket-tts-tr.yaml")
        text = (repo / "config.yaml").read_text(encoding="utf-8")
        # Yayımlanan config olmayan bir sürüm etiketini gösteriyor; indirilen dosyalar kullanılır.
        config.write_text(re.sub(rf"hf://{POCKET_REPO}/([^@\s\"']+)@[\w.-]+", lambda m: str(repo / m.group(1)), text),
                          encoding="utf-8")
        self.model = TTSModel.load_model(config=str(config))
        if DEV != "cpu":
            self.model.to(DEV)
        log("pocket-tts cihazı:", next(self.model.parameters()).device)
        self.sr = self.model.sample_rate
        self.ayar = ayar
        self.cikti = cikti
        self.state = None

    def referans_kur(self, hakem: "Hakem") -> str:
        ref = self.ayar["referans"]
        yol = {"canli": HERE / "referans/referans-canli.wav", "temel": HERE / "referans/referans-temel-ses.wav",
               "sakin": HERE / "referans/referans-sakin.wav"}.get(ref, HERE / ref)
        if ref == "sakin" and not yol.exists():
            yol = self.sakin_uret(hakem)
        self.state = self.model.get_state_for_audio_prompt(str(yol))
        self.model.temp = self.ayar["sicaklik"]
        return str(yol)

    def sakin_uret(self, hakem: "Hakem") -> Path:
        """Sakin anlatım referansı: temel sesle SAKIN_METIN, 12 tohum. Doğru okunanlar (CER <= %2) arasından
        tonlaması insana en yakın olan seçilir: cümle sonu eğimi insan ortancasına yakın, perde oynaklığı 2.4-8 yarım ton."""
        self.state = self.model.get_state_for_audio_prompt(str(HERE / "referans/referans-temel-ses.wav"))
        self.model.temp = 0.5
        en_iyi = None
        for tohum in range(12):
            x = self.soyle(SAKIN_METIN, tohum)
            p = hakem.olc(x, self.sr, SAKIN_METIN)
            t = tonlama.ozellikler(resample(x, self.sr, 16000), p.pop("_kelimeler"), SAKIN_METIN)
            sapma = abs(t.get("son_kelime", 6) - INSAN_SON_KELIME) / 2 + (0 if 2.4 <= t.get("perde_std", 0) <= 8 else 2)
            log(f"sakin referans tohum {tohum}: CER {p['whisper']['cer']:.3f} son kelime {t.get('son_kelime')} "
                f"perde {t.get('perde_std')} sapma {sapma:.2f}")
            anahtar = (p["whisper"]["cer"] > 0.02, sapma)
            if en_iyi is None or anahtar < en_iyi[0]:
                en_iyi = (anahtar, x)
        yol = self.cikti / "referans-sakin.wav"
        wav_yaz(yol, en_iyi[1], self.sr)
        return yol

    def soyle(self, metin: str, tohum: int, referans: str | None = None, mod: str | None = None,
              stil: str | None = None, model=None, cfg_d=None, adim_d=None) -> np.ndarray:
        """pocket-tts 50 jetondan uzun parçada kelime atlayabilir; uzun cümle virgülden bölünüp kısa araya birleştirilir."""
        torch.manual_seed(tohum)
        parcalar = []
        bolumler = bol(metin, self.ayar["bolum_kelime"])
        iki_nokta = float(self.ayar.get("iki_nokta_ara", 0) or 0)
        if iki_nokta > 0:  # iki nokta üst üsteden sonra gerçek duraklama: ayrı üretilip sessizlikle birleştirilir
            bolumler = [b for parca in bolumler for b in re.split(r"(?<=:)\s+", parca) if b.strip()]
        for k, bolum in enumerate(bolumler):
            if k:
                ara = iki_nokta if iki_nokta > 0 and bolumler[k - 1].rstrip().endswith(":") else self.ayar["bolum_ara"]
                parcalar.append(np.zeros(int(ara * self.sr), np.float32))
            x = self.model.generate_audio(self.state, bolum).float().cpu().numpy().squeeze()
            parcalar.append(kirp(x, self.sr))
        return np.concatenate(parcalar)


class Hakem:
    def __init__(self, ayar: dict):
        from faster_whisper import WhisperModel
        from huggingface_hub import hf_hub_download
        from transformers import Wav2Vec2CTCTokenizer, Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        self.asr = WhisperModel(ayar["hakem"], device=DEV, compute_type="float16" if DEV == "cuda" else "int8")
        self.ctc = None
        for ad in ayar["ctc"]:
            try:
                self.tok = Wav2Vec2CTCTokenizer.from_pretrained(ad)
                self.fe = Wav2Vec2FeatureExtractor.from_pretrained(ad)
                self.ctc = Wav2Vec2ForCTC.from_pretrained(ad).to(DEV).eval()
                self.ctc_ad = ad
                log("CTC hakem:", ad)
                break
            except Exception as e:  # noqa: BLE001
                log(f"CTC {ad} yüklenemedi: {e}")
        self.utmos = torch.jit.load(hf_hub_download("balacoon/utmos", "utmos.jit"), map_location=DEV).eval()

    @torch.inference_mode()
    def olc(self, x: np.ndarray, sr: int, hedef: str) -> dict:
        x16 = resample(x, sr, 16000)
        sure = len(x16) / 16000
        seg, _ = self.asr.transcribe(x16, language="tr", beam_size=5, condition_on_previous_text=False,
                                     word_timestamps=True, vad_filter=False)
        seg = list(seg)
        duyulan = "".join(s.text for s in seg).strip()
        kelimeler = [w for s in seg for w in (s.words or [])]
        kuyruk = sure - (kelimeler[-1].end if kelimeler else 0)
        bosluk = max([b.start - a.end for a, b in zip(kelimeler, kelimeler[1:])] + [0])
        sonuc = {"sure": round(sure, 2), "duyulan": duyulan, "whisper": hata(hedef, duyulan, esit=True),
                 "kuyruk": round(kuyruk, 2), "bosluk": round(bosluk, 2),
                 "tepe": round(float(np.abs(x).max()), 3),
                 "hiz": round(len(normalize(hedef).replace(" ", "")) / max(0.1, sure), 2)}
        if self.ctc is not None:
            girdi = self.fe(x16, sampling_rate=16000, return_tensors="pt").input_values.to(DEV)
            ids = self.ctc(girdi).logits.argmax(-1)[0].cpu().tolist()
            ctc_metin = self.tok.decode(ids)
            sonuc["ctc_duyulan"] = ctc_metin
            sonuc["ctc"] = hata(hedef, ctc_metin)
            sonuc["ctc_esit"] = hata(hedef, ctc_metin, esit=True)
        sonuc["mos"] = round(self.utmos(torch.from_numpy(x16).unsqueeze(0).to(DEV)).item(), 3)
        sonuc["_kelimeler"] = kelimeler
        return sonuc

    @torch.inference_mode()
    def emisyon(self, x16: np.ndarray) -> np.ndarray:
        girdi = self.fe(x16, sampling_rate=16000, return_tensors="pt").input_values.to(DEV)
        return torch.log_softmax(self.ctc(girdi).logits[0].float(), -1).cpu().numpy()

    def kelimeler(self, x16: np.ndarray) -> list:
        seg, _ = self.asr.transcribe(x16, language="tr", beam_size=5, condition_on_previous_text=False,
                                     word_timestamps=True, vad_filter=False)
        return [w for s in seg for w in (s.words or [])]


INSAN_VERI = "https://huggingface.co/api/datasets/google/fleurs/parquet/tr_tr/test/0.parquet"


def insan_profili(hakem: Hakem, ayar: dict, cikti: Path) -> None:
    """İnsan okuyucu kayıtlarından tonlama özelliklerinin dağılımı (Google FLEURS Türkçe, CC BY 4.0; yalnız
    istatistik, ses saklanmaz)."""
    import io
    import urllib.request

    import pandas as pd
    import soundfile as sf

    yol = Path("/tmp/fleurs-tr.parquet")
    if not yol.exists():
        urllib.request.urlretrieve(INSAN_VERI, yol)
    df = pd.read_parquet(yol)
    log(f"insan verisi: FLEURS tr_tr test, {len(df)} kayıt, sütunlar {list(df.columns)}")
    kayitlar = []
    for n, ornek in df.sample(frac=1, random_state=0).iterrows():
        if len(kayitlar) >= ayar.get("insan_n", 200):
            break
        try:
            a = ornek["audio"]
            x, sr = sf.read(io.BytesIO(a["bytes"]))
            x = x.mean(1) if x.ndim > 1 else x
            metin = str(ornek["raw_transcription"]).strip()
            if not (1.5 <= len(x) / sr <= 15) or len(metin.split()) < 3:
                continue
            x16 = resample(x.astype(np.float32), sr, 16000)
            o = tonlama.ozellikler(x16, hakem.kelimeler(x16), metin)
            if o:
                kayitlar.append(o)
        except Exception as e:  # noqa: BLE001
            log(f"insan örneği {n} atlandı: {e}")
    prof = tonlama.profil(kayitlar)
    prof["_kaynak"] = {"veri": "google/fleurs tr_tr test (CC BY 4.0)", "ornek": len(kayitlar)}
    (cikti / "insan_profil.json").write_text(json.dumps(prof, ensure_ascii=False, indent=1, default=jsonla),
                                             encoding="utf-8")
    log("insan profili: " + json.dumps(prof, ensure_ascii=False, default=jsonla))


def yanlis(p: dict, ayar: dict) -> bool:
    """İki hakem de hata görürse yanlış: Whisper (eşitlenmiş) > cer_sinir ve CTC (eşitlenmiş) > ctc_sinir."""
    return p["whisper"]["cer"] > ayar["cer_sinir"] and p.get("ctc_esit", {}).get("cer", 1) > ayar["ctc_sinir"]


def temiz(p: dict, ayar: dict) -> bool:
    return (p["whisper"]["cer"] <= 0.01 and p["kuyruk"] <= ayar["kuyruk_sinir"]
            and p["bosluk"] <= ayar["sessizlik_sinir"])


def anahtar(p: dict, ayar: dict) -> tuple:
    """Yanlış kelime > kuyruk > takılma > hata kovası (%1'lik) > tonlama sapması > (Whisper + 0.5 CTC) > doğallık.

    Hata kovası: hatası aynı yüzdelik dilimde olan adaylar arasında tonlaması insana yakın olan seçilir."""
    ctc = p.get("ctc_esit", p.get("ctc", {})).get("cer", 0)
    hata_top = p["whisper"]["cer"] + 0.5 * ctc
    return (yanlis(p, ayar), p["kuyruk"] > ayar["kuyruk_sinir"], p["bosluk"] > ayar["sessizlik_sinir"],
            int(p["whisper"]["cer"] * 100), p.get("tonlama_sapma", 0), round(hata_top, 4), -p["mos"])


def tonlama_ekle(p: dict, x: np.ndarray, sr: int, metin: str, prof: dict | None) -> None:
    """İnsan profili varsa adayın tonlama sapmasını hesaplar (aday seçiminde kullanılır)."""
    if not prof:
        return
    try:
        o = tonlama.ozellikler(resample(x, sr, 16000), p["_kelimeler"], metin)
        p["tonlama_sapma"] = tonlama.sapma(o, prof)
    except Exception as e:  # noqa: BLE001
        log(f"tonlama ölçülemedi: {e}")


def perde_genislet(x: np.ndarray, sr: int, kat: float) -> np.ndarray:
    """Tonlama eğrisini konuşmacının ortanca perdesi etrafında kat oranında açar (yarım ton ölçeğinde); Praat
    Manipulation + PSOLA ile yeniden sentezler. Sentez ses referansa göre düz (deney 19: perde aralığı 10.2 / 12.9)."""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(x.astype(np.float64), sr)
    man = call(snd, "To Manipulation", 0.01, 60, 400)
    pt = call(man, "Extract pitch tier")
    f0 = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400).selected_array["frequency"]
    f0 = f0[f0 > 0]
    if len(f0) < 20:
        return x
    med = float(np.median(f0))
    call(pt, "Formula", f"{med} * (self / {med}) ^ {kat}")
    call([pt, man], "Replace pitch tier")
    y = call(man, "Get resynthesis (overlap-add)").values[0].astype(np.float32)
    return y[: len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))


def duraklama_ekle(x: np.ndarray, sr: int, kelimeler: list, virgul: float, nokta: float) -> tuple[np.ndarray, list, list]:
    """Whisper'ın virgül/nokta koyduğu kelimeden sonraki sessizlik hedefin altındaysa farkı sessizlikle tamamlar.
    Kullanıcı (2026-11-22): sınırda doğal sessizlik yokken (model kelimeleri bağlamış) ortadan dijital sessizlik
    sokmak sesi "internet çekmiyor" gibi kesiyordu. Bu yüzden ekleme yalnız sınırın ±60 ms çevresindeki en sessiz 10 ms
    pencereye yapılır; orası konuşma düzeyinin 35 dB altında değilse eklenmez. Kenarlara 10 ms yumuşak geçiş konur.
    Dönüş: yeni ses, kaydırılmış kelime zamanları, ekleme konumları (yeni seste, sn)."""
    h = int(0.01 * sr)
    n = len(x) // h
    e = 10 * np.log10((x[: n * h].reshape(n, h) ** 2).mean(1) + 1e-12) if n else np.zeros(0)
    ust = float(np.percentile(e, 95)) if n else 0.0
    ekler = []  # (örnek konumu, eklenecek sn)
    for a, b in zip(kelimeler, kelimeler[1:]):
        w = a.word.strip()
        hedef = nokta if w[-1:] in ".!?;" else virgul if w[-1:] == "," else 0
        bosluk = b.start - a.end
        if not hedef or bosluk >= hedef:
            continue
        orta = (a.end + b.start) / 2
        i0, i1 = max(0, int((orta - 0.06) / 0.01)), min(n, int((orta + 0.06) / 0.01) + 1)
        if i1 <= i0:
            continue
        k = i0 + int(np.argmin(e[i0:i1]))
        if e[k] > ust - 35:
            continue  # doğal sessizlik yok: ekleme yapılmaz
        ekler.append((k * h + h // 2, hedef - max(0.0, bosluk)))
    if not ekler:
        return x, kelimeler, []
    f = int(0.01 * sr)
    pen = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f))
    parcalar, imlec, yerler, kay = [], 0, [], 0.0
    for i, ek in ekler:
        sol = x[imlec:i].copy()
        if len(sol) >= f:
            sol[-f:] *= pen[::-1]
        parcalar += [sol, np.zeros(int(ek * sr), np.float32)]
        yerler.append(round(i / sr + kay, 3))
        kay += ek
        imlec = i
    sag = x[imlec:].copy()
    if len(sag) >= f:
        sag[:f] *= pen
    parcalar.append(sag)

    class K:  # kaydırılmış kelime
        def __init__(self, w, s, e):
            self.word, self.start, self.end = w, s, e
    yeni = []
    for k in kelimeler:
        kay = sum(ek for i, ek in ekler if i / sr <= k.start)
        yeni.append(K(k.word, k.start + kay, k.end + kay))
    return np.concatenate(parcalar).astype(np.float32), yeni, yerler


def uzun_unlu(x, p, parca, ayar, ses, hakem):
    """Uzun ünlüleri seste uzatır; uzatılmış ses yeniden ölçülür, yanlışa düşerse uzatılmamış ses kalır."""
    sozluk = hakem.tok.get_vocab()
    uzun = set(parca.get("uzun", []))
    em0 = hakem.emisyon(resample(x, ses.sr, 16000))
    sure0 = uzatma.harf_sureleri(em0, parca["okunus"], sozluk)
    if parca.get("ayn"):
        p = {**p, "ayn_bosluk": uzatma.ara_bosluk(em0, parca["okunus"], sozluk, parca["ayn"])}
    oran0 = uzatma.uzun_kisa_orani(sure0, parca["okunus"], uzun)
    # Ünlü tablosu her zaman kaydedilir: [konum, süre sn, uzun mu, öbek sonu mu] (kelime düzeyi uzunluk raporu için)
    tablo0 = [[t["i"], t["sure"], t["uzun"], t["obek_sonu"]] for t in uzatma.unlu_tablosu(sure0, parca["okunus"], uzun)]
    p = {**p, "unlu_once": tablo0}
    kat = parca.get("uzatma", ayar["uzatma"])
    if kat == "uyarlamali":
        y, islem = uzatma.sure_duzelt(x, ses.sr, sure0, parca["okunus"], uzun, ayar.get("hedef_uzun", 1.8),
                                      ayar.get("sinir_kisa", 1.5))
        if len(y) == len(x) and not islem.get("uzatilan") and not islem.get("kisaltilan"):
            return x, {**p, "unlu_sonra": tablo0,
                       "uzatma": {"oran_once": oran0, "oran_sonra": oran0, "uygulandi": True, "islem": islem}}
    elif kat <= 1:
        return x, {**p, "unlu_sonra": tablo0, "uzatma": {"oran_once": oran0, "oran_sonra": oran0, "uygulandi": True}}
    else:
        y, islem = uzatma.uzat(x, ses.sr, [sure0[i] for i in uzun if i in sure0], kat), {}
    py = hakem.olc(y, ses.sr, parca.get("hedef", parca["okunus"]))
    sure1 = uzatma.harf_sureleri(hakem.emisyon(resample(y, ses.sr, 16000)), parca["okunus"], sozluk)
    oran1 = uzatma.uzun_kisa_orani(sure1, parca["okunus"], uzun)
    tablo1 = [[t["i"], t["sure"], t["uzun"], t["obek_sonu"]] for t in uzatma.unlu_tablosu(sure1, parca["okunus"], uzun)]
    if yanlis(py, ayar) and not yanlis(p, ayar):
        return x, {**p, "unlu_sonra": tablo0,
                   "uzatma": {"oran_once": oran0, "oran_sonra": oran1, "uygulandi": False, "islem": islem}}
    return y, {**py, "unlu_once": tablo0, "unlu_sonra": tablo1,
               "uzatma": {"oran_once": oran0, "oran_sonra": oran1, "uygulandi": True, "islem": islem,
                          "cer_once": p["whisper"]["cer"]}}


def tonlama_ozet(rapor: list) -> dict:
    t = [r.get("tonlama", {}) for r in rapor]
    duz = [x["son_egim"] for x in t if x.get("bitis") == "duz" and "son_egim" in x]
    soru = [x["son_egim"] for x in t if x.get("bitis") == "soru" and "son_egim" in x]
    uyum = [x["tonlama_uyum"] for x in t if x.get("tonlama_uyum") is not None]
    return {"perde_std_ort": round(float(np.mean([x["perde_std"] for x in t if "perde_std" in x] or [0])), 2),
            "duz_sonu_dusen": round(sum(e < 0 for e in duz) / len(duz), 3) if duz else None,
            "soru_sonu_yukselen": round(sum(e > 0 for e in soru) / len(soru), 3) if soru else None,
            "tonlama_uyum_ort": round(float(np.mean(uyum)), 3) if uyum else None,
            **uzatma_ozet(rapor)}


def uzatma_ozet(rapor: list) -> dict:
    u = [r["uzatma"] for r in rapor if r.get("uzatma")]
    once = [x["oran_once"] for x in u if x.get("oran_once")]
    sonra = [x["oran_sonra"] for x in u if x.get("oran_sonra") and x.get("uygulandi")]
    return {"uzun_kisa_once": round(float(np.mean(once)), 3) if once else None,
            "uzun_kisa_sonra": round(float(np.mean(sonra)), 3) if sonra else None,
            "uzatma_geri_alinan": sum(not x.get("uygulandi") for x in u)}


def jsonla(o):
    return o.item() if hasattr(o, "item") else str(o)


def srt_zaman(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main() -> None:
    is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ayar = {**VARSAYILAN, **is_.get("ayar", {})}
    cikti = HERE / "cikti"
    (cikti / "secilen").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if is_.get("mod") == "insan":
        insan_profili(Hakem(ayar), ayar, cikti)
        (cikti / "sonuc.json").write_text(json.dumps({"ozet": {"mod": "insan"}, "parcalar": []}), encoding="utf-8")
        return
    prof_yol = HERE / "referans/insan_profil.json"
    prof = {k: v for k, v in json.loads(prof_yol.read_text(encoding="utf-8")).items() if not k.startswith("_")} \
        if prof_yol.exists() else None
    ses = VoxSes(ayar, cikti) if ayar["motor"] == "voxcpm" else Ses(ayar, cikti)
    hakem = Hakem(ayar)
    ref = ses.referans_kur(hakem)
    log(f"cihaz {DEV}, referans {ref}, sıcaklık {ayar['sicaklik']}, yükleme {time.time() - t0:.0f} sn")

    rapor, iz = [], []
    for i, parca in enumerate(is_["parcalar"]):
        adaylar, t_ses, t_hakem = [], 0.0, 0.0
        for tohum in range(ayar["aday"]):
            t1 = time.time()
            x = ses.soyle(parca["okunus"], tohum, parca.get("vox_referans"), parca.get("vox_mod"), parca.get("vox_stil"),
                           parca.get("vox_model"), parca.get("vox_cfg"), parca.get("vox_adim"))
            t2 = time.time()
            p = hakem.olc(x, ses.sr, parca.get("hedef", parca["okunus"]))
            tonlama_ekle(p, x, ses.sr, parca["okunus"], prof)
            t_ses, t_hakem = t_ses + t2 - t1, t_hakem + time.time() - t2
            adaylar.append((p, tohum, x))
            # Erken durma: kelimeler doğru, ses artığı ve takılma yok. Tonlama seçimi belirler, durmayı engellemez
            # (tonlama şartı cümle başına 8-16 aday ürettiriyordu).
            if sum(temiz(a[0], ayar) for a in adaylar) >= ayar["erken_dur"]:
                break
        en_iyi = min(adaylar, key=lambda a: anahtar(a[0], ayar))
        if yanlis(en_iyi[0], ayar) or en_iyi[0]["kuyruk"] > ayar["kuyruk_sinir"]:
            ses.model.temp = ayar["kurtarma_sicaklik"]
            for tohum in range(100, 100 + ayar["kurtarma_aday"]):
                t1 = time.time()
                x = ses.soyle(parca["okunus"], tohum, parca.get("vox_referans"), parca.get("vox_mod"), parca.get("vox_stil"),
                           parca.get("vox_model"), parca.get("vox_cfg"), parca.get("vox_adim"))
                t2 = time.time()
                p = hakem.olc(x, ses.sr, parca.get("hedef", parca["okunus"]))
                tonlama_ekle(p, x, ses.sr, parca["okunus"], prof)
                t_ses, t_hakem = t_ses + t2 - t1, t_hakem + time.time() - t2
                adaylar.append((p, tohum, x))
                if temiz(p, ayar):
                    break
            ses.model.temp = ayar["sicaklik"]
        p, tohum, x = min(adaylar, key=lambda a: anahtar(a[0], ayar))
        x = x * min(1.0, 0.9 / max(1e-6, float(np.abs(x).max())))  # tepe -1 dBFS altı (son ses ayrıca loudnorm'dan geçer)
        # Uzun ünlü süresi her zaman ölçülür; uzatma > 1 ise seste uzatılır.
        if (parca.get("uzun") or parca.get("ayn")) and hakem.ctc is not None:
            x, p = uzun_unlu(x, p, parca, ayar, ses, hakem)
        kat = float(parca.get("perde_kat", ayar.get("perde_kat", 1.0)) or 1.0)
        if abs(kat - 1.0) > 1e-3:
            try:
                x = perde_genislet(x, ses.sr, kat)
                p["perde_kat"] = kat
            except Exception as e:  # noqa: BLE001
                log(f"perde genişletilemedi: {e}")
        vd, nd = float(parca.get("virgul_ara", ayar.get("virgul_ara", 0)) or 0), float(ayar.get("nokta_ara", 0.35))
        if vd > 0 and p.get("_kelimeler"):
            x16_once = len(x)
            x, p["_kelimeler"], p["duraklama_yerleri"] = duraklama_ekle(x, ses.sr, p["_kelimeler"], vd, nd)
            p["duraklama_eklenen"] = round((len(x) - x16_once) / ses.sr, 2)
        p = {**p, "tepe_ham": p["tepe"], "tepe": round(float(np.abs(x).max()), 3)}
        try:
            p["tonlama"] = tonlama.ozellikler(resample(x, ses.sr, 16000), p["_kelimeler"], parca["okunus"])
            if prof:
                p["tonlama"].update(tonlama.puan(p["tonlama"], prof))
        except Exception as e:  # noqa: BLE001
            log(f"tonlama ölçülemedi: {e}")
        # Kelime zamanları (ifade ölçümü: vurgu, duraklama) rapora yazılır
        p["kelime_zaman"] = [[w.word.strip(), round(float(w.start), 2), round(float(w.end), 2)]
                             for w in p.get("_kelimeler") or []]
        p.pop("_kelimeler", None)
        for a in adaylar:
            a[0].pop("_kelimeler", None)
        x48 = resample(x, ses.sr, SR_OUT)
        wav_yaz(cikti / "secilen" / f"{parca['id']}.wav", x48, SR_OUT)
        iz.append((parca, x48))
        rapor.append({**{k: parca[k] for k in ("id", "metin", "okunus") if k in parca}, "secilen": tohum,
                      **{k: v for k, v in p.items()}, "aday_sayisi": len(adaylar),
                      "adaylar": [{"tohum": t, **{k: v for k, v in a.items() if k not in ("duyulan", "ctc_duyulan")}}
                                  for a, t, _ in adaylar]})
        (cikti / "ara-sonuc.json").write_text(json.dumps(rapor, ensure_ascii=False, default=jsonla), encoding="utf-8")
        uyari = " ".join(w for w, c in (("KUYRUK", p["kuyruk"] > ayar["kuyruk_sinir"]),
                                         ("TAKILMA", p["bosluk"] > ayar["sessizlik_sinir"]),
                                         ("YANLIŞ", yanlis(p, ayar))) if c)
        log(f"[{i + 1}/{len(is_['parcalar'])}] {parca['id']} aday {len(adaylar)} tohum {tohum} "
            f"CER {p['whisper']['cer']:.3f} CTC {p.get('ctc', {}).get('cer', -1):.3f} MOS {p['mos']:.2f} "
            f"({p['sure']:.1f} sn ses; üretim {t_ses:.0f} sn, hakem {t_hakem:.0f} sn) {uyari}")

    ozet = {
        "parca": len(rapor),
        "whisper_cer_ort": round(float(np.mean([r["whisper"]["cer"] for r in rapor])), 4),
        "whisper_wer_ort": round(float(np.mean([r["whisper"]["wer"] for r in rapor])), 4),
        "ctc_cer_ort": round(float(np.mean([r.get("ctc", {}).get("cer", 0) for r in rapor])), 4),
        "mos_ort": round(float(np.mean([r["mos"] for r in rapor])), 3),
        "yanlis": int(sum(yanlis(r, ayar) for r in rapor)),
        "kuyruk": sum(r["kuyruk"] > ayar["kuyruk_sinir"] for r in rapor),
        "takilma": sum(r["bosluk"] > ayar["sessizlik_sinir"] for r in rapor),
        "kirpilma": sum(r["tepe"] >= 0.999 for r in rapor),
        "hiz_ort": round(float(np.mean([r["hiz"] for r in rapor])), 2),
        "aday_ort": round(float(np.mean([r["aday_sayisi"] for r in rapor])), 2),
        "sure_sn": round(time.time() - t0),
        **tonlama_ozet(rapor),
        "ctc_hakem": getattr(hakem, "ctc_ad", None), "ayar": ayar,
    }
    (cikti / "sonuc.json").write_text(json.dumps({"ozet": ozet, "parcalar": rapor}, ensure_ascii=False, indent=1, default=jsonla),
                                      encoding="utf-8")

    if is_.get("mod") == "ornek":
        # Parçaları aralarındaki sessizlikle birleştir; -16 LUFS (sesli kitap / podcast düzeyi), -1 dBTP.
        parcalar, zaman, simdi, srt = [], [], 0.0, []
        for n, (parca, x) in enumerate(iz, 1):
            parcalar.append(x)
            srt.append(f"{n}\n{srt_zaman(simdi)} --> {srt_zaman(simdi + len(x) / SR_OUT)}\n{parca['metin']}\n")
            simdi += len(x) / SR_OUT
            ara = np.zeros(int(parca.get("ara", 0.5) * SR_OUT), np.float32)
            parcalar.append(ara)
            simdi += len(ara) / SR_OUT
        wav_yaz(cikti / "ham.wav", np.concatenate(parcalar), SR_OUT)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cikti / "ham.wav"), "-af",
                        "loudnorm=I=-16:TP=-1:LRA=11", "-ar", str(SR_OUT), "-ac", "1", str(cikti / "ornek.wav")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cikti / "ornek.wav"), "-c:a", "libmp3lame", "-b:a",
                        "128k", str(cikti / "ornek.mp3")], check=True)
        (cikti / "ham.wav").unlink()
        (cikti / "altyazi.srt").write_text("\n".join(srt), encoding="utf-8")
        log(f"örnek: {simdi:.1f} sn")
    log("ÖZET " + json.dumps({k: v for k, v in ozet.items() if k != "ayar"}, ensure_ascii=False, default=jsonla))


if __name__ == "__main__":
    main()
