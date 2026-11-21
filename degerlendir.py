#!/usr/bin/env python3
"""
Colab çıktısını açar, başarı ölçütlerine göre değerlendirir, en kötü parçaları ve önceki turla farkı yazar.

  python3 degerlendir.py <cikti-turNN.zip> [--tur N]

Çıktı: iterasyonlar/turNN/ (açılmış çıktı + rapor.md), iterasyonlar/gecmis.tsv (tur başına bir satır).
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / "metin"))
from olcum import hata  # noqa: E402

CER_SINIR = 0.03   # Whisper (eşitlenmiş)
CTC_SINIR = 0.06   # CTC (eşitlenmiş); bir cümle iki hakem de hata görürse yanlış sayılır
OLCUT = {  # ad: (alan, karşılaştırma, sınır)
    "yanlış kelimeli parça yok (Whisper > %3 ve CTC > %6)": ("yanlis", "==", 0),
    "ortalama Whisper CER <= %1.5": ("whisper_cer_ort", "<=", 0.015),
    "kuyruk (ses artığı) yok": ("kuyruk", "==", 0),
    "takılma (uzun sessizlik) yok": ("takilma", "==", 0),
    "kırpılma yok": ("kirpilma", "==", 0),
    "UTMOS ort >= 3.3": ("mos_ort", ">=", 3.3),
    "hız 11-15.5 harf/sn": ("hiz_ort", "aralik", (11, 15.5)),
    "uzun ünlü / kısa ünlü >= 1.4": ("uzun_kisa_sonra", ">=", 1.4),
    "tonlama insan aralığında >= %75": ("tonlama_uyum_ort", ">=", 0.75),
}
GECMIS_ALAN = ["whisper_cer_ort", "whisper_wer_ort", "ctc_cer_ort", "mos_ort", "yanlis", "kuyruk", "takilma",
               "hiz_ort", "uzun_kisa_sonra", "tonlama_uyum_ort", "duz_sonu_dusen", "perde_std_ort", "aday_ort", "sure_sn"]


def gecti(deger, kar, sinir) -> bool:
    if kar == "aralik":
        return sinir[0] <= deger <= sinir[1]
    return {"==": deger == sinir, "<=": deger <= sinir, ">=": deger >= sinir}[kar]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cikti", type=Path)
    p.add_argument("--tur", type=int)
    a = p.parse_args()
    tur = a.tur if a.tur is not None else int("".join(c for c in a.cikti.stem if c.isdigit()) or 0)
    hedef = KOK / "iterasyonlar" / a.cikti.stem.replace("cikti-", "")
    if a.cikti.suffix == ".zip":
        hedef.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(a.cikti).extractall(hedef)
    else:
        hedef = a.cikti
    veri = json.loads((hedef / "sonuc.json").read_text(encoding="utf-8"))
    oz, parcalar = veri["ozet"], veri["parcalar"]
    # Whisper hatası yerelde, güncel eşitleme kuralıyla yeniden hesaplanır (Colab'deki değer "whisper_colab").
    for r in parcalar:
        r.setdefault("whisper_colab", r["whisper"])
        ref = r.get("hedef") or r.get("metin") or r["okunus"]  # kitabın asıl metni (okunuş modele yöneliktir)
        r["whisper"] = hata(ref, r["duyulan"], esit=True)
        r["ctc_esit"] = hata(ref, r.get("ctc_duyulan", ""), esit=True)
    oz["whisper_cer_ort"] = round(sum(r["whisper"]["cer"] for r in parcalar) / len(parcalar), 4)
    oz["whisper_wer_ort"] = round(sum(r["whisper"]["wer"] for r in parcalar) / len(parcalar), 4)
    oz["yanlis"] = sum(r["whisper"]["cer"] > CER_SINIR and r["ctc_esit"]["cer"] > CTC_SINIR for r in parcalar)
    oz["ctc_esit_cer_ort"] = round(sum(r["ctc_esit"]["cer"] for r in parcalar) / len(parcalar), 4)
    (hedef / "sonuc.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")

    satir = [f"# {hedef.name}", "", "## Ölçütler", ""]
    hepsi = True
    for ad, (alan, kar, sinir) in OLCUT.items():
        if oz.get(alan) is None:
            satir.append(f"- [ ] {ad}: ölçülmedi")
            hepsi = False
            continue
        ok = gecti(oz[alan], kar, sinir)
        hepsi &= ok
        satir.append(f"- [{'x' if ok else ' '}] {ad}: {oz[alan]}")
    satir += ["", f"**SONUÇ: {'BAŞARILI' if hepsi else 'DEVAM'}**", "",
              f"CTC CER ort {oz['ctc_cer_ort']} ({oz.get('ctc_hakem')}), WER {oz['whisper_wer_ort']}, "
              f"aday ort {oz['aday_ort']}, süre {oz['sure_sn']} sn", "",
              "## En kötü parçalar (Whisper + 0.5 CTC)", ""]
    kotu = sorted(parcalar, key=lambda r: -(r["whisper"]["cer"] + 0.5 * r.get("ctc", {}).get("cer", 0)))[:15]
    for r in kotu:
        satir += [f"### {r['id']}  CER {r['whisper']['cer']}  CTC {r.get('ctc', {}).get('cer')}  MOS {r['mos']}  "
                  f"kuyruk {r['kuyruk']}  boşluk {r['bosluk']}  hız {r['hiz']}",
                  f"- hedef:   {r['okunus']}", f"- whisper: {r['duyulan']}", f"- ctc:     {r.get('ctc_duyulan', '')}", ""]

    gecmis = KOK / "iterasyonlar" / "gecmis.tsv"
    onceki = None
    if gecmis.exists():
        satirlar = gecmis.read_text(encoding="utf-8").splitlines()
        kayitlar = [s.split("\t") for s in satirlar[1:] if s and not s.startswith(hedef.name + "\t")]
        if kayitlar:
            onceki = dict(zip(satirlar[0].split("\t"), kayitlar[-1]))
    else:
        satirlar = ["\t".join(["tur"] + GECMIS_ALAN + ["ayar"])]
        kayitlar = []
    if onceki:
        satir += ["## Önceki turla fark", ""] + [f"- {k}: {onceki.get(k)} -> {oz.get(k)}" for k in GECMIS_ALAN[:12]]
    yeni = "\t".join([hedef.name] + [str(oz.get(k)) for k in GECMIS_ALAN] + [json.dumps(oz["ayar"], ensure_ascii=False)])
    gecmis.write_text("\n".join([satirlar[0]] + ["\t".join(k) for k in kayitlar] + [yeni]) + "\n", encoding="utf-8")
    (hedef / "rapor.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    print("\n".join(satir))


if __name__ == "__main__":
    main()
