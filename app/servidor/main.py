"""Servidor do painel (FastAPI). Escuta só em 127.0.0.1 — nada fica exposto na rede.

Rodar:  .venv\\Scripts\\python.exe -m uvicorn app.servidor.main:app --host 127.0.0.1 --port 8765
(ou iniciar.bat, que também compila a tela se precisar e abre o navegador)
"""
from __future__ import annotations

import os
from pathlib import Path as _P

# Modelos de IA (Whisper, CLIP) já estão baixados: modo offline evita consultas ao Hugging Face a cada uso
# (e o aviso "unauthenticated requests"). Só liga se o cache existir — num PC novo, o 1º uso ainda baixa.
_HUB = _P.home() / ".cache" / "huggingface" / "hub"
if (_HUB / "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo").exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import motor, publicacao, recursos, storyboard
from .banco import RAIZ, agora, atualizar_etapa, conectar, criar_video, registrar
from .etapas import COLUNAS, ETAPAS


def _silenciar_conexao_cortada(loop: asyncio.AbstractEventLoop, contexto: dict) -> None:
    """No Windows, quando o navegador corta uma conexão no meio (o player de vídeo faz isso ao pular para outro
    ponto, recarregar ou trocar de tela), o asyncio registra um ConnectionResetError (WinError 10054). É inofensivo:
    só esse caso é silenciado; qualquer outro erro continua aparecendo normalmente."""
    if isinstance(contexto.get("exception"), ConnectionResetError):
        return
    loop.default_exception_handler(contexto)


@asynccontextmanager
async def _ciclo_de_vida(_app: FastAPI):
    asyncio.get_running_loop().set_exception_handler(_silenciar_conexao_cortada)
    yield


app = FastAPI(title="Guia de Runeterra Studio", lifespan=_ciclo_de_vida)
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
        dados = json.loads(r.get("dados") or "{}")
        # Arquivo que já não existe (ex.: limpeza depois de publicar) não vai para a tela: evita players quebrados/404.
        for campo in ("video", "audio", "original"):
            if isinstance(dados.get(campo), str) and not (RAIZ / dados[campo]).exists():
                dados.pop(campo)
                dados["arquivos_removidos"] = True
        lista.append({**e, "numero": n, "status": r.get("status", "pendente"), "resumo": r.get("resumo"),
                      "detalhe": r.get("detalhe"), "dados": dados, "atualizado_em": r.get("atualizado_em")})
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
        if antiga["coluna"] == "publicado" and corpo.coluna != "publicado":
            raise HTTPException(409, "vídeo publicado é definitivo: os arquivos já foram arquivados")
        if corpo.coluna == "publicado":
            _motor_livre(vid)
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
        _roteirista_livre(con, vid)
        est = motor.receber_roteiro(con, vid, corpo.texto, corpo.nome)
        con.commit()
    return est


class GerarRoteiro(BaseModel):
    minutos: float = 20
    notas: str = ""
    base: str | None = None  # roteiro base (canal gringo): só fatos/temas, nunca tradução
    titulo: str | None = None


class AjustarRoteiro(BaseModel):
    pedido: str


def _roteirista_livre(con, vid: int) -> None:
    """Trocar o roteiro com a direção/rascunho rodando deixaria o trabalho em curso apontando para o texto errado."""
    st = {r["chave"]: r["status"] for r in con.execute("SELECT chave, status FROM etapas WHERE video_id=?", (vid,))}
    if not st:
        raise HTTPException(404)
    if st.get("roteiro") == "andamento":
        raise HTTPException(409, "o roteirista ainda está trabalhando neste roteiro")
    executando = motor.situacao()["executando"]
    rodando = [k for k in ("direcao", "rascunho", "gravacao", "render") if st.get(k) == "andamento"]
    if rodando or (executando and executando["video"] == vid):
        raise HTTPException(409, "espere o motor terminar (" + (", ".join(rodando) or executando["tarefa"]) +
                            ") antes de trocar o roteiro")


@app.post("/api/videos/{vid}/roteiro/gerar")
def gerar_roteiro(vid: int, corpo: GerarRoteiro):
    with conectar() as con:
        _roteirista_livre(con, vid)
        motor.pedir_roteiro(con, vid, {"acao": "gerar", **corpo.model_dump()})
        con.commit()
    return {"ok": True}


@app.post("/api/videos/{vid}/roteiro/ajustar")
def ajustar_roteiro(vid: int, corpo: AjustarRoteiro):
    if len(corpo.pedido.strip()) < 3:
        raise HTTPException(400, "escreva o que quer mudar")
    with conectar() as con:
        _roteirista_livre(con, vid)
        if not motor.ler_roteiro(con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]):
            raise HTTPException(400, "ainda não há roteiro para ajustar")
        motor.pedir_roteiro(con, vid, {"acao": "ajustar", "pedido": corpo.pedido.strip()})
        con.commit()
    return {"ok": True}


@app.get("/api/videos/{vid}/roteiro/historico")
def historico_roteiro(vid: int):
    from . import roteirista

    with conectar() as con:
        pasta = _pasta(con, vid)
    return {"conversa": roteirista.historico(pasta), "versoes": roteirista.versoes(pasta)}


class Restaurar(BaseModel):
    versao: int


@app.post("/api/videos/{vid}/roteiro/restaurar")
def restaurar_roteiro(vid: int, corpo: Restaurar):
    with conectar() as con:
        pasta = _pasta(con, vid)
        _roteirista_livre(con, vid)
        arq = pasta / "direcao" / f"roteiro_v{corpo.versao}.txt"
        if not arq.exists():
            raise HTTPException(404, "versão não encontrada")
        est = motor.receber_roteiro(con, vid, arq.read_text(encoding="utf-8"), f"volta para a v{corpo.versao}")
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


@app.post("/api/videos/{vid}/storyboard/{cid}")
def ajustar_cena(vid: int, cid: str, acao: dict):
    with conectar() as con:
        pasta = _pasta(con, vid)
    try:
        return storyboard.ajustar(pasta, cid, acao)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/acervo/buscar")
def buscar_acervo(q: str):
    return storyboard.buscar_no_acervo(q)


@app.post("/api/videos/{vid}/rascunho/refazer")
def refazer_rascunho(vid: int):
    with conectar() as con:
        _pasta(con, vid)
        status = con.execute("SELECT status FROM etapas WHERE video_id=? AND chave='direcao'", (vid,)).fetchone()["status"]
        if status == "andamento":
            raise HTTPException(409, "a direção já está trabalhando")
        if status != "concluido":  # ex.: o roteiro mudou e a direção ainda não foi refeita
            raise HTTPException(409, "a direção ainda não foi feita para este roteiro")
        atualizar_etapa(con, vid, "direcao", "andamento", "na fila", "novo rascunho")
        r = con.execute("SELECT dados FROM etapas WHERE video_id=? AND chave='rascunho'", (vid,)).fetchone()
        dados = json.loads(r["dados"] or "{}")
        atualizar_etapa(con, vid, "rascunho", "andamento", f"gerando v{dados.get('versao', 1) + 1}…", "na fila", dados)
        registrar(con, vid, "Novo rascunho pedido (storyboard)", "info")
        con.commit()
    motor.FILA.put((vid, "rascunho"))
    return {"ok": True}


@app.post("/api/videos/{vid}/gravacao")
async def enviar_gravacao(vid: int, arquivo: UploadFile):
    """Recebe a gravação em pedaços (arquivos grandes não passam inteiros pela memória)."""
    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in motor.EXT_GRAVACAO:
        raise HTTPException(400, f"formato não aceito ({ext or 'sem extensão'}); use wav, mp3, m4a, flac, ogg, mp4, mkv, mov…")
    with conectar() as con:
        pasta = _pasta(con, vid)
    entrada = pasta / "entrada"
    entrada.mkdir(parents=True, exist_ok=True)
    destino = entrada / f"gravacao_{agora().replace(':', '-')}{ext}"
    with destino.open("wb") as f:
        while bloco := await arquivo.read(8 * 1024 * 1024):
            f.write(bloco)
    with conectar() as con:
        motor.receber_gravacao(con, vid, destino)
        con.commit()
    return {"ok": True, "arquivo": destino.name}


@app.post("/api/videos/{vid}/gravacao/da-pasta")
def gravacao_da_pasta(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        motor.pasta_do_video(v["slug"])
        arquivo = motor.gravacao_na_pasta(v["slug"])
        if arquivo is None:
            raise HTTPException(400, f"nenhum áudio/vídeo encontrado em projetos/{v['slug']}/entrada/")
        motor.receber_gravacao(con, vid, arquivo)
        con.commit()
    return {"ok": True, "arquivo": arquivo.name}


@app.post("/api/videos/{vid}/gravacao/aprovar")
def aprovar_gravacao(vid: int):
    with conectar() as con:
        r = con.execute("SELECT status, dados FROM etapas WHERE video_id=? AND chave='gravacao'", (vid,)).fetchone()
        if not r or not json.loads(r["dados"] or "{}").get("relatorio"):
            raise HTTPException(400, "não há gravação limpa para aprovar")
        motor.aprovar_gravacao(con, vid)
        con.commit()
    return {"ok": True}


@app.post("/api/videos/{vid}/abrir-pasta-entrada")
def abrir_pasta_entrada(vid: int):
    """Abre o Explorador do Windows na pasta entrada/ do vídeo (o servidor roda no próprio PC do Felipe)."""
    import subprocess

    with conectar() as con:
        pasta = _pasta(con, vid) / "entrada"
    pasta.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(pasta.resolve())])
    return {"caminho": str(pasta.resolve())}


@app.get("/api/videos/{vid}/publicacao")
def ver_publicacao(vid: int):
    with conectar() as con:
        pasta = _pasta(con, vid)
        url = con.execute("SELECT url_youtube FROM videos WHERE id=?", (vid,)).fetchone()["url_youtube"]
    arq = pasta / "direcao" / "publicacao.json"
    finais = sorted((pasta / "saida").glob("final_v*.mp4"), key=lambda p: p.stat().st_mtime) if (pasta / "saida").exists() else []
    textos = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None
    if textos and textos.get("thumbnail") and not (RAIZ / textos["thumbnail"]).exists():
        textos["thumbnail"] = None  # removida na limpeza
    return {"textos": textos,
            "tamanhos": publicacao.tamanhos(pasta), "url": url,
            "video_final": str(finais[-1].resolve()) if finais else None}


@app.put("/api/videos/{vid}/publicacao")
def salvar_publicacao(vid: int, textos: dict):
    with conectar() as con:
        pasta = _pasta(con, vid)
    arq = pasta / "direcao" / "publicacao.json"
    atual = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    for campo in ("titulo", "descricao", "tags", "comentario_fixado"):
        if campo in textos:
            atual[campo] = textos[campo]
    arq.write_text(json.dumps(atual, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True}


@app.post("/api/videos/{vid}/publicacao/gerar")
def gerar_publicacao(vid: int):
    with conectar() as con:
        _pasta(con, vid)
        atualizar_etapa(con, vid, "publicacao", "andamento", "na fila", "")
        con.commit()
    motor.FILA.put((vid, "publicacao"))
    return {"ok": True}


class Publicado(BaseModel):
    url: str | None = None


@app.post("/api/videos/{vid}/publicado")
def marcar_publicado(vid: int, corpo: Publicado):
    with conectar() as con:
        _pasta(con, vid)
        _motor_livre(vid)
        motor.marcar_publicado(con, vid, (corpo.url or "").strip() or None)
        con.commit()
    return {"ok": True}


def _motor_livre(vid: int) -> None:
    """Publicar arquiva os arquivos: não pode acontecer com o motor mexendo neste vídeo."""
    executando = motor.situacao()["executando"]
    if executando and executando["video"] == vid:
        raise HTTPException(409, "o motor está trabalhando neste vídeo agora; espere terminar")


@app.post("/api/videos/{vid}/abrir-pasta-saida")
def abrir_pasta_saida(vid: int):
    import subprocess

    with conectar() as con:
        pasta = _pasta(con, vid) / "saida"
    pasta.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(pasta.resolve())])
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
        executando = motor.situacao()["executando"]
        if executando and executando["video"] == vid:
            raise HTTPException(409, "o motor está trabalhando neste vídeo agora; espere terminar para excluir")
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
        con.execute("DELETE FROM videos WHERE id=?", (vid,))  # etapas/pendências/atividade saem em cascata
        con.commit()
    # arquivos do vídeo vão para a Lixeira do Windows (recuperáveis), não somem de vez
    from send2trash import send2trash

    for pasta in (motor.PASTA_PROJETOS / slug, RAIZ / "app" / "video" / "public" / slug):
        if pasta.exists():
            send2trash(str(pasta.resolve()))
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
        if p["chave"] == "ver_final":  # vídeo aprovado: prepara a publicação sozinho
            motor.ao_aprovar_final(con, p["video_id"])
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
