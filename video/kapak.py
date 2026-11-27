"""Sesli kitap kapak görselleri üretir (özgün geometrik desen + başlık). Düzen: video/TARZ.md."""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, SS = 1920, 1080, 2
ZEMIN = (14, 38, 40)
ALTIN = (201, 164, 92)
KREM = (240, 228, 200)
NOTO = "/usr/share/fonts/truetype/noto/"


def font(ad, boy):
    return ImageFont.truetype(NOTO + ad, boy * SS)


def yildiz(d, cx, cy, r, renk, kal):
    """Sekiz köşeli yıldız: iç içe geçmiş iki kare."""
    for aci0 in (0, 45):
        n = [(cx + r * math.cos(math.radians(aci0 + 90 * i)), cy + r * math.sin(math.radians(aci0 + 90 * i))) for i in range(4)]
        d.line(n + [n[0]], fill=renk, width=kal)


def desen():
    w, h = W * SS, H * SS
    img = Image.new("RGB", (w, h), ZEMIN)
    kat = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    s = 180 * SS
    renk = ALTIN + (46,)
    for gy in range(-1, h // s + 2):
        for gx in range(-1, w // s + 2):
            cx, cy = gx * s + (s // 2 if gy % 2 else 0), gy * s * 0.866
            yildiz(d, cx, cy, s * 0.42, renk, 2 * SS)
            yildiz(d, cx, cy, s * 0.22, renk, 1 * SS)
            for k in range(8):
                a = math.radians(22.5 + 45 * k)
                d.line([(cx + s * 0.39 * math.cos(a), cy + s * 0.39 * math.sin(a)),
                        (cx + s * 0.5 * math.cos(a), cy + s * 0.5 * math.sin(a))], fill=renk, width=SS)
    img.paste(kat, (0, 0), kat)
    # kenarları karartan hâle
    mask = Image.new("L", (w // 8, h // 8), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-w // 40, -h // 20, w // 8 + w // 40, h // 8 + h // 20], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(40)).resize((w, h))
    koyu = Image.new("RGB", (w, h), (5, 16, 18))
    return Image.composite(img, koyu, mask)


def ortala(d, y, metin, f, renk, aralik=0):
    if aralik:
        gen = sum(d.textlength(c, font=f) for c in metin) + aralik * SS * (len(metin) - 1)
        x = (W * SS - gen) / 2
        for c in metin:
            d.text((x, y), c, font=f, fill=renk)
            x += d.textlength(c, font=f) + aralik * SS
    else:
        d.text((W * SS / 2, y), metin, font=f, fill=renk, anchor="ma")


def sigdir(d, metin, ad, boy, azami):
    while d.textlength(metin, font=font(ad, boy)) > azami * SS and boy > 30:
        boy -= 2
    return font(ad, boy)


MEKTUPLAR = {"yazar": "SALÂHUDDÎN İBN MEVLÂNÂ SİRÂCUDDÎN", "ad": "MEKTÛBLAR", "alt": "ve Ba‘zı Mesâ’il-i Mühimme"}


def kapak(ust, alt, cikti, kitap=MEKTUPLAR):
    img = desen()
    d = ImageDraw.Draw(img, "RGBA")
    # orta pano
    x0, y0, x1, y1 = 330 * SS, 150 * SS, (W - 330) * SS, (H - 150) * SS
    d.rectangle([x0, y0, x1, y1], fill=(9, 26, 28, 225))
    d.rectangle([x0 + 14 * SS, y0 + 14 * SS, x1 - 14 * SS, y1 - 14 * SS], outline=ALTIN, width=3 * SS)
    d.rectangle([x0 + 24 * SS, y0 + 24 * SS, x1 - 24 * SS, y1 - 24 * SS], outline=ALTIN + (120,), width=SS)
    for cx, cy in ((x0 + 14 * SS, y0 + 14 * SS), (x1 - 14 * SS, y0 + 14 * SS), (x0 + 14 * SS, y1 - 14 * SS), (x1 - 14 * SS, y1 - 14 * SS)):
        d.rectangle([cx - 9 * SS, cy - 9 * SS, cx + 9 * SS, cy + 9 * SS], fill=(9, 26, 28))
        yildiz(d, cx, cy, 13 * SS, ALTIN, 2 * SS)

    ortala(d, 215 * SS, kitap["yazar"], font("NotoSerif-Regular.ttf", 26), ALTIN, aralik=4)
    ortala(d, 270 * SS, kitap["ad"], font("NotoSerifDisplay-Bold.ttf", 120), KREM, aralik=10)
    ortala(d, 425 * SS, kitap["alt"], font("NotoSerifDisplay-Italic.ttf", 44), KREM + (215,))
    # ayraç
    yc = 520 * SS
    d.line([(W * SS / 2 - 300 * SS, yc), (W * SS / 2 - 30 * SS, yc)], fill=ALTIN, width=2 * SS)
    d.line([(W * SS / 2 + 30 * SS, yc), (W * SS / 2 + 300 * SS, yc)], fill=ALTIN, width=2 * SS)
    yildiz(d, W * SS / 2, yc, 18 * SS, ALTIN, 2 * SS)

    ortala(d, 570 * SS, ust, font("NotoSerif-Regular.ttf", 34), ALTIN, aralik=6)
    f = sigdir(d, alt, "NotoSerifDisplay-Regular.ttf", 84, 1120)
    ortala(d, 630 * SS, alt, f, KREM)
    ortala(d, 845 * SS, "SESLİ KİTAP", font("NotoSerif-Regular.ttf", 24), ALTIN + (200,), aralik=8)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(cikti, quality=92)


if __name__ == "__main__":
    kapak(sys.argv[1], sys.argv[2], sys.argv[3])
