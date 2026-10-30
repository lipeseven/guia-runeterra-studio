"""Roteirista: gera e ajusta o roteiro pelo painel (Claude Opus via claude -p — mesma cota do plano Pro).

- gerar(): do zero (tema + notas) ou a partir de um roteiro BASE (canal gringo) — inspiração, não tradução.
- ajustar(): ajuste fino por pedido; o Claude devolve SÓ os parágrafos alterados (barato e preserva o resto,
  inclusive edições à mão do Felipe).
O "jeito do canal" fica em docs/estilo_roteiro.md (editável).
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from .banco import RAIZ

sys.path.insert(0, str(RAIZ / "tools" / "direcao"))

PPM = 162  # palavras por minuto narrado do Felipe


def _sistema() -> str:
    from .banco import CANAL, caminho

    estilo = (caminho("docs") / "estilo_roteiro.md").read_text(encoding="utf-8")
    return (f"Você é o roteirista do canal brasileiro de YouTube \"{CANAL['nome']}\" ({CANAL['assunto']}). "
            "Escreve roteiros para o Felipe NARRAR com a própria voz.\n\n" + estilo)


def _limpar(texto: str) -> str:
    """Tira cercas de código, títulos markdown e linhas em branco duplicadas que o modelo às vezes devolve."""
    texto = re.sub(r"^```\w*\s*|\s*```$", "", texto.strip())
    linhas = [ln for ln in texto.splitlines() if not ln.lstrip().startswith("#")]
    texto = "\n".join(ln.rstrip() for ln in linhas)
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip() + "\n"


def gerar(titulo: str, minutos: float, notas: str, base: str | None, dossie: dict | None = None) -> str:
    from claude_cli import chamar

    alvo = round(minutos * PPM)
    partes = [f"Título/tema do vídeo: {titulo}",
              f"Duração narrada alvo: ~{minutos:g} minutos (~{alvo} palavras; aceitável ±10%)."]
    if notas.strip():
        partes.append(f"Orientações do Felipe para este vídeo:\n{notas.strip()}")
    if dossie:
        from .pesquisa import para_o_roteirista

        partes.append(para_o_roteirista(dossie))
    if base and base.strip():
        partes.append(("ROTEIRO BASE (só ESTRUTURA e temas — os FATOS vêm do dossiê acima; o base pode ter erros. "
                       if dossie else "ROTEIRO BASE (fonte de FATOS e temas — ")
                      + "NÃO traduza frases, piadas, ganchos ou analogias; reestruture e escreva do jeito do canal):"
                      "\n<<<\n" + base.strip()[:60000] + "\n>>>")
    if dossie:
        partes.append("REGRA DE FATOS: toda afirmação de lore do roteiro precisa estar no dossiê de fatos verificados. "
                      "O que não está lá NÃO entra (nem do roteiro base, nem da sua memória). Lore antigo só como "
                      "\"na versão antiga…\". Opinar, comparar e brincar à vontade — fatos, só do dossiê.")
    partes.append("Escreva o roteiro COMPLETO agora, no formato do canal. Responda SOMENTE com o texto do roteiro.")
    texto = chamar("\n\n".join(partes), _sistema(), modelo="opus", etiqueta="roteiro-gerar", timeout=1500)
    return _limpar(texto)


def ajustar(texto: str, pedido: str, historico: list[dict], dossie: dict | None = None) -> tuple[str, str]:
    """Aplica um pedido de ajuste fino. Devolve (texto novo, resumo do que mudou)."""
    from claude_cli import chamar_json

    from .pesquisa import para_o_roteirista

    pars =[p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    numerado = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(pars))
    anteriores = "\n".join(f"- {h['pedido']}" for h in historico[-6:])
    prompt = ((f"Pedidos anteriores do Felipe neste roteiro (contexto):\n{anteriores}\n\n" if anteriores else "") +
              (para_o_roteirista(dossie) + "\n(Fato de lore novo só se estiver no dossiê.)\n\n" if dossie else "") +
              f"ROTEIRO ATUAL (parágrafos numerados):\n{numerado}\n\n"
              f"PEDIDO DO FELIPE AGORA:\n{pedido.strip()}\n\n"
              "Altere SÓ o necessário para atender o pedido, mantendo o resto idêntico. Responda SOMENTE com JSON:\n"
              '{"resumo": "1 frase dizendo o que mudou", "alteracoes": ['
              '{"paragrafo": 3, "acao": "trocar", "texto": "novo parágrafo inteiro"}, '
              '{"paragrafo": 5, "acao": "remover"}, '
              '{"paragrafo": 7, "acao": "inserir_depois", "texto": "parágrafo novo"}]}\n'
              'Use "paragrafo": -1 com "inserir_depois" para inserir no começo. Os números são os do roteiro ATUAL.')
    r = chamar_json(prompt, _sistema(), modelo="opus", etiqueta="roteiro-ajuste", timeout=1200)
    novos = list(pars)
    alteracoes = [a for a in r.get("alteracoes", []) if isinstance(a.get("paragrafo"), int)]
    # aplica de trás para frente para os números continuarem valendo
    for a in sorted(alteracoes, key=lambda a: a["paragrafo"], reverse=True):
        i, acao = a["paragrafo"], a.get("acao")
        if acao == "trocar" and 0 <= i < len(novos) and a.get("texto"):
            novos[i] = a["texto"].strip()
        elif acao == "remover" and 0 <= i < len(novos):
            novos.pop(i)
        elif acao == "inserir_depois" and -1 <= i < len(novos) and a.get("texto"):
            novos.insert(i + 1, a["texto"].strip())
    if not alteracoes:
        raise ValueError("o Claude não propôs nenhuma alteração para esse pedido")
    return _limpar("\n\n".join(novos)), r.get("resumo") or pedido


# --- histórico de conversa com o roteirista (direcao/conversa_roteiro.json) ---

def historico(pasta: Path) -> list[dict]:
    arq = pasta / "direcao" / "conversa_roteiro.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []


def anotar(pasta: Path, item: dict) -> None:
    h = historico(pasta)
    h.append(item)
    (pasta / "direcao" / "conversa_roteiro.json").write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


# --- o que mudou entre versões (comparação local, sem Claude) ---

def _paragrafos(texto: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]


def _trocas(antes: list[str], depois: list[str]) -> list[tuple[int, int, int, int]]:
    """Trechos diferentes (i1, i2, j1, j2); parágrafos trocados em mesmo número viram um por um (desfaz-se cada um)."""
    trocas = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, antes, depois, autojunk=False).get_opcodes():
        if op == "replace" and i2 - i1 == j2 - j1:
            trocas += [(i1 + k, i1 + k + 1, j1 + k, j1 + k + 1) for k in range(i2 - i1)]
        elif op != "equal":
            trocas.append((i1, i2, j1, j2))
    return trocas


def _palavras(antes: str, depois: str) -> list[dict]:
    a, b = [re.findall(r"\s+|\w+|[^\w\s]", x) for x in (antes, depois)]
    saida = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            saida.append({"t": "igual", "x": "".join(a[i1:i2])})
            continue
        if i2 > i1:
            saida.append({"t": "saiu", "x": "".join(a[i1:i2])})
        if j2 > j1:
            saida.append({"t": "entrou", "x": "".join(b[j1:j2])})
    return saida


def _comparacao(pasta: Path) -> tuple[int, int, list[str], list[str]] | None:
    """(versão atual, versão base, parágrafos da base, parágrafos atuais). Depois de um "desfazer", a base continua a
    mesma de antes (comparar_com.json), senão as outras alterações sumiriam da lista."""
    dirc = pasta / "direcao"
    numeros = sorted(int(re.search(r"_v(\d+)", p.stem).group(1)) for p in dirc.glob("roteiro_v*.txt"))
    if len(numeros) < 2:
        return None
    atual, base = numeros[-1], numeros[-2]
    fixa = dirc / "comparar_com.json"
    if fixa.exists():
        dados = json.loads(fixa.read_text(encoding="utf-8"))
        if dados.get("versao") == atual and dados.get("base") in numeros:
            base = dados["base"]
    return (atual, base, _paragrafos((dirc / f"roteiro_v{base}.txt").read_text(encoding="utf-8")),
            _paragrafos((dirc / f"roteiro_v{atual}.txt").read_text(encoding="utf-8")))


def mudancas(pasta: Path) -> dict | None:
    """O que mudou na versão atual, palavra por palavra. Roteiro reescrito quase todo não vira lista."""
    c = _comparacao(pasta)
    if not c:
        return None
    atual, base, antes, depois = c
    trocas = _trocas(antes, depois)
    iguais = max(len(antes), len(depois)) - sum(max(i2 - i1, j2 - j1) for i1, i2, j1, j2 in trocas)
    if iguais < 0.3 * max(len(antes), len(depois)):
        return {"versao": atual, "base": base, "reescrito": True, "lista": []}
    return {"versao": atual, "base": base, "reescrito": False, "lista": [
        {"paragrafo": j1, "partes": _palavras("\n\n".join(antes[i1:i2]), "\n\n".join(depois[j1:j2]))}
        for i1, i2, j1, j2 in trocas]}


def desfazer_mudanca(pasta: Path, indice: int) -> tuple[str, int]:
    """Texto atual com UMA alteração desfeita e a versão base da comparação."""
    _, base, antes, depois = _comparacao(pasta)
    i1, i2, j1, j2 = _trocas(antes, depois)[indice]
    return "\n\n".join(depois[:j1] + antes[i1:i2] + depois[j2:]), base


def fixar_base(pasta: Path, versao: int, base: int) -> None:
    (pasta / "direcao" / "comparar_com.json").write_text(json.dumps({"versao": versao, "base": base}), encoding="utf-8")


def versoes(pasta: Path) -> list[dict]:
    def num(p: Path) -> int:
        return int(re.search(r"_v(\d+)", p.stem).group(1))

    saida = []
    for p in sorted((pasta / "direcao").glob("roteiro_v*.txt"), key=num):
        texto = p.read_text(encoding="utf-8")
        saida.append({"versao": num(p), "palavras": len(re.findall(r"\w+", texto)), "inicio": texto[:90]})
    return saida
