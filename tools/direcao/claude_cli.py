"""Chamadas ao Claude pelo Claude Code em modo automático (assinatura Pro do Felipe, sem API).

Enxuto de propósito para economizar cota: sem ferramentas, sem MCP, sem configurações do usuário,
sem CLAUDE.md (roda numa pasta temporária) e com instruções próprias — ~800 tokens de base em vez de ~37 mil.
Imagens vão como blocos de conteúdo (stream-json), sem precisar da ferramenta de leitura de arquivos.
"""
from __future__ import annotations

import base64
import contextlib
import contextvars
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

EXE = Path(os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"))
REGISTRO = Path(__file__).resolve().parents[2] / "dados" / "comum" / "uso_claude.jsonl"  # consumo, para o painel


class ErroClaude(RuntimeError):
    pass


# ---------------------------------------------------------------- modo orquestrador (sem `claude -p`)
# Card que não pode chamar o modelo pelo painel (documentário do F1): dentro de `pelo_orquestrador(pasta)`, `chamar`
# NÃO roda o Claude Code. Cada prompt vira `<pasta>/<etiqueta>_<hash>.prompt.txt`; se já existe a resposta
# (`<mesmo nome>.resposta.txt`, gravada pelo orquestrador/chat), ela é usada; senão sobe `PrecisaOrquestrador` e a
# tarefa pausa. Rodar a tarefa de novo refaz as mesmas chamadas (mesmo prompt = mesma resposta, sem gastar cota) e
# avança até o próximo prompt sem resposta.
_ORQUESTRADOR: contextvars.ContextVar[Path | None] = contextvars.ContextVar("orquestrador", default=None)


class PrecisaOrquestrador(BaseException):
    """Pausa (não é erro): o prompt foi gravado e espera a resposta do orquestrador. BaseException de propósito, para
    atravessar os `except Exception` de quem trata falha de rede/cota como aviso (conferência, pesquisa)."""

    def __init__(self, prompt: Path, resposta: Path, etiqueta: str):
        super().__init__(f"aguardando o orquestrador: {prompt.name}")
        self.prompt, self.resposta, self.etiqueta = prompt, resposta, etiqueta


@contextlib.contextmanager
def pelo_orquestrador(pasta: Path):
    marca = _ORQUESTRADOR.set(Path(pasta))
    try:
        yield
    finally:
        _ORQUESTRADOR.reset(marca)


def _pelo_orquestrador(prompt: str, sistema: str, modelo: str, imagens: list[Path] | None, etiqueta: str) -> str | None:
    pasta = _ORQUESTRADOR.get()
    if pasta is None:
        return None
    h = hashlib.sha1("\0".join([sistema, prompt, *(str(p) for p in imagens or [])]).encode("utf-8")).hexdigest()[:16]
    nome = f"{re.sub(r'[^a-z0-9_-]', '_', (etiqueta or 'prompt').lower())}_{h}"
    arq_p, arq_r = pasta / f"{nome}.prompt.txt", pasta / f"{nome}.resposta.txt"
    if arq_r.exists() and arq_r.read_text(encoding="utf-8").strip():
        return arq_r.read_text(encoding="utf-8")
    pasta.mkdir(parents=True, exist_ok=True)
    arq_p.write_text(f"# modelo sugerido: {modelo}\n# imagens: {', '.join(str(p) for p in imagens or []) or 'nenhuma'}\n"
                     f"# grave a resposta (só o texto/JSON pedido) em: {arq_r}\n\n## SISTEMA\n{sistema}\n\n## PROMPT\n{prompt}\n",
                     encoding="utf-8")
    raise PrecisaOrquestrador(arq_p, arq_r, etiqueta)


def _bloco_imagem(caminho: Path) -> dict:
    tipo = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[caminho.suffix.lower()]
    return {"type": "image", "source": {"type": "base64", "media_type": tipo,
                                        "data": base64.b64encode(caminho.read_bytes()).decode()}}


def extrair_json(texto: str):
    """Aceita JSON puro ou dentro de ```json ... ```."""
    m = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
    bruto = m.group(1) if m else texto
    inicio = min([i for i in (bruto.find("{"), bruto.find("[")) if i >= 0], default=0)
    return json.loads(bruto[inicio:])


def chamar(prompt: str, sistema: str, modelo: str = "opus", imagens: list[Path] | None = None,
           etiqueta: str = "", tentativas: int = 2, timeout: int = 900, ferramentas: str = "") -> str:
    """`ferramentas` (ex.: "WebSearch,WebFetch"): só para quem precisa, já liberadas (sem pergunta); o padrão é nenhuma."""
    resposta = _pelo_orquestrador(prompt, sistema, modelo, imagens, etiqueta)
    if resposta is not None:
        return resposta
    if not EXE.exists():
        raise ErroClaude(f"Claude Code não encontrado em {EXE}")
    conteudo = [_bloco_imagem(p) for p in (imagens or [])] + [{"type": "text", "text": prompt}]
    mensagem = json.dumps({"type": "user", "message": {"role": "user", "content": conteudo}}, ensure_ascii=False)
    cmd = [str(EXE), "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--tools", ferramentas, *(["--allowedTools", ferramentas] if ferramentas else []), "--system-prompt", sistema, "--strict-mcp-config", "--setting-sources", "",
           "--model", modelo, "--no-session-persistence"]
    ultimo_erro = ""
    for tentativa in range(tentativas):
        t0 = time.time()
        p = subprocess.run(cmd, input=mensagem, capture_output=True, text=True, encoding="utf-8",
                           cwd=tempfile.gettempdir(), timeout=timeout)
        resultado = None
        for linha in p.stdout.splitlines():
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                resultado = ev
        if resultado and not resultado.get("is_error") and resultado.get("result"):
            _registrar(etiqueta, modelo, resultado, time.time() - t0)
            return resultado["result"]
        ultimo_erro = (resultado or {}).get("result") or p.stderr[-500:] or p.stdout[-500:]
        if "limit" in ultimo_erro.lower():  # cota do Pro esgotada: não adianta insistir agora
            raise ErroClaude(f"Cota do Claude esgotada por agora: {ultimo_erro}")
        time.sleep(3 * (tentativa + 1))
    raise ErroClaude(f"Claude falhou: {ultimo_erro}")


def chamar_json(prompt: str, sistema: str, **kw):
    """Chama e devolve o JSON da resposta; se vier malformado, pede para corrigir uma vez."""
    texto = chamar(prompt, sistema, **kw)
    try:
        return extrair_json(texto)
    except json.JSONDecodeError as e:
        conserto = chamar(f"O JSON abaixo está inválido ({e}). Devolva SOMENTE o JSON corrigido.\n\n{texto}",
                          "Você corrige JSON. Responda só com JSON válido.", modelo="sonnet", etiqueta="conserto-json")
        return extrair_json(conserto)


def _registrar(etiqueta: str, modelo: str, r: dict, segundos: float) -> None:
    u = r.get("usage", {})
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "etiqueta": etiqueta, "modelo": modelo,
                            "segundos": round(segundos, 1), "entrada": u.get("input_tokens", 0),
                            "cache_criado": u.get("cache_creation_input_tokens", 0),
                            "cache_lido": u.get("cache_read_input_tokens", 0),
                            "saida": u.get("output_tokens", 0)}, ensure_ascii=False) + "\n")
