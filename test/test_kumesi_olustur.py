#!/usr/bin/env python3
"""
Seslendirme test kümesini kurar: kitaptan katmanlı örnek + elle yazılmış zor durumlar.

Test kümesi yalnız metnin aslını tutar; okunuş her turda o anki kurallarla yeniden üretilir (kurallar değiştikçe).
Katmanlar: kısa (<= 8 kelime), orta (9-20), uzun (21+); her katmanda Osmanlıca yoğunluğu yüksek olanlar öne alınır.
Kullanım: python3 test/test_kumesi_olustur.py kitaplar/mektuplar/parcalar.json -o test/test_kumesi.json
"""
import argparse
import json
import random
import re
from pathlib import Path

ZOR = [
    # (kimlik, metin, neyi sınar)
    ("zor-sayi", "Şeyhimizden i‘tibâren 33 vâsıta ile müselsel ve muttasıldır; bu mektûb 1340 senesinde yazıldı.", "sayı"),
    ("zor-benzesme", "Mektûbunuzu aldım, cevâbını yazdım; sebebi budur ki muhabbet şartdır ve kalbde yer etdi.", "ünsüz benzeşmesi"),
    ("zor-hemze", "Mes’ele şudur: Kur’ân-ı Kerîm’in âyetlerini te’emmül eden mü’min, şey’in hakîkatini anlar.", "hemze, kesme"),
    ("zor-ayn", "Ma‘lûmunuz olsun ki ‘ilm, ‘amel ve ma‘rifet birbirinden ayrılmaz.", "ayın"),
    ("zor-izafet", "Tarîka-i ‘Aliyye-i Nakşbendiyye’nin âdâb-ı zarûriyyesi, sohbet-i şeyh ve râbıta-i kalbiyyedir.", "zincirleme izafet"),
    ("zor-arapca-tamlama", "Bu hakîkati Seyyidü’l-Enbiyâ ve’l-Mürselîn hazretleri fi’l-hakîka beyân buyurmuşlardır.", "Arapça harf-i tarif"),
    ("zor-soru", "Siz mi bana muhabbet ediyorsunuz, yoksa ben mi size muhabbet ediyorum?", "soru tonlaması"),
    ("zor-unlem", "Biz yanlış biliyor ve anlıyormuşuz. Bizdeki muhabbet sizden imiş!", "ünlem"),
    ("zor-parantez", "Şâh-ı Nakşbend (kuddise sirruhû) hazretleri bir zümre-i makbûlâna iltifât buyurdu.", "parantez, dua"),
    ("zor-eski-ek", "Anları ğıyâbdan ahz-ı feyz edecek dereceye îsâl içün anlara bunu söylemeğe karar verdi.", "eski ekler, gayn"),
    ("zor-uzun", "Tahsîl-i rızâ-yı İlâhî ve ma‘rifet-i hâssa-i Bârî içün bir veliyy-i mahbûba muhabbet, bi’l-vâsıta Mahbûb-ı Mutlak Hudâ’ya ve Zât-ı Bârî-i Te‘âlâ’ya muhabbetdir.", "uzun cümle"),
    ("zor-isim", "İmâm-ı Rabbânî, Bahâ’üddîn Nakşbend ve ‘Abdü’l-Hâlık Ğucdüvânî bu yolun büyüklerindendir.", "özel isim"),
]


def yogunluk(metin: str) -> float:
    kelimeler = metin.split()
    isaretli = sum(bool(re.search(r"[âîûÂÎÛ‘’]|-[iıuü]\b", w)) for w in kelimeler)
    return isaretli / max(1, len(kelimeler))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("parcalar", type=Path)
    p.add_argument("-o", "--cikti", type=Path, required=True)
    p.add_argument("--tohum", type=int, default=7)
    a = p.parse_args()
    parcalar = [x for x in json.loads(a.parcalar.read_text(encoding="utf-8")) if x["tur"] == "paragraf"]
    rnd = random.Random(a.tohum)
    katman = {"kisa": (1, 8, 10), "orta": (9, 20, 18), "uzun": (21, 99, 10)}
    secilen = []
    for ad, (alt, ust, adet) in katman.items():
        havuz = [x for x in parcalar if alt <= len(x["metin"].split()) <= ust and len(x["metin"]) > 12]
        havuz.sort(key=lambda x: -yogunluk(x["metin"]))
        ust_yari = havuz[: len(havuz) // 3]          # Osmanlıca yoğun üçte bir
        for x in rnd.sample(ust_yari, adet // 2) + rnd.sample(havuz, adet - adet // 2):
            if x["id"] not in {s["id"] for s in secilen}:
                secilen.append({"id": f"kitap-{x['id']}", "katman": ad, "sayfa": x["sayfa"], "metin": x["metin"]})
    secilen += [{"id": k, "katman": "zor", "sinar": n, "metin": m} for k, m, n in ZOR]
    a.cikti.write_text(json.dumps(secilen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(secilen)} test cümlesi -> {a.cikti}")


if __name__ == "__main__":
    main()
