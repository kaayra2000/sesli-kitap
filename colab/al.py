#!/usr/bin/env python3
"""Colab 4. hücresinin base64 çıktısını (Playwright evaluate ile kaydedilen dosya) zip'e çevirir.

Kullanım: python3 colab/al.py <b64-dosyası> <hedef.zip>
"""
import base64
import json
import sys

s = open(sys.argv[1], encoding="utf-8").read().strip()
if s.startswith('"'):
    s = json.loads(s)
open(sys.argv[2], "wb").write(base64.b64decode(s))
print(sys.argv[2])
