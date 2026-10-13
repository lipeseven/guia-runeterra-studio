"""Editor de variedade: distribui efeitos de entrada e movimentos ao longo do vídeo inteiro.

Regras de editor humano:
- nunca o mesmo efeito duas vezes seguidas na mesma categoria;
- efeitos usados recentemente ficam menos prováveis (memória das últimas escolhas);
- corte seco é frequente (efeito em tudo também é sinal de automação);
- duração e intensidade variam a cada uso.
Os nomes dos efeitos batem com app/video/src/efeitos.tsx.
"""
from __future__ import annotations

import random
from collections import deque

PESOS_TEXTO = {
    "corte": 22, "fade": 14, "subir": 10, "descer": 5, "esquerda": 6, "direita": 6,
    "maquina": 8, "palavras": 8, "pop": 6, "desfoque": 7, "revelar": 7, "espacar": 4,
}
PESOS_IMAGEM = {
    "corte": 26, "fade": 14, "deslizar_esq": 5, "deslizar_dir": 5, "deslizar_cima": 5,
    "assentar": 12, "revelar_esq": 6, "revelar_dir": 6, "desfoque": 8, "pop": 6, "giro": 4,
}
PESOS_MOVIMENTO = {
    "aproximar": 22, "afastar": 18, "pan_esq": 14, "pan_dir": 14, "subir": 7, "descer": 7,
    "parado": 10, "aproximar_pan": 8,
}
# Faixa de duração (quadros a 60 fps) de cada efeito.
DURACAO = {"corte": (1, 1), "maquina": (14, 30), "palavras": (16, 34), "pop": (14, 20)}
DURACAO_PADRAO = (7, 18)


class Variador:
    def __init__(self, semente: int | str, memoria: int = 3):
        self.rng = random.Random(semente)
        self.recentes = {k: deque(maxlen=memoria) for k in ("texto", "imagem", "movimento")}

    def _escolher(self, categoria: str, pesos: dict[str, int]) -> str:
        recentes = self.recentes[categoria]
        ajustados = {}
        for nome, peso in pesos.items():
            if recentes and nome == recentes[-1]:
                continue  # nunca repete o anterior
            if nome in recentes:
                peso *= 0.35  # usado há pouco: bem menos provável
            ajustados[nome] = peso
        nome = self.rng.choices(list(ajustados), weights=list(ajustados.values()))[0]
        recentes.append(nome)
        return nome

    def _duracao(self, efeito: str) -> int:
        a, b = DURACAO.get(efeito, DURACAO_PADRAO)
        return self.rng.randint(a, b)

    def texto(self) -> dict:
        e = self._escolher("texto", PESOS_TEXTO)
        return {"efeito": e, "quadros": self._duracao(e)}

    def imagem(self) -> dict:
        e = self._escolher("imagem", PESOS_IMAGEM)
        return {"efeito": e, "quadros": self._duracao(e)}

    def movimento(self) -> dict:
        m = self._escolher("movimento", PESOS_MOVIMENTO)
        return {"tipo": m, "intensidade": round(self.rng.uniform(0.03, 0.09), 3)}
