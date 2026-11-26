"""Bölüm mp3'lerinden kapaklı YouTube videoları üretir: her bölüm ayrı + kitabın tamamı."""
import re, subprocess, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from kapak import kapak

KAYNAK = Path.home() / "Downloads/mektuplar-kitap"
CIKTI = KAYNAK / "video"
ARA = 3.0  # tam kitapta bölümler arası sessizlik (sn)
BOLUMLER = [
    ("01", "BİRİNCİ BÖLÜM", "Sülûk İçün Ma‘ârif-i ‘Aliyye"),
    ("02", "İKİNCİ BÖLÜM", "Temessük-i Hakîkî"),
    ("03", "ÜÇÜNCÜ BÖLÜM", "Mertebe-i Hullet"),
    ("04", "DÖRDÜNCÜ BÖLÜM", "Dünyâ Mü’minin Sicnidir"),
    ("05", "BEŞİNCİ BÖLÜM", "Mü’minler Ölmez — Hayât-ı Berzah"),
    ("06", "ALTINCI BÖLÜM", "Âdâb-ı Zarûriyye"),
]


def sure(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))


def video(resim, ses, cikti):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "1", "-i", str(resim), "-i", str(ses),
                    "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", "1", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-t", str(sure(ses)), "-movflags", "+faststart",
                    str(cikti)], check=True)


def kucuk(resim, cikti):
    Image.open(resim).resize((1280, 720), Image.LANCZOS).save(cikti, quality=90)


def zaman(sn):
    ms = round(sn * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def saniye(z):
    h, m, s = z.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    CIKTI.mkdir(exist_ok=True)
    srt_tum, sira, kayma, bolum_bas = [], 1, 0.0, []
    sesler = []
    for no, ust, ad in BOLUMLER:
        mp3 = next(KAYNAK.glob(f"Mektuplar-{no}-*.mp3"))
        ad_dosya = mp3.stem
        resim = CIKTI / f"{ad_dosya}-kapak.jpg"
        kapak(ust, ad, resim)
        kucuk(resim, CIKTI / f"{ad_dosya}-kucukresim.jpg")
        hedef = CIKTI / f"{ad_dosya}.mp4"
        if not hedef.exists():
            video(resim, mp3, hedef)
        (CIKTI / f"{ad_dosya}.srt").write_bytes(mp3.with_suffix(".srt").read_bytes())
        bolum_bas.append((kayma, ad))
        for blok in mp3.with_suffix(".srt").read_text(encoding="utf-8").strip().split("\n\n"):
            sat = blok.split("\n")
            a, b = [saniye(x.strip()) for x in sat[1].split("-->")]
            srt_tum.append(f"{sira}\n{zaman(a + kayma)} --> {zaman(b + kayma)}\n" + "\n".join(sat[2:]))
            sira += 1
        sesler.append(mp3)
        kayma += sure(mp3) + ARA
        print("hazır:", hedef.name, flush=True)

    # kitabın tamamı
    tam = CIKTI / "Mektuplar-Tamami"
    resim = Path(f"{tam}-kapak.jpg")
    kapak("SESLİ KİTABIN TAMAMI", "Altı Bölüm Bir Arada", resim)
    kucuk(resim, f"{tam}-kucukresim.jpg")
    liste = CIKTI / "birlestir.txt"
    sessiz = CIKTI / "sessiz.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(ARA), str(sessiz)], check=True)
    girdiler, filtre = [], ""
    for i, s in enumerate(sesler):
        girdiler += ["-i", str(s), "-i", str(sessiz)]
    girdiler = girdiler[:-2]  # sondaki sessizlik gereksiz
    n = len(girdiler) // 2
    filtre = "".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono[a{i}];" for i in range(n))
    filtre += "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    wav = CIKTI / "tam.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *girdiler, "-filter_complex", filtre, "-map", "[out]", str(wav)], check=True)
    if not Path(f"{tam}.mp4").exists():
        video(resim, wav, f"{tam}.mp4")
    Path(f"{tam}.srt").write_text("\n\n".join(srt_tum) + "\n", encoding="utf-8")
    with open(CIKTI / "bolum-zamanlari.txt", "w", encoding="utf-8") as f:
        for bas, ad in bolum_bas:
            s = int(bas)
            f.write(f"{s // 3600}:{s // 60 % 60:02}:{s % 60:02} {ad}\n")
    for x in (wav, sessiz, liste):
        x.unlink(missing_ok=True)
    print("hazır: tam kitap", flush=True)


if __name__ == "__main__":
    main()
