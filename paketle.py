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
    p.add_argument("mod", choices=["test", "ornek", "deney", "insan", "yaris", "metin", "ayar", "referans", "gercek", "aday", "tasarim"])
    p.add_argument("--tur", type=int, default=0)
    p.add_argument("--bas", default="b0008-c00")
    p.add_argument("--sn", type=float, default=110)
    p.add_argument("--bitis", default="", help="ornek: bu parça kimliğinde dur (bölüm sonu)")
    p.add_argument("--kume", default="test/test_kumesi.json", help="test modunda cümle kümesi")
    p.add_argument("--ad", default="tur", help="konu adı öneki (tur, dogrulama)")
    a = p.parse_args()
    ayarlar = json.loads((KOK / "ayarlar.json").read_text(encoding="utf-8"))
    sozluk = sozluk_yukle()

    if a.mod == "test":
        konu = f"{a.ad}{a.tur:02d}"
        test = json.loads((KOK / a.kume).read_text(encoding="utf-8"))
        parcalar = [{"id": t["id"], "metin": t["metin"], "hedef": t["metin"], "okunus": okunus(t["metin"], sozluk, ayarlar["okunus"]),
                     "ara": 0.5} for t in test]
    elif a.mod in ("ayar", "referans", "gercek", "aday", "tasarim"):
        konu = f"{a.mod}{a.tur:02d}"
        metinler = [
            {"id": "duz", "metin": "Değerli çalışma arkadaşlarımız, yarın sabah saat dokuzdan on bire kadar e posta "
                                   "sisteminde planlı bakım çalışması yapılacaktır. Anlayışınız için teşekkür ederiz."},
            {"id": "osmanlica", "metin": "Ma‘lûmunuz olsun ki: Muhabbet, fi’l-hakîka Allâh’dan mevhûbdur. Hakîkat-i fenâ "
                                         "ile müşerref olan sâlik, Mevlâ-yı Müte‘âl’in rızâsına nâil olur."}]
        parcalar = [{"id": t["id"], "metin": t["metin"], "hedef": t["metin"], "okunus": okunus(t["metin"], sozluk, ayarlar["okunus"]),
                     "ara": 1.0} for t in metinler]
        ayarlar["seslendirme"] = {**ayarlar["seslendirme"], "aday": 2}
    elif a.mod == "metin":
        # Serbest metinler (ör. düz Türkçe örnekler): her metin tek parça, ayrı dosya olarak döner.
        konu = f"metin{a.tur:02d}"
        metinler = json.loads((KOK / a.kume).read_text(encoding="utf-8"))
        parcalar = [{"id": t["id"], "metin": t["metin"], "hedef": t["metin"], "okunus": okunus(t["metin"], sozluk, ayarlar["okunus"]),
                     "ara": 1.0} for t in metinler]
        a.mod = "ornek"
    elif a.mod == "yaris":
        # Model yarışı: test kümesinden 12 cümle (6 kitap, 6 zor) + örnek bölümden 6 cümle; sabit ses = standarttaki
        # temel ses (Piper Fahrettin) referansı ve metni (it_yapisi iletisim/ses/zamanli_seslendir.py REFERENCE_TEXT).
        konu = f"yaris{a.tur:02d}"
        test = json.loads((KOK / "test/test_kumesi.json").read_text(encoding="utf-8"))
        secim = [t for t in test if t["katman"] in ("orta", "uzun")][:6] + [t for t in test if t["katman"] == "zor"][:6]
        hepsi = hazirla(KITAP.read_text(encoding="utf-8"), ayarlar["parca_en_cok_kelime"], ayarlar["okunus"])
        secim += [{"id": f"ornek-{x['id']}", "metin": x["metin"]} for x in hepsi
                  if x["id"] in ("b0011-c00", "b0011-c03", "b0012-c00", "b0013-c01", "b0013-c09", "b0014-c01")]
        cumleler = [{"id": t["id"], "metin": t["metin"], "hedef": t["metin"], "okunus": okunus(t["metin"], sozluk, ayarlar["okunus"]),
                     "okunus_sapka": okunus(t["metin"], sozluk, {**ayarlar["okunus"], "sapka": "koru"})} for t in secim]
        is_ = {"konu": konu, "mod": "yaris", "cumleler": cumleler, "referans": {
            "yol": "referans/referans-temel-ses.wav",
            "metin": "Birimler ve yöneticiler artık düzenli kartlarda, net bir ağaç yapısında görünür. "
                     "Bir isme ya da fotoğrafa tıkladığınızda, sağda kişi kartı açılır."}}
        parcalar = []
    elif a.mod == "insan":
        konu, parcalar = "insan", []
    elif a.mod == "deney":
        # Uzun ünlü deneyi: her cümle her şapka biçimiyle; hakem metnin aslıyla (hedef) karşılaştırır.
        konu = f"deney{a.tur:02d}"
        deney = json.loads((KOK / (a.kume if a.kume.endswith("deneyi.json") else "test/uzatma_deneyi.json"))
                           .read_text(encoding="utf-8"))
        cumleler = deney.get("cumleler") or json.loads((KOK / deney["kume"]).read_text(encoding="utf-8"))
        parcalar = []
        for t in cumleler:
            for v in deney["varyantlar"]:
                v = v if isinstance(v, dict) else {"ad": v, "okunus": {"sapka": v}}
                oku = {**ayarlar["okunus"], **v.get("okunus", {})}
                x = {"id": f"{t['id']}--{v['ad']}", "metin": t["metin"], "hedef": t["metin"], "ara": 0.5,
                     "okunus": okunus(t["metin"], sozluk, oku), "uzatma": v.get("uzatma", 1.0),
                     **({"vox_referans": v["vox_referans"]} if v.get("vox_referans") else {})}
                # Ayn/hemze durağı ölçümü: işaretli okunuşta \x01 konumları -> (sol, sağ) harf çiftleri
                isaretli = okunus(t["metin"], sozluk, {**oku, "ayn": "isaret"})
                konum = [i for i, c in enumerate(isaretli) if c == "\x01"]
                if konum:
                    if oku.get("ayn", "yok") == "yok":
                        x["ayn"] = [(i - k - 1, i - k) for k, i in enumerate(konum)]
                    elif len(isaretli) == len(x["okunus"]):
                        x["ayn"] = [(i - 1, i + 1) for i in konum]
                sapkali = okunus(t["metin"], sozluk, {**oku, "sapka": "koru"})
                if len(sapkali) == len(x["okunus"]):
                    x["uzun"] = [i for i, c in enumerate(sapkali) if c in "âîûÂÎÛ"]
                parcalar.append(x)
        ayarlar["seslendirme"] = {**ayarlar["seslendirme"], **deney["ayar"]}
    else:
        konu = f"ornek{a.tur:02d}"
        hepsi = hazirla(KITAP.read_text(encoding="utf-8"), ayarlar["parca_en_cok_kelime"], ayarlar["okunus"], birlestir=True)
        bas = next(i for i, x in enumerate(hepsi) if x["id"] >= a.bas)
        parcalar, kelime = [], 0
        for x in hepsi[bas:]:
            if a.bitis and x["id"] >= a.bitis:
                break
            parcalar.append(x)
            kelime += len(x["okunus"].split())
            if kelime / KELIME_DK * 60 >= a.sn:
                break
    if a.mod == "yaris":
        hedef = KOK / "dist" / f"is-{konu}.zip"
        hedef.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("is.json", json.dumps(is_, ensure_ascii=False, indent=1))
            for f in ["colab/seslendir.py", "colab/calistir.sh", "colab/tonlama.py", "colab/uzatma.py", "metin/okunus.py",
                      "metin/okunus.tsv", "metin/olcum.py"]:
                z.write(KOK / f, Path(f).name)
            for f in sorted((KOK / "colab/yaris").glob("*")):
                z.write(f, f"yaris/{f.name}")
            for f in sorted((KOK / "referans").glob("*")):
                z.write(f, f"referans/{f.name}")
        print(f"{hedef}  ({len(is_['cumleler'])} cümle)")
        return
    # Uzun ünlü indeksleri: şapkalı okunuşla karşılaştırılır (şapka 1:1 harf, uzunluk aynı).
    for x in (p for p in parcalar if "uzun" not in p):
        sapkali = okunus(x["metin"], sozluk, {**ayarlar["okunus"], "sapka": "koru"})
        if len(sapkali) == len(x["okunus"]):
            # Uzun ünlü: şapkalı okunuşta şapkalı harf (okunuş şapkalıysa da ölçülür)
            x["uzun"] = [i for i, c in enumerate(sapkali) if c in "âîûÂÎÛ"]
    is_ = {"konu": konu, "mod": a.mod, "ayar": ayarlar["seslendirme"], "parcalar": parcalar}
    hedef = KOK / "dist" / f"is-{konu}.zip"
    hedef.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("is.json", json.dumps(is_, ensure_ascii=False, indent=1))
        for f in ["colab/seslendir.py", "colab/calistir.sh", "metin/okunus.py", "metin/okunus.tsv", "metin/olcum.py", "colab/tonlama.py", "colab/uzatma.py",
                  "colab/ayar_tarama.py", "colab/referans_ara.py",
                  "colab/gercek_ses.py", "colab/ses_adaylari.py", "colab/ses_tasarimi.py"]:
            if (KOK / f).exists():
                z.write(KOK / f, Path(f).name)
        for f in sorted((KOK / "referans").glob("*.wav")) + sorted((KOK / "referans").glob("*.json")):
            z.write(f, f"referans/{f.name}")
    print(f"{hedef}  ({len(parcalar)} parça)")


if __name__ == "__main__":
    main()
