"""
Okunuş: transliterasyonlu Osmanlı Türkçesi metni, TTS modelinin doğru okuyacağı yazıya çevirir.

Alt yazıda metnin aslı kalır; yalnız modele giden metin değişir. Kurallar bir insan okuyucunun eski imlâyı
sesli okurken yaptığına göre seçildi ("etdim" -> "ettim", "içün" -> "için", "sebeb" -> "sebep").
Kural ayarları `AYARLAR`'dadır; döngü (README, "Öz yinelemeli test") bu ayarları dener.
Sözlük `okunus.tsv` (yazılan<TAB>okunacak, tam kelime) kurallardan önce uygulanır.
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

AYARLAR = {
    "sapka": "kaldir",       # â î û: "koru" ya da "kaldir"
    "ünsüz_benzesme": True,  # etdim -> ettim, çokdur -> çoktur, sebeb -> sebep
    "eski_ekler": True,      # içün -> için, anı -> onu, etmeğe -> etmeye
    "cift_y": True,          # ehemmiyyet -> ehemmiyet
    "tire_birlestir": True,  # şerî‘at-i ğarrâ -> şeriati garra, fi’l-hakîka -> filhakika
}

ARAP = r"؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"
HARF = "A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"

BIRLER = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
ONLAR = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def sayi_yazi(n: int) -> str:
    """Tam sayıyı Türkçe yazıya çevirir (0-999999)."""
    if n == 0:
        return "sıfır"
    parcalar = []
    binler, kalan = divmod(n, 1000)
    if binler:
        parcalar.append("bin" if binler == 1 else f"{sayi_yazi(binler)} bin")
    yuz, kalan = divmod(kalan, 100)
    if yuz:
        parcalar.append("yüz" if yuz == 1 else f"{BIRLER[yuz]} yüz")
    on, bir = divmod(kalan, 10)
    parcalar += [w for w in (ONLAR[on], BIRLER[bir]) if w]
    return " ".join(parcalar)


def sozluk_yukle(yol: Path = HERE / "okunus.tsv") -> list[tuple[str, str]]:
    ciftler = []
    if yol.exists():
        for satir in yol.read_text(encoding="utf-8").splitlines():
            if satir.strip() and not satir.startswith("#") and "\t" in satir:
                yazilan, okunan = satir.split("\t", 1)
                ciftler.append((yazilan.strip(), okunan.strip()))
    # Uzun kalıp önce: "radıya ‘anhu’l-Bârî" "radıya"dan önce eşleşsin.
    return sorted(ciftler, key=lambda c: -len(c[0]))


def sozluk_uygula(metin: str, ciftler: list[tuple[str, str]]) -> str:
    for yazilan, okunan in ciftler:
        metin = re.sub(rf"(?<![{HARF}]){re.escape(yazilan)}(?![{HARF}])", okunan, metin)
    return metin


def kucuk(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


ISTISNA = {"muhammed", "seyyid", "ahmed", "mahmud", "mahmûd", "abd", "nakşibend", "gucdüvânî", "ğucdüvânî"}


def benzesme(kelime: str) -> str:
    """Eski imlânın yazdığı ötümlü ünsüzü okunuşa çevirir."""
    # Ötümsüz ünsüzden (ya da b/c'den) sonra gelen ek başı d -> t: etdim, çokdur, şartdır, sebebden, hâricdir
    if any(kucuk(kelime).endswith(x) for x in ISTISNA):
        return kelime
    kelime = re.sub(r"([çfhkpsşt])d(?=[ıiuüae])", r"\1t", kelime)
    # b/c + d yalnız ekte (sebebden, hâricdir); "Abdullah", "abdest" gibi kök içi bd kalır
    kelime = re.sub(r"(?<=[{0}]{{2}})([bc])d(?=[ıiuüae])".format(HARF),
                    lambda m: {"b": "p", "c": "ç"}[m.group(1)] + "t", kelime)
    # Kelime sonu b, c -> p, ç (sebeb, kalb, kitâb, hâric); d yalnız 4+ harfli kelimede (Ahmed, vücûd, murâd)
    kelime = re.sub(r"b(?=l[ae]r)", "p", kelime)  # kitâblar, mektûblar
    kelime = re.sub(r"b$", "p", kelime)
    kelime = re.sub(r"c$", "ç", kelime)
    if len(kelime) >= 4:
        kelime = re.sub(r"(?<=[âîûaeıioöuü])d$", "t", kelime)
        kelime = re.sub(r"(?<=[rln])d$", "t", kelime)
    return kelime


def eski_ek(kelime: str) -> str:
    k = kelime
    k = re.sub(r"^(i)çün$", r"\1çin", k)
    k = re.sub(r"^İçün$", "İçin", k)
    k = re.sub(r"^([Aa])n(ı|ın|ları|lara|ların|larda|lardan)$",
               lambda m: ("O" if m.group(1) == "A" else "o") + "n" + {"ı": "u", "ın": "un"}.get(m.group(2), m.group(2)), k)
    k = re.sub(r"(m)eğe$", r"\1eye", k)
    k = re.sub(r"(m)ağa$", r"\1aya", k)
    return k


def okunus(metin: str, ciftler: list[tuple[str, str]] | None = None, ayar: dict | None = None) -> str:
    a = {**AYARLAR, **(ayar or {})}
    ciftler = sozluk_yukle() if ciftler is None else ciftler
    t = re.sub(r"\[\^[^\]]+\]", "", metin)                 # dipnot imleri
    t = re.sub(rf"«[^»]*[{ARAP}][^»]*»", " ", t)           # Arap harfli ibare (meali ayrıca verilir)
    t = re.sub(rf"[{ARAP}ً-ٰٟ]+", " ", t)
    t = t.replace("*", "").replace("✱", ",").replace("…", ",")
    t = re.sub(r"\s*[—–]\s*", ", ", t)
    t = t.replace("[", "").replace("]", "")
    t = re.sub(r"[“”\"«»]", "", t)
    t = sozluk_uygula(t, ciftler)
    t = re.sub(r"\b(\d+)/(\d+)\b", lambda m: f"{sayi_yazi(int(m.group(1)))} {sayi_yazi(int(m.group(2)))}", t)
    t = re.sub(r"\b\d{1,6}\b", lambda m: sayi_yazi(int(m.group(0))), t)
    t = t.replace("‘", "")
    t = t.replace("Nakşbend", "Nakşibend")
    if a["tire_birlestir"]:
        t = re.sub(rf"(?<=[{HARF}])[’']?-(?=[{HARF}])", "", t)
    t = re.sub(rf"(?<=[{HARF}])[’'](?=[{HARF}])", "", t)    # hemze ve kesme: şey’in -> şeyin, Allah’ın -> Allahın
    t = re.sub(r"[’']", "", t)

    def kelime_isle(m: re.Match) -> str:
        w = m.group(0)
        if a["eski_ekler"]:
            w = eski_ek(w)
        # ğ (gayn) -> g: kelime başında, ünsüzden sonra ya da â/û önünde (ğâyet, meşğûl, ğark)
        w = re.sub(r"^ğ", "g", w)
        w = re.sub(r"^Ğ", "G", w)
        w = re.sub(r"(?<=[bcçdfghjklmnprsştvyz])ğ", "g", w)
        w = re.sub(r"ğ(?=[âû])", "g", w)
        if a["cift_y"]:
            w = re.sub(r"([iıîİ])yy([eaâ])", r"\1y\2", w)
        if a["ünsüz_benzesme"]:
            w = benzesme(w)
        if a["sapka"] == "kaldir":
            w = w.translate(str.maketrans("âîûÂÎÛ", "aiuAİU"))
        return w

    t = re.sub(rf"[{HARF}]+", kelime_isle, t)
    t = re.sub(r"(?<=[a-zçğıöşü])([A-ZÇĞİÖŞÜ])", lambda m: kucuk(m.group(1)), t)  # esSeyyid -> esseyyid
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"^\s*[,;:]\s*", "", t)
    return " ".join(t.split())
