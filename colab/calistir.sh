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
LD_LIBRARY_PATH="$(python3 -c 'import os, nvidia.cublas.lib as a, nvidia.cudnn.lib as b; print(list(a.__path__)[0] + ":" + list(b.__path__)[0])'):${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
python3 -c "import torch;print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'UYARI: GPU yok')"

rm -rf cikti
python3 seslendir.py is.json 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\(" 
[[ -f cikti/sonuc.json ]] || { echo "Seslendirme bitmedi." >&2; exit 1; }
cp is.json cikti/
# Çıktıyı küçült: seçilen cümleler Opus (tarayıcıdan alınan çıktı küçük kalsın), örnekte yalnız mp3.
shopt -s nullglob
for f in cikti/secilen/*.wav; do ffmpeg -v error -y -i "$f" -c:a libopus -b:a 48k "${f%.wav}.opus" && rm "$f"; done
rm -f cikti/ornek.wav cikti/ara-sonuc.json
(cd cikti && zip -q -r "../cikti-${konu}.zip" .)
echo "TAMAM: cikti-${konu}.zip hazır ($(du -h "cikti-${konu}.zip" | cut -f1))"
