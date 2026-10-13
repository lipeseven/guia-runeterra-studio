"""Demonstração da ressincronização: UMA direção (ancorada nas palavras do roteiro) renderizada
com a voz guia e com a gravação real do Felipe.

Uso:
    .venv\\Scripts\\python.exe tools\\prototipo\\fiddlesticks.py
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audio"))
from alinhar import alinhar, palavras_do_roteiro  # noqa: E402
from capa import detectar as detectar_circulos  # noqa: E402
from comum import BANCO_ACERVO, RAIZ, preparar_ffmpeg  # noqa: E402
from direcao.variacao import Variador  # noqa: E402
from limpar_gravacao import carregar, normalizar, transcrever  # noqa: E402
from voz_guia import gerar as gerar_voz_guia  # noqa: E402
from prototipo.preparar import PUBLICO, midia  # noqa: E402

PASTA = RAIZ / "dados" / "teste_gravacao"
SAIDA = RAIZ / "app/video/src/dados/fiddle.json"


def main() -> None:
    preparar_ffmpeg()
    roteiro = (PASTA / "roteiro.txt").read_text(encoding="utf-8")
    paragrafo = roteiro.split("\n\n")[0]  # a demo usa só o 1º parágrafo
    toks = palavras_do_roteiro(paragrafo)

    # 1) voz guia + tempos dela
    guia_wav = PASTA / "voz_guia.wav"
    print("voz guia:", gerar_voz_guia(paragrafo, guia_wav))
    falas_guia = transcrever(carregar(guia_wav))
    guia = alinhar(paragrafo, [w for f in falas_guia for w in f["palavras"]])

    # 2) gravação limpa (já processada pelo limpar_gravacao.py) + tempos dela
    real = alinhar(paragrafo, json.loads((PASTA / "resultado" / "palavras.json").read_text(encoding="utf-8")))
    fim_real = max(w["f"] for w in real) + 0.4
    fim_guia = max(w["f"] for w in guia) + 0.4

    for nome, origem, fim in (("fiddle_guia.wav", guia_wav, fim_guia),
                              ("fiddle_real.wav", PASTA / "resultado" / "limpa.wav", fim_real)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origem), "-t", f"{fim:.2f}", "-ar", "48000", "-ac", "2",
                        str(PUBLICO / nome)], check=True)

    # 3) UMA direção, ancorada em índices de palavras do roteiro
    def idx(palavra: str, depois: int = 0) -> int:
        return next(k for k in range(depois, len(toks)) if normalizar(toks[k]) == normalizar(palavra))

    con = sqlite3.connect(BANCO_ACERVO)
    capa = midia(con, 209)
    circulos, _ = detectar_circulos(str(PUBLICO / Path(capa["arquivo"]).name))
    c = circulos[9]  # Fiddlesticks (último da capa)
    secao = {"titulo": "Fiddlesticks", "icone": {"nome": "Fiddlesticks", "midia": capa,
                                                  "foco": [c["cx"], c["cy"]], "diametro": 2 * c["r"] * 0.93}}
    var = Variador("fiddle-demo")
    cenas = [
        {"tipo": "cartao", "de": 0, "ate": idx("um", idx("campo")) - 1, "itens": [
            {"de": 0, "midia": midia(con, 321), "legenda": "um conto infantil", "legenda_em": idx("conto"),
             "entrada_img": var.imagem(), "entrada_legenda": var.texto(), "movimento": var.movimento()}]},
        {"tipo": "telacheia", "de": idx("um", idx("campo")), "ate": idx("Mas") - 1, "midia": midia(con, 289),
         "foco": [0.5, 0.4], "movimento": var.movimento(), "entrada_img": var.imagem()},
        {"tipo": "recorte", "de": idx("Mas"), "ate": idx("Fiddlesticks") - 1, "midia": midia(con, 335),
         "legenda": "só uma casca", "legenda_em": idx("casca"), "semente": 9,
         "entrada_img": var.imagem(), "entrada_legenda": var.texto()},
        {"tipo": "telacheia", "de": idx("Fiddlesticks"), "ate": idx("Ele") - 1, "midia": midia(con, 330),
         "foco": [0.5, 0.45], "movimento": var.movimento(), "entrada_img": var.imagem()},
        {"tipo": "cartao", "de": idx("Ele"), "ate": len(toks) - 1, "itens": [
            {"de": idx("Ele"), "midia": midia(con, 632), "legenda": "pulsar de desespero", "legenda_em": idx("pulsar"),
             "entrada_img": var.imagem(), "entrada_legenda": var.texto(), "movimento": var.movimento()}]},
    ]
    dados = {
        "fps": 60,
        "guia": {"audio": "prototipo/fiddle_guia.wav", "palavras": guia, "secao": secao, "cenas": cenas},
        "real": {"audio": "prototipo/fiddle_real.wav", "palavras": real, "secao": secao, "cenas": cenas},
    }
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {len(toks)} palavras; duração guia {fim_guia:.1f}s, real {fim_real:.1f}s")
    for cena in cenas:
        k = cena["de"]
        print(f"  {cena['tipo']:9} começa em '{toks[k]}': guia {guia[k]['i']:5.2f}s | real {real[k]['i']:5.2f}s")


if __name__ == "__main__":
    main()
