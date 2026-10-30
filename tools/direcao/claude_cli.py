"""Chamadas ao Claude pelo Claude Code em modo automático (assinatura Pro do Felipe, sem API).

Enxuto de propósito para economizar cota: sem ferramentas, sem MCP, sem configurações do usuário,
sem CLAUDE.md (roda numa pasta temporária) e com instruções próprias — ~800 tokens de base em vez de ~37 mil.
Imagens vão como blocos de conteúdo (stream-json), sem precisar da ferramenta de leitura de arquivos.
"""
from __future__ import annotations

import base64
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
           etiqueta: str = "", tentativas: int = 2, timeout: int = 900) -> str:
    if not EXE.exists():
        raise ErroClaude(f"Claude Code não encontrado em {EXE}")
    conteudo = [_bloco_imagem(p) for p in (imagens or [])] + [{"type": "text", "text": prompt}]
    mensagem = json.dumps({"type": "user", "message": {"role": "user", "content": conteudo}}, ensure_ascii=False)
    cmd = [str(EXE), "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--tools", "", "--system-prompt", sistema, "--strict-mcp-config", "--setting-sources", "",
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
