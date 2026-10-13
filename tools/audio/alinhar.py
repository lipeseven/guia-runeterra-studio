"""Alinha uma narração (voz guia ou gravação limpa) às PALAVRAS DO ROTEIRO.

A direção do vídeo aponta para índices de palavras do roteiro; este alinhamento dá o tempo de
cada uma delas num áudio específico. Trocar a voz guia pela gravação real = trocar a tabela.

Uso:
    .venv\\Scripts\\python.exe tools\\audio\\alinhar.py <roteiro.txt> <palavras.json> <saida.json>
    (palavras.json: [{"t"|"p": palavra, "i": início, "f": fim}, ...] — ex.: gerado pelo limpar_gravacao.py)

Palavras do roteiro que a narração não tem (lidas diferente, engolidas) recebem tempo
interpolado entre as vizinhas e ficam marcadas com "estimado": true.
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from limpar_gravacao import normalizar  # noqa: E402


def palavras_do_roteiro(texto: str) -> list[str]:
    """Tokens do roteiro exatamente como a direção os indexa (pontuação fica grudada na palavra)."""
    return texto.split()


def alinhar(roteiro: str, narradas: list[dict]) -> list[dict]:
    toks = palavras_do_roteiro(roteiro)
    hifen = lambda t: re.sub(r"\s*-\s*", "", t)
    a = [normalizar(hifen(t)) for t in toks]
    # junta palavras com hífen separadas pelo Whisper ("paralisá" "-las")
    nar = []
    for w in narradas:
        texto = w.get("t", w.get("p", ""))
        if nar and texto.startswith("-"):
            nar[-1] = {**nar[-1], "t": nar[-1]["t"] + texto, "f": w["f"]}
        else:
            nar.append({"t": texto, "i": w["i"], "f": w["f"]})
    b = [normalizar(hifen(w["t"])) for w in nar]

    tempos: list[dict | None] = [None] * len(toks)
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tempos[i1 + k] = {"i": nar[j1 + k]["i"], "f": nar[j1 + k]["f"]}
        elif op == "replace" and j2 > j1:
            # trecho lido diferente: distribui o tempo dos lidos pelas palavras do roteiro
            ini, fim = nar[j1]["i"], nar[j2 - 1]["f"]
            n = i2 - i1
            for k in range(n):
                tempos[i1 + k] = {"i": ini + (fim - ini) * k / n, "f": ini + (fim - ini) * (k + 1) / n,
                                  "estimado": True}

    # palavras sem tempo (omitidas na leitura): interpola entre as vizinhas conhecidas
    for k, t in enumerate(tempos):
        if t is None:
            ant = next((tempos[j]["f"] for j in range(k - 1, -1, -1) if tempos[j]), 0.0)
            prox = next((tempos[j]["i"] for j in range(k + 1, len(tempos)) if tempos[j]), ant)
            tempos[k] = {"i": ant, "f": max(ant, prox), "estimado": True}
    return [{"t": tok, "i": round(t["i"], 3), "f": round(t["f"], 3), **({"estimado": True} if t.get("estimado") else {})}
            for tok, t in zip(toks, tempos)]


def main() -> None:
    roteiro = Path(sys.argv[1]).read_text(encoding="utf-8")
    narradas = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    saida = alinhar(roteiro, narradas)
    Path(sys.argv[3]).write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    est = sum(1 for w in saida if w.get("estimado"))
    print(f"{len(saida)} palavras do roteiro alinhadas; {est} com tempo estimado")


if __name__ == "__main__":
    main()
