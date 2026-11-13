"""Teste de render do kit/transicoes nos DOIS motores + folhas de sequência a 60 q/s + sincronia com o SFX.

1. regera kit/transicoes/transicoes.global.js (esbuild) e roda o teste do kit (node testes.ts);
2. calcula os eventos de SFX (kit/sfx, Banco semente 0) e monta: public dir do Remotion e assets/sfx + tags <audio> do
   HyperFrames, só com os WAVs usados (o banco fica fora do Git: procura em kit/sfx/banco aqui ou na pasta principal);
3. renderiza PNG quadro a quadro nos dois motores e mede nos PIXELS, para cada transição:
   - duração = quadros que não são iguais à cena A pura (quadro antes) nem à B pura (quadro depois): deve ser EXATAMENTE
     a declarada (corte = 0: o quadro do corte já é a cena B inteira);
   - quadro de maior mudança entre quadros seguidos × quadro de pico do kit (onde cai o pico do som);
4. renderiza MP4 com som nos dois motores e mede, no áudio, o pico de cada SFX × o quadro de pico da transição;
5. compara os motores, monta as folhas (JPG) e grava resultado.json.

  .venv\\Scripts\\python.exe F1\\horizontal\\testes\\transicoes\\rodar.py [--sem-render] [--sem-audio]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import motores as M  # noqa: E402

HORIZ = M.HORIZ
KIT = HORIZ / "kit" / "transicoes"
SFX = HORIZ / "kit" / "sfx"
SAIDA = AQUI / "saida"


def banco() -> Path:
    for base in [M.RAIZ, *M.RAIZ.parents]:
        p = base / "F1" / "horizontal" / "kit" / "sfx" / "banco"
        if p.is_dir():
            return p.parent
    raise SystemExit("kit/sfx/banco não encontrado: rode .venv\\Scripts\\python.exe F1\\horizontal\\kit\\sfx\\gerar.py")


def dados_kit() -> dict:
    script = ("import {montarTransicoes, pedidosSfx} from './transicoes.ts'; import {Banco} from '../sfx/sfx.ts'; import {readFileSync} from 'node:fs';"
              "const c = JSON.parse(readFileSync('exemplo/cena.json','utf-8')); const cat = JSON.parse(readFileSync('../sfx/catalogo.json','utf-8'));"
              "const ts = montarTransicoes(c.transicoes, c.fps); const ev = new Banco(cat, 0).dePedidos(pedidosSfx(ts));"
              "console.log(JSON.stringify({ts: ts.map(t => ({tipo: t.t.tipo, n: t.n, q0: t.q0, qCorte: t.qCorte, qPico: t.qPico, tPico: t.tPico, sfx: t.t.sfx})), eventos: ev,"
              "pico: Object.fromEntries(cat.itens.map(i => [i.id, i.pico_s]))}));")
    tmp = KIT / "_dados.mts"
    tmp.write_text(script, encoding="utf-8")
    try:
        return json.loads(M.sh(["node", tmp.name], cwd=KIT).stdout)
    finally:
        tmp.unlink()


def tags_audio(eventos: list[dict]) -> str:
    """Mesma regra de sfx.py/para_hyperframes (trilhas alternadas para sons sobrepostos)."""
    linhas, fim = [], {}
    for k, e in enumerate(eventos):
        tr = next(t for t in range(20, 84) if fim.get(t, -1) <= e["inicio"])
        fim[tr] = e["inicio"] + e["dur"]
        vol = min(1.0, 10 ** (e["ganho_db"] / 20))
        linhas.append(f'<audio id="sfx-{k:02d}" class="clip" src="assets/sfx/{Path(e["arquivo"]).name}" data-start="{e["inicio"]:.3f}" '
                      f'data-duration="{e["dur"]:.3f}"' + (f' data-media-start="{e["corte_ini"]:.3f}"' if e["corte_ini"] else "")
                      + f' data-track-index="{tr}" data-volume="{vol:.4f}"></audio>')
    return "\n  ".join(linhas)


def difere(a: np.ndarray, b: np.ndarray) -> bool:
    """quadro diferente de verdade: ≥ 300 pixels com diferença > 3 níveis (o antisserrilhado não conta)"""
    return int((np.abs(a - b).max(-1) > 3).sum()) >= 300


def medir_pixels(motor: str, arqs: list[Path], ts: list[dict]) -> dict:
    res = {"motor": motor, "quadros": len(arqs), "transicoes": [], "falhas": []}
    for i, t in enumerate(ts):
        if t["n"] == 0:
            qa, qb = t["qCorte"] - 1, t["qCorte"]
        else:
            qa, qb = t["q0"] - 1, t["q0"] + t["n"]
        A, B = M.img(arqs[qa]), M.img(arqs[qb])
        medidos = []
        for q in range(qa - 8, qb + 9):
            Q = M.img(arqs[q])
            if difere(Q, A) and difere(Q, B):
                medidos.append(q)
        # quadro de maior mudança (diferença média para o quadro anterior)
        mud = {q: float(np.abs(M.img(arqs[q]) - M.img(arqs[q - 1])).mean()) for q in range(qa + 1, qb + 1)}
        q_mud = max(mud, key=mud.get)
        r = {"tipo": t["tipo"], "declarado": t["n"], "medido": len(medidos),
             "primeiro": medidos[0] if medidos else None, "ultimo": medidos[-1] if medidos else None,
             "q_pico_kit": t["qPico"], "q_maior_mudanca": q_mud}
        res["transicoes"].append(r)
        if len(medidos) != t["n"] or (medidos and (medidos[0] != t["q0"] or medidos[-1] != t["q0"] + t["n"] - 1)):
            res["falhas"].append(f"{i} {t['tipo']}: duração medida {len(medidos)} quadros ({r['primeiro']}–{r['ultimo']}), declarada {t['n']} a partir de q{t['q0']}")
        tol = 0 if t["n"] == 0 else 2
        if abs(q_mud - t["qPico"]) > tol:
            res["falhas"].append(f"{i} {t['tipo']}: maior mudança em q{q_mud}, pico do kit em q{t['qPico']}")
    return res


def ler_audio(mp4: Path) -> tuple[np.ndarray, int]:
    wav = mp4.with_suffix(".wav")
    M.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-ac", "1", "-ar", "48000", wav])
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        return x, w.getframerate()


def medir_audio(motor: str, mp4: Path, ts: list[dict], eventos: list[dict], pico: dict) -> dict:
    x, sr = ler_audio(mp4)
    # mesmo envelope que define pico_s no catálogo (kit/sfx/gerar.py: RMS em janela de 10 ms; o pico do catálogo é o
    # início do bloco de 10 ms, por isso a janela aqui vai de t a t+10 ms)
    n = int(0.01 * sr)
    c = np.concatenate([[0.0], np.cumsum(x * x)])
    env = np.sqrt((c[n:] - c[:-n]) / n)
    res = {"motor": motor, "eventos": [], "falhas": []}
    com_som = [t for t in ts if t["sfx"]]
    for t, e in zip(com_som, eventos):
        i0, i1 = int((t["tPico"] - 0.15) * sr), int((t["tPico"] + 0.15) * sr)
        tm = (i0 + int(np.argmax(env[i0:i1]))) / sr
        esperado = e["inicio"] - e["corte_ini"] + pico[e["id"]]
        res["eventos"].append({"tipo": t["tipo"], "som": e["id"], "t_pico_kit": t["tPico"], "pico_esperado_s": round(esperado, 4),
                               "pico_medido_s": round(tm, 4), "erro_ms": round((tm - t["tPico"]) * 1000, 1)})
        if abs(tm - t["tPico"]) > 0.02:
            res["falhas"].append(f"{t['tipo']}: pico do som em {tm:.3f} s, quadro de pico {t['tPico']:.3f} s")
    return res


def main() -> None:
    sem_render, sem_audio = "--sem-render" in sys.argv, "--sem-audio" in sys.argv
    SAIDA.mkdir(exist_ok=True)
    M.construir_global(KIT / "transicoes.ts", "Transicoes")
    kit_out = M.sh(["node", KIT / "testes.ts"]).stdout.strip().splitlines()
    d = dados_kit()
    ts, eventos = d["ts"], d["eventos"]
    origem = banco()
    publico = SAIDA / "remotion_public"
    if publico.exists():
        shutil.rmtree(publico)
    for e in eventos:
        (publico / e["arquivo"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem / e["arquivo"], publico / e["arquivo"])
    idx = (HORIZ / "hyperframes" / "transicoes" / "exemplo" / "index.html").read_text(encoding="utf-8").replace("<!--SFX-->", tags_audio(eventos))
    idx_tmp = SAIDA / "index_hf.html"
    idx_tmp.write_text(idx, encoding="utf-8")
    assets = {"transicoes.global.js": KIT / "transicoes.global.js", "camada.js": HORIZ / "hyperframes" / "transicoes" / "camada.js",
              "cena.js": "window.__CENA = " + (KIT / "exemplo" / "cena.json").read_text(encoding="utf-8") + ";"}
    ex_r = HORIZ / "remotion" / "transicoes" / "exemplo"
    pastas = {"remotion": SAIDA / "remotion", "hyperframes": SAIDA / "hyperframes"}
    if not sem_render:
        M.render_remotion(ex_r, "ExemploTransicoes", pastas["remotion"], {"semSom": True})
        M.render_hyperframes(HORIZ / "hyperframes" / "transicoes" / "exemplo" / "index.html", assets, pastas["hyperframes"], SAIDA / "hf_projeto")  # sem som (PNG)
    arqs = {k: M.quadros(p) for k, p in pastas.items()}
    medidas = {k: medir_pixels(k, v, ts) for k, v in arqs.items()}
    audio = {}
    if not sem_audio:
        mp4r = SAIDA / "remotion.mp4"
        M.sh(["node", M.NM / "@remotion" / "cli" / "remotion-cli.js", "render", "index.tsx", "ExemploTransicoes", mp4r,
              f"--public-dir={publico}", f"--browser-executable={M.NAVEGADOR}", "--log=error"], cwd=ex_r)
        proj = SAIDA / "hf_audio"
        if proj.exists():
            shutil.rmtree(proj)
        (proj / "assets" / "sfx").mkdir(parents=True)
        shutil.copy2(idx_tmp, proj / "index.html")
        for nome, v in assets.items():
            (proj / "assets" / nome).write_text(v, encoding="utf-8") if isinstance(v, str) else shutil.copy2(v, proj / "assets" / nome)
        for e in eventos:
            shutil.copy2(origem / e["arquivo"], proj / "assets" / "sfx" / Path(e["arquivo"]).name)
        (proj / "package.json").write_text(json.dumps({"name": "exemplo-transicoes", "private": True, "type": "module"}), encoding="utf-8")
        mp4h = SAIDA / "hyperframes.mp4"
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        M.sh([npx, "--yes", M.HF_VERSAO, "render", "--output", mp4h, "--quiet"], cwd=proj)
        audio = {"remotion": medir_audio("remotion", mp4r, ts, eventos, d["pico"]),
                 "hyperframes": medir_audio("hyperframes", mp4h, ts, eventos, d["pico"])}
    for k, v in arqs.items():
        for t in ts[1:]:
            q0 = t["q0"] - 2
            n = t["n"] + 4
            cols = 8
            idxs = list(range(q0, q0 + n))
            M.folha(v, idxs, None, 300, cols, f"{k}: {t['tipo']} ({t['n']} quadros, q{t['q0']}-q{t['q0'] + t['n'] - 1}; pico/SFX em q{t['qPico']}) + 2 quadros puros de cada lado, 60 q/s",
                    AQUI / f"folha_{k}_{t['tipo']}_60qs.jpg")
    resultado = {"kit": kit_out[-1], "eventos_sfx": eventos, "pixels": medidas, "audio": audio,
                 "remotion_vs_hyperframes": M.comparar(arqs["remotion"], arqs["hyperframes"], 1)}
    falhas = [f"{k}: {f}" for k, m in {**medidas, **{"audio " + a: b for a, b in audio.items()}}.items() for f in m["falhas"]]
    if not kit_out[-1].startswith("OK"):
        falhas.append("kit: " + kit_out[-1])
    if resultado["remotion_vs_hyperframes"]["pior"]["dif"] > 1.0:
        falhas.append(f"motores diferem: {resultado['remotion_vs_hyperframes']}")
    resultado["falhas"] = falhas
    (AQUI / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, m in medidas.items():
        print(k, json.dumps(m["transicoes"], ensure_ascii=False))
    for k, m in audio.items():
        print("audio", k, json.dumps(m["eventos"], ensure_ascii=False))
    print("remotion×hyperframes:", resultado["remotion_vs_hyperframes"])
    print("FALHAS:" if falhas else "OK: nenhuma falha", *falhas, sep="\n  ")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
