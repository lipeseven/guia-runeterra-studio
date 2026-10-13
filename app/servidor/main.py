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

from . import motor, recursos, storyboard
from .banco import RAIZ, agora, atualizar_etapa, conectar, criar_video, registrar
from .etapas import COLUNAS, ETAPAS
app = FastAPI(title="Guia de Runeterra Studio")
motor.iniciar()


@app.middleware("http")
async def sem_cache_na_pagina(request, chamar):
    """A página (index.html) nunca fica em cache: depois de recompilar, o navegador pega a versão nova.
    Os arquivos em /assets têm nome com hash e podem ficar em cache normalmente."""
    resposta = await chamar(request)
    if not request.url.path.startswith(("/assets/", "/api/arquivo")):
        resposta.headers["Cache-Control"] = "no-store"
    return resposta


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
        "SELECT * FROM atividade WHERE video_id=? ORDER BY quando DESC, id DESC LIMIT 40", (vid,))]
    return {**dict(v), "etapas": lista, "pendencias": pend, "atividade": ativ,
            "condicoes_direcao": motor.condicoes_direcao(con, vid)}


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
        antiga = con.execute("SELECT coluna, travado FROM videos WHERE id=?", (vid,)).fetchone()
        if not antiga:
            raise HTTPException(404)
        if antiga["travado"]:
            raise HTTPException(409, "vídeo travado: destrave para mover")
        ordem = corpo.ordem if corpo.ordem is not None else (
            con.execute("SELECT MAX(ordem) FROM videos WHERE coluna=?", (corpo.coluna,)).fetchone()[0] or 0) + 1
        con.execute("UPDATE videos SET coluna=?, ordem=?, atualizado_em=? WHERE id=?", (corpo.coluna, ordem, agora(), vid))
        if antiga["coluna"] != corpo.coluna:
            nome = next(c["titulo"] for c in COLUNAS if c["chave"] == corpo.coluna)
            registrar(con, vid, f"Movido para “{nome}”", "info")
            motor.ao_mover(con, vid, corpo.coluna)
        con.commit()
    return {"ok": True}


class Roteiro(BaseModel):
    texto: str
    nome: str = "roteiro colado"


@app.get("/api/videos/{vid}/roteiro")
def ler_roteiro(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        texto = motor.ler_roteiro(v["slug"])
        return {"texto": texto, **(motor.estatisticas(texto) if texto else {})}


@app.post("/api/videos/{vid}/roteiro")
def enviar_roteiro(vid: int, corpo: Roteiro):
    if len(corpo.texto.strip()) < 20:
        raise HTTPException(400, "roteiro vazio ou curto demais")
    with conectar() as con:
        if not con.execute("SELECT 1 FROM videos WHERE id=?", (vid,)).fetchone():
            raise HTTPException(404)
        est = motor.receber_roteiro(con, vid, corpo.texto, corpo.nome)
        con.commit()
    return est


@app.post("/api/videos/{vid}/roteiro/aprovar")
def aprovar_roteiro(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v or not motor.ler_roteiro(v["slug"]):
            raise HTTPException(400, "não há roteiro para aprovar")
        motor.aprovar_roteiro(con, vid)
        con.commit()
    return {"ok": True}


class Capa(BaseModel):
    nome: str
    dados_base64: str  # imagem enviada pelo navegador


@app.get("/api/videos/{vid}/capa")
def ler_capa(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        return motor.ler_capa(v["slug"])


@app.post("/api/videos/{vid}/capa")
def enviar_capa(vid: int, corpo: Capa):
    import base64

    ext = Path(corpo.nome).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(400, "envie a capa em JPG, PNG ou WEBP")
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        info = motor.receber_capa(con, vid, base64.b64decode(corpo.dados_base64), ext)
        con.commit()
    return info


@app.post("/api/videos/{vid}/capa/aprovar")
def aprovar_capa(vid: int):
    with conectar() as con:
        v = con.execute("SELECT capa FROM videos WHERE id=?", (vid,)).fetchone()
        if not v or not v["capa"]:
            raise HTTPException(400, "não há capa para aprovar")
        motor.aprovar_capa(con, vid)
        con.commit()
    return {"ok": True}


def _pasta(con, vid: int) -> Path:
    v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    if not v:
        raise HTTPException(404)
    return motor.PASTA_PROJETOS / v["slug"]


@app.get("/api/videos/{vid}/storyboard")
def ver_storyboard(vid: int):
    with conectar() as con:
        pasta = _pasta(con, vid)
    return {"cenas": storyboard.cenas(pasta), "tipos": storyboard.TIPOS,
            "pedidos_pendentes": len(storyboard.pendentes_para_o_diretor(storyboard.carregar(pasta)["ajustes"])),
            "ajustes": len(storyboard.carregar(pasta)["ajustes"])}


@app.post("/api/videos/{vid}/storyboard/{k}")
def ajustar_cena(vid: int, k: int, acao: dict):
    with conectar() as con:
        pasta = _pasta(con, vid)
    try:
        return storyboard.ajustar(pasta, k, acao)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/acervo/buscar")
def buscar_acervo(q: str):
    return storyboard.buscar_no_acervo(q)


@app.post("/api/videos/{vid}/rascunho/refazer")
def refazer_rascunho(vid: int):
    with conectar() as con:
        _pasta(con, vid)
        if con.execute("SELECT status FROM etapas WHERE video_id=? AND chave='direcao'", (vid,)).fetchone()["status"] == "andamento":
            raise HTTPException(409, "a direção já está trabalhando")
        atualizar_etapa(con, vid, "direcao", "andamento", "na fila", "novo rascunho")
        registrar(con, vid, "Novo rascunho pedido (storyboard)", "info")
        con.commit()
    motor.FILA.put((vid, "rascunho"))
    return {"ok": True}


@app.get("/api/motor")
def estado_motor():
    return motor.situacao()


class Travar(BaseModel):
    travado: bool


@app.patch("/api/videos/{vid}/travar")
def travar(vid: int, corpo: Travar):
    with conectar() as con:
        if not con.execute("UPDATE videos SET travado=?, atualizado_em=? WHERE id=?",
                           (int(corpo.travado), agora(), vid)).rowcount:
            raise HTTPException(404)
        registrar(con, vid, "Travado" if corpo.travado else "Destravado", "info")
        con.commit()
    return {"ok": True}


@app.delete("/api/videos/{vid}")
def excluir(vid: int):
    with conectar() as con:
        v = con.execute("SELECT travado FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        if v["travado"]:
            raise HTTPException(409, "vídeo travado: destrave para excluir")
        con.execute("DELETE FROM videos WHERE id=?", (vid,))  # etapas/pendências/atividade saem em cascata
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
        if (p["chave"] or "").startswith("erro_"):
            motor.tentar_de_novo(con, p["video_id"], p["chave"][5:])
            con.commit()
            return {"ok": True}
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
    permitido = [(RAIZ / "dados").resolve(), motor.PASTA_PROJETOS.resolve()]
    if not any(alvo.is_relative_to(p) for p in permitido) or not alvo.is_file():
        raise HTTPException(404)
    return FileResponse(alvo)


# Tela compilada (app/painel/dist). Em desenvolvimento, use o Vite (npm run dev), que faz proxy de /api.
_DIST = RAIZ / "app" / "painel" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="painel")
