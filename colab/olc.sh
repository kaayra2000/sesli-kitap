#!/usr/bin/env bash
# Yalnız ölçüm: mevcut /content/is/cikti üzerinde ifade (ve istenirse insan) ölçümünü çalıştırıp çıktıyı yeniden paketler.
# Seslendirme bittikten sonra ölçüm adımı başarısız olduysa kullanılır: !cd /content/is && bash olc.sh [--insan]
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
konu=$(python3 -c 'import json;print(json.load(open("is.json"))["konu"])')
IF=/content/ifade
IFLD=$($IF/bin/python -c 'import os,glob,nvidia;print(":".join(sorted({os.path.dirname(p) for p in glob.glob(os.path.join(list(nvidia.__path__)[0],"*","lib","*.so*"))})))')
env LD_LIBRARY_PATH="$IFLD:${LD_LIBRARY_PATH:-}" $IF/bin/python ifade_olc.py cikti 2>&1 | grep -vE "it/s\]|s/it\]|Warning|warn\(" | tail -5
[[ "${1:-}" == "--insan" ]] && env LD_LIBRARY_PATH="$IFLD:${LD_LIBRARY_PATH:-}" $IF/bin/python ifade_olc.py --insan cikti 2>&1 | grep -vE "it/s\]|s/it\]|Warning|warn\(" | tail -5
shopt -s nullglob
for f in cikti/secilen/*.wav; do ffmpeg -v error -y -i "$f" -c:a libopus -b:a 48k "${f%.wav}.opus" && rm "$f"; done
rm -f "cikti-${konu}.zip"; (cd cikti && zip -q -r "../cikti-${konu}.zip" .)
echo "TAMAM: cikti-${konu}.zip hazır ($(du -h "cikti-${konu}.zip" | cut -f1))"
