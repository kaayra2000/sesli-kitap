"""Parça parça seslendirilmiş bir bölümün çıktılarını (ornek.mp3 + altyazi.srt) tek ses ve altyazıda birleştirir.

Kullanım: python3 video/parcalari_birlestir.py <hedef-klasör> <parça1-klasörü> <parça2-klasörü> ...
Her parçanın ses dosyası, son cümlesinden sonraki sessizlikle bittiği için parçalar arka arkaya eklenir.
Hedefte ornek.mp3 ve altyazi.srt oluşur (video/bolum.py'nin beklediği adlar).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from uret import saniye, sure, zaman  # noqa: E402


def main():
    hedef, *parcalar = [Path(x) for x in sys.argv[1:]]
    hedef.mkdir(parents=True, exist_ok=True)
    srt, sira, kayma = [], 1, 0.0
    for p in parcalar:
        for blok in (p / "altyazi.srt").read_text(encoding="utf-8").strip().split("\n\n"):
            sat = blok.split("\n")
            a, b = [saniye(x.strip()) for x in sat[1].split("-->")]
            srt.append(f"{sira}\n{zaman(a + kayma)} --> {zaman(b + kayma)}\n" + "\n".join(sat[2:]))
            sira += 1
        kayma += sure(p / "ornek.mp3")
    liste = hedef / "liste.txt"
    liste.write_text("".join(f"file '{(p / 'ornek.mp3').resolve()}'\n" for p in parcalar), encoding="utf-8")
    # Yeniden kodlama: mp3 çerçeve sınırlarında kayma olmasın, altyazı zamanları tutsun
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
                    "-c:a", "libmp3lame", "-b:a", "128k", str(hedef / "ornek.mp3")], check=True)
    liste.unlink()
    (hedef / "altyazi.srt").write_text("\n\n".join(srt) + "\n", encoding="utf-8")
    print(hedef / "ornek.mp3", f"{sure(hedef / 'ornek.mp3'):.1f} sn (parçalar toplamı {kayma:.1f} sn)", sira - 1, "altyazı")


if __name__ == "__main__":
    main()
