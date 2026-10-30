"""Pesquisa ANTES do roteiro: o roteirista só escreve com fatos comprovados (Felipe, 2026-10-29).

1. assuntos: o Sonnet lê tema + orientações (+ roteiro base) e lista personagens/lugares/eventos e termos de busca;
   se houver roteiro base, também extrai as AFIRMAÇÕES de lore dele.
2. fontes: wiki do canal + Universe (ou Pokédex) baixadas localmente (cache em dados/runeterra/pesquisa_cache).
3. dossiê: o Sonnet extrai dos trechos os fatos úteis para o vídeo, cada um com a fonte (canon atual × lore antigo).
4. crivo do roteiro base: cada afirmação × trechos das fontes → confirmada / corrigida / desatualizada / sem fonte.
O resultado fica em direcao/dossie.json; roteirista.gerar() e ajustar() usam só ele como fonte de fatos.
A conferência (conferencia.py) continua depois do roteiro, como rede de segurança.
"""
from __future__ import annotations

import json
from pathlib import Path

from .banco import CANAL, agora
from .conferencia import FONTE, SISTEMA, _embed, _pokedex, _trechos, _universe, _wiki

LOL = CANAL.get("fatos", "lol") == "lol"


def _assuntos(titulo: str, notas: str, base: str | None) -> dict:
    from claude_cli import chamar_json

    partes = [f"Tema do vídeo: {titulo}"]
    if notas.strip():
        partes.append(f"Orientações do Felipe:\n{notas.strip()[:4000]}")
    if base:
        partes.append("ROTEIRO BASE (de outro canal; pode ter erros, lore desatualizado ou não canon):\n<<<\n"
                      + base.strip()[:40000] + "\n>>>")
    pedido_base = ('"afirmacoes": [{"afirmacao": "o fato, curto, em português", "trecho": "palavras do roteiro base", '
                   '"busca": "english search terms"}]' if base else '"afirmacoes": []')
    return chamar_json(
        "\n\n".join(partes) + "\n\n"
        f"Vamos pesquisar este tema na {FONTE['nome']} ANTES de escrever o roteiro. Liste até 12 assuntos a pesquisar "
        f"(os {FONTE['quem']}, lugares, eventos, objetos centrais do tema), com o termo de busca em INGLÊS para a wiki"
        + (" e marque se é personagem com biografia oficial." if LOL else ".")
        + (" Liste também TODAS as afirmações de lore checáveis do roteiro base (quem fez o quê, quando, onde, "
           "parentesco, nomes) — no máximo 40, as que importam para o vídeo." if base else "")
        + '\n\nJSON: {"assuntos": [{"nome": "Aatrox", "busca": "Aatrox", "personagem": true}], ' + pedido_base + "}",
        SISTEMA, modelo="sonnet", etiqueta="pesquisa-assuntos")


def _fontes(assunto: dict) -> list[tuple[str, str]]:
    fontes = _wiki(assunto.get("busca") or assunto["nome"])
    if assunto.get("personagem"):
        fontes += _universe(assunto["nome"]) if LOL else _pokedex(assunto["nome"])
    return fontes


def _melhores(trechos: list[tuple[str, str]], consulta: str, n: int) -> list[tuple[str, str]]:
    if len(trechos) <= n:
        return trechos
    e = _embed([consulta] + [t for _, t in trechos])
    notas = e[1:] @ e[0]
    return [trechos[i] for i in sorted(notas.argsort()[::-1][:n])]


def _fatos(titulo: str, notas: str, grupo: list[tuple[dict, list[tuple[str, str]]]]) -> list[dict]:
    from claude_cli import chamar_json

    blocos, fontes = [], []
    for assunto, trechos in grupo:
        linhas = []
        for f, t in trechos:
            fontes.append(f)
            linhas.append(f"[{len(fontes) - 1}] ({f}) {t}")
        blocos.append(f"### {assunto['nome']}\n" + ("\n".join(linhas) or "(nada encontrado)"))
    r = chamar_json(
        f"Tema do vídeo: {titulo}\n" + (f"Orientações: {notas.strip()[:1500]}\n" if notas.strip() else "")
        + "\nTrechos das fontes:\n\n" + "\n\n".join(blocos) + "\n\n"
        "Monte o dossiê de fatos para o roteirista: extraia DOS TRECHOS os fatos úteis para este vídeo (eventos, "
        "quem fez o quê, origens, relações, lugares, datas/eras, detalhes marcantes). Use SÓ o que os trechos dizem — "
        "nada do seu conhecimento. Escreva cada fato em português, curto e autossuficiente. Marque `canon`: \"atual\" "
        "(lore vigente), \"antigo\" (seção Legacy/lore antigo/retcon) ou \"jogo\" (só falas/eventos do jogo, não "
        "conto/biografia). Até 30 fatos por grupo, sem repetir.\n\n"
        'JSON: {"fatos": [{"assunto": "Aatrox", "fato": "...", "fonte": 0, "canon": "atual"}]}',
        SISTEMA, modelo="sonnet", etiqueta="pesquisa-fatos", timeout=900)
    saida = []
    for x in r.get("fatos", []):
        if not x.get("fato"):
            continue
        i = x.get("fonte")
        saida.append({"assunto": x.get("assunto", ""), "fato": x["fato"], "canon": x.get("canon", "atual"),
                      "fonte": fontes[i] if isinstance(i, int) and 0 <= i < len(fontes) else None})
    return saida


def _crivo(afirmacoes: list[dict], todos: list[tuple[str, str]], aviso) -> list[dict]:
    from claude_cli import chamar_json

    blocos = []
    for k, a in enumerate(afirmacoes):
        tr = _trechos(_wiki(a.get("busca") or a["afirmacao"])) + todos
        a["trechos"] = [{"fonte": f, "texto": t} for f, t in _melhores(tr, a["afirmacao"], 3)] if tr else []
        blocos.append(f"### Afirmação {k}: {a['afirmacao']}\n" + ("\n".join(
            f"[{j}] ({x['fonte']}) {x['texto']}" for j, x in enumerate(a["trechos"])) or "(nenhum trecho encontrado)"))
    aviso(f"passando {len(afirmacoes)} afirmação(ões) do roteiro base pelo crivo")
    v = chamar_json(
        f"Cada afirmação veio de um roteiro de OUTRO canal. Compare com os trechos das fontes ({FONTE['nome']}):\n"
        "- confirmada: os trechos sustentam o essencial;\n"
        "- corrigida: os trechos CONTRADIZEM (outra pessoa, outro lugar, outro motivo, outra época) — dê a versão "
        "correta segundo a fonte em `correcao`;\n"
        "- desatualizada: só vale no lore antigo/Legacy/retcon ou não é canon — explique em `correcao` o que vale hoje, "
        "se a fonte disser;\n"
        "- sem_fonte: os trechos não falam disso (não julgue pelo seu conhecimento).\n\n" + "\n\n".join(blocos)
        + '\n\nJSON: {"vereditos": [{"i": 0, "veredito": "confirmada|corrigida|desatualizada|sem_fonte", '
          '"correcao": "1 frase em português (vazio se confirmada)", "trecho": 0}]}',
        SISTEMA, modelo="sonnet", etiqueta="pesquisa-crivo", timeout=900)
    vered = {x["i"]: x for x in v.get("vereditos", []) if isinstance(x.get("i"), int)}
    saida = []
    for k, a in enumerate(afirmacoes):
        x = vered.get(k, {})
        t = x.get("trecho")
        saida.append({"afirmacao": a["afirmacao"], "trecho": a.get("trecho", ""),
                      "veredito": x.get("veredito", "sem_fonte"), "correcao": x.get("correcao", ""),
                      "fonte": a["trechos"][t] if isinstance(t, int) and 0 <= t < len(a["trechos"]) else None})
    return saida


def pesquisar(pasta: Path, titulo: str, notas: str, base: str | None, aviso=lambda m: None) -> dict:
    """Monta direcao/dossie.json (fatos com fonte + crivo do roteiro base) e devolve o dossiê."""
    aviso("listando o que pesquisar")
    r = _assuntos(titulo, notas, base)
    assuntos = [a for a in r.get("assuntos", []) if a.get("nome")][:12]
    aviso(f"buscando {len(assuntos)} assunto(s) na {FONTE['nome']}")
    achados, todos = [], []
    for a in assuntos:
        tr = _melhores(_trechos(_fontes(a)), f"{titulo}. {a['nome']}", 10)
        achados.append((a, tr))
        todos += tr
    fatos: list[dict] = []
    for g in range(0, len(achados), 4):
        aviso(f"montando o dossiê de fatos ({g // 4 + 1}/{(len(achados) + 3) // 4})")
        fatos += _fatos(titulo, notas, achados[g:g + 4])
    afirm = [a for a in r.get("afirmacoes", []) if a.get("afirmacao")][:40] if base else []
    crivo = _crivo(afirm, todos, aviso) if afirm else []
    dossie = {"quando": agora(), "titulo": titulo, "assuntos": [a["nome"] for a in assuntos],
              "fatos": fatos, "crivo": crivo}
    (pasta / "direcao" / "dossie.json").write_text(json.dumps(dossie, ensure_ascii=False, indent=1), encoding="utf-8")
    return dossie


def ler(pasta: Path) -> dict | None:
    arq = pasta / "direcao" / "dossie.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def para_o_roteirista(dossie: dict) -> str:
    """O dossiê em texto para o prompt do roteirista: fatos aprovados + o que NÃO repetir do roteiro base."""
    linhas = ["FATOS VERIFICADOS (dossiê de pesquisa — a ÚNICA fonte de fatos de lore do roteiro):"]
    for f in dossie.get("fatos", []):
        selo = {"antigo": " [lore ANTIGO — só cite como 'na versão antiga…']", "jogo": " [só no jogo]"}.get(f.get("canon"), "")
        linhas.append(f"- ({f.get('assunto', '')}) {f['fato']}{selo}")
    erros = [c for c in dossie.get("crivo", []) if c["veredito"] != "confirmada"]
    if erros:
        linhas.append("\nCRIVO DO ROTEIRO BASE — NÃO repita estes pontos como estão lá:")
        for c in erros:
            linhas.append(f"- [{c['veredito']}] base dizia: {c['afirmacao']}"
                          + (f" → segundo a fonte: {c['correcao']}" if c.get("correcao") else " → não entra"))
    return "\n".join(linhas)
