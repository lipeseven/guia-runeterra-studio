"""Storyboard do Rascunho (fase 7b): cada cena da SPEC com as frases, os momentos-chave e quadros de prévia.

Como o storyboard do Runeterra (por cena, ancorado em palavras), mas a prévia é o PRÓPRIO trecho do montador: gerar a
prévia de uma cena = renderizar o trecho dela (o mesmo cache por hash que o rascunho usa, `trechos/`) e tirar os
quadros dos momentos-chave. Mudou a cena (ação direta ou pedido atendido) → hash novo → só ela é renderizada de novo,
e a próxima montagem do rascunho já acha o trecho pronto.

    python storyboard.py <pasta_horizontal> previa <id,id|todas>     # roda em processo à parte (o painel dispara)

Arquivos em `<pasta>/storyboard/`: `<cena>_<hash>.json` (quadros da prévia), `<cena>_<hash>_q<N>.jpg`,
`aprovacoes.json` ({cena: hash aprovado ★}), `gerando.json` (trava enquanto renderiza), `falhas.json` (último erro por cena).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(AQUI.parent / "diretor"))

FPS = 60
LARGURA, ALTURA = 1280, 720      # a resolução do rascunho: a prévia e o rascunho dividem o mesmo trecho em cache
LARGURA_QUADRO = 480
MAX_QUADROS = 6
DEPOIS_DA_PALAVRA = 0.3           # s depois do início da palavra-âncora (o efeito já apareceu)
GERANDO_MAX_S = 2 * 3600


def _ler(p: Path, padrao=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return padrao


def _gravar(p: Path, dados) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def pasta_sb(pasta: Path) -> Path:
    return Path(pasta) / "storyboard"


def frases(palavras: list[dict], i0: int, i1: int) -> list[dict]:
    """Texto falado da cena em frases (pontuação), cada uma com o índice da 1ª palavra e o tempo."""
    out, atual, ini = [], [], i0
    for k in range(i0, i1):
        if not atual:
            ini = k
        atual.append(palavras[k]["t"])
        if re.search(r"[.!?:;]$|\.\.\.$", palavras[k]["t"]) or k == i1 - 1:
            out.append({"i": ini, "t": round(palavras[ini]["i"], 2), "texto": " ".join(atual)})
            atual = []
    return out


def _ancoras(no, out: list, onde: str) -> None:
    if isinstance(no, dict):
        if isinstance(no.get("i"), int):
            out.append((no["i"], f"{onde}{' ' + str(no['tipo']) if no.get('tipo') else ''} em “{no.get('em', '')}”"))
        for k, v in no.items():
            _ancoras(v, out, onde)
    elif isinstance(no, list):
        for v in no:
            _ancoras(v, out, onde)


def momentos(cena: dict, palavras: list[dict], job: dict | None) -> list[dict]:
    """Momentos-chave da cena: início, âncoras dos kits (ritmo, anotação…), SFX e fim. `q` = quadro LOCAL do trecho."""
    pre = job["pre"] if job else 0
    L = int(round(cena["t1"] * FPS)) - int(round(cena["t0"] * FPS))
    q_de = lambda i: pre + int(round((palavras[i]["i"] - cena["t0"] + DEPOIS_DA_PALAVRA) * FPS))   # noqa: E731
    brutos = [(pre + 6, "início", cena["i0"])]
    anc: list = []
    for u in cena.get("kits", []):
        _ancoras(u.get("params"), anc, u["kit"])
    brutos += [(q_de(i), r, i) for i, r in anc if 0 <= i < len(palavras)]
    brutos += [(q_de(s["i"]), f"SFX {s['categoria']} em “{s['em']}”", s["i"]) for s in cena.get("sfx", []) if 0 <= s["i"] < len(palavras)]
    brutos.append((pre + L - 1, "fim", max(cena["i0"], cena["i1"] - 1)))
    out: list[dict] = []
    for q, rot, i in sorted(brutos, key=lambda x: x[0]):
        q = min(max(q, pre), pre + L - 1)
        if out and q - out[-1]["q"] < 20:      # dois momentos colados viram um quadro só
            out[-1]["rotulo"] += f" · {rot}"
            continue
        out.append({"q": q, "rotulo": rot, "i": i, "t": round(cena["t0"] + (q - pre) / FPS, 2)})
    if len(out) > MAX_QUADROS:   # sobra o 1º, o último e os do meio espaçados
        meio = out[1:-1]
        passo = len(meio) / (MAX_QUADROS - 2)
        out = [out[0], *[meio[int(k * passo)] for k in range(MAX_QUADROS - 2)], out[-1]]
    return out


def _plano(pasta: Path) -> dict:
    import montar as MT
    return MT.planejar(pasta, exigir_estado=False, por_cena=True)


def _gerando(pasta: Path) -> dict:
    g = _ler(pasta_sb(pasta) / "gerando.json", {}) or {}
    if g and time.time() - g.get("inicio", 0) > GERANDO_MAX_S:
        return {}
    return g


def ler(pasta: Path, raiz: Path | None = None) -> dict:
    """Estado do storyboard para o painel (rápido: não renderiza). Caminhos dos quadros relativos a `raiz` se dada."""
    pasta = Path(pasta)
    import comum
    spec = comum.ler_json(pasta / "spec.json")
    if not spec:
        return {"cenas": [], "aviso": "sem SPEC ainda"}
    _, palavras, tempos, _ = comum.entradas(pasta)
    try:
        plano = _plano(pasta)
        jobs, problemas, aviso = {j["cena"]: j for j in plano["jobs"]}, plano["problemas_cena"], None
    except Exception as e:   # noqa: BLE001 — sem plano (ex.: transições do kit falharam) o storyboard ainda lista as cenas
        jobs, problemas, aviso = {}, {}, f"não deu para planejar as cenas: {e}"
    sb = pasta_sb(pasta)
    aprov = _ler(sb / "aprovacoes.json", {}) or {}
    falhas = _ler(sb / "falhas.json", {}) or {}
    rasc = {c["id"]: c["hash"] for c in (_ler(pasta / "rascunho" / "rascunho.json", {}) or {}).get("cenas", [])}
    gerando = _gerando(pasta)

    def rel(p: Path) -> str:
        if raiz:
            try:
                return Path(p).resolve().relative_to(Path(raiz).resolve()).as_posix()
            except ValueError:
                pass
        return str(p)

    cenas = []
    for n, c in enumerate(spec["cenas"]):
        job = jobs.get(c["id"])
        h = job["hash"] if job else None
        previa = _ler(sb / f"{c['id']}_{h}.json") if h else None
        vistas_antes = bool(list(sb.glob(f"{c['id']}_*.json"))) if sb.exists() else False
        if c["id"] in problemas:
            st = "sem_receita"
        elif c["id"] in gerando.get("cenas", []):
            st = "gerando"
        elif h and aprov.get(c["id"]) == h:
            st = "aprovada"
        elif previa:
            st = "pronta"
        elif falhas.get(c["id"], {}).get("hash") == h:
            st = "falhou"
        elif (c["id"] in aprov) or vistas_antes or (c["id"] in rasc and rasc[c["id"]] != h):
            st = "desatualizada"
        else:
            st = "sem_previa"
        cenas.append({
            "id": c["id"], "n": n + 1, "em": c["em"], "i0": c["i0"], "i1": c["i1"], "t0": c["t0"], "t1": c["t1"],
            "capitulo": c["capitulo"], "objetivo": c["objetivo"], "motor": c["motor"],
            "kits": [{"kit": u["kit"], "params": u["params"]} for u in c.get("kits", [])],
            "texto_tela": c.get("texto", []), "camera": c.get("camera"), "movimento": c.get("movimento"),
            "transicao": c["transicao"], "sfx": c.get("sfx", []),
            "frases": frases(palavras, c["i0"], c["i1"]),
            "momentos": momentos(c, palavras, job), "hash": h, "estado": st,
            "problema": problemas.get(c["id"]), "falha": falhas.get(c["id"], {}).get("erro") if st == "falhou" else None,
            "no_rascunho": rasc.get(c["id"]) == h if c["id"] in rasc else None,
            "quadros": [{**q, "arquivo": rel(sb / q["arquivo"])} for q in (previa or {}).get("quadros", [])],
        })
    return {"cenas": cenas, "tempos": tempos, "gerando": gerando.get("cenas", []), "aviso": aviso,
            "palavras": [p["t"] for p in palavras],
            "contagem": {k: sum(1 for c in cenas if c["estado"] == k) for k in
                         ("aprovada", "pronta", "desatualizada", "sem_previa", "gerando", "falhou", "sem_receita")}}


def aprovar(pasta: Path, cid: str) -> dict:
    """★ da cena: guarda o hash que o Felipe viu. Recusa se a prévia do hash atual não existe."""
    plano = _plano(pasta)
    job = next((j for j in plano["jobs"] if j["cena"] == cid), None)
    if not job:
        raise ValueError(plano["problemas_cena"].get(cid) or f"cena {cid} não existe na SPEC")
    if not (pasta_sb(pasta) / f"{cid}_{job['hash']}.json").exists():
        raise ValueError("gere e veja a prévia desta versão da cena antes de aprovar ★")
    arq = pasta_sb(pasta) / "aprovacoes.json"
    a = _ler(arq, {}) or {}
    a[cid] = job["hash"]
    _gravar(arq, a)
    return a


def _extrair(trecho: Path, qs: list[int], destino: list[Path]) -> None:
    expr = "+".join(f"eq(n\\,{q})" for q in qs)
    tmp = destino[0].parent / f"_x_{destino[0].stem}_%02d.jpg"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(trecho), "-vf", f"select='{expr}',scale={LARGURA_QUADRO}:-2",
                        "-fps_mode", "passthrough", "-q:v", "4", str(tmp)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg (quadros da prévia): {r.stderr[-600:]}")
    for k, d in enumerate(destino):
        src = tmp.parent / (tmp.name.replace("%02d", f"{k + 1:02d}"))
        if not src.exists():
            raise RuntimeError(f"quadro {qs[k]} não saiu do trecho {trecho.name}")
        src.replace(d)


def gerar(pasta: Path, cenas: list[str] | None, log=print) -> dict:
    """Renderiza (ou acha no cache) o trecho de cada cena pedida e grava os quadros da prévia. Uma cena que falha não
    derruba as outras (motivo em `falhas.json`)."""
    import comum
    import segmentos as S
    pasta = Path(pasta)
    sb = pasta_sb(pasta)
    sb.mkdir(parents=True, exist_ok=True)
    plano = _plano(pasta)
    spec = plano["spec"]
    _, palavras, _, _ = comum.entradas(pasta)
    por_id = {c["id"]: c for c in spec["cenas"]}
    alvo = [j for j in plano["jobs"] if not cenas or j["cena"] in cenas]
    falhas = _ler(sb / "falhas.json", {}) or {}
    feitas = {}
    for c in cenas or []:
        if c in plano["problemas_cena"]:
            falhas[c] = {"hash": None, "erro": plano["problemas_cena"][c]}
    # Remotion em lote (abre o motor uma vez para todas as cenas Remotion pedidas); HyperFrames uma a uma
    try:
        rem = [j for j in alvo if j["motor"] == "remotion"]
        res = S.renderizar_lote(rem, pasta, LARGURA, ALTURA, rascunho=True) if rem else {}
    except Exception as e:   # noqa: BLE001
        res = {}
        for j in rem:
            falhas[j["cena"]] = {"hash": j["hash"], "erro": f"{type(e).__name__}: {str(e)[:400]}"}
        log(f"  lote remotion falhou: {e}")
    for j in alvo:
        try:
            r = res.get(j["cena"]) or (S.renderizar(j, pasta, LARGURA, ALTURA, rascunho=True) if j["motor"] != "remotion" else None)
            if r is None:
                continue
            ms = momentos(por_id[j["cena"]], palavras, j)
            qs = sorted({m["q"] for m in ms})
            arqs = [sb / f"{j['cena']}_{j['hash']}_q{q}.jpg" for q in qs]
            _extrair(Path(r["arquivo"]), qs, arqs)
            quadros = [{**m, "arquivo": f"{j['cena']}_{j['hash']}_q{m['q']}.jpg"} for m in ms]
            _gravar(sb / f"{j['cena']}_{j['hash']}.json", {"cena": j["cena"], "hash": j["hash"], "motor": j["motor"],
                                                           "trecho": r["arquivo"], "do_cache": r["do_cache"], "quadros": quadros})
            for velho in sb.glob(f"{j['cena']}_*"):       # prévias de versões antigas desta cena saem (o trecho fica no cache)
                if j["hash"] not in velho.name:
                    velho.unlink(missing_ok=True)
            falhas.pop(j["cena"], None)
            feitas[j["cena"]] = {"do_cache": r["do_cache"], "quadros": len(quadros)}
            log(f"  cena {j['cena']} {j['motor']:11} {'cache' if r['do_cache'] else 'renderizada'} · {len(quadros)} quadro(s)")
        except Exception as e:   # noqa: BLE001
            falhas[j["cena"]] = {"hash": j["hash"], "erro": f"{type(e).__name__}: {str(e)[:400]}"}
            log(f"  cena {j['cena']} FALHOU: {e}")
    _gravar(sb / "falhas.json", falhas)
    return {"feitas": feitas, "falhas": {k: v for k, v in falhas.items() if not cenas or k in cenas}}


def _main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) < 3 or argv[1] != "previa":
        print(__doc__)
        return 2
    pasta = Path(argv[0])
    cenas = None if argv[2] == "todas" else argv[2].split(",")
    try:
        r = gerar(pasta, cenas)
        fila = pasta_sb(pasta) / "fila.json"
        while (pedidas := _ler(fila, [])):   # cenas pedidas enquanto este processo renderizava
            fila.unlink(missing_ok=True)
            r2 = gerar(pasta, pedidas)
            r = {"feitas": {**r["feitas"], **r2["feitas"]}, "falhas": {**r["falhas"], **r2["falhas"]}}
    except Exception as e:   # noqa: BLE001
        traceback.print_exc()
        falhas = _ler(pasta_sb(pasta) / "falhas.json", {}) or {}
        for c in cenas or []:
            falhas[c] = {"hash": None, "erro": f"{type(e).__name__}: {str(e)[:400]}"}
        _gravar(pasta_sb(pasta) / "falhas.json", falhas)
        return 1
    finally:
        (pasta_sb(pasta) / "gerando.json").unlink(missing_ok=True)
    print(json.dumps(r, ensure_ascii=False))
    return 1 if r["falhas"] else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
