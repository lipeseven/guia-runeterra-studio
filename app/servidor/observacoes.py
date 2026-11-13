"""Observações gerais do Felipe sobre o vídeo (qualquer formato), ditadas por voz ou digitadas.

- Ficam no banco (tabela `observacoes`) e num espelho na pasta do card: `<projeto>/observacoes.json`
  (quem lê de fora, como o diretor documental do F1, lê o arquivo; nunca o banco).
- Ditado: o navegador grava (MediaRecorder) e envia o áudio; a transcrição (faster-whisper local, PT-BR) roda em
  processo à parte (`tools/audio/ditado.py`), uma de cada vez, numa thread: o servidor responde na hora com o id da
  tarefa e a tela pergunta até ficar pronta. O texto volta para o campo, o Felipe corrige e só então salva.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from .banco import RAIZ, agora, conectar, registrar

rota = APIRouter()

SCRIPT = RAIZ / "tools" / "audio" / "ditado.py"
EXT = {".webm", ".ogg", ".oga", ".opus", ".wav", ".mp3", ".m4a", ".mp4", ".flac", ".aac"}
LIMITE = 50 * 1024 * 1024      # ~ dezenas de minutos de opus; observação é curta
TEMPO = 900                    # s (CPU, áudio longo)
TAREFAS: dict[str, dict] = {}  # id → {status: transcrevendo|pronto|falhou, texto, erro, video}
_UMA_POR_VEZ = threading.Lock()


def _slug(con, vid: int) -> str:
    v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    if not v:
        raise HTTPException(404, "vídeo não encontrado")
    return v["slug"]


def _pasta(slug: str) -> Path:
    from .motor import PASTA_PROJETOS

    return PASTA_PROJETOS / slug


def listar(con, vid: int) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT id, texto, origem, criada_em, editada_em FROM observacoes WHERE video_id=? ORDER BY criada_em, id", (vid,))]


def _espelhar(con, vid: int) -> list[dict]:
    """Grava `<projeto>/observacoes.json` (lista em ordem de criação). Sem observações, o arquivo sai."""
    lista = listar(con, vid)
    arq = _pasta(_slug(con, vid)) / "observacoes.json"
    if lista:
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
    elif arq.exists():
        arq.unlink()
    return lista


def _limpo(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        raise HTTPException(400, "observação vazia")
    return t[:20000]


class Nova(BaseModel):
    texto: str
    origem: str = "texto"


class Edicao(BaseModel):
    texto: str


@rota.get("/api/videos/{vid}/observacoes")
def ver(vid: int):
    with conectar() as con:
        _slug(con, vid)
        return {"observacoes": listar(con, vid)}


@rota.post("/api/videos/{vid}/observacoes")
def criar(vid: int, corpo: Nova):
    with conectar() as con:
        _slug(con, vid)
        origem = corpo.origem if corpo.origem in ("voz", "texto") else "texto"
        con.execute("INSERT INTO observacoes (video_id, texto, origem, criada_em) VALUES (?,?,?,?)",
                    (vid, _limpo(corpo.texto), origem, agora()))
        registrar(con, vid, "Observação geral salva" + (" (ditada)" if origem == "voz" else ""), "info")
        lista = _espelhar(con, vid)
        con.commit()
        return {"observacoes": lista}


@rota.put("/api/videos/{vid}/observacoes/{oid}")
def editar(vid: int, oid: int, corpo: Edicao):
    with conectar() as con:
        _slug(con, vid)
        if not con.execute("UPDATE observacoes SET texto=?, editada_em=? WHERE id=? AND video_id=?",
                           (_limpo(corpo.texto), agora(), oid, vid)).rowcount:
            raise HTTPException(404, "observação não encontrada")
        lista = _espelhar(con, vid)
        con.commit()
        return {"observacoes": lista}


@rota.delete("/api/videos/{vid}/observacoes/{oid}")
def apagar(vid: int, oid: int):
    with conectar() as con:
        _slug(con, vid)
        if not con.execute("DELETE FROM observacoes WHERE id=? AND video_id=?", (oid, vid)).rowcount:
            raise HTTPException(404, "observação não encontrada")
        registrar(con, vid, "Observação geral apagada", "info")
        lista = _espelhar(con, vid)
        con.commit()
        return {"observacoes": lista}


# ---------------------------------------------------------------- ditado
def _transcrever(tid: str, arquivo: Path) -> None:
    t = TAREFAS[tid]
    try:
        with _UMA_POR_VEZ:   # um modelo por vez na máquina (dois ditados seguidos esperam a vez)
            t["status"] = "transcrevendo"
            r = subprocess.run([sys.executable, str(SCRIPT), str(arquivo)], capture_output=True, timeout=TEMPO)
        try:
            d = json.loads(r.stdout.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            d = {"ok": False, "erro": r.stderr.decode("utf-8", "replace")[-400:] or "ditado.py não respondeu"}
        if d.get("ok"):
            t.update(status="pronto", texto=d.get("texto", ""), dispositivo=d.get("dispositivo"))
        else:
            t.update(status="falhou", erro=d.get("erro", "falhou"))
    except subprocess.TimeoutExpired:
        t.update(status="falhou", erro="a transcrição demorou demais")
    except Exception as e:  # noqa: BLE001
        t.update(status="falhou", erro=f"{type(e).__name__}: {e}")
    finally:
        arquivo.unlink(missing_ok=True)   # o que fica é o texto (o Felipe corrige e salva)


@rota.post("/api/videos/{vid}/observacoes/transcrever")
async def transcrever(vid: int, arquivo: UploadFile):
    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in EXT:
        raise HTTPException(400, f"formato de áudio não aceito ({ext or 'sem extensão'})")
    with conectar() as con:
        pasta = _pasta(_slug(con, vid)) / "observacoes_audio"
    pasta.mkdir(parents=True, exist_ok=True)
    tid = uuid.uuid4().hex[:12]
    destino = pasta / f"ditado_{tid}{ext}"
    tamanho = 0
    with destino.open("wb") as f:
        while bloco := await arquivo.read(1024 * 1024):
            tamanho += len(bloco)
            if tamanho > LIMITE:
                f.close()
                destino.unlink(missing_ok=True)
                raise HTTPException(413, "áudio grande demais para uma observação")
            f.write(bloco)
    if tamanho == 0:
        destino.unlink(missing_ok=True)
        raise HTTPException(400, "áudio vazio (o microfone gravou algo?)")
    TAREFAS[tid] = {"status": "na_fila", "texto": None, "erro": None, "video": vid}
    threading.Thread(target=_transcrever, args=(tid, destino), daemon=True).start()
    return {"tarefa": tid, "status": "na_fila"}


@rota.get("/api/transcricoes/{tid}")
def tarefa(tid: str):
    t = TAREFAS.get(tid)
    if not t:
        raise HTTPException(404, "tarefa de transcrição não encontrada (o servidor reiniciou?)")
    return {"tarefa": tid, **t}
