#!/usr/bin/env python3
"""
Bölümün tamamının kelime kelime ölçüm raporu (teslimden önce çalıştırılır).

- Kelime: metnin her kelimesi Whisper ve CTC dökümüyle hizalanır; iki hakemin de farklı duyduğu kelime "yanlış".
  Her yanlış kelime, bölüm sesindeki zamanıyla (altyazi.srt'deki parça başlangıcı) listelenir.
- Tamlama: her izafet tamlamasının yerel hatası.
- Tonlama: dört özelliğin (perde_std, alcalma, hiz_cv, son_kelime) her biri için insan 10-90 aralığının altında /
  üstünde kalan parça sayısı. Not: aralık insan kayıtlarının %80'ini kapsar; gerçek insan okuması bu ölçüde ~%80 alır.

Kullanım: python3 test/bolum_raporu.py iterasyonlar/ornek06 [> rapor.md]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "metin"))
sys.path.insert(0, str(KOK / "test"))
from kelime_hatalari import kelimeler, yanlislar  # noqa: E402
from olcum import tamlamalar, yerel_hata  # noqa: E402


def zamanlar(srt: Path) -> list[str]:
    return re.findall(r"(\d\d:\d\d:\d\d),\d+ -->", srt.read_text(encoding="utf-8")) if srt.exists() else []


def main() -> None:
    d = Path(sys.argv[1])
    P = json.loads((d / "sonuc.json").read_text(encoding="utf-8"))["parcalar"]
    prof = {k: v for k, v in json.loads((KOK / "referans/insan_profil.json").read_text()).items() if not k.startswith("_")}
    zaman = zamanlar(d / "altyazi.srt")
    toplam, yanlis, liste = 0, Counter(), []
    tam_n, tam_ok, tam_kotu = 0, 0, []
    ton = {k: Counter() for k in prof}
    uyum = []
    for n, p in enumerate(P):
        ref = p.get("hedef") or p["metin"]
        kel = kelimeler(ref, True)
        toplam += len(kel)
        w, c = yanlislar(ref, p.get("duyulan", "")), yanlislar(ref, p.get("ctc_duyulan", ""))
        z = zaman[n] if n < len(zaman) else "?"
        for i in sorted(w.keys() & c.keys()):
            yanlis[kel[i]] += 1
            liste.append((z, kel[i], w[i], c[i]))
        for f in tamlamalar(p["metin"]):
            tam_n += 1
            e = yerel_hata(f, p.get("duyulan", ""))
            tam_ok += e <= 0.15
            if e > 0.15:
                tam_kotu.append((z, f, round(e, 2)))
        t = p.get("tonlama", {})
        if t.get("tonlama_uyum") is not None:
            uyum.append(t["tonlama_uyum"])
        for ad, (alt, _, ust) in prof.items():
            anahtar = "son_kelime" if ad.startswith("son_kelime_") else ad
            if anahtar not in t or (ad.startswith("son_kelime_") and ad != f"son_kelime_{t.get('bitis')}"):
                continue
            ton[ad]["ölçülen"] += 1
            ton[ad]["altında"] += t[anahtar] < alt
            ton[ad]["üstünde"] += t[anahtar] > ust
    n_yanlis = sum(yanlis.values())
    print(f"# Bölüm ölçüm raporu: {d.name}\n")
    print(f"- Kelime: {toplam}, iki hakemce yanlış duyulan {n_yanlis} (%{100 * n_yanlis / max(1, toplam):.1f}), "
          f"doğru %{100 - 100 * n_yanlis / max(1, toplam):.1f}")
    print(f"- Tamlama: {tam_ok}/{tam_n} doğru")
    print(f"- Tonlama uyumu ort: %{100 * sum(uyum) / max(1, len(uyum)):.0f} (insan okuması bu ölçüde ~%80)\n")
    print("## Tonlama: hangi özellik, hangi yönde insan aralığı dışında\n")
    adlar = {"perde_std": "perde oynaklığı", "alcalma": "cümle boyu alçalma", "hiz_cv": "hız değişkenliği",
             "son_kelime_duz": "cümle sonu düşüşü"}
    for ad, s in ton.items():
        if s["ölçülen"]:
            print(f"- {adlar.get(ad, ad)} ({ad}, insan {prof[ad][0]}..{prof[ad][2]}): {s['ölçülen']} parçanın "
                  f"{s['altında']}'i altında, {s['üstünde']}'i üstünde")
    print("\n## Yanlış duyulan kelimeler (zaman, metin, Whisper / CTC)\n")
    for z, k, a, b in liste:
        print(f"- {z} **{k}** -> {a or '(yok)'} / {b or '(yok)'}")
    if tam_kotu:
        print("\n## Hatalı tamlamalar\n")
        for z, f, e in tam_kotu:
            print(f"- {z} {f} (yerel hata {e})")
    print("\n## En sık yanlış kelimeler\n")
    for k, n in yanlis.most_common(20):
        print(f"- {k}: {n}")


if __name__ == "__main__":
    main()
