#!/usr/bin/env python3
"""Colab 4. hücresinin base64 çıktısını (Playwright ile kaydedilen dosya) zip'e çevirip açar.

Kullanım: python3 colab/al.py <b64-dosyası> <hedef-klasör>
"""
import base64
import io
import re
import sys
import zipfile
from pathlib import Path

s = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"B64START(.+?)B64END", s, re.S)
b = re.sub(r"[^A-Za-z0-9+/=]", "", m.group(1).replace("\\n", ""))
hedef = Path(sys.argv[2])
hedef.mkdir(parents=True, exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(b))).extractall(hedef)
print(hedef, sorted(p.name for p in hedef.iterdir()))
