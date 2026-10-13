"""Servidor do painel (FastAPI). Escuta só em 127.0.0.1 — nada fica exposto na rede.

Rodar:  .venv\\Scripts\\python.exe -m uvicorn app.servidor.main:app --host 127.0.0.1 --port 8765
(ou iniciar.bat, que também compila a tela se precisar e abre o navegador)
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import recursos
from .banco import RAIZ, agora, conectar, criar_video, registrar
from .etapas import COLUNAS, ETAPAS
app = FastAPI(title="Guia de Runeterra Studio")


def _video(con, vid: int) -> dict:
    v = con.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()
    if not v:
        raise HTTPException(404, "vídeo não encontrado")
    etapas = {r["chave"]: dict(r) for r in con.execute("SELECT * FROM etapas WHERE video_id=?", (vid,))}
    lista = []
    for n, e in enumerate(ETAPAS, 1):
        r = etapas.get(e["chave"], {})
        lista.append({**e, "numero": n, "status": r.get("status", "pendente"), "resumo": r.get("resumo"),
                      "detalhe": r.get("detalhe"), "dados": json.loads(r.get("dados") or "{}"),
                      "atualizado_em": r.get("atualizado_em")})
    pend = [dict(r) for r in con.execute(
        "SELECT * FROM pendencias WHERE video_id=? AND resolvida=0 ORDER BY criada_em", (vid,))]
    ativ = [dict(r) for r in con.execute(
        "SELECT * FROM atividade WHERE video_id=? ORDER BY quando DESC LIMIT 40", (vid,))]
    return {**dict(v), "etapas": lista, "pendencias": pend, "atividade": ativ}


@app.get("/api/quadro")
def quadro():
    with conectar() as con:
        videos = []
        for v in con.execute("SELECT * FROM videos ORDER BY ordem"):
            st = [r["status"] for r in con.execute("SELECT status FROM etapas WHERE video_id=?", (v["id"],))]
            pend = con.execute("SELECT COUNT(*) FROM pendencias WHERE video_id=? AND resolvida=0", (v["id"],)).fetchone()[0]
            videos.append({**dict(v), "progresso": {s: st.count(s) for s in set(st)}, "total_etapas": len(st),
                           "pendencias": pend})
        return {"colunas": COLUNAS, "videos": videos}


class NovoVideo(BaseModel):
    titulo: str
    coluna: str = "ideia"


@app.post("/api/videos")
def novo_video(corpo: NovoVideo):
    with conectar() as con:
        return {"id": criar_video(con, corpo.titulo.strip(), corpo.coluna)}


class Mover(BaseModel):
    coluna: str
    ordem: float | None = None


@app.patch("/api/videos/{vid}/mover")
def mover(vid: int, corpo: Mover):
    if corpo.coluna not in {c["chave"] for c in COLUNAS}:
        raise HTTPException(400, "coluna inválida")
    with conectar() as con:
        antiga = con.execute("SELECT coluna FROM videos WHERE id=?", (vid,)).fetchone()
        if not antiga:
            raise HTTPException(404)
        ordem = corpo.ordem if corpo.ordem is not None else (
            con.execute("SELECT MAX(ordem) FROM videos WHERE coluna=?", (corpo.coluna,)).fetchone()[0] or 0) + 1
        con.execute("UPDATE videos SET coluna=?, ordem=?, atualizado_em=? WHERE id=?", (corpo.coluna, ordem, agora(), vid))
        if antiga["coluna"] != corpo.coluna:
            nome = next(c["titulo"] for c in COLUNAS if c["chave"] == corpo.coluna)
            registrar(con, vid, f"Movido para “{nome}”", "info")
        con.commit()
    return {"ok": True}


@app.get("/api/videos/{vid}")
def video(vid: int):
    with conectar() as con:
        return _video(con, vid)


@app.post("/api/pendencias/{pid}/resolver")
def resolver(pid: int):
    with conectar() as con:
        p = con.execute("SELECT * FROM pendencias WHERE id=?", (pid,)).fetchone()
        if not p:
            raise HTTPException(404)
        con.execute("UPDATE pendencias SET resolvida=1 WHERE id=?", (pid,))
        registrar(con, p["video_id"], f"Resolvido: {p['titulo']}", "ok")
        # Sem mais pendências abertas na etapa, ela deixa de "precisar de você".
        if p["etapa"] and not con.execute(
                "SELECT 1 FROM pendencias WHERE video_id=? AND etapa=? AND resolvida=0", (p["video_id"], p["etapa"])).fetchone():
            con.execute("UPDATE etapas SET status='concluido', atualizado_em=? WHERE video_id=? AND chave=? AND status='atencao'",
                        (agora(), p["video_id"], p["etapa"]))
        con.commit()
    return {"ok": True}


@app.get("/api/recursos")
def api_recursos():
    return recursos.resumo()


@app.get("/api/arquivo")
def arquivo(caminho: str):
    """Serve mídias geradas (capas, vídeos de rascunho). Só dentro de dados/ e projetos/."""
    alvo = (RAIZ / caminho).resolve()
    permitido = [(RAIZ / "dados").resolve(), (RAIZ / "projetos").resolve()]
    if not any(alvo.is_relative_to(p) for p in permitido) or not alvo.is_file():
        raise HTTPException(404)
    return FileResponse(alvo)


# Tela compilada (app/painel/dist). Em desenvolvimento, use o Vite (npm run dev), que faz proxy de /api.
_DIST = RAIZ / "app" / "painel" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="painel")
