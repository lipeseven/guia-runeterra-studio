"""Servidor do painel (FastAPI). Escuta só em 127.0.0.1 — nada fica exposto na rede.

Rodar:  .venv\\Scripts\\python.exe -m uvicorn app.servidor.main:app --host 127.0.0.1 --port 8765
(ou Iniciar Runeterra.bat, que também compila a tela se precisar e abre o navegador)
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
import re
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import motor, publicacao, recursos, storyboard
from .banco import RAIZ, agora, atualizar_etapa, conectar, criar_video, registrar
from .etapas import COLUNAS, ETAPAS, etapas_do_formato


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
    # o CLIP (busca do storyboard) leva ~10 s para carregar: carrega já, em segundo plano, para a 1ª busca ser rápida
    asyncio.get_running_loop().run_in_executor(None, storyboard.preaquecer_busca)
    yield


from .banco import CANAL  # noqa: E402

app = FastAPI(title=f"{CANAL['nome']} Studio", lifespan=_ciclo_de_vida)


@app.get("/api/aprendizado")
def ver_aprendizado():
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from aprendizado import PASTA, propostas

    ex = PASTA / "exemplos_legendas.json"
    return {"propostas": propostas(), "exemplos": len(json.loads(ex.read_text(encoding="utf-8"))) if ex.exists() else 0}


class Decisao(BaseModel):
    acao: str  # aprovar | recusar
    texto: str | None = None


@app.post("/api/aprendizado/{pid}")
def decidir_aprendizado(pid: int, corpo: Decisao):
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from aprendizado import decidir

    if corpo.acao not in ("aprovar", "recusar"):
        raise HTTPException(400, "ação inválida")
    return decidir(pid, corpo.acao, corpo.texto)


def _pasta_roteiros() -> Path:
    """Pasta do Felipe para roteiros e transcrições (.txt), mesmo de vídeos sem card: <Canal>/dados/roteiros."""
    from .banco import caminho

    pasta = caminho("dados_acervo").parent / "roteiros"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


class FatosDoCanal(BaseModel):
    texto: str


@app.get("/api/fatos-do-canal")
def ler_fatos_do_canal():
    from .conferencia import ARQ_FATOS

    return {"texto": ARQ_FATOS.read_text(encoding="utf-8-sig") if ARQ_FATOS.exists() else "", "caminho": str(ARQ_FATOS)}


@app.post("/api/fatos-do-canal")
def salvar_fatos_do_canal(corpo: FatosDoCanal):
    from .conferencia import ARQ_FATOS

    ARQ_FATOS.parent.mkdir(parents=True, exist_ok=True)
    ARQ_FATOS.write_text(corpo.texto.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")
    return {"ok": True}


@app.get("/api/roteiros")
def listar_roteiros():
    pasta = _pasta_roteiros()
    arqs = sorted(pasta.rglob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"pasta": str(pasta.resolve()),
            "arquivos": [{"nome": p.relative_to(pasta).as_posix(), "modificado": p.stat().st_mtime} for p in arqs]}


@app.get("/api/roteiros/{nome:path}")
def ler_roteiro_da_pasta(nome: str):
    pasta = _pasta_roteiros().resolve()
    arq = (pasta / nome).resolve()
    if not arq.is_relative_to(pasta) or arq.suffix.lower() != ".txt" or not arq.is_file():
        raise HTTPException(404, "arquivo não encontrado na pasta de roteiros")
    bruto = arq.read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:  # Bloco de Notas antigo salva em ANSI
        texto = bruto.decode("cp1252")
    return {"nome": arq.name, "texto": texto.replace("\r\n", "\n")}


@app.get("/api/canal")
def ver_canal():
    """Canal deste servidor + a lista de canais (só nome e porta) para o seletor do painel."""
    from canal import todos

    return {"chave": CANAL["chave"], "nome": CANAL["nome"], "porta": CANAL["porta"], "canais": todos(),
            "formatos": CANAL.get("formatos", [])}
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
    for n, e in enumerate(etapas_do_formato(v["formato"], set(etapas)), 1):
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
            "condicoes_direcao": motor.condicoes_direcao(con, vid),
            "conferindo": vid in motor.CONFERINDO}  # conferência do roteiro na fila/rodando: não dá para aprovar


@app.get("/api/quadro")
def quadro():
    with conectar() as con:
        videos = []
        for v in con.execute("SELECT * FROM videos ORDER BY ordem"):
            st = [r["status"] for r in con.execute("SELECT status FROM etapas WHERE video_id=?", (v["id"],))]
            pend = con.execute("SELECT COUNT(*) FROM pendencias WHERE video_id=? AND resolvida=0", (v["id"],)).fetchone()[0]
            ultima = con.execute("SELECT titulo FROM pendencias WHERE video_id=? AND resolvida=0 ORDER BY id DESC LIMIT 1",
                                 (v["id"],)).fetchone()
            videos.append({**dict(v), "progresso": {s: st.count(s) for s in set(st)}, "total_etapas": len(st),
                           "pendencias": pend, "aguardando": ultima["titulo"] if ultima else None})
        return {"colunas": COLUNAS, "videos": videos}


class NovoVideo(BaseModel):
    titulo: str
    coluna: str = "ideia"
    formato: str = "horizontal"


@app.post("/api/videos")
def novo_video(corpo: NovoVideo):
    with conectar() as con:
        vid = criar_video(con, corpo.titulo.strip(), corpo.coluna, formato=corpo.formato)
    motor.pedir_acervo()  # card novo: confere se entrou coisa nova no acervo (o acervo muda pouco; não roda toda hora)
    return {"id": vid}


class JaPublicado(BaseModel):
    titulo: str
    url: str | None = None
    data: str | None = None  # AAAA-MM-DD
    capa_nome: str | None = None
    capa_base64: str | None = None
    roteiro: str | None = None


@app.post("/api/videos/ja-publicado")
def video_ja_publicado(corpo: JaPublicado):
    """Vídeo publicado ANTES do sistema: só entra no histórico (capa, link, roteiro). Nasce em Publicado, sem
    direção, render, arquivamento nem atualização do acervo (nada roda, 0 cota)."""
    import base64

    titulo = corpo.titulo.strip()
    if not titulo:
        raise HTTPException(400, "dê um título ao vídeo")
    ext = Path(corpo.capa_nome or "").suffix.lower()
    if corpo.capa_base64 and ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(400, "envie a capa em JPG, PNG ou WEBP")
    quando = f"{corpo.data}T12:00:00" if corpo.data else None
    with conectar() as con:
        vid = criar_video(con, titulo, "publicado")
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
        pasta = motor.PASTA_PROJETOS / slug
        pasta.mkdir(parents=True, exist_ok=True)
        capa = None
        if corpo.capa_base64:
            (pasta / f"capa{ext}").write_bytes(base64.b64decode(corpo.capa_base64))
            capa = (pasta / f"capa{ext}").relative_to(RAIZ).as_posix()
        if corpo.roteiro and corpo.roteiro.strip():
            (pasta / "roteiro.txt").write_text(corpo.roteiro.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")
        con.execute("UPDATE etapas SET status='concluido', atualizado_em=? WHERE video_id=? AND status='pendente'",
                    (agora(), vid))
        con.execute("UPDATE videos SET capa=?, url_youtube=?, atualizado_em=? WHERE id=?",
                    (capa, (corpo.url or "").strip() or None, quando or agora(), vid))
        registrar(con, vid, "Publicado antes do sistema: adicionado ao histórico do canal"
                  + (" (com roteiro)" if corpo.roteiro and corpo.roteiro.strip() else ""), "ok", quando)
        con.commit()
    return {"id": vid}


@app.post("/api/acervo/atualizar")
def atualizar_acervo():
    motor.pedir_acervo()
    return {"ok": True}


@app.get("/api/acervo/situacao")
def situacao_acervo():
    return motor.ACERVO["ultima"] or {}


class Mover(BaseModel):
    coluna: str
    ordem: float | None = None


@app.patch("/api/videos/{vid}/mover")
def mover(vid: int, corpo: Mover):
    if corpo.coluna not in {c["chave"] for c in COLUNAS}:
        raise HTTPException(400, "coluna inválida")
    with conectar() as con:
        antiga = con.execute("SELECT coluna, travado, formato FROM videos WHERE id=?", (vid,)).fetchone()
        if not antiga:
            raise HTTPException(404)
        if motor._animado(con, vid) and corpo.coluna == "gravacao":
            raise HTTPException(409, "vídeo animado não usa a coluna Gravação: a voz sobe no painel Voz")
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
        texto = motor.ler_roteiro(v["slug"])  # com as [notas]
        narracao = motor.PASTA_PROJETOS / v["slug"] / "direcao" / "roteiro.txt"
        est = motor.estatisticas(narracao.read_text(encoding="utf-8")) if narracao.exists() else {}
        brief = narracao.parent / "briefing.json"  # briefing que veio junto com o roteiro (só as outras seções)
        secoes = json.loads(brief.read_text(encoding="utf-8"))["secoes"] if brief.exists() else []
        return {"texto": texto, "briefing": secoes, **est}


@app.get("/api/videos/{vid}/roteiro/conferencia")
def ver_conferencia(vid: int):
    with conectar() as con:
        pasta = _pasta(con, vid)
    arq, base = pasta / "direcao" / "conferencia.json", pasta / "direcao" / "roteiro_base.txt"
    dados = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None
    import hashlib

    narr = pasta / "direcao" / "roteiro.txt"  # a conferência é do roteiro ATUAL? (senão, está rodando de novo)
    atual = narr.exists() and dados and dados.get("roteiro") == hashlib.sha1(
        narr.read_text(encoding="utf-8").encode()).hexdigest()[:16]
    from . import pesquisa

    return {"conferencia": dados, "atual": bool(atual) and vid not in motor.CONFERINDO, "dossie": pesquisa.ler(pasta),
            "base": base.read_text(encoding="utf-8") if base.exists() else None}


class Base(BaseModel):
    texto: str


@app.post("/api/videos/{vid}/roteiro/base")
def guardar_base(vid: int, corpo: Base):
    """Roteiro base (canal gringo) para o detector de semelhança — também quando o roteiro veio de fora."""
    with conectar() as con:
        pasta = _pasta(con, vid)
        arq = pasta / "direcao" / "roteiro_base.txt"
        arq.parent.mkdir(parents=True, exist_ok=True)
        if corpo.texto.strip():
            from .conferencia import limpar_base

            arq.write_text(limpar_base(corpo.texto) + "\n", encoding="utf-8")
        else:
            arq.unlink(missing_ok=True)
        motor.pedir_conferencia(vid)
    return {"ok": True}


@app.post("/api/videos/{vid}/roteiro/conferir")
def conferir_roteiro(vid: int, tudo: bool = False):
    with conectar() as con:
        pasta = _pasta(con, vid)
    if tudo:  # "conferir tudo de novo": esquece o que já foi checado (todos os parágrafos voltam ao Claude)
        (pasta / "direcao" / "conferencia_cache.json").unlink(missing_ok=True)
    motor.pedir_conferencia(vid)
    return {"ok": True}


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


@app.get("/api/videos/{vid}/roteiro/mudancas")
def mudancas_roteiro(vid: int):
    from . import roteirista

    with conectar() as con:
        pasta = _pasta(con, vid)
    return roteirista.mudancas(pasta) or {"versao": None, "base": None, "reescrito": False, "lista": []}


class Desfazer(BaseModel):
    versao: int
    indice: int


@app.post("/api/videos/{vid}/roteiro/desfazer")
def desfazer_mudanca_roteiro(vid: int, corpo: Desfazer):
    """Desfaz UMA alteração da versão atual (vira versão nova; as outras alterações ficam)."""
    from . import roteirista

    with conectar() as con:
        pasta = _pasta(con, vid)
        _roteirista_livre(con, vid)
        m = roteirista.mudancas(pasta)
        if not m or m["versao"] != corpo.versao or not 0 <= corpo.indice < len(m["lista"]):
            raise HTTPException(409, "o roteiro mudou; recarregue a página")
        texto, base = roteirista.desfazer_mudanca(pasta, corpo.indice)
        est = motor.receber_roteiro(con, vid, texto, f"desfez alteração no parágrafo {m['lista'][corpo.indice]['paragrafo'] + 1}")
        roteirista.fixar_base(pasta, corpo.versao + 1, base)
        con.commit()
    return est


@app.post("/api/videos/{vid}/roteiro/aprovar")
def aprovar_roteiro(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v or not motor.ler_roteiro(v["slug"]):
            raise HTTPException(400, "não há roteiro para aprovar")
        if vid in motor.CONFERINDO:
            raise HTTPException(409, "espere a conferência do roteiro terminar antes de aprovar")
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


def _estilo(pasta: Path) -> int:
    arq = pasta / "direcao" / "estilo_visual.json"
    return int(json.loads(arq.read_text(encoding="utf-8")).get("versao", 2)) if arq.exists() else 2


@app.get("/api/videos/{vid}/storyboard")
def ver_storyboard(vid: int):
    with conectar() as con:
        pasta = _pasta(con, vid)
    return {"cenas": storyboard.cenas(pasta), "tipos": storyboard.TIPOS,
            "pedidos_pendentes": len(storyboard.pendentes_para_o_diretor(storyboard.carregar(pasta)["ajustes"])),
            "ajustes": len(storyboard.carregar(pasta)["ajustes"]),
            "pendentes": len(storyboard.pendentes(pasta)),  # mexidas depois que o último rascunho começou
            "pendentes_detalhe": storyboard.detalhe_dos_pendentes(pasta),
            "capa": next((p.relative_to(RAIZ).as_posix() for p in sorted((pasta / "direcao").glob("capa.*"))), None),
            "estilo": _estilo(pasta)}  # 2 = recursos novos (transições); o 1º vídeo ficou no 1


@app.post("/api/videos/{vid}/storyboard/descartar")
def descartar_pendentes(vid: int):
    """Desfaz tudo o que foi mexido no storyboard depois do último rascunho (a fila de pendentes)."""
    with conectar() as con:
        pasta = _pasta(con, vid)
    try:
        nao = storyboard.descartar_pendentes(pasta)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "nao_desfeitas": len(nao)}


@app.post("/api/videos/{vid}/storyboard/{cid}")
def ajustar_cena(vid: int, cid: str, acao: dict):
    with conectar() as con:
        pasta = _pasta(con, vid)
    try:
        return storyboard.ajustar(pasta, cid, acao)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/internet/buscar")
def buscar_internet(q: str, n: int = 24):
    from . import internet

    return internet.buscar(q, min(max(n, 4), 60))


class DaInternet(BaseModel):
    url: str
    titulo: str = ""
    pagina: str = ""
    fonte: str = ""
    licenca: str = ""
    autor: str = ""


@app.post("/api/internet/baixar")
def baixar_da_internet(corpo: DaInternet):
    """Baixa a imagem escolhida na busca da internet e cataloga no acervo (fora da pasta do Felipe)."""
    from . import internet

    try:
        return internet.baixar(corpo.url, corpo.titulo, corpo.pagina, corpo.fonte, corpo.licenca, corpo.autor)
    except Exception as e:
        raise HTTPException(400, f"não consegui baixar essa imagem: {e}")


class Link(BaseModel):
    url: str
    inicio: str | None = None  # "1:23" ou "83" (segundos): baixa só o trecho entre início e fim
    fim: str | None = None


def _segundos(t: str) -> int:
    partes = [int(p) for p in t.strip().split(":")]
    if not partes or len(partes) > 3 or any(p < 0 for p in partes):
        raise ValueError
    s = 0
    for p in partes:
        s = s * 60 + p
    return s


@app.post("/api/acervo/clipe-do-link")
def clipe_do_link(corpo: Link):
    """Vídeo da internet por link (YouTube etc.): entra na fila, é baixado e vira tomadas no acervo."""
    url = corpo.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "cole um link (https://…)")
    trecho = None
    if (corpo.inicio or "").strip() or (corpo.fim or "").strip():
        try:
            trecho = (_segundos(corpo.inicio or "0"), _segundos(corpo.fim or ""))
        except ValueError:
            raise HTTPException(400, "use minutos:segundos no início e no fim (ex.: 1:23 e 1:41)")
        if trecho[1] <= trecho[0]:
            raise HTTPException(400, "o fim precisa vir depois do início")
    motor.pedir_clipe(url, trecho)
    return {"ok": True}


@app.post("/api/acervo/importar-riot")
def importar_riot():
    motor.FILA.put((0, "importar_riot"))
    return {"ok": True}


@app.post("/api/acervo/importar-oficial")
def importar_oficial():
    """Importador de material oficial do CANAL deste servidor (Runeterra: Riot)."""
    tarefa = {"runeterra": "importar_riot"}.get(CANAL["chave"])
    if not tarefa:
        raise HTTPException(400, "este canal não tem importador de material oficial")
    motor.FILA.put((0, tarefa))
    return {"ok": True}


@app.get("/api/acervo/clipes-baixados")
def clipes_baixados():
    return {"pendentes": [motor.descrever_clipe(p) for p in motor.CLIPES_PEDIDOS], "ultimos": motor.CLIPES["ultimos"]}


@app.get("/api/acervo/buscar")
def buscar_acervo(q: str, n: int = 16, clipes: bool = False):
    """`n` cresce de 16 em 16 com o "mostrar mais" do storyboard; `clipes` = vídeos (tomadas) e GIFs."""
    n = min(max(n, 1), 400)
    return storyboard.buscar_clipes(q, n) if clipes else storyboard.buscar_no_acervo(q, n)


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
        if motor.gravacao_aprovada(vid, con):  # depois da gravação: o storyboard gera um vídeo final novo (voz real)
            atualizar_etapa(con, vid, "render", "andamento", "na fila", "novo vídeo final")
            motor.fechar_pendencia(con, vid, "ver_final")
            registrar(con, vid, "Novo vídeo final pedido (storyboard)", "info")
        else:
            r = con.execute("SELECT dados FROM etapas WHERE video_id=? AND chave='rascunho'", (vid,)).fetchone()
            dados = json.loads(r["dados"] or "{}")
            atualizar_etapa(con, vid, "rascunho", "andamento", f"gerando v{dados.get('versao', 1) + 1}…", "na fila", dados)
            motor.limpar_avisos(con, vid, motor.AVISOS_DO_RASCUNHO)  # eram da versão anterior
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


def _pasta_gravacao(vid: int) -> Path:
    with conectar() as con:
        return _pasta(con, vid) / "trabalho" / "gravacao"


@app.get("/api/videos/{vid}/gravacao/falas")
def falas_da_gravacao(vid: int):
    """Linha do tempo da gravação: cada fala (tempo no ORIGINAL), se ficou ou saiu, e as suas escolhas."""
    pasta = _pasta_gravacao(vid)
    arq = pasta / "falas.json"
    if not arq.exists():
        return {"falas": [], "decisoes": {}}
    falas = [{k: v for k, v in f.items() if k != "palavras"} | {"inicio_cortado": (f.get("inicio_cortado") or {}).get("texto")}
             for f in json.loads(arq.read_text(encoding="utf-8"))]
    dec = pasta / "decisoes.json"
    return {"falas": falas, "decisoes": json.loads(dec.read_text(encoding="utf-8")) if dec.exists() else {}}


class DecisaoFala(BaseModel):
    id: int
    acao: str  # manter | cortar | inicio (devolve o começo cortado) | padrao (volta ao automático)


@app.post("/api/videos/{vid}/gravacao/falas")
def decidir_fala(vid: int, corpo: DecisaoFala):
    if corpo.acao not in ("manter", "cortar", "inicio", "padrao"):
        raise HTTPException(400, "ação inválida")
    pasta = _pasta_gravacao(vid)
    dec_arq = pasta / "decisoes.json"
    dec = json.loads(dec_arq.read_text(encoding="utf-8")) if dec_arq.exists() else {}
    if corpo.acao == "padrao":
        dec.pop(str(corpo.id), None)
    else:
        dec[str(corpo.id)] = corpo.acao
    dec_arq.write_text(json.dumps(dec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"decisoes": dec}


@app.post("/api/videos/{vid}/gravacao/refazer")
def refazer_audio_limpo(vid: int):
    """Refaz o áudio limpo com as escolhas da linha do tempo (rápido: não transcreve de novo)."""
    if not (_pasta_gravacao(vid) / "falas.json").exists():
        raise HTTPException(409, "esta limpeza é antiga (sem linha do tempo): mande a gravação de novo")
    motor.FILA.put((vid, "remontar_gravacao"))
    return {"ok": True}


@app.post("/api/videos/{vid}/voz")
async def enviar_voz(vid: int, arquivo: UploadFile):
    """Vídeo vertical: a voz vem pronta, gerada pelo Felipe em outro programa."""
    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"):
        raise HTTPException(400, "envie um arquivo de áudio")
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        motor.pasta_do_video(v["slug"])
        destino = motor.PASTA_PROJETOS / v["slug"] / "entrada" / f"voz_{agora().replace(':', '-')}{ext}"
        with destino.open("wb") as saida:
            shutil.copyfileobj(arquivo.file, saida)
        motor.receber_voz(con, vid, destino)
        con.commit()
    return {"ok": True, "arquivo": destino.name}


@app.post("/api/videos/{vid}/voz/da-pasta")
def voz_da_pasta(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        motor.pasta_do_video(v["slug"])
        arquivo = motor.gravacao_na_pasta(v["slug"])
        if arquivo is None:
            raise HTTPException(400, f"nenhum áudio encontrado em {motor.caminho_rel(v['slug'], 'entrada')}/")
        motor.receber_voz(con, vid, arquivo)
        con.commit()
    return {"ok": True, "arquivo": arquivo.name}


def _dirc(vid: int) -> Path:
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    if not v:
        raise HTTPException(404)
    return motor.PASTA_PROJETOS / v["slug"] / "direcao"


@app.get("/api/videos/{vid}/animacao")
def animacao(vid: int):
    """Vertical: os planos escolhidos pelo diretor (com o trecho e o segundo em que começam) e os pedidos na fila."""
    dirc = _dirc(vid)
    arq, tempos = dirc / "vertical.json", dirc / "tempos_voz.json"
    if not arq.exists() or not tempos.exists():
        return {"planos": [], "pedidos": motor.pedidos_animacao(dirc), "avisos": []}
    d = json.loads(arq.read_text(encoding="utf-8"))
    pal = json.loads(tempos.read_text(encoding="utf-8"))
    fora = {"id", "i", "tipo", "em", "marcas", "marcas_texto", "clima", "codigo", "set"}
    planos = []
    for n, p in enumerate(d["planos"]):
        fim = d["planos"][n + 1]["i"] if n + 1 < len(d["planos"]) else len(pal)
        planos.append({"id": p["id"], "n": n + 1, "tipo": p.get("tipo") or f"cena própria ({p.get('set', 'pista')})", "clima": p.get("clima"), "inicio": 0 if n == 0 else pal[p["i"]]["i"],
                       "trecho": " ".join(w["t"] for w in pal[p["i"]:fim]),
                       "extras": [k for k in p if k not in fora]})
    return {"planos": planos, "pedidos": motor.pedidos_animacao(dirc), "avisos": [_aviso(a, d["planos"]) for a in d.get("avisos", [])]}


def _aviso(texto: str, planos: list[dict]) -> dict:
    """Aviso do diretor com a cena a que se refere ("pedido não feito (cena N)": responder vira pedido daquela cena)."""
    m = re.match(r"pedido não feito \((?:cena (\d+)|pedido geral)\)", texto)
    n = int(m[1]) if m and m[1] else 0
    return {"texto": texto, "resposta": bool(m), "plano": planos[n - 1]["id"] if 0 < n <= len(planos) else None}


def _tirar_aviso(dirc: Path, k: int) -> str:
    arq = dirc / "vertical.json"
    d = json.loads(arq.read_text(encoding="utf-8"))
    avisos = d.get("avisos", [])
    if not 0 <= k < len(avisos):
        raise HTTPException(404, "aviso não existe mais (a animação mudou): recarregue")
    texto = avisos.pop(k)
    arq.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return texto


class RespostaAviso(BaseModel):
    texto: str


@app.post("/api/videos/{vid}/animacao/aviso/{k}/responder")
def responder_aviso(vid: int, k: int, corpo: RespostaAviso):
    """A resposta do Felipe a um "pedido não feito" vira pedido da mesma cena, com o aviso junto (contexto do diretor)."""
    dirc = _dirc(vid)
    if not corpo.texto.strip():
        raise HTTPException(400, "escreva a resposta")
    planos = json.loads((dirc / "vertical.json").read_text(encoding="utf-8"))["planos"]
    texto = _tirar_aviso(dirc, k)
    aviso = _aviso(texto, planos)
    pedidos = motor.pedidos_animacao(dirc) + [{"plano": aviso["plano"], "quando": agora(),
                                               "texto": f"{corpo.texto.strip()} (resposta ao seu aviso: \"{texto}\")"}]
    (dirc / "pedidos_vertical.json").write_text(json.dumps(pedidos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True}


@app.delete("/api/videos/{vid}/animacao/aviso/{k}")
def aceitar_aviso(vid: int, k: int):
    """"Está bom assim": o aviso sai da lista."""
    _tirar_aviso(_dirc(vid), k)
    return {"ok": True}


class PedidoAnimacao(BaseModel):
    texto: str
    plano: str | None = None  # id do plano; sem id = pedido geral


@app.post("/api/videos/{vid}/animacao/pedido")
def pedir_animacao(vid: int, corpo: PedidoAnimacao):
    dirc = _dirc(vid)
    if not corpo.texto.strip():
        raise HTTPException(400, "escreva o pedido")
    pedidos = motor.pedidos_animacao(dirc) + [{"plano": corpo.plano, "texto": corpo.texto.strip(), "quando": agora()}]
    (dirc / "pedidos_vertical.json").write_text(json.dumps(pedidos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "pedidos": pedidos}


@app.delete("/api/videos/{vid}/animacao/pedido/{n}")
def tirar_pedido(vid: int, n: int):
    dirc = _dirc(vid)
    pedidos = motor.pedidos_animacao(dirc)
    if 0 <= n < len(pedidos):
        pedidos.pop(n)
    (dirc / "pedidos_vertical.json").write_text(json.dumps(pedidos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "pedidos": pedidos}


class Musica(BaseModel):
    ligada: bool
    descricao: str = ""
    volume: float = -14.0  # dB sobre a trilha nivelada em -20 LUFS; -14 fica ~13 dB abaixo da voz


@app.get("/api/videos/{vid}/musica")
def ver_musica(vid: int):
    """Vertical: música de fundo (gerada no PC, ou a do Felipe na pasta musica/ do projeto, que tem prioridade)."""
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    import vertical

    dirc = _dirc(vid)
    cfg = vertical.config_musica(dirc.parent)
    em_uso = vertical.arquivo_musica(dirc.parent) if cfg.get("ligada") else None
    return {**cfg, "pasta": str(dirc.parent / "musica"), "em_uso": em_uso.name if em_uso else None,
            "propria": bool(em_uso and not em_uso.name.startswith("trilha_"))}


@app.post("/api/videos/{vid}/musica")
def mudar_musica(vid: int, corpo: Musica):
    """Salva a escolha e põe na fila: gera a trilha (se precisar) e refaz só o áudio do último vídeo."""
    dirc = _dirc(vid)
    if not any((dirc.parent / "saida").glob("final_v*.mp4")):
        raise HTTPException(400, "ainda não há vídeo renderizado")
    arq = dirc / "musica.json"
    cfg = json.loads(arq.read_text(encoding="utf-8-sig")) if arq.exists() else {}
    descricao = corpo.descricao.strip() or cfg.get("descricao", "")  # campo vazio = mantém a música que já existe
    if descricao != cfg.get("descricao", ""):
        cfg.pop("arquivo", None)  # descrição nova = trilha nova
    cfg.update({"ligada": corpo.ligada, "descricao": descricao, "volume": max(-40.0, min(0.0, corpo.volume))})
    arq.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    (dirc.parent / "musica").mkdir(exist_ok=True)
    with conectar() as con:
        motor.fechar_pendencia(con, vid, "ver_final")
        atualizar_etapa(con, vid, "render", "andamento", "na fila", "música de fundo" if corpo.ligada else "tirando a música")
        registrar(con, vid, "Música de fundo: " + (f"ligada ({descricao or 'padrão'})" if corpo.ligada else "desligada"), "info")
        con.commit()
    motor.FILA.put((vid, "musica"))
    return {"ok": True}


class RefazerAnimacao(BaseModel):
    do_zero: bool = False
    so_render: bool = False  # sem Claude: renderiza de novo a direção atual (ex.: um modelo 3D mudou)


@app.post("/api/videos/{vid}/animacao/refazer")
def refazer_animacao(vid: int, corpo: RefazerAnimacao):
    """Com os pedidos (só os planos pedidos mudam), do zero (o diretor escolhe tudo de novo) ou só o render."""
    dirc = _dirc(vid)
    if corpo.so_render and not (dirc / "vertical.json").exists():
        raise HTTPException(400, "ainda não há animação para renderizar")
    if corpo.so_render and motor.pedidos_animacao(dirc):
        raise HTTPException(400, "há pedidos na fila: use “Refazer com os pedidos” (ou tire os pedidos)")
    if not corpo.do_zero and not corpo.so_render and not motor.pedidos_animacao(dirc):
        raise HTTPException(400, "escreva ao menos um pedido, ou peça para refazer do zero")
    with conectar() as con:
        motor.fechar_pendencia(con, vid, "ver_final")
        motor.fechar_pendencia(con, vid, "sem_mudanca")
        if corpo.do_zero:
            atualizar_etapa(con, vid, "direcao", "andamento", "na fila", "do zero")
            registrar(con, vid, "Animação: refazer do zero", "info")
        elif corpo.so_render:
            atualizar_etapa(con, vid, "render", "andamento", "na fila", "só o render (sem Claude)")
            registrar(con, vid, "Animação: renderizar de novo, sem Claude", "info")
        else:
            atualizar_etapa(con, vid, "render", "andamento", "na fila", "com os seus pedidos")
            registrar(con, vid, f"Animação: {len(motor.pedidos_animacao(dirc))} pedido(s) enviados ao diretor", "info")
        con.commit()
    motor.FILA.put((vid, "direcao" if corpo.do_zero else "rascunho"))
    return {"ok": True}


@app.post("/api/videos/{vid}/gravacao/da-pasta")
def gravacao_da_pasta(vid: int):
    with conectar() as con:
        v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
        if not v:
            raise HTTPException(404)
        motor.pasta_do_video(v["slug"])
        arquivo = motor.gravacao_na_pasta(v["slug"])
        if arquivo is None:
            raise HTTPException(400, f"nenhum áudio/vídeo encontrado em {motor.caminho_rel(v['slug'], 'entrada')}/")
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
        try:
            motor.marcar_publicado(con, vid, (corpo.url or "").strip() or None)
        except RuntimeError as e:  # arquivo aberto em outro programa: nada foi arquivado
            raise HTTPException(409, str(e))
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
        l = con.execute("SELECT slug, titulo FROM videos WHERE id=?", (vid,)).fetchone()
        slug, titulo = l["slug"], l["titulo"]
        pastas = [motor.PASTA_PROJETOS / slug, RAIZ / "app" / "video" / "public" / slug]
        try:
            marcadas = motor.separar_para_apagar(pastas)  # arquivo aberto: não apaga nada
        except OSError:
            raise HTTPException(409, "algum arquivo deste vídeo está aberto em outro programa; feche e tente de novo")
        con.execute("DELETE FROM videos WHERE id=?", (vid,))  # etapas/pendências/atividade saem em cascata
        con.commit()
    motor.tirar_da_fila(vid)  # o número do card pode voltar a ser usado num card novo
    publicacao.esquecer_uso(slug)
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from aprendizado import esquecer

    esquecer(slug, titulo)
    motor.apagar_de_vez(marcadas)  # definitivo, sem Lixeira: o Felipe não quer mais nada deste card
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
    """Serve mídias geradas (capas, vídeos de rascunho). Só dentro de dados/ e dos dados do canal."""
    alvo = (RAIZ / caminho).resolve()
    permitido = [(RAIZ / "dados").resolve(), motor.PASTA_PROJETOS.parent.resolve()]
    if not any(alvo.is_relative_to(p) for p in permitido) or not alvo.is_file():
        raise HTTPException(404)
    return FileResponse(alvo)


@app.get("/api/acervo/video/{midia_id}")
def video_do_acervo(midia_id: int):
    """Vídeo original do acervo (só leitura), para escolher o momento de um clipe no storyboard."""
    import sys

    sys.path.insert(0, str(RAIZ / "tools"))
    from comum import PASTA_ACERVO, PASTA_INTERNET, abrir_acervo

    r = abrir_acervo().execute("SELECT caminho FROM midias WHERE id=? AND tipo='video'", (midia_id,)).fetchone()
    alvo = (PASTA_ACERVO / r[0]).resolve() if r else None  # baixado da internet: caminho absoluto
    if (not alvo or not alvo.is_file()
            or not any(alvo.is_relative_to(p.resolve()) for p in (PASTA_ACERVO, PASTA_INTERNET))):
        raise HTTPException(404)
    return FileResponse(alvo)


# Tela compilada (app/painel/dist). Em desenvolvimento, use o Vite (npm run dev), que faz proxy de /api.
_DIST = RAIZ / "app" / "painel" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="painel")
