"""Montador do horizontal documental: spec.json + estado → um MP4 a 60 q/s com UMA mixagem (fase 5; ver README.md).

    python montar.py <pasta_do_projeto_horizontal> [--final] [--cenas id,id] [--checar] [--livre] [--registrar] [--forcar]

- `--checar`: só confere se dá para montar (ativos, receitas, banco de SFX, narração) e sai.
- `--cenas`: renderiza (ou acha no cache) só os trechos dessas cenas, sem juntar (cena por demanda).
- `--final`: 1920×1080 e codificação mais lenta; o padrão é o RASCUNHO (1280×720, rápido).
- `--livre`: não exige SPEC aprovada/verificação no estado.json (testes do montador).
- `--registrar`: grava o resultado no estado.json (etapa `rascunho`: `gerado` ou `falhou`), como o painel faz.
Saída: `<pasta>/rascunho/rascunho.mp4` + `relatorio.json` (tudo) + `verificacao/` (medidas e folhas); com
`--registrar`, `rascunho.json` (resumo) é o arquivo da etapa no estado.json.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(AQUI.parent / "diretor"))

import blocos as B       # noqa: E402
import juncao as J       # noqa: E402
import mixagem as M      # noqa: E402
import quadros as Q      # noqa: E402
import receitas as R     # noqa: E402
import segmentos as S    # noqa: E402

FPS = 60
RESOLUCAO = {"rascunho": (1280, 720), "final": (1920, 1080)}


class NaoMonta(Exception):
    """O que falta para montar (mensagem clara para o painel)."""


def _diretor():
    import comum
    import etapas
    return comum, etapas


def narracao(pasta: Path) -> Path | None:
    for c in (pasta / "narracao.wav", pasta.parent / "trabalho" / "gravacao" / "limpa.wav"):
        if c.exists():
            return c
    return None


def trilha(pasta: Path) -> Path | None:
    return next((c for c in (pasta / "trilha.wav", pasta / "trilha.mp3") if c.exists()), None)


def _transicoes(cenas: list[dict]) -> list[dict | None]:
    """Transição de ENTRADA de cada cena no formato do kit (None = 1ª cena ou corte sem quadros)."""
    out = [None]
    for c in cenas[1:]:
        t = c["transicao"]
        out.append({"tipo": t["tipo"], "em": c["t0"], **({"quadros": t["quadros"]} if t["tipo"] != "corte" else {})})
    return out


def planejar(pasta: Path, exigir_estado: bool = True, por_cena: bool = False) -> dict:
    """Lê SPEC, palavras e estado; monta as receitas de todas as cenas. NaoMonta com TUDO o que falta.
    `por_cena` (storyboard): o que falta numa cena não barra as outras; vai em `problemas_cena` {id: motivo}."""
    comum, etapas = _diretor()
    pasta = Path(pasta)
    spec = comum.ler_json(pasta / "spec.json")
    if not spec:
        raise NaoMonta("sem spec.json: gere e aprove a SPEC antes do rascunho")
    problemas, avisos = [], []
    if exigir_estado:
        est = etapas.ler(pasta)
        st = {n: est["etapas"][n]["status"] for n in etapas.NOMES}
        if st["spec"] != "aprovado":
            problemas.append(f"a SPEC está '{st['spec']}': aprove ★ antes de montar")
        if st["verificacao"] not in ("gerado",):
            problemas.append(f"a Verificação está '{st['verificacao']}': rode a verificação da SPEC atual antes de montar")
        v = comum.ler_json(pasta / etapas.ARQUIVO["verificacao"]) or {}
        if v.get("status") == "reprovado":
            problemas.append(f"a verificação reprovou a SPEC ({len(v.get('erros', []))} erro(s)): corrija antes de montar")
    _, palavras, tempos, _ = comum.entradas(pasta)
    if tempos == "estimados":
        avisos.append("tempos ESTIMADOS (sem narração medida): o rascunho serve só para ver a ordem e o ritmo aproximado")
    cenas = spec["cenas"]
    trans = _transicoes(cenas)
    try:
        est_t = J.estados([t for t in trans if t], 1280, 720, _tmp(pasta))
    except RuntimeError as e:
        raise NaoMonta(str(e)) from None
    it = iter(est_t)
    est_por_cena = [next(it) if t else None for t in trans]
    jobs, por_id = [], {}
    for k, c in enumerate(cenas):
        n_in = est_por_cena[k]["n"] if est_por_cena[k] else 0
        n_out = est_por_cena[k + 1]["n"] if k + 1 < len(cenas) and est_por_cena[k + 1] else 0
        L = int(round(c["t1"] * FPS)) - int(round(c["t0"] * FPS))
        if n_in - n_in // 2 + n_out // 2 > L:
            por_id[c["id"]] = f"transições maiores que a cena ({L} quadros)"
            problemas.append(f"cena {c['id']} (“{c['em']}”): transições maiores que a cena ({L} quadros)")
            continue
        try:
            jobs.append(R.receita(c, palavras, n_in // 2, n_out - n_out // 2))
        except (R.FaltaAtivo, R.SemReceita) as e:
            por_id[c["id"]] = f"{'falta ' if isinstance(e, R.FaltaAtivo) else ''}{e}"
            problemas.append(f"cena {c['id']} (“{c['em']}”, {c['motor']}): {'falta ' if isinstance(e, R.FaltaAtivo) else ''}{e}")
    try:
        M.pasta_banco()
    except FileNotFoundError as e:
        if por_cena:
            avisos.append(str(e))
        else:
            problemas.append(str(e))
    if por_cena:   # storyboard: só o que é da cena; estado/banco de SFX não barram a prévia
        return {"spec": spec, "palavras": palavras, "tempos": tempos, "jobs": jobs, "transicoes": est_por_cena,
                "problemas_cena": por_id, "avisos": avisos + [p for p in problemas if not p.startswith("cena ")]}
    narr = narracao(pasta)
    if not narr:
        avisos.append("sem narração (narracao.wav ou trabalho/gravacao/limpa.wav): rascunho sem voz")
    if not trilha(pasta):
        avisos.append("sem trilha (trilha.wav/.mp3 na pasta): rascunho sem música")
    if problemas:
        raise NaoMonta("não dá para montar: " + " | ".join(problemas))
    return {"spec": spec, "palavras": palavras, "tempos": tempos, "jobs": jobs, "transicoes": est_por_cena,
            "narracao": narr, "trilha": trilha(pasta), "avisos": avisos}


def _tmp(pasta: Path) -> Path:
    t = Path(pasta) / "trechos" / "_montagem"
    t.mkdir(parents=True, exist_ok=True)
    return t


def montar(pasta: Path, modo: str = "rascunho", cenas: list[str] | None = None, exigir_estado: bool = True,
           forcar: bool = False, log=print, teto_bloco: float | None = None) -> dict:
    teto_bloco = B.TETO_BLOCO_S if teto_bloco is None else teto_bloco
    pasta = Path(pasta)
    W, H = RESOLUCAO[modo]
    t_ini = time.time()
    plano = planejar(pasta, exigir_estado)
    spec, jobs = plano["spec"], plano["jobs"]
    alvo = [j for j in jobs if not cenas or j["cena"] in cenas]
    if cenas and len(alvo) != len(set(cenas)):
        raise NaoMonta(f"cena(s) não existem na SPEC: {sorted(set(cenas) - {j['cena'] for j in jobs})}")
    trechos = {}
    # Remotion: as cenas que faltam vão em lotes (o motor abre uma vez por lote); HyperFrames: uma a uma
    lote = S.renderizar_lote([j for j in alvo if j["motor"] == "remotion"], pasta, W, H, rascunho=modo == "rascunho", forcar=forcar)
    for j in alvo:
        r = lote.get(j["cena"]) or S.renderizar(j, pasta, W, H, rascunho=modo == "rascunho", forcar=forcar)
        log(f"  cena {j['cena']} {j['motor']:11} {r['quadros']:5} q  {'cache' if r['do_cache'] else 'renderizada'}")
        trechos[j["cena"]] = r
    if cenas:
        return {"cenas": trechos}
    # transições nas coordenadas da saída (a barra do wipe e o desfoque dependem da largura)
    tmp = _tmp(pasta)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    trans = _transicoes(spec["cenas"])
    est_t = iter(J.estados([t for t in trans if t], W, H, tmp))
    est = [next(est_t) if t else None for t in trans]
    lista = [trechos[c["id"]] for c in spec["cenas"]]
    pcs = J.pecas(spec["cenas"], lista, est, W, H, tmp)
    total = int(round(spec["cenas"][-1]["t1"] * FPS))
    saida_dir = pasta / modo
    saida_dir.mkdir(parents=True, exist_ok=True)
    evs = M.eventos(spec["cenas"], plano["palavras"], [e for e in est if e])
    log(f"  mixagem: {len(evs)} SFX, narração {'sim' if plano['narracao'] else 'não'}, trilha {'sim' if plano['trilha'] else 'não'}")
    mix = M.mixar(evs, total / FPS, saida_dir / "audio", plano["narracao"], plano["trilha"])
    mp4 = saida_dir / f"{modo}.mp4"
    # blocos de cenas inteiras (≤ teto), cada um codificado à parte e com cache; junção final sem recodificar o vídeo
    cenas_s = spec["cenas"]
    grupos, av_blocos = B.agrupar(cenas_s, [e["n"] if e else 0 for e in est], teto_bloco)
    th = {c["id"]: {"hash": trechos[c["id"]]["hash"], "quadros": trechos[c["id"]]["quadros"]} for c in cenas_s}
    tr_info = {c["id"]: {"hash_estado": _diretor()[0].hash_dados(est[k]["quadros"]), "a": th[cenas_s[k - 1]["id"]]["hash"],
                         "b": th[c["id"]]["hash"]} for k, c in enumerate(cenas_s) if est[k]}
    segs = B.codificar(B.segmentos(pcs, cenas_s, grupos), th, tr_info, pasta, modo, W, H, tmp, forcar=forcar, log=log)
    B.concatenar(segs, Path(mix["arquivos"]["master"]), mp4, modo == "rascunho", tmp)
    B.limpar(pasta, modo, segs, manter=len(segs))   # guarda uma versão anterior de cada bloco (desfazer barato)
    cod = segs[0]["codec"]
    rel = {"versao": 1, "modo": modo, "arquivo": str(mp4), "largura": W, "altura": H, "fps": FPS, "quadros": total,
           "duracao": round(total / FPS, 4), "codificador": cod, "spec_hash": _diretor()[0].hash_dados(spec),
           "tempos": plano["tempos"], "avisos": plano["avisos"] + mix["avisos"] + av_blocos,
           "blocos": {"teto_s": teto_bloco, "segmentos": segs,
                      "codificados": sum(1 for s in segs if not s["do_cache"]), "do_cache": sum(1 for s in segs if s["do_cache"])},
           "cenas": [{"id": c["id"], "em": c["em"], "motor": c["motor"], "kits": j["kits"], "Q0": int(round(c["t0"] * FPS)),
                      "Q1": int(round(c["t1"] * FPS)), "pre": j["pre"], "pos": j["pos"], "transicao": c["transicao"]["tipo"],
                      "n_entrada": est[k]["n"] if est[k] else 0, "hash": j["hash"], "trecho": trechos[c["id"]]["arquivo"],
                      "trecho_quadros": trechos[c["id"]]["quadros"], "do_cache": trechos[c["id"]]["do_cache"]}
                     for k, (c, j) in enumerate(zip(spec["cenas"], jobs))],
           "pecas": pcs, "audio": mix}
    log("  verificando quadros, junções e sincronia…")
    rel["verificacao"] = Q.verificar(rel, saida_dir / "verificacao")
    rel["segundos"] = round(time.time() - t_ini, 1)
    (saida_dir / "relatorio.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    return rel


def resumo(rel: dict) -> str:
    v = rel["verificacao"]
    nov = sum(1 for c in rel["cenas"] if not c["do_cache"])
    b = rel.get("blocos") or {}
    return (f"{len(rel['cenas'])} cenas ({nov} renderizadas, {len(rel['cenas']) - nov} do cache), "
            + (f"{len(b['segmentos'])} bloco(s)/junção(ões) ({b['codificados']} codificado(s)), " if b else "")
            + f"{rel['duracao']:.1f} s, "
            f"{rel['largura']}x{rel['altura']} 60 q/s, {rel['audio']['master']['lufs']:.1f} LUFS; verificação {v['status']}"
            + (f" ({len(v['erros'])} erro(s))" if v["erros"] else ""))


def _main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    pasta = Path(argv[0])
    modo = "final" if "--final" in argv else "rascunho"
    cenas = argv[argv.index("--cenas") + 1].split(",") if "--cenas" in argv else None
    exigir = "--livre" not in argv
    registrar = "--registrar" in argv
    if "--checar" in argv:
        try:
            p = planejar(pasta, exigir)
        except NaoMonta as e:
            print(e)
            return 1
        print(f"ok: {len(p['jobs'])} cenas prontas para montar")
        for a in p["avisos"]:
            print("  aviso:", a)
        return 0
    try:
        rel = montar(pasta, modo, cenas, exigir, "--forcar" in argv)
    except Exception as e:   # noqa: BLE001 — o painel precisa do motivo de qualquer falha
        msg = str(e) if isinstance(e, NaoMonta) else f"{type(e).__name__}: {str(e)[:600]}"
        print("FALHOU:", msg)
        if not isinstance(e, NaoMonta):
            traceback.print_exc()
        if registrar:
            _diretor()[1].marcar(pasta, modo if modo == "rascunho" else "rascunho", "falhou", msg[:300])
        return 1
    if cenas:
        return 0
    print(resumo(rel))
    for e in rel["verificacao"]["erros"]:
        print("  ERRO", e)
    if registrar and modo == "rascunho":
        _, etapas = _diretor()
        spec = json.loads((pasta / "spec.json").read_text(encoding="utf-8"))
        dados = {k: rel[k] for k in ("versao", "modo", "arquivo", "largura", "altura", "fps", "quadros", "duracao", "spec_hash", "tempos", "avisos")}
        dados["cenas"] = [{k: c[k] for k in ("id", "motor", "Q0", "Q1", "hash", "do_cache")} for c in rel["cenas"]]
        dados["loudness"] = rel["audio"]["master"]
        dados["blocos"] = {k: rel["blocos"][k] for k in ("teto_s", "codificados", "do_cache")}
        dados["blocos"]["segmentos"] = [{k: s[k] for k in ("tipo", "cenas", "quadros", "hash")} for s in rel["blocos"]["segmentos"]]
        dados["verificacao"] = {k: rel["verificacao"][k] for k in ("status", "erros", "avisos")}
        if rel["verificacao"]["erros"]:
            etapas.marcar(pasta, "rascunho", "falhou", f"verificação do vídeo reprovou: {rel['verificacao']['erros'][0][:200]}")
        else:
            etapas.registrar(pasta, "rascunho", dados, base=spec, resumo=resumo(rel))
    return 1 if rel["verificacao"]["erros"] else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
