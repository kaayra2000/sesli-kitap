#!/usr/bin/env bash
# Colab'de sesli kitap işini çalıştırır: bağımlılıkları kurar (oturumda bir kez), seslendirir, cikti zip'ini yazar.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
konu=$(python3 -c 'import json;print(json.load(open("is.json"))["konu"])')

if [[ ! -f /content/.sesli-kitap-kurulu ]]; then
  echo "Bağımlılıklar kuruluyor..."
  pip install -q pocket-tts faster-whisper 2>&1 | grep -vE "^(\s|Requirement|  )" | tail -5 || true
  touch /content/.sesli-kitap-kurulu
fi
python3 -c "import torch;print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'UYARI: GPU yok')"

rm -rf cikti
python3 seslendir.py is.json 2>&1 | grep --line-buffered -vE "it/s\]|s/it\]|Warning|warn\(" 
[[ -f cikti/sonuc.json ]] || { echo "Seslendirme bitmedi." >&2; exit 1; }
cp is.json cikti/
(cd cikti && zip -q -r "../cikti-${konu}.zip" .)
echo "TAMAM: cikti-${konu}.zip hazır ($(du -h "cikti-${konu}.zip" | cut -f1))"
