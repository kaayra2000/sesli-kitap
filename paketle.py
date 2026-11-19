#!/usr/bin/env python3
"""
Colab iş paketini kurar: dist/is-<konu>.zip (betikler, okunuş kuralları, sentetik referans sesler, parçalar).

  python3 paketle.py test  --tur 3                    # test kümesi, ayarlar.json ile
  python3 paketle.py ornek --bas b0011-c00 --sn 110   # kitaptan ~110 sn'lik örnek

Colab'e yalnız kitap metni, betikler ve sentetik (Piper / pocket-tts üretimi) referans sesler gider; kişisel veri yok.
"""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / "metin"))
from okunus import okunus, sozluk_yukle  # noqa: E402
from hazirla import hazirla  # noqa: E402

# Kitabın aktarımı bedri_gencer reposunda (bu reponun yanında); SESLI_KITAP_MD ile başka yol verilebilir.
KITAP = Path(os.environ.get("SESLI_KITAP_MD", KOK.parent / "bedri_gencer/claude/Salahuddin b Siracüddin-BB-Mektuplar-SS/"
                            "Salahuddin b Siracüddin-BB-Mektuplar-SS.md"))
KELIME_DK = 125


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mod", choices=["test", "ornek", "deney", "insan"])
    p.add_argument("--tur", type=int, default=0)
    p.add_argument("--bas", default="b0008-c00")
    p.add_argument("--sn", type=float, default=110)
    p.add_argument("--kume", default="test/test_kumesi.json", help="test modunda cümle kümesi")
    p.add_argument("--ad", default="tur", help="konu adı öneki (tur, dogrulama)")
    a = p.parse_args()
    ayarlar = json.loads((KOK / "ayarlar.json").read_text(encoding="utf-8"))
    sozluk = sozluk_yukle()

    if a.mod == "test":
        konu = f"{a.ad}{a.tur:02d}"
        test = json.loads((KOK / a.kume).read_text(encoding="utf-8"))
        parcalar = [{"id": t["id"], "metin": t["metin"], "okunus": okunus(t["metin"], sozluk, ayarlar["okunus"]),
                     "ara": 0.5} for t in test]
    elif a.mod == "insan":
        konu, parcalar = "insan", []
    elif a.mod == "deney":
        # Uzun ünlü deneyi: her cümle her şapka biçimiyle; hakem metnin aslıyla (hedef) karşılaştırır.
        konu = f"deney{a.tur:02d}"
        deney = json.loads((KOK / "test/uzatma_deneyi.json").read_text(encoding="utf-8"))
        parcalar = [{"id": f"{t['id']}-{v}", "metin": t["metin"], "hedef": t["metin"], "ara": 0.5,
                     "okunus": okunus(t["metin"], sozluk, {**ayarlar["okunus"], "sapka": v})}
                    for t in deney["cumleler"] for v in deney["varyantlar"]]
        ayarlar["seslendirme"] = {**ayarlar["seslendirme"], **deney["ayar"]}
    else:
        konu = f"ornek{a.tur:02d}"
        hepsi = hazirla(KITAP.read_text(encoding="utf-8"), ayarlar["parca_en_cok_kelime"], ayarlar["okunus"])
        bas = next(i for i, x in enumerate(hepsi) if x["id"] >= a.bas)
        parcalar, kelime = [], 0
        for x in hepsi[bas:]:
            parcalar.append(x)
            kelime += len(x["okunus"].split())
            if kelime / KELIME_DK * 60 >= a.sn:
                break
    # Uzun ünlü indeksleri: şapkalı okunuşla karşılaştırılır (şapka 1:1 harf, uzunluk aynı).
    for x in parcalar:
        sapkali = okunus(x["metin"], sozluk, {**ayarlar["okunus"], "sapka": "koru"})
        if len(sapkali) == len(x["okunus"]):
            x["uzun"] = [i for i, (a, b) in enumerate(zip(x["okunus"], sapkali)) if a != b]
    is_ = {"konu": konu, "mod": a.mod, "ayar": ayarlar["seslendirme"], "parcalar": parcalar}
    hedef = KOK / "dist" / f"is-{konu}.zip"
    hedef.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("is.json", json.dumps(is_, ensure_ascii=False, indent=1))
        for f in ["colab/seslendir.py", "colab/calistir.sh", "metin/okunus.py", "metin/okunus.tsv", "metin/olcum.py", "colab/tonlama.py", "colab/uzatma.py"]:
            if (KOK / f).exists():
                z.write(KOK / f, Path(f).name)
        for f in sorted((KOK / "referans").glob("*.wav")) + sorted((KOK / "referans").glob("*.json")):
            z.write(f, f"referans/{f.name}")
    print(f"{hedef}  ({len(parcalar)} parça)")


if __name__ == "__main__":
    main()
