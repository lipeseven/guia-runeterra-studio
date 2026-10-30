r"""Leitura visual das referências DO CANAL (GRS_CANAL) pelo Claude: 4 folhas de contato por vídeo (início, 1/3,
2/3, fim) → anotações em português no formato de dados/runeterra/analise_referencias/leitura_visual.md. Uma chamada por
vídeo (Sonnet, imagens), retomável: vídeo já lido não é pedido de novo.

Uso:  set GRS_CANAL=pokemon && .venv\Scripts\python.exe tools\analise_referencias\leitura_visual.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "direcao"))
from canal import CANAL, caminho  # noqa: E402
from claude_cli import chamar  # noqa: E402

PASTA = caminho("analise")
SAIDA = PASTA / "leitura_visual.md"
CACHE = PASTA / "leitura_visual.json"

PEDIDO = """Estas são folhas de contato (miniaturas em ordem, cada uma = uma cena) de um vídeo de referência do YouTube
do nicho "{assunto}", título: "{titulo}". Estatísticas: {stats}.

Faça ANOTAÇÕES BRUTAS em português (lista de tópicos curtos, como um editor estudando o estilo), cobrindo:
- tipos de cena e com que frequência (tela cheia, cartão com moldura, recorte sem fundo, texto, lista/mosaico,
  tela dividida, clipe do anime/jogo, mapa, gráfico…);
- fundo predominante (branco, escuro, colorido, textura) e paleta;
- tipografia e textos na tela (legendas, rótulos, títulos, números, setas);
- como os Pokémon/personagens aparecem (arte oficial, sprites, renders 3D, cena do anime, cartas…);
- estrutura: abertura, transições entre seções, marca registrada que se repete, fechamento;
- o que destoa / o que dá personalidade ao canal.
Seja concreto (cite exemplos que você vê). Sem introdução, só os tópicos."""


def main() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    stats = {e.get("video", ""): e for e in json.loads((PASTA / "estatisticas.json").read_text(encoding="utf-8"))} \
        if (PASTA / "estatisticas.json").exists() else {}
    for pasta in sorted(p for p in PASTA.iterdir() if (p / "folhas").is_dir()):
        if pasta.name in cache:
            continue
        folhas = sorted((pasta / "folhas").glob("*.jpg"))
        if not folhas:
            continue
        idx = sorted({0, len(folhas) // 3, 2 * len(folhas) // 3, len(folhas) - 1})
        escolhidas = [folhas[i] for i in idx]
        st = next((v for k, v in stats.items() if k and k[:30].lower().replace(" ", "-")[:20] in pasta.name), {})
        resumo = {k: st[k] for k in ("min", "cenas", "media", "mediana") if k in st}
        print(f"lendo {pasta.name} ({len(escolhidas)} folhas)", flush=True)
        texto = chamar(PEDIDO.format(assunto=CANAL["assunto"], titulo=pasta.name, stats=json.dumps(resumo)),
                       "Você é um editor de vídeo analisando referências. Responda só com as anotações.",
                       modelo="sonnet", imagens=escolhidas, etiqueta="leitura-visual")
        cache[pasta.name] = texto.strip()
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Leitura visual das referências — canal {CANAL['nome']} (anotações brutas)\n"]
    md += [f"## {nome}\n{texto}\n" for nome, texto in cache.items()]
    SAIDA.write_text("\n".join(md), encoding="utf-8")
    print(f"pronto: {SAIDA}", flush=True)


if __name__ == "__main__":
    main()
