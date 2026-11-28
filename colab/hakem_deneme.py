"""Küçük, işe özel hakem modelleri denemesi (kulak testi klipleriyle karşılaştırmak için).

Kullanım (Colab): python3 hakem_deneme.py <klip-klasörü> <klip_bilgi.json> <çıktı.csv> [fonem,durak,qwen]

Hakemler:
- fonem: facebook/wav2vec2-xlsr-53-espeak-cv-ft (Apache-2.0) sesi IPA fonemlerine çevirir. Metnin espeak-ng Türkçe
  fonemleriyle karşılaştırılır: fonem hata oranı (fonem_hata) ve beklenenden fazla uzun ünlü (fazla_uzun: tanınan "ː"
  sayısı eksi metinde beklenen uzun ünlü sayısı).
- durak: uygarkurt/bert-restore-punctuation-turkish (MIT) metindeki doğal durak yerlerini tahmin eder. Sesteki
  duraklar (kelime arası > 0,25 sn, Whisper kelime zamanları) bu yerlerle karşılaştırılır: yersiz_durak (doğal durak
  olmayan yerde duruş), eksik_durak (doğal durak yerinde duruş yok).
- qwen: Qwen/Qwen2.5-Omni-3B genel hakem; her klip için boyut boyut puan ister (GPU önerilir).
"""
import csv
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np
import torch

DEV = "cuda" if torch.cuda.is_available() else "cpu"
klasor, bilgi_yol, cikti = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
secim = sys.argv[4].split(",") if len(sys.argv) > 4 else ["fonem", "durak"]
bilgi = {f"{b['no']:02d}": b for b in json.loads(bilgi_yol.read_text())}
sonuc = {k: {} for k in bilgi}


def oku16(f):
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, dtype=np.float32).copy()


def pip(*p):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *p], check=False)


def duzenle(s):
    return re.sub(r"\s+", " ", s).strip()


def levenshtein(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        onceki, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            onceki, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, onceki + (x != y))
    return d[-1]


def fonem():
    subprocess.run("apt-get -qq install -y espeak-ng > /dev/null", shell=True, check=False)
    pip("phonemizer", "transformers")
    from phonemizer import phonemize
    from transformers import AutoProcessor, Wav2Vec2ForCTC
    ad = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    proc = AutoProcessor.from_pretrained(ad)
    model = Wav2Vec2ForCTC.from_pretrained(ad).to(DEV).eval()
    for k, b in bilgi.items():
        x = oku16(klasor / f"{k}.mp3")
        with torch.inference_mode():
            ids = model(proc(x, sampling_rate=16000, return_tensors="pt").input_values.to(DEV)).logits.argmax(-1)
        taninan = duzenle(proc.batch_decode(ids)[0])
        beklenen = duzenle(phonemize(b["okunus"], language="tr", backend="espeak", strip=True,
                                     preserve_punctuation=False, with_stress=False))
        t, e = taninan.replace(" ", ""), beklenen.replace(" ", "")
        sonuc[k]["fonem_hata"] = levenshtein(t, e) / max(1, len(e))
        uzun_beklenen = len(re.findall("[âîûÂÎÛ]", b["okunus"])) + e.count("ː")
        sonuc[k]["fazla_uzun"] = max(0, taninan.count("ː") - uzun_beklenen)
        sonuc[k]["taninan_uzun"] = taninan.count("ː")
        sonuc[k]["_fonem"] = taninan
        sonuc[k]["_beklenen"] = beklenen


def durak():
    pip("transformers")
    from transformers import pipeline
    p = pipeline("token-classification", model="uygarkurt/bert-restore-punctuation-turkish",
                 aggregation_strategy="none", device=0 if DEV == "cuda" else -1)
    for k, b in bilgi.items():
        kz = b.get("kelime_zaman") or []
        if len(kz) < 3:
            continue
        kelimeler = [re.sub(r"[^\wÇĞİÖŞÜçğıöşüâîûÂÎÛ'’-]", "", w[0]) for w in kz]
        duz = " ".join(w.lower() for w in kelimeler if w)
        etiket = p(duz)
        # Her kelimenin sonuna gelen noktalama tahmini: kelimenin son alt parçasının etiketi
        sinir, konum, i = set(), 0, 0
        for w_i, w in enumerate(kelimeler):
            if not w:
                continue
            bas = duz.find(w.lower(), konum)
            son = bas + len(w)
            konum = son
            parcalar = [e for e in etiket if bas <= e["start"] < son]
            if parcalar and parcalar[-1]["entity"] not in ("O", "LABEL_0"):
                sinir.add(w_i)
        duruslar = {i for i in range(len(kz) - 1) if kz[i + 1][1] - kz[i][2] > 0.25}
        sonuc[k]["yersiz_durak"] = len(duruslar - sinir)
        sonuc[k]["eksik_durak"] = len(sinir - duruslar - {len(kz) - 1})
        sonuc[k]["durak_sayisi"] = len(duruslar)


SORULAR = {  # her boyut tek soru, cevap tek rakam; puan = rakamların olasılık ağırlıklı ortalaması
    "dogallik": "Bu ses, «{metin}» metninin Türkçe seslendirmesi. Ne kadar doğal, insan okuması gibi? "
                "1 çok yapay, 5 tamamen insan gibi. Yalnız bir rakam yaz.",
    "uzatma": "Bu ses, «{metin}» metninin Türkçe seslendirmesi. Kısa olması gereken heceleri yanlış yerde uzatıyor mu? "
              "1 hiç uzatmıyor, 5 çok sık yanlış uzatıyor. Yalnız bir rakam yaz.",
    "durak": "Bu ses, «{metin}» metninin Türkçe seslendirmesi. Cümlenin ortasında yersiz duraklama, takılma var mı? "
             "1 hiç yok, 5 çok var. Yalnız bir rakam yaz.",
    "tonlama": "Bu ses, «{metin}» metninin Türkçe seslendirmesi. Tonlaması ve vurgusu doğal mı? "
               "1 tekdüze ve yanlış, 5 çok doğal. Yalnız bir rakam yaz.",
    "okuma": "Bu ses, «{metin}» metninin Türkçe seslendirmesi. Metindeki kelimeleri yanlış okuyor mu? "
             "1 hiç yanlış yok, 5 çok yanlış var. Yalnız bir rakam yaz.",
}


def qwen():
    import os
    ad = os.environ.get("QWEN_AD", "Qwen/Qwen2.5-Omni-7B")
    try:
        from transformers import Qwen2_5OmniForConditionalGeneration  # noqa: F401
    except ImportError:
        pip("git+https://github.com/huggingface/transformers", "qwen-omni-utils", "accelerate")
    import transformers
    ek = {}
    bellek = torch.cuda.get_device_properties(0).total_memory / 2**30 if torch.cuda.is_available() else 0
    if os.environ.get("QWEN_4BIT") == "1" or bellek < 30:  # T4/L4'e sığsın: 4-bit (bitsandbytes NF4)
        pip("bitsandbytes")
        ek["quantization_config"] = transformers.BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
        print(f"4-bit yükleniyor (GPU {bellek:.0f} GB)", flush=True)
    if "Qwen3" in ad:
        model = transformers.Qwen3OmniMoeForConditionalGeneration.from_pretrained(ad, dtype=torch.bfloat16,
                                                                                    device_map="auto", **ek)
        proc = transformers.Qwen3OmniMoeProcessor.from_pretrained(ad)
    else:
        model = transformers.Qwen2_5OmniForConditionalGeneration.from_pretrained(ad, dtype=torch.bfloat16,
                                                                                   device_map="auto",
                                                                                   enable_audio_output=False, **ek)
        proc = transformers.Qwen2_5OmniProcessor.from_pretrained(ad)
    thinker = model.thinker
    rakam = [proc.tokenizer.encode(str(i), add_special_tokens=False)[0] for i in range(1, 6)]
    kisa = ad.split("/")[-1].lower().replace(".", "")
    for k, b in bilgi.items():
        x = oku16(klasor / f"{k}.mp3")
        for boyut, soru in SORULAR.items():
            mesaj = [{"role": "user", "content": [{"type": "audio", "audio": x},
                                                  {"type": "text", "text": soru.format(metin=b["metin"])}]}]
            metin = proc.apply_chat_template(mesaj, add_generation_prompt=True, tokenize=False)
            girdi = proc(text=metin, audio=[x], return_tensors="pt", padding=True, sampling_rate=16000).to(thinker.device)
            with torch.inference_mode():
                son = thinker(**girdi).logits[0, -1].float()
            p = torch.softmax(son[rakam], -1).cpu().numpy()
            sonuc[k][f"{kisa}_{boyut}"] = float((p * np.arange(1, 6)).sum())
        print(k, {a: round(v, 2) for a, v in sonuc[k].items() if a.startswith(kisa)}, flush=True)

for ad in secim:
    try:
        {"fonem": fonem, "durak": durak, "qwen": qwen}[ad]()
        print(f"[tamam] {ad}", flush=True)
    except Exception:  # noqa: BLE001
        print(f"[HATA] {ad}\n{traceback.format_exc()[-1500:]}", flush=True)

sutun = sorted({s for v in sonuc.values() for s in v if not s.startswith("_")})
with open(cikti, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["klip", *sutun])
    for k in sorted(sonuc):
        w.writerow([k, *[sonuc[k].get(s, "") for s in sutun]])
Path(str(cikti) + ".json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
print("SONUÇ", cikti, ", ".join(sutun))
