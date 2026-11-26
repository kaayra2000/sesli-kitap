#!/usr/bin/env python3
"""
Akademik transliterasyonla yazılmış metinleri (ör. Kufralı, Nakşbendîliğin Kuruluş ve Yayılışı) okunuşa hazırlar.

Metnin aslı değişmez; bu ön işleme yalnız seslendirilecek metni üretir:
- kaynak gösterme (bk., ayn. esr., s. 12 …) ayraçları ve silsile sıra numaraları atılır,
- "al-" harf-i tarifi Türkçe okunuşa çevrilir (al-Dîn → ed-Dîn, al-Hamadânî → el-Hamadânî),
- yaygın ad kalıpları Türkçe söylenişine çevrilir (Bahâ’ al-Dîn → Bahâeddîn, ‘Abd Allâh → Abdullâh,
  Abû → Ebû, Hᵛâca → Hâce),
- kısaltmalar açılır (ölm. → ölümü, b. → bin), Roma rakamlı sıra sayıları yazıya çevrilir (IV. asır → dördüncü asır).
"""

import re

BUYUK = "A-ZÇĞİÖŞÜÂÎÛ"
HARF = "A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"
GUNES = set("tsşdzrnl")  # şemsî harfler: al- ardından gelen harfe benzeşir

SIRA = {1: "birinci", 2: "ikinci", 3: "üçüncü", 4: "dördüncü", 5: "beşinci", 6: "altıncı", 7: "yedinci",
        8: "sekizinci", 9: "dokuzuncu", 10: "onuncu", 11: "on birinci", 12: "on ikinci", 13: "on üçüncü",
        14: "on dördüncü", 15: "on beşinci", 16: "on altıncı", 17: "on yedinci", 18: "on sekizinci",
        19: "on dokuzuncu", 20: "yirminci"}
ROMA = {"I": 1, "V": 5, "X": 10, "L": 50}

# Kaynak gösteren ayraçlar: içinde bu işaretlerden biri olan (...) okunmaz
KAYNAK = re.compile(r"\bbk\.|\bayn\.|\bgöst\.|\bmes\.|\bnr\.|\bv\.dd?\.|\btrc\.|\bs\. ?\d|\b[IVX]+, \d|Bulak|Mısır, \d|İstanbul, \d")

# Paragrafın tamamı okunmaz (aktaranın notu, şema açıklaması, kaynak listesi)
ATLA = re.compile(r"^(\[Aktaran notu|Şemadaki işaretler|Silsilelerin bu kısmı)")


def roma(s: str) -> int | None:
    if not re.fullmatch(r"[IVXL]+", s):
        return None
    t, onceki = 0, 0
    for c in reversed(s):
        d = ROMA[c]
        t, onceki = (t - d, onceki) if d < onceki else (t + d, d)
    return t


def _sira(m: re.Match) -> str:
    n = roma(m.group(1))
    if not n or n not in SIRA:
        return m.group(0)
    s, sonraki = SIRA[n], m.group(2)
    if sonraki.isupper():  # başlık: "IV. FASIL" -> "Dördüncü Fasıl"
        sonraki = sonraki[0] + sonraki[1:].replace("I", "ı").replace("İ", "i").lower()
    if sonraki[0].isupper() and sonraki != m.group(2) or m.start() == 0:
        s = s.replace("i", "İ", 1) if s[0] == "i" else s[0].upper() + s[1:]
    return s + " " + sonraki


def _al(m: re.Match) -> str:
    on, harf = m.group(1), m.group(2)
    k = harf.lower()
    tarif = f"e{k}-" if k in GUNES else "el-"
    return on + tarif + harf


def _abd(m: re.Match) -> str:
    """‘Abd al-Rahmân -> Abdurrahmân, ‘Abd al-Hâlik -> Abdülhâlik, ‘Abd al-‘Azîz -> Abdülazîz."""
    ayn, harf = m.group(1), m.group(2)
    k = harf.lower()
    return "Abdu" + k + k if k in GUNES and not ayn else "Abdül" + k


def kaynak_at(metin: str) -> str:
    """İç içe olmayan ayraçlardan kaynak gösterenleri ve silsile numaralarını siler."""
    onceki = None
    while onceki != metin:
        onceki = metin
        metin = re.sub(r"\s*\(([^()]*)\)", lambda m: "" if KAYNAK.search(m.group(1)) else m.group(0), metin)
    metin = re.sub(r"\s*\(\d{1,2}\)", "", metin)  # silsile sıra numarası: Ma‘rûf al-Karhî (4)
    metin = re.sub(r"⁽\d⁾\s*", "", metin)
    return metin


def duzelt(paragraf: str) -> str | None:
    """Seslendirilecek paragrafı döndürür; okunmayacaksa None."""
    p = paragraf.strip()
    if ATLA.match(p):
        return None
    p = p.replace("[?]", "").replace("*", "")
    p = re.sub(r"\[([^\]^]*)\]", r"\1", p)  # aktaranın tamamladığı harfler: [hakkı]nda -> hakkında
    p = kaynak_at(p)
    p = re.sub(r"^-\s+", "", p)  # liste imi
    p = re.sub(rf"\s+-\s+(?=[{BUYUK}‘(])", ", ", p)  # birleşmiş liste öğeleri
    # Ad kalıpları
    p = p.replace("Hᵛâcagân", "Hâcegân").replace("Hᵛâca", "Hâce").replace("Hᵛ", "H")
    p = re.sub(r"\bAbû\s*’l-", "Ebü’l-", p)
    p = re.sub(r"\bAbû\b", "Ebû", p)
    p = re.sub(r"\bAbî\s*’l-", "Ebi’l-", p)
    p = re.sub(r"\bAbî\b", "Ebî", p)
    p = re.sub(rf"‘Abd al-(‘?)([{HARF}])", _abd, p)
    p = re.sub(r"‘?(Abd|‘Ubayd|Ubayd) Allâh", lambda m: {"Abd": "Abdullâh"}.get(m.group(1).strip("‘"), "Ubeydullâh"), p)
    p = re.sub(rf"\b([{BUYUK}][{HARF}‘]+) All[âa]h\b", lambda m: m.group(1) + "ullâh", p)
    p = re.sub(rf"(?<![{HARF}‘])([{BUYUK}‘][{HARF}‘]*?)’? al-Dîn\b", lambda m: m.group(1) + "eddîn", p)
    p = re.sub(rf"(^|[\s(“‘-])al-(‘?[{HARF}])", _al, p)
    # Kısaltmalar
    p = re.sub(r"\bölm\.\s*", "ölümü ", p)
    p = re.sub(r"\bdoğm\.\s*", "doğumu ", p)
    p = re.sub(rf"(?<=[{HARF}])\s+b\.\s+(?=[{BUYUK}‘’])", " bin ", p)
    p = re.sub(r"\(s\.a\.v\.\)|\bs\.a\.v\.", "sallallâhu aleyhi ve sellem", p)
    p = re.sub(r"\s*=\s*", ", ", p)
    # Roma rakamlı sıra sayısı: "IV. ve V. asırlar", "II. Bâyezîd", "I. FASIL"
    p = re.sub(r"\b([IVXL]{1,5})\.\s+(?=\S)(\S+)", _sira, p)
    p = re.sub(r"\(\s*\)", "", p)
    p = re.sub(r"\s+([,.;:])", r"\1", p)
    p = re.sub(r",\s*,", ",", p)
    p = re.sub(r"\s{2,}", " ", p).strip()
    return p or None

