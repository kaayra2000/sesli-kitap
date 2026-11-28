"""Bir kitabın tek bölümünü YouTube'a hazırlar: ses (Opus) ve altyazı repoya, kapak repoya, video ve küçük resim
yerel klasöre, başlık/açıklama kitabın yukleme-bilgileri.md dosyasına.

Kullanım: python3 video/bolum.py <kitap> <no> <ornek.mp3> <altyazi.srt>
          python3 video/bolum.py <kitap> <no>     # yalnız repodaki ses/<slug>.opus ve .srt'den videoyu yeniden üretir
                                                  # (YouTube'daki video kaybolursa)
Bölüm bilgisi kitaplar/<kitap>/kitap.json içindeki "video" alanından okunur:
  "video": {"kapak": {"yazar", "ad", "alt"}, "baslik": "Mârifetnâme", "yazarin": "Erzurumlu İbrâhim Hakkı'nın", "yazar_cumle": "...",
            "etiket": "#SesliKitap ...", "bolumler": {"01": {"slug", "ust", "sira", "ad"}}}
Tarz: video/TARZ.md.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kapak import kapak  # noqa: E402
from uret import kucuk, video  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
YZ = ("Bu seslendirme yapay zekâ ile üretilmiştir. Ses, bir metinden konuşma sentezi modeliyle "
      "(VoxCPM2) oluşturulmuştur, gerçek bir kişinin okuması değildir. Osmanlı Türkçesi ve Arapça "
      "kökenli bazı kelimelerin okunuşunda hatalar olabilir. Türkçe altyazı mevcuttur.")


def ayar(kitap):
    return json.loads((KOK / "kitaplar" / kitap / "kitap.json").read_text(encoding="utf-8"))


def aciklamalar(kitap):
    """Kitabın bütün bölümleri için başlık ve açıklamayı yukleme-bilgileri.md'ye yazar."""
    v = ayar(kitap)["video"]
    bolumler = v["bolumler"]
    liste = "\n".join(f"• {b['sira']}: {b['ad']}" for b in bolumler.values())
    out = []
    for no, b in bolumler.items():
        baslik = f"{v['baslik']} {b['sira']}: {b['ad']} | Sesli Kitap"
        if len(baslik) > 100:
            baslik = f"{v['baslik']} | {b['ad']} | Sesli Kitap"
        assert len(baslik) <= 100, baslik
        acik = (f"{v['yazarin']} «{v['baslik']}» adlı eserinden {b['sira']}: {b['ad']}.\n\n"
                f"{v['yazar_cumle']}\n\n⚠️ {YZ}\n\nHazırlanan bölümler (oynatma listesinde kitap sırasıyla):\n{liste}\n\n{v['etiket']}")
        out.append((b["slug"], baslik, acik))
    md = "\n\n---\n\n".join(f"## {d}\n\n**Başlık:** {b}\n\n**Açıklama:**\n\n{a}" for d, b, a in out)
    (KOK / "kitaplar" / kitap / "yukleme-bilgileri.md").write_text(md + "\n", encoding="utf-8")
    return {d: (b, a) for d, b, a in out}


def main():
    kitap, no = sys.argv[1], sys.argv[2]
    v = ayar(kitap)["video"]
    b = v["bolumler"][no]
    klasor = KOK / "kitaplar" / kitap
    opus, srt_repo = klasor / "ses" / f"{b['slug']}.opus", klasor / "ses" / f"{b['slug']}.srt"
    mp3, srt = (Path(sys.argv[3]), Path(sys.argv[4])) if len(sys.argv) > 4 else (opus, srt_repo)
    (klasor / "ses").mkdir(exist_ok=True)
    (klasor / "gorsel").mkdir(exist_ok=True)
    yerel = KOK / "dist" / f"{kitap}-video"  # git dışı; tarayıcı yüklemesi repo içinden yapılabiliyor
    yerel.mkdir(parents=True, exist_ok=True)
    ad = b["slug"]

    if mp3.resolve() != opus.resolve():  # yeni ses: repoya Opus olarak girer
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ac", "1", "-c:a", "libopus", "-b:a", "32k",
                        "-application", "audio", str(opus)], check=True)
    if srt.resolve() != srt_repo.resolve():
        shutil.copy(srt, srt_repo)
    shutil.copy(srt, yerel / f"{ad}.srt")
    resim = klasor / "gorsel" / f"{ad}-kapak.jpg"
    kapak(b["ust"], b["ad"], resim, v["kapak"])
    kucuk(resim, yerel / f"{ad}-kucukresim.jpg")
    hedef = yerel / f"{ad}.mp4"
    video(resim, mp3, hedef)
    baslik, _ = aciklamalar(kitap)[ad]
    print("hazır:", hedef, "|", baslik)


if __name__ == "__main__":
    main()
