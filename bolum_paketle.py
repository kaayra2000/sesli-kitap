#!/usr/bin/env python3
"""
Bir kitap bölümünü Colab'de seslendirmek için ~1,5 saatlik parçalara bölüp iş paketleri kurar.
Oturum koparsa yalnız o parça yeniden üretilir. Parçalar sonra `video/parcalari_birlestir.py` ile birleşir.

  python3 bolum_paketle.py marifetname 04 --kume 110
  -> dist/is-ornek401.zip, dist/is-ornek402.zip, ... (tur = bölüm no * 100 + parça no)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from paketle import kitap_yukle  # noqa: E402
sys.path.insert(0, str(KOK / "metin"))
from hazirla import hazirla  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kitap")
    p.add_argument("no", help="bölüm numarası (dosya adının başı), ör. 04")
    p.add_argument("--kume", type=int, default=110, help="iş başına en çok parça (~1 dk/parça)")
    a = p.parse_args()

    bilgi = json.loads((KOK / "kitaplar" / a.kitap / "kitap.json").read_text(encoding="utf-8"))
    klasor = "sadelestirilmis" if bilgi.get("seslendirme") == "sadelestirilmis" else "aktarim"
    md = next((KOK / "kitaplar" / a.kitap / klasor).glob(f"{a.no}-*.md"))
    os.environ["SESLI_KITAP_MD"] = str(md)
    _, ek = kitap_yukle(a.kitap)
    ayarlar = json.loads((KOK / "ayarlar.json").read_text(encoding="utf-8"))
    ids = [x["id"] for x in hazirla(md.read_text(encoding="utf-8"), ayarlar["parca_en_cok_kelime"], ayarlar["okunus"],
                                    birlestir=True, **ek)]  # paketle.py ornek ile aynı bölme
    # Parça sınırı başlık ya da paragraf başına düşsün (bXXXX-c00)
    bas = [0]
    while len(ids) - bas[-1] > a.kume * 1.3:
        i = bas[-1] + a.kume
        while i < len(ids) and not ids[i].endswith("-c00"):
            i += 1
        bas.append(i)
    tur0 = int(a.no.rstrip("abc")) * 100 + (10 * " abc".index(a.no[-1]) if a.no[-1] in "abc" else 0)
    for k, b in enumerate(bas, 1):
        bitis = ids[bas[k]] if k < len(bas) else ""
        komut = [sys.executable, str(KOK / "paketle.py"), "ornek", "--kitap", a.kitap, "--tur", str(tur0 + k),
                 "--bas", ids[b], "--sn", "1000000"] + (["--bitis", bitis] if bitis else [])
        print(f"parça {k}: {ids[b]} .. {bitis or 'son'}", flush=True)
        subprocess.run(komut, check=True)


if __name__ == "__main__":
    main()
