"""
Uzun ünlü uzatma: TTS şapkalı ünlüyü (â î û) uzatmıyor, şapkayı verince de "ğ" ekliyor (deney01). Bu yüzden ses
şapkasız metinle üretilir, uzun ünlüler sonradan seste uzatılır:

1. Hizalama: wav2vec2 CTC çıktısıyla metnin harfleri seste zorlamalı hizalanır (Viterbi), her harfin süresi bulunur.
2. Uzatma: uzun ünlünün ortasındaki perde periyodu (otokorelasyon) kopyalanıp araya eklenir (TD-PSOLA'nın
   çoğaltma adımı). Perde ve tını değişmez; yalnız ünlü uzar.
3. Ölçüm: uzun ünlü ortalama süresi / kısa ünlü ortalama süresi (uzun_kisa_orani). Osmanlıca okuyucuda ~1.5-2.
"""
import numpy as np

UNLU = set("aeıioöuü")
KARE_SN = 0.02  # wav2vec2: 320 örnek / 16 kHz


def hedef_dizi(metin: str, sozluk: dict) -> tuple[list[int], list[int]]:
    """Metni CTC jetonlarına çevirir; her jetonun metindeki karakter indeksiyle birlikte. Boşluk '|' olur."""
    jeton, indeks = [], []
    onceki_bosluk = True
    for i, c in enumerate(metin.replace("İ", "i").replace("I", "ı").lower().translate(str.maketrans("âîû", "aiu"))):
        if c.isspace():
            if not onceki_bosluk and "|" in sozluk:
                jeton.append(sozluk["|"])
                indeks.append(-1)
            onceki_bosluk = True
        elif c in sozluk:
            jeton.append(sozluk[c])
            indeks.append(i)
            onceki_bosluk = False
    return jeton, indeks


def hizala(log_olas: np.ndarray, jeton: list[int], bos: int = 0) -> list[tuple[int, int]]:
    """CTC zorlamalı hizalama (Viterbi). log_olas: [T, C]. Dönüş: her jeton için (ilk kare, son kare)."""
    T, L = len(log_olas), len(jeton)
    S = 2 * L + 1
    etiket = np.full(S, bos)
    etiket[1::2] = jeton
    NEG = -1e9
    dp = np.full((T, S), NEG)
    geri = np.zeros((T, S), np.int8)
    dp[0, 0] = log_olas[0, bos]
    if S > 1:
        dp[0, 1] = log_olas[0, etiket[1]]
    atla = np.zeros(S, bool)
    atla[3::2] = np.array([jeton[k] != jeton[k - 1] for k in range(1, L)], bool)
    for t in range(1, T):
        a = dp[t - 1]
        b = np.concatenate([[NEG], a[:-1]])
        c = np.concatenate([[NEG, NEG], a[:-2]])
        c = np.where(atla, c, NEG)
        yig = np.stack([a, b, c])
        sec = yig.argmax(0)
        dp[t] = yig.max(0) + log_olas[t, etiket]
        geri[t] = sec
    s = S - 1 if S == 1 or dp[-1, S - 1] >= dp[-1, S - 2] else S - 2
    yol = np.zeros(T, int)
    for t in range(T - 1, -1, -1):
        yol[t] = s
        s -= int(geri[t, s])
    araliklar = [[None, None] for _ in range(L)]
    for t, s in enumerate(yol):
        if s % 2 == 1:
            k = s // 2
            araliklar[k][0] = t if araliklar[k][0] is None else araliklar[k][0]
            araliklar[k][1] = t
    return [(a, b) if a is not None else (-1, -1) for a, b in araliklar]


def harf_sureleri(log_olas: np.ndarray, metin: str, sozluk: dict) -> dict[int, tuple[float, float]]:
    """Metnin karakter indeksi -> (başlangıç sn, bitiş sn). Bir harfin süresi bir sonraki harfe kadar uzar."""
    jeton, indeks = hedef_dizi(metin, sozluk)
    if not jeton or len(jeton) > len(log_olas):
        return {}
    ar = hizala(log_olas, jeton, sozluk.get("[PAD]", sozluk.get("<pad>", 0)))
    sonuc = {}
    for k, ((a, _), i) in enumerate(zip(ar, indeks)):
        if i < 0 or a < 0:
            continue
        sonraki = next((ar[j][0] for j in range(k + 1, len(ar)) if ar[j][0] >= 0), a + 3)
        sonuc[i] = (a * KARE_SN, max(a + 1, sonraki) * KARE_SN)
    return sonuc


def periyot(x: np.ndarray, sr: int) -> int | None:
    """Otokorelasyonla perde periyodu (örnek); ötümsüzse None."""
    if len(x) < sr // 35:
        return None
    x = x - x.mean()
    r = np.correlate(x, x, "full")[len(x) - 1:]
    lo, hi = sr // 350, min(len(r) - 1, sr // 70)
    if hi <= lo or r[0] <= 0:
        return None
    k = lo + int(np.argmax(r[lo:hi]))
    return k if r[k] / r[0] > 0.45 else None


def uzat(x: np.ndarray, sr: int, araliklar: list[tuple[float, float]], kat: float) -> np.ndarray:
    """Her (başlangıç, bitiş) ünlü aralığını, ortasındaki perde periyodunu çoğaltarak kat oranında uzatır."""
    if kat <= 1 or not araliklar:
        return x
    parcalar, imlec = [], 0
    for bas, son in sorted(araliklar):
        a, b = int(bas * sr), int(son * sr)
        if a < imlec or b - a < sr // 50:
            continue
        orta = (a + b) // 2
        merkez = x[max(a, orta - sr // 40): min(b, orta + sr // 40)]
        P = periyot(merkez, sr)
        if not P:
            continue
        n = int(round((kat - 1) * (b - a) / P))
        if n <= 0:
            continue
        # Ortadaki tam periyodu n kez ekle; birleşimlerde 1/4 periyotluk çapraz geçiş.
        dongu = x[orta - P // 2: orta - P // 2 + P].copy()
        if len(dongu) < P:
            continue
        f = max(4, P // 4)
        yuk, ini = np.linspace(0, 1, f), np.linspace(1, 0, f)
        ek = np.tile(dongu, n)
        sol = x[imlec:orta - P // 2].copy()
        sag = x[orta - P // 2:].copy()
        if len(sol) >= f and len(ek) >= 2 * f and len(sag) >= f:
            ek[:f] = ek[:f] * yuk + sol[-f:] * ini
            sol = sol[:-f]
            ek[-f:] = ek[-f:] * ini + sag[:f] * yuk
            sag_bas = f
        else:
            sag_bas = 0
        parcalar += [sol, ek]
        imlec = orta - P // 2 + sag_bas
    parcalar.append(x[imlec:])
    return np.concatenate(parcalar).astype(np.float32)


def uzun_kisa_orani(sureler: dict[int, tuple[float, float]], metin: str, uzun: set[int]) -> float | None:
    """Uzun ünlülerin ortalama süresi / kısa ünlülerin ortalama süresi."""
    kucuk = metin.replace("İ", "i").replace("I", "ı").lower().translate(str.maketrans("âîû", "aiu"))
    u = [b - a for i, (a, b) in sureler.items() if i in uzun]
    k = [b - a for i, (a, b) in sureler.items() if i not in uzun and kucuk[i] in UNLU]
    return round(float(np.mean(u) / np.mean(k)), 3) if u and k else None


def ara_bosluk(log_olas: np.ndarray, metin: str, sozluk: dict, ciftler: list) -> list[float]:
    """Metindeki (sol, sağ) karakter çiftleri arasındaki süre (sn): sol harfin son karesi ile sağ harfin ilk karesi
    arası. Ayn/hemze durağı ölçülür (ma‘nen: a ile n arası)."""
    jeton, indeks = hedef_dizi(metin, sozluk)
    if not jeton or len(jeton) > len(log_olas):
        return []
    ar = hizala(log_olas, jeton, sozluk.get("[PAD]", sozluk.get("<pad>", 0)))
    son = {i: b for (a, b), i in zip(ar, indeks) if i >= 0 and b >= 0}
    ilk = {i: a for (a, b), i in zip(ar, indeks) if i >= 0 and a >= 0}
    return [round((ilk[s] - son[l] - 1) * KARE_SN, 3) for l, s in ciftler if l in son and s in ilk]
