"""Kanal profil resmi ve banner'ı (kapaklarla aynı üslupta)."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from kapak import ALTIN, KREM, ZEMIN, font, yildiz, desen, W, H, SS

CIKTI = Path.home() / "Downloads/mektuplar-kitap/video/kanal"


def kitap(d, cx, cy, s, renk, kal):
    """Açık kitap: iki kavisli sayfa."""
    for yon in (-1, 1):
        n = []
        for i in range(21):
            t = i / 20
            x = cx + yon * s * t
            y = cy - s * 0.12 * math.sin(math.pi * t) - s * 0.05 * t
            n.append((x, y))
        alt = [(cx + yon * s * t, cy + s * 0.55 - s * 0.05 * t + s * 0.06 * math.sin(math.pi * t)) for t in (i / 20 for i in range(20, -1, -1))]
        d.polygon(n + alt, outline=renk, width=kal)
        for k in (0.22, 0.33, 0.44):
            d.line([(cx + yon * s * 0.15, cy + s * k), (cx + yon * s * 0.85, cy + s * k - s * 0.03)], fill=renk, width=max(1, kal // 2))


def profil():
    s = 800 * SS
    img = Image.new("RGB", (s, s), ZEMIN)
    d = ImageDraw.Draw(img, "RGBA")
    c = s / 2
    d.ellipse([c - s * 0.40, c - s * 0.40, c + s * 0.40, c + s * 0.40], outline=ALTIN, width=8 * SS)
    d.ellipse([c - s * 0.36, c - s * 0.36, c + s * 0.36, c + s * 0.36], outline=ALTIN + (110,), width=2 * SS)
    kitap(d, c, c - s * 0.058, s * 0.27, KREM, 7 * SS)
    img.resize((800, 800), Image.LANCZOS).save(CIKTI / "profil.png")


def banner():
    w, h = 2560 * SS, 1440 * SS
    img = Image.new("RGB", (w, h), (6, 18, 20))
    isik = Image.new("L", (w // 8, h // 8), 0)
    ImageDraw.Draw(isik).ellipse([-w // 32, h // 40, w // 8 + w // 32, h // 8 - h // 40], fill=255)
    isik = isik.filter(ImageFilter.GaussianBlur(60)).resize((w, h))
    img = Image.composite(Image.new("RGB", (w, h), ZEMIN), img, isik)
    d = ImageDraw.Draw(img, "RGBA")
    # güvenli alan: ortada 1546x423
    x0, y0, x1, y1 = (w - 1500 * SS) / 2, (h - 400 * SS) / 2, (w + 1500 * SS) / 2, (h + 400 * SS) / 2
    d.rectangle([x0, y0, x1, y1], fill=(9, 26, 28, 230))
    d.rectangle([x0 + 10 * SS, y0 + 10 * SS, x1 - 10 * SS, y1 - 10 * SS], outline=ALTIN, width=3 * SS)
    f = font("NotoSerifDisplay-Bold.ttf", 120)
    d.text((w / 2, h / 2 - 25 * SS), "SESLİ SAYFALAR", font=f, fill=KREM, anchor="ms")
    d.line([(w / 2 - 330 * SS, h / 2 + 20 * SS), (w / 2 - 30 * SS, h / 2 + 20 * SS)], fill=ALTIN, width=2 * SS)
    d.line([(w / 2 + 30 * SS, h / 2 + 20 * SS), (w / 2 + 330 * SS, h / 2 + 20 * SS)], fill=ALTIN, width=2 * SS)
    d.ellipse([w / 2 - 8 * SS, h / 2 + 12 * SS, w / 2 + 8 * SS, h / 2 + 28 * SS], outline=ALTIN, width=2 * SS)
    d.text((w / 2, h / 2 + 105 * SS), "Eski ve yeni kitaplar, sesli olarak", font=font("NotoSerifDisplay-Italic.ttf", 52), fill=ALTIN, anchor="ms")
    img.resize((2560, 1440), Image.LANCZOS).save(CIKTI / "banner.jpg", quality=92)


if __name__ == "__main__":
    CIKTI.mkdir(parents=True, exist_ok=True)
    profil(); banner()
