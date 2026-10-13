"""Diretor — 2ª passada (com imagens): o Claude olha as folhas de candidatos e escolhe."""
from __future__ import annotations

from pathlib import Path

from claude_cli import chamar_json

SISTEMA = """Você é o diretor visual do canal "Guia de Runeterra" (lore de League of Legends) escolhendo imagens.
Cada linha das folhas é uma necessidade (id em amarelo, a frase narrada e a legenda) com até 4 candidatos numerados.
Critérios, em ordem:
1. A imagem ilustra o SENTIDO da frase no contexto (metáforas não são literais).
2. O personagem certo: nunca use a imagem de outro personagem fingindo ser o citado.
3. Não repetir a mesma imagem em necessidades diferentes, a menos que não haja alternativa.
4. Para "recorte": personagem isolado (fundo transparente/branco). Para "clipe": a tomada mostra a ação narrada.
5. Se NENHUM candidato serve de verdade, recuse (escolha null) — melhor buscar outra imagem depois do que errar.
"foco" = ponto de interesse da imagem escolhida (x, y de 0 a 1, ex.: o rosto), usado para enquadrar.
Responda SOMENTE com JSON."""


def escolher(necs: list[dict], folhas: list[Path], modelo: str = "opus") -> dict:
    lista = "\n".join(f"{n['id']} ({n['tipo']}): {n['frase'][:160]}" + (f" | legenda: {n['legenda']}" if n.get("legenda") else "")
                      for n in necs)
    prompt = (f"Folhas anexadas: {len(folhas)}. Necessidades:\n{lista}\n\n"
              'Responda: {"<id>": {"escolha": 1-4 ou null, "foco": [x, y], "motivo": "até 10 palavras"}, ...} '
              "com TODAS as necessidades.")
    return chamar_json(prompt, SISTEMA, modelo=modelo, imagens=folhas, etiqueta="direcao-escolha")
