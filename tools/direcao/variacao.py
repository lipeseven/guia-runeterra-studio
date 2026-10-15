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

# Textos auxiliares (legendas, rótulos, nomes) quase sempre entram SECOS: animação em texto cansa (pedido do
# Felipe, 2026-10-15). Só um fade discreto de vez em quando. A variedade fica nas imagens.
PESOS_TEXTO = {"corte": 85, "fade": 15}
PESOS_IMAGEM = {
    "corte": 26, "fade": 14, "deslizar_esq": 5, "deslizar_dir": 5, "deslizar_cima": 5,
    "assentar": 12, "revelar_esq": 6, "revelar_dir": 6, "desfoque": 8, "pop": 6, "giro": 4,
    "clarao": 3,  # impacto: raro de propósito
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
        self.recentes = {k: deque(maxlen=memoria) for k in
                         ("texto", "imagem", "movimento", "mosaico", "hub", "dividida", "lado", "citacao")}

    def _escolher(self, categoria: str, pesos: dict[str, int], livre: bool = False) -> str:
        """`livre`: sorteio puro pelos pesos, sem penalizar repetição (texto: corte seco seguido é o desejado)."""
        recentes = self.recentes[categoria]
        if livre:
            nome = self.rng.choices(list(pesos), weights=list(pesos.values()))[0]
            recentes.append(nome)
            return nome
        ajustados = {}
        poucas = sum(1 for p in pesos.values() if p > 0) <= 3  # com 2–3 opções, proibir repetir vira relógio
        for nome, peso in pesos.items():
            if peso <= 0:
                continue
            if recentes and nome == recentes[-1]:
                if not poucas:
                    continue  # nunca repete o anterior
                peso *= 0.45
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
        e = self._escolher("texto", PESOS_TEXTO, livre=True)
        return {"efeito": e, "quadros": self.rng.randint(6, 10) if e == "fade" else 1}  # fade curto e discreto

    def imagem(self) -> dict:
        e = self._escolher("imagem", PESOS_IMAGEM)
        return {"efeito": e, "quadros": self._duracao(e)}

    def mosaico(self, aspectos: list[float]) -> tuple[list[dict], int]:
        """Posições das peças de um mosaico (centro x/y, largura, rotação, lado de entrada) + borda.
        `aspectos` = largura/altura de cada peça. Layout também não repete o anterior."""
        n = len(aspectos)
        layout = self._escolher("mosaico", {"faixa": 10, "lateral": 8, "espalhado": 10, "grade": 6 if n == 4 else 0})
        r = self.rng
        pecas = []
        if layout == "faixa":
            largura = min(520, 1760 / n - 40)
            lado = r.choice(["baixo", "alternado"])
            for k in range(n):
                pecas.append({"x": 960 + (k - (n - 1) / 2) * (largura + 40), "y": r.uniform(760, 820),
                              "largura": largura, "rotacao": r.uniform(-2, 2),
                              "de_onde": "baixo" if lado == "baixo" else ("esq" if k % 2 == 0 else "dir")})
        elif layout == "lateral":
            x = r.choice([360, 1560])
            largura = min(560, 900 / max(1, n) * aspectos[0])
            for k in range(n):
                pecas.append({"x": x, "y": 540 + (k - (n - 1) / 2) * (largura / aspectos[k] + 30),
                              "largura": largura, "rotacao": r.uniform(-1.5, 1.5),
                              "de_onde": "esq" if x < 960 else "dir"})
        elif layout == "espalhado":
            ancoras = [(430, 300), (1490, 300), (430, 780), (1490, 780), (960, 540), (960, 300), (960, 780)]
            r.shuffle(ancoras)
            for k in range(n):
                x, y = ancoras[k]
                lado = "esq" if x < 700 else "dir" if x > 1220 else ("cima" if y < 540 else "baixo")
                pecas.append({"x": x + r.uniform(-60, 60), "y": y + r.uniform(-40, 40),
                              "largura": r.uniform(460, 600), "rotacao": r.uniform(-7, 7), "de_onde": lado})
        else:  # grade 2x2
            for k, (x, y) in enumerate([(500, 290), (1420, 290), (500, 790), (1420, 790)]):
                pecas.append({"x": x, "y": y, "largura": 820, "rotacao": 0,
                              "de_onde": "esq" if x < 960 else "dir"})
        for p in pecas:
            p["quadros"] = r.randint(12, 22)
            p.update({k: round(v, 1) for k, v in p.items() if isinstance(v, float)})
        return pecas, r.choice([0, 6, 10])

    def movimento(self) -> dict:
        m = self._escolher("movimento", PESOS_MOVIMENTO)
        return {"tipo": m, "intensidade": round(self.rng.uniform(0.03, 0.09), 3)}

    # --- recursos da leitura visual completa (guia de estilo §10.2) ---
    def hub(self) -> dict:
        """Transição de seção: capa com zoom ou esteira de ícones (alterna, sem repetir sempre a mesma)."""
        variante = self._escolher("hub", {"grade": 10, "esteira": 10})
        return {"variante": variante, "zoom": round(self.rng.uniform(2.2, 2.8), 2)}

    def dividida(self) -> dict:
        entrada = self._escolher("dividida", {"corte": 10, "deslizar": 8, "revelar": 6})
        return {"entrada": entrada, "separador": self.rng.choice([0, 8, 14]), "movimento": self.movimento()}

    def lista(self) -> dict:
        return {"entrada": self.imagem(), "inclinado": self.rng.random() < 0.4}

    def lado(self) -> str:
        """Lado da imagem no meio a meio: alterna, mas não como relógio."""
        return self._escolher("lado", {"esq": 10, "dir": 10})

    def lado_citacao(self) -> str:
        return self._escolher("citacao", {"esq": 8, "dir": 8, "centro": 6})
