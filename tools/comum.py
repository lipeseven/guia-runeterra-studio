"""Utilidades compartilhadas pelas ferramentas: configuração, caminhos e banco do acervo."""
from __future__ import annotations

import os
import sqlite3
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = tomllib.loads((RAIZ / "projeto.toml").read_text(encoding="utf-8"))

PASTA_ACERVO = Path(CONFIG["pastas"]["acervo"])
BANCO_ACERVO = RAIZ / CONFIG["acervo"]["banco"]
PASTA_MINIATURAS = RAIZ / CONFIG["acervo"]["miniaturas"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS midias (
    id          INTEGER PRIMARY KEY,
    caminho     TEXT UNIQUE NOT NULL,   -- relativo à pasta do acervo
    nome        TEXT NOT NULL,
    ext         TEXT NOT NULL,
    tipo        TEXT NOT NULL,          -- imagem | gif | video | audio | pdf
    bytes       INTEGER,
    mtime       REAL,
    sha1        TEXT,
    phash       TEXT,
    largura     INTEGER,
    altura      INTEGER,
    duracao     REAL,
    transparente INTEGER DEFAULT 0,
    prefixo     TEXT,                   -- nome sem o número final (ex.: aatrox23 -> aatrox)
    origem      TEXT DEFAULT 'acervo',  -- acervo | riot | wiki | reddit | artstation | ia | ...
    autor       TEXT,
    url         TEXT,
    licenca     TEXT,
    categoria   TEXT,                   -- splash | icone | recorte | meme | foto | mapa | hq | cinematica | ...
    personagens TEXT,                   -- JSON
    descricao   TEXT,
    uso         TEXT,                   -- em que momento do vídeo funciona (principalmente memes)
    tags        TEXT,                   -- JSON
    revisado    INTEGER DEFAULT 0,
    criado_em   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_midias_prefixo ON midias(prefixo);
CREATE INDEX IF NOT EXISTS idx_midias_sha1 ON midias(sha1);
-- Memória de uso: quais mídias cada vídeo PUBLICADO usou (o diretor evita repetir as recentes).
CREATE TABLE IF NOT EXISTS uso_midia (
    midia_id    INTEGER NOT NULL REFERENCES midias(id),
    video       TEXT NOT NULL,          -- slug do vídeo
    publicado_em TEXT NOT NULL,
    PRIMARY KEY (midia_id, video)
);
-- Efeitos sonoros (tools/audio/sfx.py): Freesound (só CC0/CC BY) ou gerados localmente (Stable Audio Open).
CREATE TABLE IF NOT EXISTS sons (
    id          INTEGER PRIMARY KEY,
    arquivo     TEXT UNIQUE NOT NULL,   -- relativo a dados/sfx/
    categoria   TEXT NOT NULL,
    descricao   TEXT,                   -- nome/descrição original ou o prompt usado na geração
    origem      TEXT NOT NULL,          -- freesound | gerado
    autor       TEXT,
    url         TEXT,
    licenca     TEXT,                   -- CC0 | CC BY 4.0 | Stability Community
    duracao     REAL,
    vetor       BLOB                    -- CLAP do áudio (float32, normalizado) para busca por descrição
);
CREATE TABLE IF NOT EXISTS uso_som (
    som_id      INTEGER NOT NULL REFERENCES sons(id),
    video       TEXT NOT NULL,
    publicado_em TEXT NOT NULL,
    PRIMARY KEY (som_id, video)
);
"""


def abrir_acervo() -> sqlite3.Connection:
    BANCO_ACERVO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO_ACERVO)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def preparar_ffmpeg() -> None:
    """Garante FFmpeg no PATH mesmo em terminais abertos antes da instalação via winget."""
    import shutil
    if shutil.which("ffmpeg"):
        return
    for p in (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WinGet" / "Packages").glob(
            "Gyan.FFmpeg*/*/bin"):
        os.environ["PATH"] = f"{p}{os.pathsep}{os.environ['PATH']}"
        return
    sys.exit("FFmpeg não encontrado. Instale com: winget install Gyan.FFmpeg")
