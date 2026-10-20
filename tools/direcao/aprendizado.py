"""Aprendizado entre vídeos, por canal (os canais não se conhecem: cada um tem a sua pasta).

1. coletar(): ao PUBLICAR (antes do arquivamento), lê o storyboard do vídeo e guarda
   - os pares de legenda "o diretor escreveu → o Felipe corrigiu" (exemplos reais para o diretor pegar o tom);
   - a retrospectiva dos ajustes (tipos trocados, momento do texto, imagens trocadas, pedidos ao diretor…).
2. propor(): uma chamada pequena ao Sonnet transforma a retrospectiva em REGRAS NOVAS propostas — nada entra nas
   regras sem o Felipe aprovar no painel.
3. exemplos_para_o_prompt(): os pares mais recentes vão no prompt do diretor.

Arquivos em <dados do canal>/aprendizado/: exemplos_legendas.json, propostas.json, retrospectiva_<slug>.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canal import CANAL, caminho  # noqa: E402

PASTA = caminho("dados_acervo").parent / "aprendizado"  # Runeterra: dados/aprendizado
MAX_EXEMPLOS = 40
NO_PROMPT = 15


def _ler(arq: Path, padrao):
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else padrao


def _gravar(arq: Path, dados) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def coletar(pasta_video: Path, slug: str, titulo: str) -> dict | None:
    """Lê plano + ajustes do vídeo e guarda exemplos e retrospectiva. Devolve a retrospectiva (None = nada a aprender)."""
    dirc = pasta_video / "direcao"
    if not (dirc / "plano.json").exists() or not (dirc / "ajustes.json").exists():
        return None
    plano = json.loads((dirc / "plano.json").read_text(encoding="utf-8"))
    ajustes = json.loads((dirc / "ajustes.json").read_text(encoding="utf-8"))
    cenas = {c.get("id"): c for c in plano.get("cenas", [])}

    pares = []
    for cid, aj in ajustes.items():
        c = cenas.get(cid)
        if c and "legenda" in aj and (aj["legenda"] or "") != (c.get("legenda") or "") and aj["legenda"]:
            pares.append({"diretor": c.get("legenda") or "(sem texto)", "felipe": aj["legenda"], "tipo": c["tipo"],
                          "video": titulo})
    arq_ex = PASTA / "exemplos_legendas.json"
    exemplos = [e for e in _ler(arq_ex, []) if e.get("video") != titulo] + pares
    _gravar(arq_ex, exemplos[-MAX_EXEMPLOS:])

    tipos = Counter((cenas[c]["tipo"], a["tipo"]) for c, a in ajustes.items()
                    if c in cenas and a.get("tipo") and a["tipo"] != cenas[c]["tipo"])
    momento = [a["legenda_indice"] for a in ajustes.values() if "legenda_indice" in a]
    retro = {
        "video": titulo, "slug": slug, "quando": datetime.now().isoformat(timespec="seconds"),
        "cenas_no_plano": len(cenas), "cenas_ajustadas": len(ajustes),
        "tipos_no_plano": dict(Counter(c["tipo"] for c in cenas.values()).most_common()),
        "tipo_trocado": [f"{a} → {b}: {n}" for (a, b), n in tipos.most_common(12)],
        "imagem_trocada": sum(1 for a in ajustes.values() if "candidato" in a or "midia" in a),
        "texto_reescrito": len(pares),
        "momento_do_texto": {"mudado": len(momento), "junto_com_a_imagem": sum(1 for m in momento if m < 0)},
        "cenas_removidas": sum(1 for a in ajustes.values() if a.get("removida") and not a.get("juntada_em")),
        "juntadas": sum(1 for a in ajustes.values() if a.get("juntar")),
        "corte_movido": sum(1 for a in ajustes.values() if "inicio_indice" in a),
        "movimento_escolhido": dict(Counter(a["movimento"] for a in ajustes.values() if a.get("movimento"))),
        "pedidos_ao_diretor": [a["comentario"][:200] for a in ajustes.values() if a.get("comentario")][:30],
        "exemplos_de_legenda": pares[:25],
    }
    _gravar(PASTA / f"retrospectiva_{slug}.json", retro)
    return retro


def propor(slug: str, regras_atuais: str, chamar_json) -> list[dict]:
    """Retrospectiva → até 5 regras novas propostas (pendentes de aprovação)."""
    retro = _ler(PASTA / f"retrospectiva_{slug}.json", None)
    if not retro or retro["cenas_ajustadas"] == 0:
        return []
    r = chamar_json(
        f"Você melhora o diretor visual automático do canal \"{CANAL['nome']}\" ({CANAL['assunto']}).\n"
        "Abaixo: o que o Felipe precisou corrigir à mão no storyboard do último vídeo, e as REGRAS ATUAIS do diretor.\n"
        "Proponha de 0 a 5 regras NOVAS, curtas e acionáveis, que fariam o diretor acertar de primeira no próximo vídeo. "
        "Só proponha o que os números mostram com clareza (padrão repetido, não caso isolado). NÃO repita nem reformule "
        "o que já está nas regras atuais. Cada regra com a evidência (números do vídeo).\n\n"
        f"CORREÇÕES DO VÍDEO \"{retro['video']}\":\n{json.dumps(retro, ensure_ascii=False)}\n\n"
        f"REGRAS ATUAIS:\n{regras_atuais[-12000:]}\n\n"
        'JSON: {"regras": [{"regra": "texto da regra (1 a 2 frases)", "evidencia": "números que justificam"}]}',
        "Responda SOMENTE JSON.", modelo="sonnet", etiqueta="aprendizado-retrospectiva")
    arq = PASTA / "propostas.json"
    propostas = _ler(arq, [])
    prox = max((p["id"] for p in propostas), default=0) + 1
    novas = []
    for k, x in enumerate(r.get("regras", [])[:5]):
        if x.get("regra"):
            novas.append({"id": prox + k, "video": retro["video"], "quando": retro["quando"], "regra": x["regra"].strip(),
                          "evidencia": (x.get("evidencia") or "").strip(), "status": "pendente"})
    _gravar(arq, propostas + novas)
    return novas


def propostas() -> list[dict]:
    return _ler(PASTA / "propostas.json", [])


def decidir(pid: int, acao: str, texto: str | None = None) -> dict:
    """aprovar (com o texto editado, se veio) → entra no regras_de_direcao.md do canal; recusar → só registra."""
    arq = PASTA / "propostas.json"
    lista = _ler(arq, [])
    p = next(x for x in lista if x["id"] == pid)
    if acao == "aprovar":
        p["regra"] = (texto or p["regra"]).strip()
        regras = caminho("docs") / "regras_de_direcao.md"
        atual = regras.read_text(encoding="utf-8")
        titulo = "## Aprendizados aprovados pelo Felipe (retrospectivas automáticas)"
        if titulo not in atual:
            atual = atual.rstrip() + f"\n\n{titulo}\n"
        atual = atual.rstrip() + f"\n- {p['regra']} _(vídeo: {p['video']})_\n"
        regras.write_text(atual, encoding="utf-8")
    p["status"] = "aprovada" if acao == "aprovar" else "recusada"
    _gravar(arq, lista)
    return p


def exemplos_para_o_prompt() -> str:
    ex = _ler(PASTA / "exemplos_legendas.json", [])[-NO_PROMPT:]
    if not ex:
        return ""
    linhas = "\n".join(f"- ({e['tipo']}) diretor: \"{e['diretor']}\" → Felipe: \"{e['felipe']}\"" for e in ex)
    return ("\n\n=== COMO O FELIPE CORRIGE AS LEGENDAS (exemplos reais dos vídeos anteriores) ===\n"
            "Escreva as legendas já do jeito dele (o tom, o tamanho, os nomes próprios):\n" + linhas)
