#!/usr/bin/env python3
"""
Kitabın Markdown aktarımını (bedri_gencer/claude/X/X.md) seslendirme parçalarına böler.

Çıktı JSON: [{"id": "b012-p03-c1", "tur": "baslik|paragraf", "sayfa": 9, "metin": aslı, "okunus": modele giden,
              "ara": parçadan sonraki sessizlik (sn)}, ...]
Atlananlar: sayfa imleri, fihrist tabloları, dipnot tanımları. Arap harfli ibare okunmaz; dipnotunda ya da hemen
ardındaki paragrafta Türkçe meali varsa meal okunur.

Kullanım: python3 metin/hazirla.py <kitap.md> -o kitap.json [--en-cok 28]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okunus import ARAP, okunus, sozluk_yukle  # noqa: E402

ARALAR = {"virgul": 0.3, "cumle": 0.55, "paragraf": 1.0, "baslik": 1.6}
KISALTMA = r"(?<![\wÇĞİÖŞÜçğıöşü])(?:hz|Hz|r\.a|s|sr|ay|bkz|vb|vs|ö|Ö|h|m)\."


def dipnotlar(md: str) -> dict[str, str]:
    """[^m3]: ... «arapça» “meal” -> {"m3": "meal"} (yalnız tırnaklı meali olanlar)."""
    sonuc = {}
    for kimlik, govde in re.findall(r"^\[\^([^\]]+)\]:\s*(.+)$", md, re.M):
        meal = re.findall(r"“([^”]+)”", govde)
        if meal and re.search(f"[{ARAP}]", govde):
            sonuc[kimlik] = " ".join(meal)
    return sonuc


def mealleri_koy(paragraf: str, notlar: dict[str, str]) -> str:
    """«arapça»[^mN] -> , meal, ; «arapça» — açıklama -> açıklama; geri kalan Arapça okunuşta düşer."""
    paragraf = re.sub(rf"«[^»]*[{ARAP}][^»]*»\s*[—–]\s*", "", paragraf)

    def koy(m: re.Match) -> str:
        meal = notlar.get(m.group(1))
        return f", {meal.rstrip('.')}, " if meal else " "
    return re.sub(rf"«[^»]*[{ARAP}][^»]*»\s*\[\^([^\]]+)\]", koy, paragraf)


def cumlelere_bol(metin: str) -> list[str]:
    korunan = re.sub(KISALTMA, lambda m: m.group(0).replace(".", "<N>"), metin)
    parca = re.split(r"(?<=[.!?:;])\s+(?=[^\s])", korunan)
    return [p.replace("<N>", ".").strip() for p in parca if p.strip()]


def uzunu_bol(cumle: str, en_cok: int) -> list[str]:
    """en_cok kelimeden uzun cümleyi ortaya en yakın virgülden ikiye böler (gerekirse tekrar)."""
    kelimeler = cumle.split()
    if len(kelimeler) <= en_cok:
        return [cumle]
    adaylar = [i for i, w in enumerate(kelimeler[:-3], 1) if w.endswith(",") and i >= 4]
    if not adaylar:
        adaylar = [i for i, w in enumerate(kelimeler[:-3], 1) if kelimeler[i] in ("ve", "fakat", "lâkin", "ki") and i >= 4]
    if not adaylar:
        return [cumle]
    orta = len(kelimeler) / 2
    i = min(adaylar, key=lambda k: abs(k - orta))
    return uzunu_bol(" ".join(kelimeler[:i]), en_cok) + uzunu_bol(" ".join(kelimeler[i:]), en_cok)


def baslik_harfi(metin: str) -> str:
    """Tamamı büyük harfli metni Türkçe kurala göre ilk harfleri büyük yazar (str.title İ'yi bozar)."""
    def kelime(w: str) -> str:
        k = w.replace("İ", "i").replace("I", "ı").lower()
        i = next((j for j, c in enumerate(k) if c.isalpha()), None)  # baştaki ‘ ’ işaretleri atlanır
        return k if i is None else k[:i] + k[i].replace("i", "İ").replace("ı", "I").upper() + k[i + 1:]
    kucuk_kelime = {"ve", "ile", "ki", "de", "da", "fî", "fi", "min", "an", "ala", "alâ", "bi", "li"}

    def tam(w: str) -> str:
        # İzafet ve harf-i tarif ekleri küçük kalır: Temessük-i Hakîkî, Seyyidü’l-Enbiyâ
        bas, *ekler = w.split("-")
        b = bas.replace("İ", "i").replace("I", "ı").lower()
        b = b if b in kucuk_kelime else kelime(bas)
        return "-".join([b] + [e.replace("İ", "i").replace("I", "ı").lower() if len(e) <= 3 else kelime(e)
                               for e in ekler])
    sonuc = re.sub(r"\S+", lambda m: tam(m.group(0)), metin)
    return sonuc[:1].upper() + sonuc[1:]


def bloklar(md: str):
    """(tur, sayfa, metin) üretir; sayfa sonunda bölünen paragrafı birleştirir."""
    ham = list(_bloklar(md))
    for i, (tur, sayfa, metin) in enumerate(ham):
        if metin is None:
            continue
        while (tur == "paragraf" and not re.search(r"[.!?:;”»)\]]$", metin) and i + 1 < len(ham)
               and ham[i + 1][0] == "paragraf" and ham[i + 1][2]
               and (ham[i + 1][2][0].islower() or re.search(r"\w-$", metin))):
            # Sayfa sonunda hecelenen kelime ("dola-" + "yısiyle") bitişik, değilse boşlukla birleşir
            metin = f"{metin[:-1]}{ham[i + 1][2]}" if re.search(r"\w-$", metin) else f"{metin} {ham[i + 1][2]}"
            ham[i + 1] = (ham[i + 1][0], ham[i + 1][1], None)
            i += 1
        yield tur, sayfa, metin


def _bloklar(md: str):
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)
    sayfa = 0
    for blok in re.split(r"\n\s*\n", md):
        blok = blok.strip()
        if not blok:
            continue
        if m := re.fullmatch(r"\[s\. ([^\]]+)\]", blok):  # sayfa imi: [s. 12], [s. IV], [s. kapak]
            sayfa = int(m.group(1)) if m.group(1).isdigit() else sayfa
            continue
        if blok.startswith("|") or re.match(r"^\[\^[^\]]+\]:", blok):
            continue
        if blok.startswith("#"):
            yield "baslik", sayfa, blok.lstrip("#").strip()
        else:
            yield "paragraf", sayfa, " ".join(blok.split())


def hazirla(md: str, en_cok: int = 28, ayar: dict | None = None, birlestir: bool = False,
            on_isle=None, baslangic: str | None = None) -> list[dict]:
    """on_isle: kitaba özgü ön işleme (metin -> okunacak metin ya da None = atla); baslangic: bu başlıktan
    önceki bloklar (kapak, içindekiler) okunmaz."""
    notlar = dipnotlar(md)
    sozluk = sozluk_yukle()
    parcalar = []
    onceki_arapca = False
    basladi = baslangic is None
    for n, (tur, sayfa, metin) in enumerate(bloklar(md)):
        if not basladi:
            if tur != "baslik" or metin != baslangic:
                continue
            basladi = True
        if on_isle is not None and (metin := on_isle(metin)) is None:
            continue
        tamamen_arapca = re.fullmatch(rf"«[^»]*[{ARAP}][^»]*»(\s*\[\^[^\]]+\])?", metin) is not None
        if tamamen_arapca:
            onceki_arapca = True
            # Meali dipnotta ise onu oku; değilse ardından gelen “...” paragrafı okunacak.
            ref = re.search(r"\[\^([^\]]+)\]", metin)
            if ref and ref.group(1) in notlar:
                metin = notlar[ref.group(1)]
            else:
                continue
        elif onceki_arapca and re.fullmatch(r"“[^”]+”\.?", metin):
            metin = metin.strip("“”.") + "."
        onceki_arapca = tamamen_arapca
        metin = mealleri_koy(metin, notlar)
        metin = metin.replace("**", "")
        if "FİHRİST" in metin:
            continue
        if metin.isupper():
            metin = baslik_harfi(metin)
        cumleler = [p for c in cumlelere_bol(metin) for p in uzunu_bol(c, en_cok)]
        if birlestir and tur == "paragraf":
            # Paragraf içindeki cümleler en_cok kelimeye kadar tek parçada okunur: model bağlamı görür, tonlama
            # doğallaşır, çok kısa (1-2 sn) parça kalmaz.
            toplu, kova = [], []
            for c in cumleler:
                if kova and len(" ".join(kova + [c]).split()) > en_cok:
                    toplu.append(" ".join(kova))
                    kova = []
                kova.append(c)
            if kova:
                toplu.append(" ".join(kova))
            cumleler = toplu
        for k, c in enumerate(cumleler):
            soz = okunus(c, sozluk, ayar)
            if not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", soz):
                continue
            if parcalar and parcalar[-1]["okunus"] == soz:  # kapak başlığı sayfada iki kez
                continue
            son = k == len(cumleler) - 1
            ara = ARALAR[tur] if son and tur == "baslik" else ARALAR["paragraf"] if son else (
                ARALAR["cumle"] if re.search(r"[.!?:;]$", c) else ARALAR["virgul"])
            parcalar.append({"id": f"b{n:04d}-c{k:02d}", "tur": tur, "sayfa": sayfa, "metin": c, "hedef": c, "okunus": soz,
                             "ara": ara})
    return parcalar


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kitap", type=Path)
    p.add_argument("-o", "--cikti", type=Path, required=True)
    p.add_argument("--en-cok", type=int, default=28, help="bir parçadaki en çok kelime")
    a = p.parse_args()
    parcalar = hazirla(a.kitap.read_text(encoding="utf-8"), a.en_cok)
    a.cikti.parent.mkdir(parents=True, exist_ok=True)
    a.cikti.write_text(json.dumps(parcalar, ensure_ascii=False, indent=1), encoding="utf-8")
    kelime = sum(len(x["okunus"].split()) for x in parcalar)
    print(f"{len(parcalar)} parça, {kelime} kelime, ~{kelime / 130:.0f} dk (130 kelime/dk)")


if __name__ == "__main__":
    main()
