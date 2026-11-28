"""YouTube başlık ve açıklamalarını üretir (video/ klasörüne yukleme-bilgileri.md)."""
from pathlib import Path
from uret import BOLUMLER, CIKTI

KITAP = "Mektûblar ve Ba‘zı Mesâ’il-i Mühimme"
YAZAR = "Salâhuddîn ibn Mevlânâ Sirâcuddîn"
SIRA = ["1", "2", "3", "4", "5", "6"]

YZ = ("Bu seslendirme yapay zekâ ile üretilmiştir. Ses, bir metinden konuşma sentezi modeliyle "
      "(VoxCPM2) oluşturulmuştur, gerçek bir kişinin okuması değildir. Osmanlı Türkçesi ve Arapça "
      "kökenli bazı kelimelerin okunuşunda hatalar olabilir. Türkçe altyazı mevcuttur.")
KAYNAK = ("Metin, eserin Osmanlı harfleriyle basılmış nüshasından hazırlanmıştır. Nüshada matbaa ve basım yılı yazmaz. "
          "İçindeki mektuplar 1340 (1921) ve 1341 (1923) tarihlidir. "
          "Sayfalar yapay zekâ yardımıyla doğrudan bu baskının görüntülerinden Latin harflerine aktarılmıştır. "
          "Metin sadeleştirilmemiş, aslına sadık okunmuştur; yalnız eski imlâ bugünkü okunuşa göre seslendirilmiştir. "
          "Âyet ve hadîslerin Arapça asılları yerine Türkçe mealleri okunur. Hiçbir modern yayının aktarımı kullanılmamıştır.")
ETIKET = "#SesliKitap #Mektûblar #İmâmıRabbânî"


def icerik():
    return "\n".join(f"{n}. {ad}" for n, (_, _, ad) in zip(SIRA, BOLUMLER))


def main():
    out = []
    for n, (no, _, ad) in zip(SIRA, BOLUMLER):
        baslik = f"Mektûblar {n}. Bölüm: {ad} | Sesli Kitap"
        assert len(baslik) <= 100, baslik
        acik = (f"{YAZAR}'in «{KITAP}» adlı eserinin {n}. bölümü: {ad}.\n\n"
                f"Eser, İmâm-ı Rabbânî'nin evlâdından {YAZAR}'e aittir.\n\n"
                f"📖 Kaynak ve hazırlık: {KAYNAK}\n\n⚠️ {YZ}\n\nKitabın bölümleri:\n{icerik()}\n\n{ETIKET}")
        out.append((f"Mektuplar-{no}", baslik, acik))
    zf = CIKTI / "bolum-zamanlari.txt"
    zam = zf.read_text(encoding="utf-8").strip() if zf.exists() else "(bekleniyor)"
    zam = zam.replace("0:00:00", "00:00", 1)
    baslik = f"Mektûblar (Tamamı) – {YAZAR} | Sesli Kitap"
    acik = (f"{YAZAR}'in «{KITAP}» adlı eserinin altı bölümü tek videoda.\n\n"
            f"Eser, İmâm-ı Rabbânî'nin evlâdından {YAZAR}'e aittir.\n\n"
            f"📖 Kaynak ve hazırlık: {KAYNAK}\n\n⚠️ {YZ}\n\nBölümler:\n{zam}\n\n{ETIKET}")
    out.append(("Mektuplar-Tamami", baslik, acik))
    md = "\n\n---\n\n".join(f"## {d}\n\n**Başlık:** {b}\n\n**Açıklama:**\n\n{a}" for d, b, a in out)
    (CIKTI / "yukleme-bilgileri.md").write_text(md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
