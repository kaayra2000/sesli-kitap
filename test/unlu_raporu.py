#!/usr/bin/env python3
"""
Ünlü uzunluğu raporu (kelime kelime): her parçada CTC hizalamasıyla ölçülen ünlü süreleri (seslendir.py
"unlu_once"/"unlu_sonra": [konum, süre, uzun mu, öbek sonu mu]) parçanın kısa ünlü ortancasına bölünür.

- Uzamamış uzun ünlü: â î û (ya da çiftlenmiş û) oranı < 1.4
- Yersiz uzamış kısa ünlü: öbek sonu olmayan kısa ünlü oranı > 1.7

Kullanım: python3 test/unlu_raporu.py <sonuc klasörü> [varyant-soneki]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

UZUN_ALT, KISA_UST = 1.4, 1.7


def kelime_bul(metin: str, i: int) -> str:
    bas = max([m.end() for m in re.finditer(r"[\s,.;:!?]", metin[:i])] or [0])
    son = re.search(r"[\s,.;:!?]|$", metin[i:]).start() + i
    w = metin[bas:son]
    k = i - bas
    return w[:k] + "[" + w[k] + "]" + w[k + 1:]


def main() -> None:
    d = Path(sys.argv[1])
    sonek = sys.argv[2] if len(sys.argv) > 2 else None
    P = json.loads((d / "sonuc.json").read_text(encoding="utf-8"))["parcalar"]
    if sonek:
        P = [p for p in P if p["id"].endswith("--" + sonek)]
    say = Counter()
    uzamamis, yersiz = [], []
    for p in P:
        t = p.get("unlu_sonra") or p.get("unlu_once")
        if not t:
            continue
        kisa = sorted(s for _, s, u, o in t if not u and not o)
        if len(kisa) < 3:
            continue
        m = kisa[len(kisa) // 2]
        for i, s, u, o in t:
            r = s / m
            if u:
                say["uzun"] += 1
                if r < UZUN_ALT:
                    uzamamis.append((p["id"], kelime_bul(p["okunus"], i), round(r, 2)))
            elif not o:
                say["kisa"] += 1
                if r > KISA_UST:
                    yersiz.append((p["id"], kelime_bul(p["okunus"], i), round(r, 2)))
    print(f"# Ünlü uzunluğu: {d.name} {sonek or ''}\n")
    print(f"- Uzun ünlü {say['uzun']}, uzamamış {len(uzamamis)} (%{100 * len(uzamamis) / max(1, say['uzun']):.0f})")
    print(f"- Kısa ünlü {say['kisa']}, yersiz uzamış {len(yersiz)} (%{100 * len(yersiz) / max(1, say['kisa']):.1f})\n")
    print("## Uzamamış uzun ünlüler\n")
    for x in uzamamis:
        print(f"- {x[0]} {x[1]} ({x[2]})")
    print("\n## Yersiz uzamış kısa ünlüler\n")
    for x in yersiz:
        print(f"- {x[0]} {x[1]} ({x[2]})")


if __name__ == "__main__":
    main()
