#!/usr/bin/env bash
# Model yarışı (Colab): her motor kendi ortamında üretir, hakem ana ortamda puanlar.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT=cikti/yaris
mkdir -p "$OUT"
pip install -q uv 2>&1 | tail -1
# Ayrı ortamlarda torch CUDA 12.6 tekerleğinden kurulur: PyPI'nin varsayılan torch'u Colab sürücüsünden yeni CUDA ister
# ve sessizce CPU'ya düşer (VoxCPM2 CPU'da cümle başına ~1 dk sürdü).
TORCH_CU="--index-url https://download.pytorch.org/whl/cu126"
GPU_VAR='import torch; assert torch.cuda.is_available()'
env -u LD_LIBRARY_PATH /content/vx/bin/python -c "$GPU_VAR" 2>/dev/null || rm -rf /content/vx
if [[ ! -x /content/vx/bin/python ]]; then
  echo "VoxCPM ortamı (Python 3.12) kuruluyor..."
  uv venv -q -p 3.12 /content/vx
  uv pip install -q -p /content/vx/bin/python torch torchaudio $TORCH_CU 2>&1 | tail -2
  uv pip install -q -p /content/vx/bin/python voxcpm soundfile 2>&1 | tail -2
  env -u LD_LIBRARY_PATH /content/vx/bin/python -c "import torch; print('VoxCPM torch', torch.__version__, 'cuda', torch.cuda.is_available())"
fi
env -u LD_LIBRARY_PATH /content/cb/bin/python -c "import perth, torch; assert perth.PerthImplicitWatermarker and torch.cuda.is_available()" 2>/dev/null || rm -rf /content/cb
if [[ ! -x /content/cb/bin/python ]]; then
  echo "Chatterbox ortamı (Python 3.11) kuruluyor..."
  uv venv -q -p 3.11 /content/cb
  uv pip install -q -p /content/cb/bin/python chatterbox-tts "setuptools<81" 2>&1 | tail -2
  env -u LD_LIBRARY_PATH /content/cb/bin/python -c "import torch; assert torch.cuda.is_available()" 2>/dev/null || \
    { TV=$(/content/cb/bin/python -c 'import torch;print(torch.__version__.split("+")[0])');
      uv pip install -q -p /content/cb/bin/python --reinstall "torch==$TV" "torchaudio==$TV" $TORCH_CU 2>&1 | tail -2; }
  env -u LD_LIBRARY_PATH /content/cb/bin/python -c "import torch; print('Chatterbox torch', torch.__version__, 'cuda', torch.cuda.is_available())"
fi
python3 yaris/uret_pocket.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s" | tail -3
# Ana ortamın LD_LIBRARY_PATH'i (CUDA 12 cuBLAS/cuDNN, faster-whisper için) ayrı ortamların torch'uyla çakışıyor.
env -u LD_LIBRARY_PATH /content/vx/bin/python yaris/uret_voxcpm.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]" | tail -40
env -u LD_LIBRARY_PATH /content/cb/bin/python yaris/uret_chatterbox.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]" | tail -5
pip install -q "git+https://github.com/sarulab-speech/UTMOSv2.git" speechbrain 2>&1 | tail -2
python3 yaris/hakem_yaris.py is.json "$OUT" 2>&1 | grep -vE "WARNING|it/s\]|s/it\]|warn"
