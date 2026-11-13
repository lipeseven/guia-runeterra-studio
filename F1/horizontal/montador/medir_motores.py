"""Mede o custo dos motores para fixar o teto dos blocos de render (fase 7b; números no README.md).

    python medir_motores.py <pasta_do_projeto_horizontal> [--duracoes 1,3,6] [--repeticoes 1]

Para cada cena de exemplo da SPEC (uma por par motor × kit), renderiza a MESMA cena com durações diferentes (sem
transições: pre = pos = 0), cronometra `segmentos.renderizar` (abrir o motor + quadros + codificar o trecho) e ajusta
uma reta  tempo = fixo + por_segundo × duração  (mínimos quadrados). `fixo` = custo de abrir o motor (bundle/navegador/
carregar a cena); `por_segundo` = segundos de render por segundo de vídeo. Também mede o lote do Remotion
(`segmentos.renderizar_lote`: várias cenas numa invocação só) para conferir que o fixo é pago uma vez por lote.
Grava `<pasta>/medicoes_motores.json` e imprime a tabela. Nada aqui entra no vídeo.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(AQUI.parent / "diretor"))

import receitas as R    # noqa: E402
import segmentos as S   # noqa: E402

FPS = 60


def _reta(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return my - b * mx, b


def _job(cena: dict, palavras: list[dict], dur: float) -> dict:
    c = copy.deepcopy(cena)
    c["t1"] = round(c["t0"] + dur, 4)
    return R.receita(c, palavras, 0, 0)


def medir(pasta: Path, duracoes: list[float], repeticoes: int = 1, W: int = 1280, H: int = 720) -> dict:
    import comum
    spec = json.loads((pasta / "spec.json").read_text(encoding="utf-8"))
    _, palavras, _, _ = comum.entradas(pasta)
    tmp = pasta / "_medicao"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    vistos, out = set(), {"resolucao": f"{W}x{H}", "duracoes_s": duracoes, "repeticoes": repeticoes, "medidas": []}
    try:
        for cena in spec["cenas"]:
            chave = (cena["motor"], tuple(sorted({u["kit"] for u in cena.get("kits", [])})))
            if chave in vistos:
                continue
            vistos.add(chave)
            xs, ys = [], []
            for d in duracoes:
                for _ in range(repeticoes):
                    job = _job(cena, palavras, d)
                    t = time.perf_counter()
                    S.renderizar(job, tmp, W, H, rascunho=True, forcar=True)
                    ys.append(time.perf_counter() - t)
                    xs.append(job["quadros"] / FPS)
                    print(f"  {chave[0]:11} {','.join(chave[1]):10} {xs[-1]:5.2f} s de vídeo → {ys[-1]:6.1f} s", flush=True)
            a, b = _reta(xs, ys)
            out["medidas"].append({"motor": chave[0], "kits": list(chave[1]), "cena": cena["id"],
                                   "pontos": [[round(x, 3), round(y, 2)] for x, y in zip(xs, ys)],
                                   "fixo_s": round(a, 2), "por_segundo_s": round(b, 3)})
        # lote do Remotion: as cenas Remotion juntas numa invocação (o fixo deve aparecer uma vez só)
        rem = [c for c in spec["cenas"] if c["motor"] == "remotion"]
        if len(rem) >= 2:
            d = duracoes[len(duracoes) // 2]
            jobs = [_job(c, palavras, d) for c in rem]
            t = time.perf_counter()
            S.renderizar_lote(jobs, tmp, W, H, rascunho=True, forcar=True)
            t_lote = time.perf_counter() - t
            sep = sum(next(m for m in out["medidas"] if m["cena"] == c["id"] or (m["motor"] == "remotion" and m["kits"] ==
                           sorted({u["kit"] for u in c["kits"]})))["fixo_s"] for c in rem)
            out["lote_remotion"] = {"cenas": len(jobs), "duracao_s": d * len(jobs), "segundos": round(t_lote, 2),
                                    "soma_dos_fixos_separados_s": round(sep, 2)}
            print(f"  lote remotion: {len(jobs)} cenas × {d} s → {t_lote:.1f} s (fixos separados somariam {sep:.1f} s)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    (pasta / "medicoes_motores.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    dur = [float(x) for x in argv[argv.index("--duracoes") + 1].split(",")] if "--duracoes" in argv else [1.0, 3.0, 6.0]
    rep = int(argv[argv.index("--repeticoes") + 1]) if "--repeticoes" in argv else 1
    r = medir(Path(argv[0]).resolve(), dur, rep)
    print("\nmotor        kits        fixo (abrir)   por segundo de vídeo")
    for m in r["medidas"]:
        print(f"{m['motor']:12} {','.join(m['kits']):10} {m['fixo_s']:8.1f} s     {m['por_segundo_s']:6.2f} s/s")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
