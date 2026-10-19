"""Banco do painel (SQLite em dados/studio.db): vídeos, etapas, pendências e atividade."""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from .etapas import ETAPAS, EM_BREVE

RAIZ = Path(__file__).resolve().parents[2]
BANCO = RAIZ / "dados" / "studio.db"

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
    if "chave" not in {r["name"] for r in con.execute("PRAGMA table_info(pendencias)")}:
        con.execute("ALTER TABLE pendencias ADD COLUMN chave TEXT")  # identifica o tipo (ex.: aprovar_roteiro)
    con.execute("DELETE FROM etapas WHERE chave='pesquisa'")  # etapa removida: virou a conferência do Roteiro
    return con


def criar_video(con: sqlite3.Connection, titulo: str, coluna: str = "ideia", capa: str | None = None) -> int:
    base, n = slugify(titulo), 1
    slug = base
    while con.execute("SELECT 1 FROM videos WHERE slug=?", (slug,)).fetchone():
        n += 1
        slug = f"{base}-{n}"
    ordem = (con.execute("SELECT MAX(ordem) FROM videos WHERE coluna=?", (coluna,)).fetchone()[0] or 0) + 1
    vid = con.execute(
        "INSERT INTO videos (titulo, slug, coluna, ordem, capa, criado_em, atualizado_em) VALUES (?,?,?,?,?,?,?)",
        (titulo, slug, coluna, ordem, capa, agora(), agora())).lastrowid
    for e in ETAPAS:
        con.execute("INSERT INTO etapas (video_id, chave, status, atualizado_em) VALUES (?,?,?,?)",
                    (vid, e["chave"], "em_breve" if e["chave"] in EM_BREVE else "pendente", agora()))
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
