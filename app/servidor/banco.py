"""Banco do painel (SQLite em Runeterra/dados/studio.db): vídeos, etapas, pendências e atividade."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from .etapas import EM_BREVE, EM_BREVE_VERTICAL, etapas_do_formato

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tools"))
from canal import CANAL, caminho  # noqa: E402  (perfil do canal deste servidor: GRS_CANAL)

BANCO = caminho("studio")
BANCO.parent.mkdir(parents=True, exist_ok=True)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id          INTEGER PRIMARY KEY,
    titulo      TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    coluna      TEXT NOT NULL DEFAULT 'ideia',
    ordem       REAL NOT NULL DEFAULT 0,
    capa        TEXT,                 -- caminho relativo à raiz do projeto
    criado_em   TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS etapas (
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    chave       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pendente',
    resumo      TEXT,                 -- linha principal do card (ex.: "3 parágrafos · 158 palavras")
    detalhe     TEXT,                 -- linha secundária
    dados       TEXT,                 -- JSON livre (arquivos, números)
    atualizado_em TEXT,
    PRIMARY KEY (video_id, chave)
);
CREATE TABLE IF NOT EXISTS pendencias (
    id          INTEGER PRIMARY KEY,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    etapa       TEXT,
    titulo      TEXT NOT NULL,
    texto       TEXT,
    resolvida   INTEGER NOT NULL DEFAULT 0,
    criada_em   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS atividade (
    id          INTEGER PRIMARY KEY,
    video_id    INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    texto       TEXT NOT NULL,
    tipo        TEXT NOT NULL DEFAULT 'info',   -- info | ok | alerta
    quando      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observacoes (       -- observações gerais do Felipe sobre o vídeo (ditadas ou digitadas)
    id          INTEGER PRIMARY KEY,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    texto       TEXT NOT NULL,
    origem      TEXT NOT NULL DEFAULT 'texto', -- voz | texto
    criada_em   TEXT NOT NULL,
    editada_em  TEXT
);
"""


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80] or "video"


def conectar() -> sqlite3.Connection:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    # Migrações simples: colunas adicionadas depois da criação do banco.
    colunas = {r["name"] for r in con.execute("PRAGMA table_info(videos)")}
    if "travado" not in colunas:
        con.execute("ALTER TABLE videos ADD COLUMN travado INTEGER NOT NULL DEFAULT 0")
    if "url_youtube" not in colunas:
        con.execute("ALTER TABLE videos ADD COLUMN url_youtube TEXT")
    if "capa_aprovada" not in colunas:
        con.execute("ALTER TABLE videos ADD COLUMN capa_aprovada INTEGER NOT NULL DEFAULT 0")
    if "formato" not in colunas:
        con.execute("ALTER TABLE videos ADD COLUMN formato TEXT NOT NULL DEFAULT 'horizontal'")
    if "chave" not in {r["name"] for r in con.execute("PRAGMA table_info(pendencias)")}:
        con.execute("ALTER TABLE pendencias ADD COLUMN chave TEXT")  # identifica o tipo (ex.: aprovar_roteiro)
    con.execute("DELETE FROM etapas WHERE chave='pesquisa'")  # etapa removida: virou a conferência do Roteiro
    # vertical: animação, render e publicação deixaram de ser "em breve" (2026-11-02)
    con.execute("UPDATE etapas SET status='pendente' WHERE status='em_breve' AND video_id IN (SELECT id FROM videos WHERE formato='vertical')")
    return con


def _formato(formato: str) -> str:
    """vertical | horizontal | horizontal_doc (este só no canal com `[horizontal_doc]`); qualquer outro = horizontal."""
    if formato == "vertical" or (formato == "horizontal_doc" and CANAL.get("horizontal_doc")):
        return formato
    return "horizontal"


def criar_video(con: sqlite3.Connection, titulo: str, coluna: str = "ideia", capa: str | None = None,
                formato: str = "horizontal") -> int:
    base, n = slugify(titulo), 1
    slug = base
    while con.execute("SELECT 1 FROM videos WHERE slug=?", (slug,)).fetchone():
        n += 1
        slug = f"{base}-{n}"
    ordem = (con.execute("SELECT MAX(ordem) FROM videos WHERE coluna=?", (coluna,)).fetchone()[0] or 0) + 1
    vid = con.execute(
        "INSERT INTO videos (titulo, slug, coluna, ordem, capa, criado_em, atualizado_em, formato) VALUES (?,?,?,?,?,?,?,?)",
        (titulo, slug, coluna, ordem, capa, agora(), agora(), _formato(formato))).lastrowid
    formato = _formato(formato)
    em_breve = EM_BREVE_VERTICAL if formato != "horizontal" or CANAL.get("horizontal") else EM_BREVE
    for e in etapas_do_formato(formato):
        con.execute("INSERT INTO etapas (video_id, chave, status, atualizado_em) VALUES (?,?,?,?)",
                    (vid, e["chave"], "em_breve" if e["chave"] in em_breve else "pendente", agora()))
    registrar(con, vid, "Vídeo criado", "info")
    con.commit()
    return vid


def atualizar_etapa(con: sqlite3.Connection, vid: int, chave: str, status: str,
                    resumo: str | None = None, detalhe: str | None = None, dados: dict | None = None) -> None:
    con.execute("UPDATE etapas SET status=?, resumo=?, detalhe=?, dados=?, atualizado_em=? WHERE video_id=? AND chave=?",
                (status, resumo, detalhe, json.dumps(dados or {}, ensure_ascii=False), agora(), vid, chave))
    con.execute("UPDATE videos SET atualizado_em=? WHERE id=?", (agora(), vid))


def registrar(con: sqlite3.Connection, vid: int | None, texto: str, tipo: str = "info", quando: str | None = None) -> None:
    con.execute("INSERT INTO atividade (video_id, texto, tipo, quando) VALUES (?,?,?,?)", (vid, texto, tipo, quando or agora()))


def pendencia(con: sqlite3.Connection, vid: int, titulo: str, texto: str, etapa: str | None = None) -> None:
    con.execute("INSERT INTO pendencias (video_id, etapa, titulo, texto, criada_em) VALUES (?,?,?,?,?)",
                (vid, etapa, titulo, texto, agora()))
