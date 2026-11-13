"""Teste de render do kit/foco nos DOIS motores + folhas de sequência a 60 q/s.

1. regera kit/foco/foco.global.js (esbuild) e roda o teste do kit (node testes.ts);
2. renderiza a cena de teste (kit/foco/exemplo/cena.json) em PNG quadro a quadro, COM e SEM a camada de foco, no
   Remotion e no HyperFrames;
3. mede nos PIXELS (com foco × sem foco, mesmo motor):
   - caixa da peça: diferença máxima (deve ser 0: a peça fica exatamente nítida, em todos os quadros);
   - janela inteira (caixa + folga): diferença máxima (0);
   - fora da janela + pena: as listras finas perdem nitidez (variância do laplaciano) e o fundo liso escurece pelo véu;
   - quadros sem foco (k = 0): imagem idêntica à referência;
   - força medida (escurecimento do fundo liso) × força do kit, quadro a quadro (entrada/saída suaves);
4. compara os dois motores e monta as folhas (JPG) nesta pasta + resultado.json.

  .venv\\Scripts\\python.exe F1\\horizontal\\testes\\foco\\rodar.py [--sem-render]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import motores as M  # noqa: E402

HORIZ = M.HORIZ
KIT = HORIZ / "kit" / "foco"
SAIDA = AQUI / "saida"


def laplaciano_var(a: np.ndarray) -> float:
    g = a.mean(-1)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def medir(motor: str, com: list[Path], sem: list[Path], cena: dict, estados: list[list[dict]]) -> dict:
    fps = cena["fps"]
    res = {"motor": motor, "quadros": len(com), "falhas": [], "por_foco": {}}
    # regiões fixas do fundo (não se movem): listras finas e um trecho liso longe dos focos
    listras = [(96, 216, 120, 640), (880, 990, 1300, 1820)]  # y0, y1, x0, x1
    liso = (300, 420, 1600, 1800)
    max_k0 = 0
    forca_err = []
    for q in range(len(com)):
        A, B = M.img(com[q]), M.img(sem[q])
        est = estados[q]
        if not est:
            max_k0 = max(max_k0, int(np.abs(A - B).max()))
            continue
        e = est[0]
        r = res["por_foco"].setdefault(e["id"], {"quadros": 0, "dif_max_caixa": 0, "dif_max_janela": 0, "nitidez_listras": [],
                                                  "quadros_k1": 0})
        r["quadros"] += 1
        c, j = e["caixa"], e["janela"]
        # caixa e janela (arredondando para dentro: o pixel de borda é parcialmente da janela)
        x0, y0, x1, y1 = math.ceil(c["x"]), math.ceil(c["y"]), math.floor(c["x"] + c["w"]), math.floor(c["y"] + c["h"])
        r["dif_max_caixa"] = max(r["dif_max_caixa"], int(np.abs(A[y0:y1, x0:x1] - B[y0:y1, x0:x1]).max()))
        if e.get("forma", "caixa") == "caixa":
            # retângulo da janela menos os cantos arredondados (encolhe pelo raio nos cantos: usa a cruz)
            rr = 22
            jx0, jy0, jx1, jy1 = math.ceil(j["x"]), math.ceil(j["y"]), math.floor(j["x"] + j["w"]), math.floor(j["y"] + j["h"])
            d1 = np.abs(A[jy0:jy1, jx0 + rr:jx1 - rr] - B[jy0:jy1, jx0 + rr:jx1 - rr]).max()
            d2 = np.abs(A[jy0 + rr:jy1 - rr, jx0:jx1] - B[jy0 + rr:jy1 - rr, jx0:jx1]).max()
            r["dif_max_janela"] = max(r["dif_max_janela"], int(max(d1, d2)))
        # força medida pelo véu no fundo liso: (1 − com/sem) / escurecer
        y0l, y1l, x0l, x1l = liso
        med = 1 - A[y0l:y1l, x0l:x1l].mean() / B[y0l:y1l, x0l:x1l].mean()
        forca_err.append(abs(med / e["escurecer"] - e["k"]))
        if e["k"] >= 0.999:
            r["quadros_k1"] += 1
            for (ly0, ly1, lx0, lx1) in listras:
                vA = laplaciano_var(A[ly0:ly1, lx0:lx1])
                vB = laplaciano_var(B[ly0:ly1, lx0:lx1])
                r["nitidez_listras"].append(vA / vB)
    res["dif_max_sem_foco_k0"] = max_k0
    res["erro_forca_max"] = round(max(forca_err), 4)
    for fid, r in res["por_foco"].items():
        nl = r.pop("nitidez_listras")
        r["nitidez_listras_com_sem"] = [round(min(nl), 4), round(max(nl), 4)] if nl else None
        if r["dif_max_caixa"] > 0:
            res["falhas"].append(f"{fid}: peça mudou com o foco (dif. máx. {r['dif_max_caixa']})")
        if r["dif_max_janela"] > 0:
            res["falhas"].append(f"{fid}: janela nítida mudou (dif. máx. {r['dif_max_janela']})")
        if not nl or max(nl) > 0.2:
            res["falhas"].append(f"{fid}: fundo não desfocou o bastante (nitidez {r['nitidez_listras_com_sem']})")
    if max_k0 > 0:
        res["falhas"].append(f"quadro sem foco diferente da referência ({max_k0})")
    if res["erro_forca_max"] > 0.06:
        res["falhas"].append(f"força medida × kit: erro {res['erro_forca_max']}")
    n = round(cena["duracao"] * fps) + 1
    if len(com) != n or len(sem) != n:
        res["falhas"].append(f"{len(com)}/{len(sem)} quadros (esperado {n})")
    return res


def main() -> None:
    sem_render = "--sem-render" in sys.argv
    SAIDA.mkdir(exist_ok=True)
    M.construir_global(KIT / "foco.ts", "Foco")
    kit = M.sh(["node", KIT / "testes.ts"]).stdout.strip().splitlines()
    cena = json.loads((KIT / "exemplo" / "cena.json").read_text(encoding="utf-8"))
    # estado do kit em cada quadro (para medir): via node
    script = ("import {montarFoco, estadoFoco} from './foco.ts'; import {readFileSync} from 'node:fs';"
              "const c = JSON.parse(readFileSync('exemplo/cena.json','utf-8')); const m = montarFoco(c);"
              "const out = []; for (let q = 0; q <= Math.round(c.duracao*c.fps); q++) out.push(estadoFoco(m, q/c.fps).map(e => ({id:e.id,k:e.k,caixa:e.caixa,janela:e.janela,"
              "escurecer: m.focos.find(f=>f.id===e.id).escurecer, forma: m.focos.find(f=>f.id===e.id).forma})));"
              "console.log(JSON.stringify(out));")
    tmp = KIT / "_estados.mts"
    tmp.write_text(script, encoding="utf-8")
    try:
        estados = json.loads(M.sh(["node", tmp.name], cwd=KIT).stdout)
    finally:
        tmp.unlink()
    pastas = {f"{m}_{v}": SAIDA / f"{m}_{v}" for m in ("remotion", "hyperframes") for v in ("com", "sem")}
    if not sem_render:
        ex_r = HORIZ / "remotion" / "foco" / "exemplo"
        M.render_remotion(ex_r, "ExemploFoco", pastas["remotion_com"])
        M.render_remotion(ex_r, "ExemploFoco", pastas["remotion_sem"], {"semFoco": True})
        cena_js = "window.__CENA = " + (KIT / "exemplo" / "cena.json").read_text(encoding="utf-8") + ";"
        base = {"foco.global.js": KIT / "foco.global.js", "camada.js": HORIZ / "hyperframes" / "foco" / "camada.js"}
        idx = HORIZ / "hyperframes" / "foco" / "exemplo" / "index.html"
        M.render_hyperframes(idx, {**base, "cena.js": cena_js}, pastas["hyperframes_com"], SAIDA / "hf_projeto")
        M.render_hyperframes(idx, {**base, "cena.js": cena_js + "window.__SEM_FOCO = true;"}, pastas["hyperframes_sem"], SAIDA / "hf_projeto_sem")
    arqs = {k: M.quadros(p) for k, p in pastas.items()}
    medidas = {m: medir(m, arqs[f"{m}_com"], arqs[f"{m}_sem"], cena, estados) for m in ("remotion", "hyperframes")}
    for m in ("remotion", "hyperframes"):
        v = arqs[f"{m}_com"]
        M.folha(v, list(range(30, 78)), (1100, 330, 1720, 800), 380, 8,
                f"{m}: foco entrando na asa traseira, quadros seguidos a 60 q/s (q30-q77): fundo desfoca, asa continua nítida", AQUI / f"folha_{m}_entrada_60qs.jpg")
        M.folha(v, list(range(0, len(v), 10)), None, 400, 7, f"{m}: cena inteira, 1 a cada 10 quadros (60 q/s)", AQUI / f"folha_{m}_cena.jpg")
    resultado = {"kit": kit[-1], "render": medidas,
                 "remotion_vs_hyperframes": M.comparar(arqs["remotion_com"], arqs["hyperframes_com"])}
    falhas = [f"{k}: {f}" for k, m in medidas.items() for f in m["falhas"]]
    if not kit[-1].startswith("OK"):
        falhas.append("kit: " + kit[-1])
    if resultado["remotion_vs_hyperframes"]["pior"]["dif"] > 1.0:
        falhas.append(f"motores diferem: {resultado['remotion_vs_hyperframes']}")
    resultado["falhas"] = falhas
    (AQUI / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, m in medidas.items():
        print(k, json.dumps({kk: vv for kk, vv in m.items() if kk != "falhas"}, ensure_ascii=False))
    print("remotion×hyperframes:", resultado["remotion_vs_hyperframes"])
    print("FALHAS:" if falhas else "OK: nenhuma falha", *falhas, sep="\n  ")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
