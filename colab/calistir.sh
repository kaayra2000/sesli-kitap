#!/usr/bin/env bash
# Colab'de sesli kitap işini çalıştırır: bağımlılıkları kurar (oturumda bir kez), seslendirir, cikti zip'ini yazar.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
konu=$(python3 -c 'import json;print(json.load(open("is.json"))["konu"])')

if [[ ! -f /content/.sesli-kitap-kurulu-2 ]]; then
  echo "Bağımlılıklar kuruluyor..."
  # faster-whisper (CTranslate2) CUDA 12 kütüphanelerini ister; Colab'in torch'u daha yeni CUDA ile gelebilir.
  pip install -q pocket-tts faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*" 2>&1 | tail -3 || true
  touch /content/.sesli-kitap-kurulu-2
fi
# Colab'in özgün yolu (sürücü: /usr/lib64-nvidia) ayrı ortamlar için saklanır.
export COLAB_LD="${LD_LIBRARY_PATH:-}"
LD_LIBRARY_PATH="$(python3 -c 'import os, nvidia.cublas.lib as a, nvidia.cudnn.lib as b; print(list(a.__path__)[0] + ":" + list(b.__path__)[0])'):${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
python3 -c "import torch;print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'UYARI: GPU yok')"

rm -rf cikti
# MFA (ünlü süresi ölçümü) seslendirmeyle paralel kurulur
if [[ "$(python3 -c 'import json;print(json.load(open("is.json")).get("ayar",{}).get("mfa",True))')" == "True" ]] && \
   [[ ! -x /content/mfa/bin/mfa ]] && [[ ! -f /content/mfa_kur.log ]]; then
  nohup bash mfa_kur.sh > /content/mfa_kur.log 2>&1 &
fi
if [[ "$(python3 -c 'import json;print(json.load(open("is.json"))["mod"])')" == "yaris" ]]; then
  bash yaris/yaris.sh
  for f in cikti/yaris/*/*.wav; do ffmpeg -v error -y -i "$f" -c:a libopus -b:a 48k "${f%.wav}.opus" && rm "$f"; done
  cp is.json cikti/ && (cd cikti && zip -q -r "../cikti-${konu}.zip" .)
  echo "TAMAM: cikti-${konu}.zip hazır ($(du -h "cikti-${konu}.zip" | cut -f1))"
  exit 0
fi
MOTOR=$(python3 -c 'import json;print(json.load(open("is.json")).get("ayar",{}).get("motor","pocket"))')
if [[ "$MOTOR" == "voxcpm" ]]; then
  # VoxCPM2 Python 3.12 ister (Colab 3.13): seslendir.py ve hakemler ayrı ortamda, CUDA 12.6 torch ile çalışır.
  VX=/content/vx
  env LD_LIBRARY_PATH="$COLAB_LD" $VX/bin/python -c "import torch, voxcpm, faster_whisper, librosa; assert torch.cuda.is_available()" 2>/dev/null || {
    echo "VoxCPM ortamı kuruluyor..."; rm -rf $VX; pip install -q uv 2>&1 | tail -1
    uv venv -q -p 3.12 $VX
    uv pip install -q -p $VX/bin/python torch torchaudio --index-url https://download.pytorch.org/whl/cu126 2>&1 | tail -2
    uv pip install -q -p $VX/bin/python voxcpm faster-whisper transformers librosa soundfile huggingface_hub modelscope praat-parselmouth 2>&1 | tail -2; }
  $VX/bin/python -c "import parselmouth" 2>/dev/null || uv pip install -q -p $VX/bin/python praat-parselmouth 2>&1 | tail -1
  VXLD=$($VX/bin/python -c 'import os,glob,nvidia;print(":".join(sorted({os.path.dirname(p) for p in glob.glob(os.path.join(list(nvidia.__path__)[0],"*","lib","*.so*"))})))')
  PY_BETIK=seslendir.py
  MOD=$(python3 -c 'import json;print(json.load(open("is.json"))["mod"])')
  [[ "$MOD" == "referans" ]] && PY_BETIK=referans_ara.py
  [[ "$MOD" == "gercek" ]] && PY_BETIK=gercek_ses.py
  [[ "$MOD" == "aday" ]] && PY_BETIK=ses_adaylari.py
  [[ "$MOD" == "tasarim" ]] && PY_BETIK=ses_tasarimi.py
  [[ "$MOD" == "ayar" || "$MOD" == "referans" || "$MOD" == "gercek" || "$MOD" == "aday" || "$MOD" == "tasarim" ]] && { [[ "$MOD" == "ayar" ]] && PY_BETIK=ayar_tarama.py;
    $VX/bin/python -c "import speechbrain, pandas, pyarrow, noisereduce" 2>/dev/null || uv pip install -q -p $VX/bin/python speechbrain pandas pyarrow noisereduce 2>&1 | tail -1; }
  env LD_LIBRARY_PATH="$VXLD:$COLAB_LD" $VX/bin/python $PY_BETIK is.json 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\("
else
python3 seslendir.py is.json 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\(" 
fi
[[ -f cikti/sonuc.json ]] || { echo "Seslendirme bitmedi." >&2; exit 1; }
cp is.json cikti/
# İfade (duygu, tonlama, vurgu) ölçümü ayrı ortamda: /content/ifade (audiobox-aesthetics, audEERING, parselmouth)
if [[ "$(python3 -c 'import json;print(json.load(open("is.json")).get("ayar",{}).get("ifade",True))')" == "True" ]]; then
  IF=/content/ifade
  env LD_LIBRARY_PATH="$COLAB_LD" $IF/bin/python -c "import audiobox_aesthetics, parselmouth, faster_whisper, pandas" 2>/dev/null || {
    echo "İfade ortamı kuruluyor..."; rm -rf $IF; uv venv -q -p 3.12 $IF
    uv pip install -q -p $IF/bin/python torch torchaudio --index-url https://download.pytorch.org/whl/cu126 2>&1 | tail -2
    uv pip install -q -p $IF/bin/python audiobox_aesthetics transformers praat-parselmouth librosa soundfile faster-whisper pandas pyarrow 2>&1 | tail -2; }
  IFLD=$($IF/bin/python -c 'import os,glob,nvidia;print(":".join(sorted({os.path.dirname(p) for p in glob.glob(os.path.join(list(nvidia.__path__)[0],"*","lib","*.so*"))})))')
  env LD_LIBRARY_PATH="$IFLD:$COLAB_LD" $IF/bin/python ifade_olc.py cikti 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\(" || echo "ifade ölçümü başarısız"
  [[ "$(python3 -c 'import json;print(json.load(open("is.json")).get("ayar",{}).get("ifade_insan",False))')" == "True" ]] && \
    env LD_LIBRARY_PATH="$IFLD:$COLAB_LD" $IF/bin/python ifade_olc.py --insan cikti 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\(" || true
fi
# Ünlü süresi: Montreal Forced Aligner. Kurulum uzun (conda); colab/mfa_kur.sh ile arka planda kurulur, hazırsa ölçülür.
if [[ "$(python3 -c 'import json;print(json.load(open("is.json")).get("ayar",{}).get("mfa",True))')" == "True" ]]; then
  if [[ -x /content/mfa/bin/mfa ]] && grep -q "MFA HAZIR" /content/mfa_kur.log 2>/dev/null; then
    # kalpy libcuda ister: yalnız Colab sürücü yolu (COLAB_LD) verilir, VoxCPM'in CUDA kütüphaneleri verilmez
    env LD_LIBRARY_PATH="$COLAB_LD" PATH=/content/mfa/bin:$PATH /content/mfa/bin/python mfa_olc.py . 2>&1 | tail -6 || echo "MFA ölçümü başarısız"
  else
    echo "MFA hazır değil (arka plan kurulumu: /content/mfa_kur.log); ünlü süresi ölçülmedi"
  fi
fi
# Çıktıyı küçült: seçilen cümleler Opus (tarayıcıdan alınan çıktı küçük kalsın), örnekte yalnız mp3.
shopt -s nullglob
for f in cikti/secilen/*.wav cikti/tarama/*/*.wav cikti/referans/sinav/*/*.wav cikti/gercek/sinav/*/*.wav cikti/adaylar/*.wav cikti/tasarim/*.wav; do ffmpeg -v error -y -i "$f" -c:a libopus -b:a 48k "${f%.wav}.opus" && rm "$f"; done
rm -f cikti/ornek.wav cikti/ara-sonuc.json
(cd cikti && zip -q -r "../cikti-${konu}.zip" .)
echo "TAMAM: cikti-${konu}.zip hazır ($(du -h "cikti-${konu}.zip" | cut -f1))"
