r"""Um quadro de UMA cena do vertical (F1) renderizado agora, para conferir uma correção olhando a imagem.

    $env:GRS_CANAL='f1'
    .venv\Scripts\python.exe tools\direcao\quadro_da_cena.py <id_do_plano> [--frac 0.6] [--escala 0.5] [--projeto <slug>] [--codigo arquivo.js]

`--frac`   ponto da cena (0 = começo, 1 = fim; 0.6 é o padrão da conferência do diretor; textos que entram palavra a
           palavra só aparecem completos perto do fim: use 0.9).
`--escala` 0.5 = 540x960 (padrão; 0.25 é pequeno demais para ver pneu, texto ou borda).
`--codigo` experimenta outro código de cena SEM gravar nada no vertical.json (o arquivo do projeto não muda).
Sem `--projeto`, usa o único card com `direcao/vertical.json` mais recente do canal.
Imprime o caminho do .jpg (em <projeto>/trabalho/conferencia_cenas/quadro_<id>_<frac>.jpg): leia a imagem.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
for p in (AQUI.parent, AQUI):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import vertical as V  # noqa: E402
from canal import CANAL, RAIZ, caminho  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plano")
    ap.add_argument("--frac", default="0.6", help="um ponto (0.6) ou vários separados por vírgula (0.1,0.5,0.9): um .jpg por ponto")
    ap.add_argument("--escala", type=float, default=0.5)
    ap.add_argument("--projeto")
    ap.add_argument("--codigo", help="arquivo .js com o código de cena a testar no lugar do atual")
    a = ap.parse_args()

    projetos = caminho("projetos")
    if a.projeto:
        proj = projetos / a.projeto
    else:
        cands = sorted(projetos.glob("*/direcao/vertical.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not cands:
            print("nenhum projeto com direcao/vertical.json", file=sys.stderr)
            return 1
        proj = cands[0].parents[1]
    trab = (proj / "trabalho").resolve()
    d = json.loads((proj / "direcao" / "vertical.json").read_text(encoding="utf-8"))
    pal = json.loads((proj / "direcao" / "tempos_voz.json").read_text(encoding="utf-8"))
    planos = d["planos"]
    n = next((i for i, p in enumerate(planos) if p["id"] == a.plano), None)
    if n is None:
        print(f"plano {a.plano} não existe em {proj.name}", file=sys.stderr)
        return 1
    if a.codigo:
        d = copy.deepcopy(d)
        d["planos"][n]["codigo"] = Path(a.codigo).read_text(encoding="utf-8")
        planos = d["planos"]
    ini = 0 if n == 0 else pal[planos[n]["i"]]["i"]
    fim = pal[planos[n + 1]["i"]]["i"] if n + 1 < len(planos) else pal[-1]["f"]
    fracs = [float(x) for x in a.frac.split(",")]

    pasta = trab / "conferencia_cenas"
    pasta.mkdir(parents=True, exist_ok=True)
    saidas = [pasta / f"quadro_{a.plano}_{int(f * 100)}.jpg" for f in fracs]
    props = trab / "quadro_da_cena_props.json"
    pedido = trab / "quadro_da_cena_pedido.json"
    props.write_text(json.dumps(V._props(d, pal, V.copiar_logos(trab, planos)), ensure_ascii=False), encoding="utf-8")
    pedido.write_text(json.dumps({"composicao": V.CFG.get("composicao", "Vertical"),
                                  "props": str(props), "publicDir": str(trab), "escala": a.escala,
                                  "quadros": [{"q": int((ini + (fim - ini) * f) * V.FPS), "saida": str(s)} for f, s in zip(fracs, saidas)]}),
                      encoding="utf-8")
    r = subprocess.run(["node", str(V.BIBLIOTECA / "quadros.mjs"), str(pedido)], cwd=RAIZ / V.CFG.get("projeto", ""),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    props.unlink(missing_ok=True)
    pedido.unlink(missing_ok=True)
    if r.returncode != 0 or not all(s.exists() for s in saidas):
        print("falhou:", (r.stderr or r.stdout)[-600:], file=sys.stderr)
        return 1
    for s in saidas:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
