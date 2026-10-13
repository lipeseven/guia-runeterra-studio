"""Prepara os dados do protótipo da Fase 1 (Remotion) a partir do vídeo dos Demônios.

Uso:
    .venv\\Scripts\\python.exe tools\\prototipo\\preparar.py

Gera em app/video/public/prototipo/ o áudio dos trechos e as imagens usadas, e em
app/video/src/dados/prototipo.json a direção (cenas ancoradas em PALAVRAS, não em segundos).
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import BANCO_ACERVO, PASTA_ACERVO, RAIZ, preparar_ffmpeg  # noqa: E402

VIDEO = RAIZ / "recursos de vídeo para aprender" / "Todos os DEMÔNIOS de League of Legends Explicados em 22 minutos.mp4"
TRANSCRICAO = RAIZ / "dados/analise_referencias/todos-os-demonios-de-league-of-legends-explicados-em-22-minutos/transcricao.json"
PUBLICO = RAIZ / "app/video/public/prototipo"
SAIDA = RAIZ / "app/video/src/dados/prototipo.json"

# Glossário mínimo: o que o Whisper ouviu -> grafia correta.
GLOSSARIO = {"asacanas": "Azakanas", "asacana": "Azakana", "ione": "Yone"}

# Ícones da grade: id no acervo, nome, foco (cx, cy em fração da imagem) e diâmetro (fração do menor lado).
GRADE = [
    (118, "Azakana", 0.43, 0.14, 0.26),
    (633, "Nocturne", 0.68, 0.30, 0.60),
    (861, "Tahm Kench", 0.40, 0.45, 0.80),
    (299, "Evelynn", 0.55, 0.30, 0.55),
    (840, "Raum", 0.60, 0.55, 0.50),
    (199, "Camphor", 0.57, 0.35, 0.60),
    (901, "Tybaulk", 0.45, 0.45, 0.70),
    (104, "Atakhan", 0.50, 0.60, 0.80),
    (76, "Ashlesh", 0.45, 0.45, 0.90),
    (326, "Fiddlesticks", 0.35, 0.30, 0.60),
]

TRECHOS = {
    # nome: (início s, fim s) no vídeo original
    "abertura": (0.0, 22.45),
    "yone": (97.6, 101.70),
}


def midia(con: sqlite3.Connection, mid: int) -> dict:
    """Copia a imagem do acervo para public/ e devolve nome + dimensões."""
    caminho = con.execute("SELECT caminho FROM midias WHERE id=?", (mid,)).fetchone()[0]
    origem = PASTA_ACERVO / caminho
    destino = PUBLICO / f"m{mid}{origem.suffix.lower().replace('.jpg_large', '.jpg')}"
    if destino.suffix in (".avif", ".jfif", ".webp"):
        destino = destino.with_suffix(".png")  # formatos que o Chrome do Remotion pode não ler bem
        with Image.open(origem) as im:
            im.save(destino)
    else:
        shutil.copyfile(origem, destino)
    with Image.open(destino) as im:
        w, h = im.size
    return {"arquivo": f"prototipo/{destino.name}", "w": w, "h": h}


def palavras_do_trecho(inicio: float, fim: float) -> list[dict]:
    dados = json.loads(TRANSCRICAO.read_text(encoding="utf-8"))
    saida = []
    for s in dados["segmentos"]:
        for p in s["palavras"]:
            if inicio - 0.05 <= p["i"] < fim:
                limpo = re.sub(r"[^\wÀ-ú]", "", p["p"]).lower()
                texto = p["p"]
                if limpo in GLOSSARIO:
                    texto = re.sub(r"[\wÀ-ú]+", GLOSSARIO[limpo], texto, count=1)
                saida.append({"t": texto, "i": round(p["i"] - inicio, 3), "f": round(p["f"] - inicio, 3)})
    return saida


def achar(palavras: list[dict], alvo: str, depois: int = 0) -> int:
    """Índice da primeira palavra (a partir de `depois`) igual a `alvo` — âncora da direção.
    Compara a palavra inteira, sem pontuação ("Nas" não pode casar com "Azakanas")."""
    for k in range(depois, len(palavras)):
        if re.sub(r"[^\wÀ-ú]", "", palavras[k]["t"]).lower() == alvo.lower():
            return k
    raise ValueError(f"palavra '{alvo}' não encontrada")


def main() -> None:
    preparar_ffmpeg()
    PUBLICO.mkdir(parents=True, exist_ok=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO_ACERVO)

    for nome, (ini, fim) in TRECHOS.items():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ini), "-to", str(fim), "-i", str(VIDEO),
                        "-vn", "-ac", "2", "-ar", "48000", str(PUBLICO / f"{nome}.wav")], check=True)

    # ---------- Trecho 1: abertura ----------
    pa = palavras_do_trecho(*TRECHOS["abertura"])
    icones = [{"nome": n, "midia": midia(con, i), "foco": [cx, cy], "diametro": d} for i, n, cx, cy, d in GRADE]
    icone_secao = icones[0]
    w_runeterra = achar(pa, "Runeterra")
    w_entidades = achar(pa, "entidades")
    w_nem = achar(pa, "nem")
    w_nas = achar(pa, "Nas")
    w_ionia = achar(pa, "Ionia")
    w_eles = achar(pa, "Eles")
    w_manif = achar(pa, "manifestação")

    abertura = {
        "audio": "prototipo/abertura.wav",
        "palavras": pa,
        "secao": {"titulo": "Azakanas", "icone": icone_secao},
        "cenas": [
            {"tipo": "grade", "de": 0, "ate": w_runeterra - 1, "icones": icones, "destaque": 0},
            {"tipo": "cartao", "de": w_runeterra - 1, "ate": w_nem - 1, "semente": 11, "itens": [
                {"de": w_runeterra - 1, "midia": midia(con, 757), "legenda": "Runeterra"},
                {"de": w_entidades, "midia": midia(con, 268), "legenda": "entidades primordiais"},
            ]},
            {"tipo": "telacheia", "de": w_nem, "ate": w_nas - 1, "midia": midia(con, 116),
             "zoom": [1.0, 1.12], "foco": [0.5, 0.45], "semente": 3},
            {"tipo": "cartao", "de": w_nas, "ate": w_eles - 1, "semente": 7, "itens": [
                {"de": w_nas, "midia": midia(con, 414), "legenda": "Ionia", "legenda_em": w_ionia},
            ]},
            {"tipo": "recorte", "de": w_eles, "ate": len(pa) - 1, "midia": midia(con, 118),
             "legenda": "manifestação espiritual", "legenda_em": w_manif, "semente": 5},
        ],
    }

    # ---------- Trecho 2: citação do Yone ----------
    py = palavras_do_trecho(*TRECHOS["yone"])
    yone = {
        "audio": "prototipo/yone.wav",
        "palavras": py,
        "cenas": [
            {"tipo": "dialogo", "de": 0, "ate": len(py) - 1,
             "esquerda": {"nome": "Yone", "midia": midia(con, 979), "foco": [0.12, 0.38], "diametro": 0.35},
             "direita": {"nome": "Azakana", "midia": midia(con, 116), "foco": [0.5, 0.5], "diametro": 0.9},
             "destaques": [achar(py, "tristeza"), achar(py, "fome")]},
        ],
        "citacao": {"autor": "Yone", "fundo": midia(con, 979), "foco": [0.6, 0.5],
                    "destaques": [achar(py, "tristeza"), achar(py, "fome")]},
    }

    SAIDA.write_text(json.dumps({"fps": 60, "abertura": abertura, "yone": yone},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {len(pa)} palavras na abertura, {len(py)} no trecho do Yone -> {SAIDA}")
    print("abertura:", " ".join(p["t"] for p in pa))
    print("yone:", " ".join(p["t"] for p in py))


if __name__ == "__main__":
    main()
