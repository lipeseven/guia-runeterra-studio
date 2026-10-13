"""Voz guia: lê o roteiro com TTS para montar o rascunho do vídeo ANTES da gravação do Felipe.

NUNCA vai para o vídeo publicado — serve só para medir tempos e revisar o rascunho.

Uso:
    .venv\\Scripts\\python.exe tools\\audio\\voz_guia.py <roteiro.txt> <saida.wav> [--motor fish|piper] [--ppm 162]

- Fish Audio (modelo gratuito s2.1-pro-free) como padrão; Piper (local) como reserva automática.
- O roteiro é dividido em blocos (por parágrafo); cada bloco fica em cache em dados/cache_voz/,
  então gerar de novo um roteiro levemente editado só refaz os blocos que mudaram.
- No fim, a velocidade é ajustada (sem mudar o tom) para bater com o ritmo do Felipe (palavras/min).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import RAIZ, preparar_ffmpeg  # noqa: E402

CACHE = RAIZ / "dados" / "cache_voz"
PPM_FELIPE = 162  # medido no vídeo "Todos os DEMÔNIOS" (fala corrida, sem pausas longas)
MODELO_PIPER = RAIZ / "dados/modelos/piper/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx"
MAX_BLOCO = 1200  # caracteres por chamada

# Pronúncia de nomes de LoL em português (o TTS lê "Xolaani" errado sem ajuda).
PRONUNCIA = {
    "Xolaani": "Cholaani", "Zaahen": "Zaarren", "Rhaast": "Rást", "Tahm Kench": "Tam Kentch",
    "Kinkou": "Kinkou", "Azakana": "Azakána", "Azakanas": "Azakánas", "Yone": "Iône",
}


def blocos(texto: str) -> list[str]:
    """Divide por parágrafo; parágrafos longos são quebrados em frases."""
    saida = []
    for par in [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]:
        atual = ""
        for frase in re.split(r"(?<=[.!?])\s+", par):
            if atual and len(atual) + len(frase) > MAX_BLOCO:
                saida.append(atual)
                atual = frase
            else:
                atual = f"{atual} {frase}".strip()
        if atual:
            saida.append(atual)
    return saida


def fish(texto: str, destino: Path) -> None:
    chave = os.environ.get("FISH_API_KEY")
    if not chave:
        raise RuntimeError("FISH_API_KEY ausente no .env")
    corpo = {
        "text": texto, "format": "wav", "sample_rate": 44100, "latency": "normal",
        "pronunciation_dictionary": [{"items": [{"key": k, "value": v} for k, v in PRONUNCIA.items()]}],
    }
    r = httpx.post("https://api.fish.audio/v1/tts", json=corpo, timeout=300,
                   headers={"Authorization": f"Bearer {chave}", "model": "s2.1-pro-free"})
    if r.status_code != 200:
        raise RuntimeError(f"Fish Audio {r.status_code}: {r.text[:300]}")
    destino.write_bytes(r.content)


def piper(texto: str, destino: Path) -> None:
    """Reserva 100% local (sem internet): Piper, voz pt_BR-faber."""
    import wave

    from piper import PiperVoice

    for nome, pron in PRONUNCIA.items():
        texto = re.sub(rf"\b{re.escape(nome)}\b", pron, texto)
    bruto = destino.with_suffix(".22k.wav")
    with wave.open(str(bruto), "wb") as wf:
        PiperVoice.load(str(MODELO_PIPER)).synthesize_wav(texto, wf)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-ar", "44100", "-ac", "1", str(destino)], check=True)
    bruto.unlink()


def duracao(arquivo: Path) -> float:
    s = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(arquivo)], capture_output=True, text=True, check=True).stdout
    return float(s)


def gerar(roteiro: str, saida: Path, motor: str = "fish", ppm_alvo: float = PPM_FELIPE) -> dict:
    load_dotenv(RAIZ / ".env")
    preparar_ffmpeg()
    CACHE.mkdir(parents=True, exist_ok=True)
    partes, usados = [], set()
    for b in blocos(roteiro):
        tentativas = [motor] + [m for m in ("fish", "piper") if m != motor]
        for m in tentativas:
            arq = CACHE / f"{m}_{hashlib.sha1(b.encode()).hexdigest()[:16]}.wav"
            try:
                if not arq.exists():
                    (fish if m == "fish" else piper)(b, arq)
                partes.append(arq)
                usados.add(m)
                break
            except Exception as e:  # cai para o próximo motor
                print(f"  ! {m} falhou ({e}); tentando o próximo", flush=True)
        else:
            raise RuntimeError("nenhum motor de voz funcionou")

    # Junta os blocos com uma pausa curta entre eles (como respiração entre parágrafos).
    lista = saida.with_suffix(".lista.txt")
    silencio = CACHE / "pausa_350ms.wav"
    if not silencio.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", "0.35", str(silencio)], check=True)
    linhas = []
    for k, p in enumerate(partes):
        linhas.append(f"file '{p.as_posix()}'")
        if k < len(partes) - 1:
            linhas.append(f"file '{silencio.as_posix()}'")
    lista.write_text("\n".join(linhas), encoding="utf-8")
    bruto = saida.with_suffix(".bruto.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-ar", "44100", "-ac", "1", str(bruto)], check=True)
    lista.unlink()

    # Calibra para o ritmo do Felipe sem alterar o tom (atempo).
    n_palavras = len(re.findall(r"\w+", roteiro))
    ppm_bruto = n_palavras / (duracao(bruto) / 60)
    fator = max(0.75, min(1.35, ppm_alvo / ppm_bruto))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-filter:a", f"atempo={fator:.4f}",
                    str(saida)], check=True)
    bruto.unlink()
    info = {"motores": sorted(usados), "blocos": len(partes), "palavras": n_palavras,
            "ppm_original": round(ppm_bruto, 1), "fator_tempo": round(fator, 3),
            "duracao": round(duracao(saida), 2), "aviso": "VOZ GUIA - nunca publicar"}
    saida.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("saida")
    ap.add_argument("--motor", choices=["fish", "piper"], default="fish")
    ap.add_argument("--ppm", type=float, default=PPM_FELIPE)
    a = ap.parse_args()
    info = gerar(Path(a.roteiro).read_text(encoding="utf-8"), Path(a.saida), a.motor, a.ppm)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
