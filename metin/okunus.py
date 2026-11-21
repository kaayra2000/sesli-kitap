"""
Okunuş: transliterasyonlu Osmanlı Türkçesi metni, TTS modelinin doğru okuyacağı yazıya çevirir.

Alt yazıda metnin aslı kalır; yalnız modele giden metin değişir. Varsayılan, Osmanlıca bilen bir okuyucu gibi
kelimeyi değiştirmeden okumaktır (içün, ma‘lûm -> mâlûm, etdim); yalnız TTS'in gerektirdiği mekanik dönüşüm yapılır.
Günümüz okunuşuna çeviren kurallar (GUNUMUZ) hakemin eşitlemesi içindir: Whisper "içün"ü "için" diye yazar,
bu hata sayılmasın.
Kural ayarları `AYARLAR`'dadır; döngü (README, "Öz yinelemeli test") bu ayarları dener.
Sözlük `okunus.tsv` (yazılan<TAB>okunacak, tam kelime) kurallardan önce uygulanır.
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

AYARLAR = {
    # Varsayılan: Osmanlıca bilen bir okuyucu gibi, kelime değiştirmeden (kullanıcı kararı, 2026-11-19).
    "sapka": "koru",          # â î û: "koru" (uzun ünlü), "kaldir" ya da "cift" (â -> aa: Kur’ân -> Kuraan)
    "gayn": True,             # ğ (gayn) -> g: ğâyet -> gâyet (TTS "ğ"yi yumuşak g gibi yutar)
    "tire_birlestir": True,   # fi’l-hakîka -> filhakîka, mertebe-i ‘azîmet -> mertebei azîmet
    "izafet_y": True,         # ünlüden sonra izafet: mertebe-i -> mertebeyi, Hudâ-ı -> Hudâyı (okuyucunun y kayması)
    # s+h, c+h, t+h, z+h, d+h, k+h, p+h: model İngilizce çift harf sanıyor (ashâbına -> "ahşabına", 2026-11-20).
    # "yok", "tire" (as-hâbına), "kesme" (as’hâbına) ya da "zwnj" (görünmez ayraç U+200C).
    "harf_ayir": "zwnj",
    # Kelime sonu Arapça ünsüz kümesi (hamd, kesb, fazl, nefy, vech): model son ünsüzü yutuyor (2026-11-20).
    # "yok", "sert" (son ötümlü ötümsüzleşir: hamt, kesp), "zwnj" (iki ünsüz arasına görünmez ayraç), "sert_zwnj", "sert_cift" (r/l/m/n sonu çiftlenir: sekrr).
    # Deney 12: zwnj araya ünlü sokuyor (sekr -> sektir); "sert" Hamd'ı düzeltti, genel doğruluk aynı.
    "son_kume": "sert",
    # Kelime içi ünsüz kümesindeki ötümlü (kalblerinden -> "kallerinden" okundu, 2026-11-20): "yok" | "sert" (kalpler).
    # Deney 15: "sert" kalplerinden yerine "kaltlerinden" çıkardı; kapalı.
    "ic_kume": "yok",
    # Kelime içi ayn (ma‘nen) ve hemze (te’sîr): okuyucu kısa bir durak (gırtlak vuruşu) yapar; silinince "manen" oluyor.
    # "yok" (silinir), "kesme" (’), "zwnj" (görünmez ayraç), "tire" (ma-nen). "isaret" yalnız ölçüm içindir.
    # Deney 15: tire durağı 0.06 -> 0.10 sn, Whisper %1.57 -> %1.30, tonlama %68 -> %83.
    "ayn": "tire",
    # Ön ünlülü hecelerden sonra û (sülûk, vücûd, füyûzât): model ünlü uyumuyla ü okuyor ("sülük").
    # "yok" | "cift" (û -> uu: sülüuuk değil sülu-uk; yalnız bu durumda).
    # Deney 15: sülûk "sülük" -> "süluk"; doğruluk değişmedi.
    "uyum_kir": "cift",
    # Günümüz okunuşuna çeviren kurallar; varsayılan kapalı, yalnız hakem eşitlemesinde kullanılır:
    "ünsüz_benzesme": False,  # etdim -> ettim, sebeb -> sebep
    "eski_ekler": False,      # içün -> için, anı -> onu
    "cift_y": False,          # ehemmiyyet -> ehemmiyet
}
GUNUMUZ = {"sapka": "kaldir", "gayn": True, "tire_birlestir": True, "izafet_y": True, "ünsüz_benzesme": True, "eski_ekler": True,
           "cift_y": True}

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


UNLU_HARF = "aeıioöuüâîûAEIİOÖUÜÂÎÛ"
TR_KUME = {"rt", "rk", "nk", "st", "lt", "nt", "rç", "lç", "şt", "ft", "ks", "rs", "rp", "lk", "mp", "ns", "nç", "rş", "şk"}


def son_kume(kelime: str, bicim: str) -> str:
    """Kelime sonundaki Türkçede olmayan ünsüz kümesini modelin okuyacağı biçime getirir."""
    if bicim == "yok" or len(kelime) < 3 or kelime[-1] in UNLU_HARF or kelime[-2] in UNLU_HARF:
        return kelime
    if kucuk(kelime[-2:]) in TR_KUME:
        return kelime
    if "sert" in bicim:
        kelime = kelime[:-1] + {"b": "p", "c": "ç", "d": "t", "g": "k"}.get(kelime[-1], kelime[-1])
    if "cift" in bicim and kelime[-1] in "rlmnRLMN" and kelime[-1] != kelime[-2]:
        kelime = kelime + kelime[-1]  # sekr -> sekrr: akıcı son ünsüz yutulmasın
    if "zwnj" in bicim and kelime[-1] != kelime[-2]:
        kelime = kelime[:-1] + "\u200c" + kelime[-1]
    return kelime


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
    # Parantez içi (dua, açıklama) ayrı bir söz öbeğidir: virgülle ayrılır, yoksa cümleye yapışıp yutuluyor.
    t = re.sub(r"\s*\(\s*", ", ", t)
    t = re.sub(r"\s*\)\s*(?=[,.;:!?])", "", t)
    t = re.sub(r"\s*\)\s*", ", ", t)
    t = re.sub(r"[“”\"«»]", "", t)
    t = sozluk_uygula(t, ciftler)
    t = re.sub(r"\b(\d+)/(\d+)\b", lambda m: f"{sayi_yazi(int(m.group(1)))} {sayi_yazi(int(m.group(2)))}", t)
    t = re.sub(r"\b\d{1,6}\b", lambda m: sayi_yazi(int(m.group(0))), t)
    ayrac = {"kesme": "’", "zwnj": "\u200c", "tire": "-", "isaret": "\x01"}.get(a.get("ayn", "yok"))
    if ayrac:
        # Yalnız kelime içi: ma‘nen, te’sîr. Özel ad eki (Allah’ın) ve harf-i tarif (fi’l-, ba‘de’t-) hariç.
        t = re.sub(rf"(?<=[{HARF}])‘(?=[{HARF}])", "\x02", t)
        def hemze(m: re.Match) -> str:
            w = m.group(0)
            if w[0].isupper():
                return w
            return re.sub(rf"(?<=[{HARF}])’(?=[{HARF}])(?![{HARF}]{{1,2}}-)(?!ll)", "\x02", w)
        t = re.sub(rf"[{HARF}’\x02-]+", hemze, t)
    t = t.replace("‘", "")
    if a["eski_ekler"]:
        t = t.replace("Nakşbend", "Nakşibend")
    if a["izafet_y"]:
        t = re.sub(rf"(?<=[aeıioöuüâîû])-([ıi])(?![{HARF}])", r"y\1", t)
    if a["tire_birlestir"]:
        t = re.sub(rf"(?<=[{HARF}])[’']?-(?=[{HARF}])", "", t)
    t = re.sub(rf"(?<=[{HARF}])[’'](?=[{HARF}])", "", t)    # hemze ve kesme: şey’in -> şeyin, Allah’ın -> Allahın
    t = re.sub(r"[’']", "", t)
    t = t.replace("\x02", ayrac or "")
    ayrac = {"tire": "-", "kesme": "’", "zwnj": "\u200c"}.get(a.get("harf_ayir", "yok"))
    if ayrac:
        t = re.sub(r"([sScCtTzZdDkKpPgG])(?=[hH])", lambda m: m.group(1) + ayrac, t)

    def kelime_isle(m: re.Match) -> str:
        w = m.group(0)
        if a["eski_ekler"]:
            w = eski_ek(w)
        # ğ (gayn) -> g: kelime başında, ünsüzden sonra ya da â/û önünde (ğâyet, meşğûl, ğark)
        if a["gayn"]:
            w = re.sub(r"^ğ", "g", w)
            w = re.sub(r"^Ğ", "G", w)
            w = re.sub(r"(?<=[bcçdfghjklmnprsştvyz])ğ", "g", w)
            w = re.sub(r"ğ(?=[âû])", "g", w)
        if a["cift_y"]:
            w = re.sub(r"([iıîİ])yy([eaâ])", r"\1y\2", w)
        if a["ünsüz_benzesme"]:
            w = benzesme(w)
        w = son_kume(w, a.get("son_kume", "yok"))
        if a.get("ic_kume", "yok") == "sert":
            w = re.sub(r"(?<=[bcçdfgğhjklmnprsştvyz])([bcdg])(?=[bcçdfgğhjklmnprsştvyz])",
                       lambda m: {"b": "p", "c": "ç", "d": "t", "g": "k"}[m.group(1)], w)
        if a.get("uyum_kir", "yok") == "cift":
            w = re.sub(r"([eiöüî][^aeıioöuüâîûAEIİOÖUÜÂÎÛ]{1,3})û", r"\1uu", w)
        if a["sapka"] == "cift":
            w = re.sub(r"[âîûÂÎÛ]", lambda m: {"â": "aa", "î": "ii", "û": "uu", "Â": "Aa", "Î": "İi", "Û": "Uu"}[m.group(0)], w)
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
