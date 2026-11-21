#!/usr/bin/env python3
"""Colab 4. hücresinin base64 çıktısını (Playwright ile kaydedilen dosya) zip'e çevirip açar.

Kullanım: python3 colab/al.py <b64-dosyası> <hedef-klasör>
          python3 colab/al.py <parça0> <parça1> ... <hedef-klasör>   (büyük çıktı P<n>START...P<n>END parçaları)
Büyük çıktı (bölüm, ~37 MB base64) tek seferde alınınca Playwright bağlantısı kopuyor; sayfadan 7 parçada alınır.
"""
import base64
import io
import re
import sys
import zipfile
from pathlib import Path

def temiz(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9+/=]", "", x.replace("\\n", ""))


*girdiler, hedef = sys.argv[1:]
if len(girdiler) == 1 and not re.search(r"P\d+START[A-Za-z0-9]", s := open(girdiler[0], encoding="utf-8").read()):
    b = temiz(re.search(r"B64START([A-Za-z0-9+/=\\n\s]+)B64END", s, re.S).group(1))
else:
    parca = {}
    for g in girdiler:
        m = re.search(r"P(\d+)START([A-Za-z0-9+/=\\n]+)P\d+END", open(g, encoding="utf-8").read(), re.S)
        parca[int(m.group(1))] = temiz(m.group(2))
    b = "".join(parca[k] for k in sorted(parca))
hedef = Path(hedef)
hedef.mkdir(parents=True, exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(b))).extractall(hedef)
print(hedef, sorted(p.name for p in hedef.iterdir()))
