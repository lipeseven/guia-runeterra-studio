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


def gerar(titulo: str, minutos: float, notas: str, base: str | None) -> str:
    from claude_cli import chamar

    alvo = round(minutos * PPM)
    partes = [f"Título/tema do vídeo: {titulo}",
              f"Duração narrada alvo: ~{minutos:g} minutos (~{alvo} palavras; aceitável ±10%)."]
    if notas.strip():
        partes.append(f"Orientações do Felipe para este vídeo:\n{notas.strip()}")
    if base and base.strip():
        partes.append("ROTEIRO BASE (fonte de FATOS e temas — NÃO traduza frases, piadas, ganchos ou analogias; "
                      "reestruture e escreva do jeito do canal):\n<<<\n" + base.strip()[:60000] + "\n>>>")
    partes.append("Escreva o roteiro COMPLETO agora, no formato do canal. Responda SOMENTE com o texto do roteiro.")
    texto = chamar("\n\n".join(partes), _sistema(), modelo="opus", etiqueta="roteiro-gerar", timeout=1500)
    return _limpar(texto)


def ajustar(texto: str, pedido: str, historico: list[dict]) -> tuple[str, str]:
    """Aplica um pedido de ajuste fino. Devolve (texto novo, resumo do que mudou)."""
    from claude_cli import chamar_json

    pars = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    numerado = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(pars))
    anteriores = "\n".join(f"- {h['pedido']}" for h in historico[-6:])
    prompt = ((f"Pedidos anteriores do Felipe neste roteiro (contexto):\n{anteriores}\n\n" if anteriores else "") +
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


def versoes(pasta: Path) -> list[dict]:
    def num(p: Path) -> int:
        return int(re.search(r"_v(\d+)", p.stem).group(1))

    saida = []
    for p in sorted((pasta / "direcao").glob("roteiro_v*.txt"), key=num):
        texto = p.read_text(encoding="utf-8")
        saida.append({"versao": num(p), "palavras": len(re.findall(r"\w+", texto)), "inicio": texto[:90]})
    return saida
