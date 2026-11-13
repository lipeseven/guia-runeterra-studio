"""Teste de render do kit/anotacao nos DOIS motores + folhas de sequência a 60 q/s.

Passos:
 1. regera kit/anotacao/anotacao.global.js (esbuild do F1/video/node_modules) e a checagem geométrica do kit (cli.ts checar);
 2. renderiza a cena de teste em PNG quadro a quadro no Remotion (remotion/anotacao/exemplo) e no HyperFrames
    (hyperframes/anotacao/exemplo, via npx hyperframes@0.9.20, nada global);
 3. mede nos PIXELS de cada quadro: tamanho e margem do oval (deve ficar constante enquanto a peça anda e gira),
    vermelho dentro de caixa de texto (deve ser zero), texto da cena fora da caixa declarada (zero), e compara a caixa
    do oval medida com a calculada pelo kit;
 4. monta as folhas de sequência (JPG) nesta pasta e grava resultado.json.

Rodar (da raiz do repositório ou de qualquer lugar):
  .venv\\Scripts\\python.exe F1\\horizontal\\testes\\anotacao\\rodar.py [--sem-render]
--sem-render reaproveita os PNG de saida/ (só refaz medidas e folhas).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
HORIZ = AQUI.parents[1]
KIT = HORIZ / "kit" / "anotacao"
RAIZ = HORIZ.parents[1]
SAIDA = AQUI / "saida"
HF_VERSAO = "hyperframes@0.9.20"


def node_modules() -> Path:
    """F1/video/node_modules deste checkout ou, numa worktree, o da pasta principal do repositório."""
    for base in [RAIZ, *RAIZ.parents]:
        p = base / "F1" / "video" / "node_modules"
        if (p / "@remotion" / "cli").is_dir():
            return p
    raise SystemExit("F1/video/node_modules não encontrado (rode npm install em F1/video na pasta principal)")


NM = node_modules()
NAVEGADOR = NM / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print((r.stdout or "")[-3000:], (r.stderr or "")[-3000:])
        raise SystemExit(f"falhou: {' '.join(map(str, cmd[:4]))}")
    return r


# ---------------------------------------------------------------- 1. kit
def construir_global() -> None:
    esbuild = NM / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    sh([str(esbuild), "anotacao.ts", "--bundle", "--format=iife", "--global-name=Anotacao", "--target=es2019", "--charset=utf8",
        "--banner:js=// GERADO por F1/horizontal/testes/anotacao/rodar.py (esbuild de anotacao.ts). Não editar à mão.",
        "--outfile=anotacao.global.js", "--log-level=warning"], cwd=KIT)


def kit_json(cmd: str, *args: str):
    return json.loads(sh(["node", str(KIT / "cli.ts"), cmd, str(KIT / "exemplo" / "cena.json"), *args]).stdout)


# ---------------------------------------------------------------- 2. render
def render_remotion(dest: Path) -> None:
    # usa o node_modules do projeto F1/horizontal/remotion (npm install lá) se existir; senão, uma junção LOCAL ao
    # exemplo (remotion/anotacao/node_modules → F1/video/node_modules). Nunca cria junção em remotion/node_modules:
    # um npm install ali escreveria dentro do F1/video.
    if not (HORIZ / "remotion" / "node_modules" / "remotion").is_dir():
        junc = HORIZ / "remotion" / "anotacao" / "node_modules"
        if not junc.exists():
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junc), str(NM)], check=True, capture_output=True)
    if dest.exists():
        shutil.rmtree(dest)
    cli = NM / "@remotion" / "cli" / "remotion-cli.js"
    sh(["node", str(cli), "render", "index.tsx", "ExemploAnotacao", str(dest), "--sequence", "--image-format=png",
        f"--browser-executable={NAVEGADOR}", "--log=error"], cwd=HORIZ / "remotion" / "anotacao" / "exemplo")


def render_hyperframes(dest: Path) -> None:
    proj = SAIDA / "hf_projeto"
    if proj.exists():
        shutil.rmtree(proj)
    (proj / "assets").mkdir(parents=True)
    shutil.copy2(HORIZ / "hyperframes" / "anotacao" / "exemplo" / "index.html", proj / "index.html")
    shutil.copy2(KIT / "anotacao.global.js", proj / "assets" / "anotacao.global.js")
    shutil.copy2(HORIZ / "hyperframes" / "anotacao" / "camada.js", proj / "assets" / "camada.js")
    (proj / "assets" / "cena.js").write_text("window.__CENA = " + (KIT / "exemplo" / "cena.json").read_text(encoding="utf-8") + ";", encoding="utf-8")
    (proj / "assets" / "fonte.js").write_text("window.__FONTE = " + (KIT / "fonte" / "caveat_traco.json").read_text(encoding="utf-8") + ";", encoding="utf-8")
    (proj / "package.json").write_text(json.dumps({"name": "exemplo-anotacao", "private": True, "type": "module"}), encoding="utf-8")
    if dest.exists():
        shutil.rmtree(dest)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    sh([npx, "--yes", HF_VERSAO, "render", "--format", "png-sequence", "--output", str(dest), "--quiet"], cwd=proj)


def quadros(pasta: Path) -> list[Path]:
    fs = sorted(p for p in pasta.rglob("*.png"))
    return fs


# ---------------------------------------------------------------- 3. medidas em pixel
def vermelho(img: np.ndarray) -> np.ndarray:
    r, g, b = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
    return (r - (g + b) / 2 > 70) & (r > 120)


def escuro(img: np.ndarray) -> np.ndarray:
    return img[..., :3].astype(int).sum(-1) < 3 * 110


def bbox(mask: np.ndarray, ox: int = 0, oy: int = 0):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()) + ox, int(ys.min()) + oy, int(xs.max()) + ox + 1, int(ys.max()) + oy + 1]


def ancora(alvo: dict, t: float) -> tuple[float, float]:
    """Mesma interpolação Catmull-Rom do kit (só dx, dy)."""
    m = alvo.get("movimento") or []
    if not m:
        return 0.0, 0.0
    if t <= m[0]["t"]:
        return m[0]["dx"], m[0]["dy"]
    if t >= m[-1]["t"]:
        return m[-1]["dx"], m[-1]["dy"]
    i = 0
    while t > m[i + 1]["t"]:
        i += 1
    k0, k1, k2, k3 = m[max(0, i - 1)], m[i], m[i + 1], m[min(len(m) - 1, i + 2)]
    u = (t - k1["t"]) / (k2["t"] - k1["t"])

    def cr(a, b, c, d):
        return 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
    return cr(k0["dx"], k1["dx"], k2["dx"], k3["dx"]), cr(k0["dy"], k1["dy"], k2["dy"], k3["dy"])


def medir(motor: str, arquivos: list[Path], cena: dict, montada: dict) -> dict:
    fps = cena["fps"]
    it = {i["id"]: i for i in montada["itens"]}
    oval = it["oval-asa"]
    co, esp = oval["caixaOval"], oval["tracos"][0]["largura"]
    t_completo = oval["fim"] + 1 / fps
    t_seta = it["seta-gira"]["inicio"]
    asa = cena["alvos"]["asa"]
    pc = asa["peca"]
    textos = {k: a for k, a in cena["alvos"].items() if a.get("texto")}
    res = {"motor": motor, "quadros": len(arquivos), "oval": [], "vermelho_em_texto": {}, "texto_fora_da_caixa": None,
           "caixa_projetada_peca": [], "falhas": []}
    red0 = None
    for q, arq in enumerate(arquivos):
        t = q / fps
        img = np.asarray(Image.open(arq).convert("RGB"))
        red = vermelho(img)
        if red0 is None:
            # o texto do Chrome tem franja colorida (antisserrilhado por subpixel): o que já é "vermelho" no quadro 0,
            # antes de qualquer anotação, é do texto parado e não conta
            red0 = red.copy()
        dx, dy = ancora(asa, t)
        # oval: região esperada (+12 px); só a partir do quadro em que terminou de desenhar
        ex0, ey0 = co["x"] + dx - esp / 2, co["y"] + dy - esp / 2
        ex1, ey1 = co["x"] + co["w"] + dx + esp / 2, co["y"] + co["h"] + dy + esp / 2
        if t >= t_completo:
            x0, y0, x1, y1 = int(ex0 - 12), int(ey0 - 12), int(math.ceil(ex1 + 12)), int(math.ceil(ey1 + 12))
            if t < t_seta:
                b = bbox(red[y0:y1, x0:x1], x0, y0)
            else:
                # depois da seta (que chega por baixo/direita) só os lados esquerdo e de cima são do oval sozinho
                sub = red[y0:y1, x0:x1].copy()
                cx, cy = int((ex0 + ex1) / 2) - x0, int((ey0 + ey1) / 2) - y0
                sub[cy:, cx:] = False
                b = bbox(sub, x0, y0)
                if b:
                    b = [b[0], b[1], None, None]
            if b:
                res["oval"].append({"q": q, "t": round(t, 4), "medido": b, "esperado": [ex0, ey0, ex1, ey1], "dx": dx, "dy": dy})
        # vermelho dentro das caixas de texto (exceto o riscado do valor corrigido)
        for tid, a in textos.items():
            if tid == "valor":
                continue
            c = a["caixa"]
            sl = (slice(int(c["y"]) + 1, int(c["y"] + c["h"]) - 1), slice(int(c["x"]) + 1, int(c["x"] + c["w"]) - 1))
            n = int((red[sl] & ~red0[sl]).sum())
            if n:
                res["vermelho_em_texto"][tid] = res["vermelho_em_texto"].get(tid, 0) + n
        # caixa projetada (AABB) da peça girando, como o método antigo media — só para comparação
        g = math.radians(pc["giroAmp"] * math.sin(2 * math.pi * t / pc["giroPeriodo"]))
        hw = abs(pc["w"] / 2 * math.cos(g)) + abs(pc["h"] / 2 * math.sin(g))
        hh = abs(pc["w"] / 2 * math.sin(g)) + abs(pc["h"] / 2 * math.cos(g))
        res["caixa_projetada_peca"].append([2 * hw, 2 * hh])
        if q == 0:
            # texto da cena dentro da caixa declarada: nenhum pixel escuro no anel de 24 px em volta da caixa
            dark = escuro(img)
            perto = np.zeros(dark.shape, bool)
            dentro = np.zeros(dark.shape, bool)
            for a in textos.values():
                c = a["caixa"]
                X0, Y0, X1, Y1 = int(c["x"]), int(c["y"]), int(math.ceil(c["x"] + c["w"])), int(math.ceil(c["y"] + c["h"]))
                perto[Y0 - 24:Y1 + 24, X0 - 24:X1 + 24] = True
                dentro[Y0:Y1, X0:X1] = True
            res["texto_fora_da_caixa"] = int((dark & perto & ~dentro).sum())
    # resumo
    ov = res["oval"]
    cheios = [o for o in ov if o["medido"][2] is not None]
    ws = [o["medido"][2] - o["medido"][0] for o in cheios]
    hs = [o["medido"][3] - o["medido"][1] for o in cheios]
    # margem medida em relação à caixa estável da peça no quadro (deslocada pela âncora)
    ca = asa["caixa"]
    mx = [o["medido"][0] - (ca["x"] + o["dx"]) for o in ov]
    my = [o["medido"][1] - (ca["y"] + o["dy"]) for o in ov]
    err = [max(abs(o["medido"][0] - o["esperado"][0]), abs(o["medido"][1] - o["esperado"][1])) for o in ov]
    pw = [c[0] for c in res["caixa_projetada_peca"]]
    ph = [c[1] for c in res["caixa_projetada_peca"]]
    res["resumo"] = {
        "quadros_oval_inteiro": len(cheios), "quadros_oval_lados_esq_cima": len(ov),
        "largura_px": [min(ws), max(ws)] if ws else None, "altura_px": [min(hs), max(hs)] if hs else None,
        "variacao_tamanho_px": max(max(ws) - min(ws), max(hs) - min(hs)) if ws else None,
        "margem_esq_px": [round(min(mx), 2), round(max(mx), 2)], "margem_cima_px": [round(min(my), 2), round(max(my), 2)],
        "variacao_margem_px": round(max(max(mx) - min(mx), max(my) - min(my)), 2),
        "erro_max_vs_kit_px": round(max(err), 2),
        "caixa_projetada_variaria_px": [round(max(pw) - min(pw), 1), round(max(ph) - min(ph), 1)],
    }
    s = res["resumo"]
    # tolerância: 2 px (antisserrilhado do traço de 7 px num deslocamento subpixel)
    if s["variacao_tamanho_px"] is None or s["variacao_tamanho_px"] > 2:
        res["falhas"].append(f"tamanho do oval variou {s['variacao_tamanho_px']} px")
    if s["variacao_margem_px"] > 2:
        res["falhas"].append(f"margem oval×peça variou {s['variacao_margem_px']} px")
    if s["erro_max_vs_kit_px"] > 2.5:
        res["falhas"].append(f"oval fora do lugar calculado pelo kit ({s['erro_max_vs_kit_px']} px)")
    if res["vermelho_em_texto"]:
        res["falhas"].append(f"anotação sobre texto: {res['vermelho_em_texto']}")
    if res["texto_fora_da_caixa"]:
        res["falhas"].append(f"texto da cena sai da caixa declarada ({res['texto_fora_da_caixa']} px escuros)")
    if len(arquivos) != round(cena["duracao"] * fps) + 1:
        res["falhas"].append(f"{len(arquivos)} quadros (esperado {round(cena['duracao'] * fps) + 1})")
    del res["caixa_projetada_peca"]
    res["oval"] = res["oval"][:: max(1, len(res["oval"]) // 40)]
    return res


def comparar(a: list[Path], b: list[Path]) -> dict:
    """Diferença média por quadro entre os dois motores (0–255) e o pior quadro."""
    difs = []
    for q in range(0, min(len(a), len(b)), 5):
        A = np.asarray(Image.open(a[q]).convert("RGB")).astype(np.int16)
        B = np.asarray(Image.open(b[q]).convert("RGB")).astype(np.int16)
        difs.append((float(np.abs(A - B).mean()), q))
    return {"media": round(sum(d for d, _ in difs) / len(difs), 3), "pior": {"q": max(difs)[1], "dif": round(max(difs)[0], 3)}}


# ---------------------------------------------------------------- 4. folhas
FONTE_ROT = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)


def folha(arquivos: list[Path], idx: list[int], corte: tuple[int, int, int, int] | None, larg: int, cols: int, titulo: str, out: Path) -> None:
    ims = []
    for q in idx:
        im = Image.open(arquivos[q]).convert("RGB")
        if corte:
            im = im.crop(corte)
        h = round(im.height * larg / im.width)
        im = im.resize((larg, h), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 118, 30], fill=(20, 20, 20))
        d.text((6, 3), f"q{q} {q / 60:.3f}s", font=FONTE_ROT, fill=(255, 255, 255))
        ims.append(im)
    rows = math.ceil(len(ims) / cols)
    W, H = ims[0].size
    sheet = Image.new("RGB", (cols * W + (cols + 1) * 4, rows * H + (rows + 1) * 4 + 44), (90, 90, 90))
    ImageDraw.Draw(sheet).text((8, 8), titulo, font=FONTE_ROT, fill=(255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, (4 + (i % cols) * (W + 4), 48 + (i // cols) * (H + 4)))
    sheet.save(out, quality=86)


def main() -> None:
    sem_render = "--sem-render" in sys.argv
    SAIDA.mkdir(exist_ok=True)
    construir_global()
    cena = json.loads((KIT / "exemplo" / "cena.json").read_text(encoding="utf-8"))
    rel_kit = kit_json("checar")
    montada = kit_json("montar")
    for i in montada["itens"]:
        for tr in i["tracos"]:
            tr.pop("pts", None)
    pastas = {"remotion": SAIDA / "remotion", "hyperframes": SAIDA / "hyperframes"}
    if not sem_render:
        render_remotion(pastas["remotion"])
        render_hyperframes(pastas["hyperframes"])
    arqs = {k: quadros(p) for k, p in pastas.items()}
    medidas = {k: medir(k, v, cena, montada) for k, v in arqs.items()}
    oval = next(i for i in montada["itens"] if i["id"] == "oval-asa")
    q0 = round(oval["inicio"] * 60)
    for k, v in arqs.items():
        # 48 quadros SEGUIDOS a 60 q/s, recortados na peça: o oval se desenhando e a peça andando/girando
        folha(v, list(range(q0, q0 + 48)), (230, 340, 990, 800), 380, 8,
              f"{k}: quadros seguidos a 60 q/s (q{q0}-q{q0 + 47}), recorte 760x460 da peça: oval se desenhando e depois parado enquanto a peça anda e gira", AQUI / f"folha_{k}_oval_60qs.jpg")
        folha(v, list(range(0, len(v), 10)), None, 400, 7, f"{k}: cena inteira, 1 a cada 10 quadros (60 q/s)", AQUI / f"folha_{k}_cena.jpg")
        # texto à mão e número corrigido, quadros seguidos
        corr = next(i for i in montada["itens"] if i["id"] == "corr-valor")
        qc = round(corr["inicio"] * 60)
        folha(v, list(range(qc, qc + 48)), (1130, 240, 1650, 540), 380, 8,
              f"{k}: riscado + número corrigido, quadros seguidos a 60 q/s (q{qc}-q{qc + 47})", AQUI / f"folha_{k}_corrigido_60qs.jpg")
    resultado = {
        "kit": {"falhas": rel_kit["falhas"], "avisos": rel_kit["avisos"], "quadros": rel_kit["quadros"],
                "ovais": {k: {kk: vv for kk, vv in v.items() if kk != "caixasPorQuadro"} for k, v in rel_kit["ovais"].items()},
                "desenho": rel_kit["desenho"],
                "dist_min_texto_px": {k: round(v, 1) for k, v in sorted(rel_kit["distMinTexto"].items(), key=lambda kv: kv[1])[:8]}},
        "render": medidas,
        "remotion_vs_hyperframes": comparar(arqs["remotion"], arqs["hyperframes"]),
    }
    falhas = rel_kit["falhas"] + [f"{k}: {f}" for k, m in medidas.items() for f in m["falhas"]]
    resultado["falhas"] = falhas
    (AQUI / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, m in medidas.items():
        print(k, json.dumps(m["resumo"], ensure_ascii=False))
    print("remotion×hyperframes:", resultado["remotion_vs_hyperframes"])
    print("FALHAS:" if falhas else "OK: nenhuma falha", *falhas, sep="\n  ")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
