#!/usr/bin/env bash
# Model yarışı (Colab): her motor kendi ortamında üretir, hakem ana ortamda puanlar.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT=cikti/yaris
mkdir -p "$OUT"
pip install -q uv 2>&1 | tail -1
if [[ ! -x /content/vx/bin/python ]]; then
  echo "VoxCPM ortamı (Python 3.12) kuruluyor..."
  uv venv -q -p 3.12 /content/vx && uv pip install -q -p /content/vx/bin/python voxcpm soundfile 2>&1 | tail -2
fi
if [[ ! -x /content/cb/bin/python ]]; then
  echo "Chatterbox ortamı (Python 3.11) kuruluyor..."
  uv venv -q -p 3.11 /content/cb && uv pip install -q -p /content/cb/bin/python chatterbox-tts 2>&1 | tail -2
fi
python3 yaris/uret_pocket.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s" | tail -3
/content/vx/bin/python yaris/uret_voxcpm.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]" | tail -40
/content/cb/bin/python yaris/uret_chatterbox.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]" | tail -5
pip install -q "git+https://github.com/sarulab-speech/UTMOSv2.git" speechbrain 2>&1 | tail -2
python3 yaris/hakem_yaris.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]|warn"
