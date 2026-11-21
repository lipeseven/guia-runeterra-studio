"""Ditado local por voz (faster-whisper PT-BR), usado nos campos de texto do painel (pedido geral da animação,
"corrigir por voz" das cenas do storyboard).

- O navegador grava (MediaRecorder) e envia o áudio; a transcrição (faster-whisper local, PT-BR) roda em processo à
  parte (`tools/audio/ditado.py`), uma de cada vez, numa thread: o servidor responde na hora com o id da tarefa e a
  tela pergunta até ficar pronta. O texto volta para o campo, o Felipe corrige e só então envia.
- O áudio é apagado assim que transcreve (fica só o texto).
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from .banco import RAIZ, conectar

rota = APIRouter()

SCRIPT = RAIZ / "tools" / "audio" / "ditado.py"
EXT = {".webm", ".ogg", ".oga", ".opus", ".wav", ".mp3", ".m4a", ".mp4", ".flac", ".aac"}
LIMITE = 50 * 1024 * 1024      # ~ dezenas de minutos de opus; ditado é curto
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
        arquivo.unlink(missing_ok=True)   # o que fica é o texto (o Felipe corrige e envia)


@rota.post("/api/videos/{vid}/ditado/transcrever")
async def transcrever(vid: int, arquivo: UploadFile):
    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in EXT:
        raise HTTPException(400, f"formato de áudio não aceito ({ext or 'sem extensão'})")
    with conectar() as con:
        pasta = _pasta(_slug(con, vid)) / "ditado_audio"
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
                raise HTTPException(413, "áudio grande demais para um ditado")
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
