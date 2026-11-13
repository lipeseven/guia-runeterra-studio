"""Teste de render do kit/cartoes nos DOIS motores + folhas de sequência a 60 q/s.

1. regera kit/cartoes/cartoes.global.js (esbuild) e roda o teste do kit (node testes.ts);
2. renderiza a cena de teste (kit/cartoes/exemplo/cena.json) em PNG quadro a quadro no Remotion e no HyperFrames;
3. mede nos PIXELS:
   - tags: pixels brancos das etiquetas (antes do cartão de pessoa entrar) sempre dentro da margem segura de 48 px e
     batendo com as caixas calculadas pelo kit (erro ≤ 2 px);
   - pessoa: a tinta escura dentro do cartão (fora da foto) fica dentro das caixas de texto do kit, e a largura medida
     do nome bate com a da tabela (a largura sem navegador está certa);
   - capítulo: tinta do título dentro da área útil (160 px de cada lado) e batendo com as caixas do kit;
4. compara os dois motores, monta as folhas (JPG) nesta pasta e grava resultado.json.

  .venv\\Scripts\\python.exe F1\\horizontal\\testes\\cartoes\\rodar.py [--sem-render]
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
KIT = HORIZ / "kit" / "cartoes"
SAIDA = AQUI / "saida"
MARGEM = 48


def bbox(mask: np.ndarray, ox: int = 0, oy: int = 0):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()) + ox, int(ys.min()) + oy, int(xs.max()) + ox + 1, int(ys.max()) + oy + 1]


def estados_kit(cena: dict) -> list:
    script = ("import {montarCartoes, estadoCartoes} from './cartoes.ts'; import {readFileSync} from 'node:fs';"
              "const c = JSON.parse(readFileSync('exemplo/cena.json','utf-8')); const m = montarCartoes(c); const out = [];"
              "for (let q = 0; q <= Math.round(c.duracao*c.fps); q++) out.push(estadoCartoes(m, q/c.fps).map(e => ({id:e.id,tipo:e.tipo,"
              "opacidade:e.opacidade,caixa:e.caixa,textos:e.textos,tag:e.tag})));"
              "const pessoa = m.itens.find(i => i.tipo==='pessoa').m; console.log(JSON.stringify({q: out, foto: pessoa.foto.clip, cartao: pessoa.cartao}));")
    tmp = KIT / "_estados.mts"
    tmp.write_text(script, encoding="utf-8")
    try:
        return json.loads(M.sh(["node", tmp.name], cwd=KIT).stdout)
    finally:
        tmp.unlink()


def medir(motor: str, arqs: list[Path], cena: dict, kit: dict) -> dict:
    W, H = cena["largura"], cena["altura"]
    res = {"motor": motor, "quadros": len(arqs), "falhas": []}
    est = kit["q"]
    # --- tags (só enquanto nenhuma pessoa/capítulo está na tela: o branco é só das etiquetas)
    erro_tag, fora_margem, n_tag = 0.0, 0, 0
    for q, e in enumerate(est):
        tags = [x for x in e if x["tipo"] == "tag"]
        if not tags or any(x["tipo"] != "tag" for x in e) or q % 2:
            continue
        A = M.img(arqs[q])
        branco = (A >= 254).all(-1)
        b = bbox(branco)
        if b is None:
            continue
        n_tag += 1
        if b[0] < MARGEM or b[1] < MARGEM or b[2] > W - MARGEM or b[3] > H - MARGEM:
            # o anel branco do ponto pode ficar perto da borda; só conta se a etiqueta estiver toda visível
            fora_margem += 1
        # cada etiqueta inteira (opacidade 1): bbox do branco = caixa do kit (o branco começa depois da listra de 6 px)
        for x in tags:
            if x["opacidade"] < 0.999:
                continue
            c = x["tag"]["caixa"]
            x0, y0, x1, y1 = int(c["x"]) - 6, int(c["y"]) - 6, math.ceil(c["x"] + c["w"]) + 6, math.ceil(c["y"] + c["h"]) + 6
            bb = bbox(branco[y0:y1, x0:x1], x0, y0)
            if bb:
                erro_tag = max(erro_tag, abs(bb[0] - (c["x"] + 6)), abs(bb[1] - c["y"]), abs(bb[2] - (c["x"] + c["w"])), abs(bb[3] - (c["y"] + c["h"])))
    res["tags"] = {"quadros_medidos": n_tag, "erro_caixa_px": round(erro_tag, 2), "quadros_fora_da_margem": fora_margem}
    if fora_margem:
        res["falhas"].append(f"tag fora da margem em {fora_margem} quadros")
    if erro_tag > 2.5:
        res["falhas"].append(f"etiqueta fora do lugar calculado ({erro_tag:.1f} px)")
    # --- pessoa: tinta do texto × caixas do kit, nos quadros com o cartão parado e inteiro
    erro_txt, larg = 0.0, []
    for q, e in enumerate(est):
        p = next((x for x in e if x["tipo"] == "pessoa" and x["opacidade"] >= 0.999), None)
        if not p or abs(p["caixa"]["x"] - kit["cartao"]["x"]) > 0.01 or q % 4:
            continue
        A = M.img(arqs[q])
        c = p["caixa"]
        x0, y0, x1, y1 = int(c["x"]) + 10, int(c["y"]) + 2, int(c["x"] + c["w"]) - 2, int(c["y"] + c["h"]) - 2
        fx1 = int(kit["foto"]["x"] + kit["foto"]["w"]) + 4
        escuro = A[y0:y1, x0:x1].sum(-1) < 3 * 140
        escuro[:, : max(0, fx1 - x0)] = False
        b = bbox(escuro, x0, y0)
        caixas = p["textos"]
        u = [min(t["x"] for t in caixas), min(t["y"] for t in caixas), max(t["x"] + t["w"] for t in caixas), max(t["y"] + t["h"] for t in caixas)]
        if b:
            erro_txt = max(erro_txt, u[0] - b[0], u[1] - b[1], b[2] - u[2], b[3] - u[3])
            # largura do nome: tinta na faixa do nome
            n = caixas[0]
            ny0, ny1 = int(n["y"]), math.ceil(n["y"] + n["h"])
            bn = bbox(A[ny0:ny1, int(n["x"]) - 4: int(n["x"] + n["w"]) + 30].sum(-1) < 3 * 140, int(n["x"]) - 4, ny0)
            if bn:
                larg.append((bn[2] - bn[0], n["w"]))
    res["pessoa"] = {"tinta_fora_da_caixa_px": round(erro_txt, 2),
                     "nome_largura_medida_kit": [larg[0][0], round(larg[0][1], 1)] if larg else None}
    if erro_txt > 2:
        res["falhas"].append(f"texto do cartão de pessoa sai da caixa do kit ({erro_txt:.1f} px)")
    if larg and abs(larg[0][0] - larg[0][1]) > 0.04 * larg[0][1] + 6:
        res["falhas"].append(f"largura do nome medida {larg[0][0]} × kit {larg[0][1]:.1f}")
    # --- capítulo: tinta do título
    cap_err, cap_n, cap_area = 0.0, 0, 0
    for q, e in enumerate(est):
        cp = next((x for x in e if x["tipo"] == "capitulo" and x["opacidade"] >= 0.999), None)
        if not cp or q % 6:
            continue
        A = M.img(arqs[q])
        for i, t in enumerate(cp["textos"]):
            y0, y1 = int(t["y"]) - 20, math.ceil(t["y"] + t["h"]) + 20
            tinta = A[y0:y1].sum(-1) < 3 * 120 if i else (A[y0:y1, :, 0] - A[y0:y1, :, 1] > 80)
            b = bbox(tinta, 0, y0)
            if not b:
                continue
            cap_n += 1
            cap_err = max(cap_err, t["x"] - b[0], t["y"] - b[1], b[2] - (t["x"] + t["w"]), b[3] - (t["y"] + t["h"]))
            if b[0] < 160 or b[2] > W - 160:
                cap_area += 1
    res["capitulo"] = {"medidas": cap_n, "tinta_fora_da_caixa_px": round(cap_err, 2), "fora_da_area_util": cap_area}
    if cap_err > 2 or cap_area:
        res["falhas"].append(f"título do capítulo fora da caixa ({cap_err:.1f} px) ou da área útil ({cap_area})")
    n = round(cena["duracao"] * cena["fps"]) + 1
    if len(arqs) != n:
        res["falhas"].append(f"{len(arqs)} quadros (esperado {n})")
    return res


def main() -> None:
    sem_render = "--sem-render" in sys.argv
    SAIDA.mkdir(exist_ok=True)
    M.construir_global(KIT / "cartoes.ts", "Cartoes")
    kit_out = M.sh(["node", KIT / "testes.ts"]).stdout.strip().splitlines()
    cena = json.loads((KIT / "exemplo" / "cena.json").read_text(encoding="utf-8"))
    kit = estados_kit(cena)
    pastas = {"remotion": SAIDA / "remotion", "hyperframes": SAIDA / "hyperframes"}
    if not sem_render:
        M.render_remotion(HORIZ / "remotion" / "cartoes" / "exemplo", "ExemploCartoes", pastas["remotion"])
        M.render_hyperframes(HORIZ / "hyperframes" / "cartoes" / "exemplo" / "index.html", {
            "cartoes.global.js": KIT / "cartoes.global.js", "camada.js": HORIZ / "hyperframes" / "cartoes" / "camada.js",
            "cena.js": "window.__CENA = " + (KIT / "exemplo" / "cena.json").read_text(encoding="utf-8") + ";",
            "foto_exemplo.jpg": KIT / "exemplo" / "foto_exemplo.jpg"}, pastas["hyperframes"], SAIDA / "hf_projeto")
    arqs = {k: M.quadros(p) for k, p in pastas.items()}
    medidas = {k: medir(k, v, cena, kit) for k, v in arqs.items()}
    for k, v in arqs.items():
        M.folha(v, list(range(48, 96)), (700, 40, 1920, 640), 380, 8,
                f"{k}: tag presa ao carro (lado escolhido pelo kit) entrando, quadros seguidos a 60 q/s (q48-q95)", AQUI / f"folha_{k}_tag_60qs.jpg")
        M.folha(v, list(range(66, 114)), (0, 680, 1100, 1080), 380, 8,
                f"{k}: cartão de pessoa entrando, quadros seguidos a 60 q/s (q66-q113)", AQUI / f"folha_{k}_pessoa_60qs.jpg")
        M.folha(v, list(range(0, len(v), 10)), None, 400, 7, f"{k}: cena inteira, 1 a cada 10 quadros (60 q/s)", AQUI / f"folha_{k}_cena.jpg")
    resultado = {"kit": kit_out[-1], "render": medidas, "remotion_vs_hyperframes": M.comparar(arqs["remotion"], arqs["hyperframes"])}
    falhas = [f"{k}: {f}" for k, m in medidas.items() for f in m["falhas"]]
    if not kit_out[-1].startswith("OK"):
        falhas.append("kit: " + kit_out[-1])
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
