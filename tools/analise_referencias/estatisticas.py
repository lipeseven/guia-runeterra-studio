"""Cruza cortes e transcrição dos vídeos de referência e imprime estatísticas de ritmo.

Uso:
    .venv\\Scripts\\python.exe tools\\analise_referencias\\estatisticas.py
"""
from __future__ import annotations

import bisect
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from detectar_cortes import PASTA_SAIDA, PASTA_VIDEOS, slug  # noqa: E402

TOLERANCIA = 0.35  # segundos entre o corte e o início da palavra/frase


def perto(alvos: list[float], t: float) -> bool:
    i = bisect.bisect_left(alvos, t)
    return any(abs(alvos[j] - t) <= TOLERANCIA for j in (i - 1, i) if 0 <= j < len(alvos))


def analisar(video: Path) -> dict:
    pasta = PASTA_SAIDA / slug(video.stem)
    cortes = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))
    transc = json.loads((pasta / "transcricao.json").read_text(encoding="utf-8"))

    cenas = cortes["cenas"]
    total = cortes["duracao_total"]
    dur = [c["duracao"] for c in cenas]
    inicios = [c["inicio"] for c in cenas[1:]]  # o 0 não é corte

    palavras = [p for s in transc["segmentos"] for p in s["palavras"]]
    ini_palavras = [p["i"] for p in palavras]
    # frase = palavra que vem depois de pontuação final
    ini_frases = [palavras[0]["i"]] + [
        palavras[k]["i"] for k in range(1, len(palavras))
        if palavras[k - 1]["p"].endswith((".", "!", "?"))]
    fala = sum(s["fim"] - s["inicio"] for s in transc["segmentos"])

    def ritmo(a: float, b: float) -> float:
        n = sum(1 for t in inicios if a <= t < b)
        return n / max((min(b, total) - a) / 60, 1e-9)

    return {
        "video": video.stem[:55],
        "min": total / 60,
        "cenas": len(cenas),
        "media": st.mean(dur),
        "mediana": st.median(dur),
        "p10": st.quantiles(dur, n=10)[0],
        "p90": st.quantiles(dur, n=10)[-1],
        "longas_15s": sum(d > 15 for d in dur) / len(dur) * 100,
        "cpm_1min": ritmo(0, 60),
        "cpm_resto": ritmo(60, total),
        "cpm_final": ritmo(total - 60, total),
        "ppm": len(palavras) / (fala / 60),
        "pct_fala": fala / total * 100,
        "corte_em_palavra": sum(perto(ini_palavras, t) for t in inicios) / len(inicios) * 100,
        "corte_em_frase": sum(perto(ini_frases, t) for t in inicios) / len(inicios) * 100,
        "palavras_por_cena": len(palavras) / len(cenas),
    }


def main() -> None:
    linhas = [analisar(v) for v in sorted(PASTA_VIDEOS.glob("*.mp4"))]
    cab = ("video", "min", "cenas", "media", "mediana", "p10", "p90", "longas_15s",
           "cpm_1min", "cpm_resto", "cpm_final", "ppm", "pct_fala",
           "corte_em_palavra", "corte_em_frase", "palavras_por_cena")
    print(" | ".join(cab))
    for l in linhas:
        print(" | ".join(f"{l[c]:.1f}" if isinstance(l[c], float) else str(l[c]) for c in cab))
    print("MEDIA GERAL | " + " | ".join(
        f"{st.mean(l[c] for l in linhas):.1f}" for c in cab[1:]))
    (PASTA_SAIDA / "estatisticas.json").write_text(
        json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
