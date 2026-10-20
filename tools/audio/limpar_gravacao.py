"""Limpa a gravação do Felipe: remove regravações, encurta pausas longas e padroniza o volume.

Uso:
    .venv\\Scripts\\python.exe tools\\audio\\limpar_gravacao.py <gravacao> <pasta-saida> [--roteiro roteiro.txt]

Gera em <pasta-saida>:
    limpa.wav        áudio final (-14 LUFS, pico -1.5 dBTP; só cortes + volume, timbre intocado)
    relatorio.json   o que foi cortado (regravações, pausas), com tempos e texto — para revisão
    palavras.json    tempo de cada palavra JÁ no áudio limpo (base da ressincronização da direção)

Regravações: quando uma frase é seguida, em poucos segundos, por outra que começa igual
(falso começo, frase interrompida, leitura repetida), fica só a ÚLTIMA leitura.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import preparar_ffmpeg  # noqa: E402

SR = 48000
# Glossário que ajuda o Whisper com nomes de LoL (ampliar conforme os vídeos).
GLOSSARIO = ("Runeterra, Fiddlesticks, Azakana, Nocturne, Tahm Kench, Evelynn, Raum, Camphor, Tybaulk, "
             "Atakhan, Ashlesh, Darkin, Aatrox, Xolaani, Zaahen, Rhaast, Varus, Naafiri, Kinkou, Yone, "
             "Ionia, Noxus, Demacia, Freljord, Shurima, Targon, Ixtal, Zaun, Piltover, Vazio")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canal import CANAL  # noqa: E402

if CANAL["chave"] != "runeterra":  # glossário do canal (canal.toml); o resto vem do próprio roteiro
    GLOSSARIO = CANAL.get("glossario", "")

PAUSA_MAX_FIM_FRASE = 0.80  # pausa dramática preservada até aqui
PAUSA_MAX_MEIO = 0.45
PAUSA_MIN = 0.12
PAUSA_APOS_REGRAVACAO = (0.35, 0.25)  # (fim de frase, meio de frase)
JANELA_REGRAVACAO = 20.0  # s: até quanto tempo depois a repetição conta como regravação


# ---------------------------------------------------------------- áudio
def carregar(caminho: Path) -> np.ndarray:
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", str(caminho), "-vn", "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(bruto, np.float32).copy()


def nivel_db(a: np.ndarray, t: float, janela: float = 0.02) -> float:
    i = int(t * SR)
    x = a[max(0, i):max(0, i) + int(janela * SR)]
    return -120.0 if len(x) == 0 else 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def refinar_bordas(a: np.ndarray, ini: float, fim: float, limiar: float = -45.0) -> tuple[float, float]:
    """O Whisper erra as bordas em dezenas de ms: estende enquanto ainda há voz (até 150/250 ms)."""
    i = ini - 0.04
    while i > ini - 0.15 and nivel_db(a, i - 0.02) > limiar:
        i -= 0.01
    f = fim + 0.06
    while f < fim + 0.25 and nivel_db(a, f) > limiar:
        f += 0.01
    return max(0.0, i), min(len(a) / SR, f)


# ---------------------------------------------------------------- trechos de fala
def trechos_de_fala(a: np.ndarray, pausa: float = 0.30) -> list[tuple[float, float]]:
    """Divide o áudio em falas contínuas usando só o VOLUME (sem IA): fala = janela acima do
    piso de ruído + 15 dB. Pausas >= `pausa` separam os trechos."""
    n = int(0.02 * SR)
    q = a[:len(a) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt(np.mean(q ** 2, axis=1)) + 1e-12)
    piso = np.percentile(db[db > -100], 10) if np.any(db > -100) else -80
    fala = db > max(-45.0, piso + 15)
    trechos, ini, silencio = [], None, 0
    for k, v in enumerate(fala):
        if v:
            if ini is None:
                ini = k
            silencio = 0
        elif ini is not None:
            silencio += 1
            if silencio * 0.02 >= pausa:
                trechos.append((ini, k - silencio + 1))
                ini, silencio = None, 0
    if ini is not None:
        trechos.append((ini, len(fala)))
    return [(max(0.0, i * 0.02 - 0.08), min(len(a) / SR, f * 0.02 + 0.12))
            for i, f in trechos if (f - i) * 0.02 >= 0.15]


# ---------------------------------------------------------------- transcrição
def transcrever(a: np.ndarray) -> list[dict]:
    """Transcreve CADA trecho de fala isoladamente. Vendo o áudio inteiro, o Whisper 'corrige' a
    leitura e omite falsos começos; isolado, ele é obrigado a transcrever o que ouviu."""
    for p in (Path(sys.prefix) / "Lib" / "site-packages" / "nvidia").glob("*/bin"):
        os.add_dll_directory(str(p))
        os.environ["PATH"] = f"{p}{os.pathsep}{os.environ['PATH']}"
    from faster_whisper import WhisperModel

    modelo = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    a16 = reamostrar_16k(a)
    falas = []
    for ini, fim in trechos_de_fala(a):
        pedaco = a16[int(ini * 16000):int(fim * 16000)]
        segs, _ = modelo.transcribe(pedaco, language="pt", word_timestamps=True, vad_filter=False,
                                    condition_on_previous_text=False, temperature=0.0, hotwords=GLOSSARIO)
        palavras = []
        for s in segs:
            if s.no_speech_prob > 0.6 and s.avg_logprob < -1.0:
                continue  # provável alucinação em ruído
            palavras += [{"p": w.word.strip(), "i": ini + w.start, "f": ini + w.end} for w in (s.words or [])]
        if palavras:
            falas.append({"palavras": palavras, "i": palavras[0]["i"], "f": palavras[-1]["f"],
                          "texto": " ".join(w["p"] for w in palavras)})
    return falas


def reamostrar_16k(a: np.ndarray) -> np.ndarray:
    saida = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                            "-ar", "16000", "-f", "f32le", "-"], input=a.astype(np.float32).tobytes(),
                           capture_output=True, check=True).stdout
    return np.frombuffer(saida, np.float32)


def recomeco_interno(fala: dict) -> dict | None:
    """'Mas não é, mas não existe...' dito sem pausa: se as 2 primeiras palavras reaparecem logo
    adiante na mesma fala, descarta o que vem antes do recomeço. Devolve a parte descartada."""
    ws = [normalizar(w["p"]) for w in fala["palavras"]]
    for m in range(1, min(8, len(ws) - 1)):
        if ws[m:m + 2] == ws[0:2] and len(ws) - m >= 3:
            descartada = {"palavras": fala["palavras"][:m], "i": fala["i"], "f": fala["palavras"][m - 1]["f"],
                          "texto": " ".join(w["p"] for w in fala["palavras"][:m])}
            fala["palavras"] = fala["palavras"][m:]
            fala["i"] = fala["palavras"][0]["i"]
            fala["texto"] = " ".join(w["p"] for w in fala["palavras"])
            return descartada
    return None


UNIDADES = "zero um dois tres quatro cinco seis sete oito nove dez onze doze treze quatorze quinze dezesseis dezessete dezoito dezenove".split()
DEZENAS = {2: "vinte", 3: "trinta", 4: "quarenta", 5: "cinquenta", 6: "sessenta", 7: "setenta", 8: "oitenta", 9: "noventa"}
CENTENAS = {1: "cento", 2: "duzentos", 3: "trezentos", 4: "quatrocentos", 5: "quinhentos", 6: "seiscentos",
            7: "setecentos", 8: "oitocentos", 9: "novecentos"}


def por_extenso(n: int) -> str:
    """Número → palavras (pt-BR), até 999.999: o Whisper escreve "10" quando o roteiro diz "dez" (e vice-versa)."""
    if n < 20:
        return UNIDADES[n]
    if n < 100:
        return DEZENAS[n // 10] + ("" if n % 10 == 0 else " e " + UNIDADES[n % 10])
    if n < 1000:
        if n == 100:
            return "cem"
        return CENTENAS[n // 100] + ("" if n % 100 == 0 else " e " + por_extenso(n % 100))
    if n < 1_000_000:
        mil = "mil" if n // 1000 == 1 else por_extenso(n // 1000) + " mil"
        return mil + ("" if n % 1000 == 0 else " e " + por_extenso(n % 1000))
    return str(n)


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"(?<=\d)\.(?=\d{3})", "", t)  # 4.600 → 4600
    t = re.sub(r"\d+", lambda m: por_extenso(int(m.group())), t)
    return re.sub(r"[^a-z0-9 ]+", "", t).strip()


def e_regravacao(a: str, b: str) -> bool:
    """`a` é uma tentativa descartada se `b` (dita logo depois) começa do mesmo jeito."""
    if not a or not b or len(a.split()) > len(b.split()) + 1:
        return False
    if b.startswith(a):
        return True
    return SequenceMatcher(None, a, b[:len(a) + 3]).ratio() >= 0.72


def detectar_regravacoes(fs: list[dict]) -> set[int]:
    descartar = set()
    for i, fi in enumerate(fs):
        a = normalizar(fi["texto"])
        for j in range(i + 1, min(i + 5, len(fs))):
            if fs[j]["i"] - fi["f"] > JANELA_REGRAVACAO:
                break
            if e_regravacao(a, normalizar(fs[j]["texto"])):
                descartar.add(i)
                break
    return descartar


# ---------------------------------------------------------------- com roteiro
def posicao_no_roteiro(fala: dict, roteiro: list[str]) -> tuple[int, int, float]:
    """Melhor trecho do roteiro (índices de palavra início/fim) para esta fala + nota de 0 a 1."""
    ws = [normalizar(w["p"]) for w in fala["palavras"] if normalizar(w["p"])]
    alvo = " ".join(ws)
    n = len(ws)
    melhor = (0, 0, 0.0)
    for tam in {max(1, n - 2), n, n + 2}:
        for i in range(0, max(1, len(roteiro) - tam + 1)):
            nota = SequenceMatcher(None, alvo, " ".join(roteiro[i:i + tam])).ratio()
            if nota > melhor[2]:
                melhor = (i, i + tam, nota)
    return melhor


def filtrar_com_roteiro(fs: list[dict], texto_roteiro: str, descartar: set[int]) -> tuple[set[int], set[int], set[int]]:
    """Devolve (falas fora do roteiro, releituras detectadas pela POSIÇÃO no texto, "regravações" que eram fala nova):
    se duas falas leem o mesmo trecho do roteiro, fica a última."""
    roteiro = [p for p in (normalizar(x) for x in texto_roteiro.split()) if p]
    pos = {k: posicao_no_roteiro(f, roteiro) for k, f in enumerate(fs) if k not in descartar}
    # Falas curtas enganam a comparação aproximada ("oi" ~ "o" = 67%): exigem quase igualdade.
    def minimo(k: int) -> float:
        return 0.5 if len(normalizar(fs[k]["texto"])) >= 15 else 0.85
    fora = {k for k, (_, _, nota) in pos.items() if nota < minimo(k)}
    novos: set[int] = set()
    ordem = [k for k in sorted(pos) if k not in fora]
    for a, k in enumerate(ordem):
        ini_k, fim_k, _ = pos[k]
        for j in ordem[a + 1:a + 6]:
            ini_j, fim_j, _ = pos[j]
            if fs[j]["i"] - fs[k]["f"] > JANELA_REGRAVACAO:
                break
            if ini_j <= ini_k + 1 and fim_j > ini_k:  # j relê o começo do trecho de k
                novos.add(k)
                break
    # Resgate pela POSIÇÃO: fala curta que cai exatamente num buraco do roteiro entre duas falas mantidas é a fala
    # que falta — mesmo com o nome transcrito errado ("e a Ashlesh" → "Yavaş, Lash") ou palavra única ("Simples.").
    # "regravação" só pela semelhança do texto erra com frases que começam igual ("a encarnação do medo" ×
    # "a encarnação da alegria"): elas também passam pelo resgate
    regravadas = set(descartar)
    resgatadas, de_regravacao = 0, set()
    for k in sorted(fora | novos | regravadas, key=lambda k: fs[k]["i"]):
        mantidas = sorted((x for x in pos if x not in fora and x not in novos and x not in regravadas),
                          key=lambda x: fs[x]["i"])
        ant = [x for x in mantidas if fs[x]["f"] <= fs[k]["i"] + 0.05]
        dep = [x for x in mantidas if fs[x]["i"] >= fs[k]["f"] - 0.05]
        if not ant or not dep:
            continue
        p, n = ant[-1], dep[0]
        buraco = roteiro[pos[p][1]:pos[n][0]]
        palavras_k = [w for w in normalizar(fs[k]["texto"]).split() if w]
        if not buraco or len(buraco) > len(palavras_k) + 4:
            continue
        # encaixe: o pedaço do buraco que mais se parece com a fala (o resto do buraco fica para a próxima)
        alvo, base = " ".join(palavras_k), pos[p][1]
        nota, i0, i1 = max((SequenceMatcher(None, alvo, " ".join(buraco[i:j])).ratio(), i, j)
                           for i in range(len(buraco)) for j in range(i + 1, len(buraco) + 1))
        if nota >= 0.3 or len(buraco) <= 3:
            if len(buraco) <= 3 and nota < 0.3:
                i0, i1 = 0, len(buraco)
            fora.discard(k)
            novos.discard(k)
            if k in regravadas:
                regravadas.discard(k)
                de_regravacao.add(k)
            pos[k] = (base + i0, base + i1, nota)
            resgatadas += 1
    if resgatadas:
        print(f"  {resgatadas} fala(s) resgatada(s) pela posição no roteiro", flush=True)
    return fora, novos, de_regravacao


def divergencias(lido: str, texto_roteiro: str) -> list[dict]:
    """Palavras lidas diferentes do roteiro (não são cortadas — só avisadas no relatório)."""
    hifen = lambda t: re.sub(r"\s*-\s*", "", t)  # "paralisá -las" (Whisper) == "paralisá-las"
    a = [w for w in (normalizar(x) for x in hifen(texto_roteiro).split()) if w]
    b = [w for w in (normalizar(x) for x in hifen(lido).split()) if w]
    saida = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            saida.append({"roteiro": " ".join(a[i1:i2]) or "-", "lido": " ".join(b[j1:j2]) or "-"})
    return saida


# ---------------------------------------------------------------- montagem
def montar(a: np.ndarray, fs: list[dict], descartar: set[int]) -> tuple[np.ndarray, list[dict], dict]:
    mantidas = [f for k, f in enumerate(fs) if k not in descartar]
    pedacos, mapa, pausas = [], [], []
    cursor = 0.0
    fade = int(0.01 * SR)
    for k, f in enumerate(mantidas):
        ini, fim = refinar_bordas(a, f["i"], f["f"])
        if k > 0:
            ant = mantidas[k - 1]
            fim_frase = ant["texto"].rstrip().endswith((".", "!", "?"))
            houve_regravacao = any(fs[d]["i"] > ant["f"] and fs[d]["f"] < f["i"] for d in descartar)
            _, fim_ant = refinar_bordas(a, ant["i"], ant["f"])
            original = max(0.0, ini - fim_ant)
            if houve_regravacao:
                alvo = PAUSA_APOS_REGRAVACAO[0 if fim_frase else 1]
            else:
                alvo = max(PAUSA_MIN, min(original, PAUSA_MAX_FIM_FRASE if fim_frase else PAUSA_MAX_MEIO))
            if original - alvo > 0.05 or houve_regravacao:
                pausas.append({"em": round(fim_ant, 2), "de": round(original, 2), "para": round(alvo, 2)})
            # usa o FINAL da pausa original (respiração antes da frase), não silêncio artificial
            p0 = max(fim_ant, ini - alvo)
            pedacos.append(a[int(p0 * SR):int(ini * SR)])
            cursor += ini - p0
        trecho = a[int(ini * SR):int(fim * SR)].copy()
        trecho[:fade] *= np.linspace(0, 1, fade)
        trecho[-fade:] *= np.linspace(1, 0, fade)
        pedacos.append(trecho)
        for w in f["palavras"]:
            mapa.append({"t": w["p"], "i": round(cursor + (w["i"] - ini), 3), "f": round(cursor + (w["f"] - ini), 3)})
        cursor += fim - ini
    info = {"pausas_encurtadas": pausas}
    return np.concatenate(pedacos), mapa, info


def normalizar_volume(entrada: Path, saida: Path, passa_alta: bool = False) -> dict:
    """Só VOLUME: loudnorm linear em duas passadas (-14 LUFS, pico -1.5 dBTP) — não mexe no timbre.
    A voz do Felipe já chega tratada pelos filtros dele; o passa-alta (tira ronco < 70 Hz) é opcional."""
    alvo = "I=-14:TP=-1.5:LRA=11"
    pre = "highpass=f=70," if passa_alta else ""
    medida = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(entrada), "-af",
                             f"{pre}loudnorm={alvo}:print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    m, _ = json.JSONDecoder().raw_decode(medida[medida.rindex("{"):])  # há texto depois do JSON
    filtro = (f"{pre}loudnorm={alvo}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(entrada), "-af", filtro, "-ar", str(SR), str(saida)], check=True)
    return {"lufs_antes": float(m["input_i"]), "pico_antes": float(m["input_tp"])}


def limpar(gravacao: Path, pasta: Path, roteiro: str | None = None, passa_alta: bool = False) -> dict:
    preparar_ffmpeg()
    pasta.mkdir(parents=True, exist_ok=True)
    a = carregar(gravacao)
    fs = transcrever(a)
    removidos = [{**d, "motivo": "recomeço sem pausa"} for f in fs if (d := recomeco_interno(f))]
    descartar = detectar_regravacoes(fs)
    motivo = {k: "regravação" for k in descartar}
    if roteiro:
        fora, releitura, nao_era = filtrar_com_roteiro(fs, roteiro, descartar)
        descartar -= nao_era  # "regravação" que era a próxima frase do roteiro
        motivo = {k: m for k, m in motivo.items() if k not in nao_era}
        motivo |= {k: "fora do roteiro" for k in fora} | {k: "releitura (pelo roteiro)" for k in releitura}
        descartar |= fora | releitura
    removidos += [{**fs[k], "motivo": m} for k, m in motivo.items()]
    audio, mapa, info = montar(a, fs, descartar)

    tmp = pasta / "_sem_volume.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(tmp)],
                   input=audio.astype(np.float32).tobytes(), check=True)
    volume = normalizar_volume(tmp, pasta / "limpa.wav", passa_alta)
    tmp.unlink()

    relatorio = {
        "duracao_original": round(len(a) / SR, 2),
        "duracao_limpa": round(len(audio) / SR, 2),
        "removidos": sorted([{"i": round(r["i"], 2), "f": round(r["f"], 2), "texto": r["texto"], "motivo": r["motivo"]}
                             for r in removidos], key=lambda x: x["i"]),
        **info,
        **volume,
        "frases_mantidas": [f["texto"] for k, f in enumerate(fs) if k not in descartar],
    }
    if roteiro:
        relatorio["divergencias_do_roteiro"] = divergencias(" ".join(relatorio["frases_mantidas"]), roteiro)
    (pasta / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / "palavras.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    return relatorio


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gravacao")
    ap.add_argument("pasta")
    ap.add_argument("--roteiro", help="arquivo .txt com o roteiro lido (recomendado)")
    ap.add_argument("--passa-alta", action="store_true", help="tira ronco < 70 Hz (só se gravar SEM os filtros de voz)")
    a = ap.parse_args()
    roteiro = Path(a.roteiro).read_text(encoding="utf-8") if a.roteiro else None
    r = limpar(Path(a.gravacao), Path(a.pasta), roteiro, a.passa_alta)
    print(f"{r['duracao_original']}s -> {r['duracao_limpa']}s | LUFS antes {r['lufs_antes']}")
    print("Removidos:")
    for x in r["removidos"]:
        print(f"  [{x['i']:6.2f}-{x['f']:6.2f}] {x['texto']}  <- {x['motivo']}")
    print(f"Pausas encurtadas: {len(r['pausas_encurtadas'])}")
    for p in r["pausas_encurtadas"]:
        print(f"  em {p['em']:6.2f}s: {p['de']:.2f}s -> {p['para']:.2f}s")
    print("Texto final:", " | ".join(r["frases_mantidas"]))
    if "divergencias_do_roteiro" in r:
        print("Lido diferente do roteiro (não cortado, só aviso):")
        for d in r["divergencias_do_roteiro"]:
            print(f"  roteiro: '{d['roteiro']}'  ->  lido: '{d['lido']}'")


if __name__ == "__main__":
    main()
