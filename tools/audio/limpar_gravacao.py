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

PAUSA_MAX_FIM_FRASE = 0.45  # + bordas ≈ 0,6 s de silêncio real (0,80 deixava ~1 s: quebrava o ritmo — Felipe, 2026-10-19)
PAUSA_MAX_MEIO = 0.28
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


def piso_apos_corte(a: np.ndarray, fim_cortado: float, ini_fala: float, limiar: float = -35.0) -> float:
    """Onde a fala pode começar depois de um começo cortado ("1, 2, 3," + "Urgot"): o Whisper marca o fim do "três" ~150 ms
    cedo, e refinar_bordas (que atravessa silêncios < 120 ms para trás) pegava o "ssss" que sobra dele. Aqui: o 1º ponto,
    depois do fim marcado, em que o volume fica abaixo de `limiar` por 40 ms seguidos."""
    t = fim_cortado
    while t < ini_fala:
        if all(nivel_db(a, t + k * 0.01) < limiar for k in range(4)):
            return t
        t += 0.01
    return fim_cortado


def cauda_abandonada(fs: list[dict], k: int) -> dict | None:
    """Fala que termina numa frase largada no meio ("…foi levado à presença da Barão Voz, enquanto ela com...") e que o
    Felipe releu logo depois ("Enquanto ela cortava…"): tira só a frase largada e fica com o que veio antes. O sinal é o
    Whisper escrever a última palavra truncada ("com...") e as palavras anteriores da cauda repetirem o começo de uma das
    3 falas seguintes. Devolve a parte tirada (e encurta `fs[k]`)."""
    f = fs[k]
    ws = f["palavras"]
    if len(ws) < 6 or not ws[-1]["p"].endswith(("...", "…")):
        return None
    norm = [normalizar(w["p"]) for w in ws]
    for t in range(2, 7):
        cauda = norm[-t:]
        for j in range(k + 1, min(k + 4, len(fs))):
            if fs[j]["i"] - f["f"] > 4.0:
                break
            prox = [normalizar(w["p"]) for w in fs[j]["palavras"][:t]]
            if len(prox) < t or cauda[:-1] != prox[:-1] or not cauda[-1]:
                continue
            if SequenceMatcher(None, cauda[-1], prox[-1][:len(cauda[-1])]).ratio() >= 0.6:
                tirada = {"palavras": ws[-t:], "i": ws[-t]["i"], "f": f["f"], "texto": " ".join(w["p"] for w in ws[-t:])}
                f["palavras"] = ws[:-t]
                f["f"] = f["palavras"][-1]["f"]
                f["texto"] = " ".join(w["p"] for w in f["palavras"])
                return tirada
    return None


def inicio_sem_respiracao(a: np.ndarray, ini: float, fim: float, voz: float = -22.0, minimo: float = 0.30,
                          folga: float = 0.12) -> float:
    """Respiração antes da fala: o Whisper a cola na 1ª palavra ("De" = 0,8 s) e refinar_bordas a mantém (é som acima de
    -45 dB). Ela fica entre -45 e ~-30 dB, a fala fica acima de -22. Se do começo da fala até a voz de verdade há `minimo`
    s ou mais desse som mais baixo, o começo vai para `folga` s antes da voz (sobra para a consoante). Vale a regra do
    Felipe (2026-11-25): respiração acentuada no começo da frase sai; pausa continua a mesma (ver `montar`)."""
    t = ini
    limite = min(ini + 1.2, fim - 0.15)  # a voz tem de estar DENTRO da fala: senão pegava a fala seguinte e o trecho ficava vazio
    while t < limite:
        if all(nivel_db(a, t + k * 0.01) > voz for k in range(4)):
            return t - folga if t - ini >= minimo else ini
        t += 0.01
    return ini


def refinar_bordas(a: np.ndarray, ini: float, fim: float, limiar: float = -45.0) -> tuple[float, float]:
    """O Whisper erra as bordas em dezenas (às vezes centenas) de ms. Estende até a última voz por perto, ATRAVESSANDO
    silêncios curtos (< 120 ms) dentro da palavra — "DN" = "dê … ene": o Whisper termina no "dê" e a parada
    antiga, no primeiro silêncio, cortava o "ene"."""
    passo, buraco = 0.01, 0.12

    def ultima_voz(t0: float, direcao: int, alcance: float) -> float:
        ultimo, silencio, t = t0, 0.0, t0
        while abs(t - t0) < alcance:
            t += direcao * passo
            if nivel_db(a, t) > limiar:
                ultimo, silencio = t, 0.0
            else:
                silencio += passo
                if silencio > buraco:
                    break
        return ultimo

    i = min(ini - 0.04, ultima_voz(ini, -1, 0.30) - 0.03)
    f = max(fim + 0.06, ultima_voz(fim, +1, 0.45) + 0.05)
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
def nomes_do_roteiro(roteiro: str | None, maximo: int = 60) -> str:
    """Nomes próprios do roteiro (palavra com maiúscula no meio da frase, ou título de uma palavra só numa linha) como
    dicas para o Whisper: sem isso "Sion" virava "Ezi, Staio" (vídeo 6, 2026-11-25). Ordem de aparição, sem repetir."""
    if not roteiro:
        return ""
    titulos: list[str] = []
    achados: list[str] = []
    for linha in roteiro.splitlines():
        linha = linha.strip()
        if re.fullmatch(r"[A-ZÀ-Ý][\w'’.-]+( [A-ZÀ-Ý][\w'’.-]+)?", linha):  # título do capítulo ("Dr. Mundo")
            titulos.append(linha)
        achados += re.findall(r"(?<=[a-zà-ÿ,;:] )([A-ZÀ-Ý][\wà-ÿ'’-]{2,})", linha)
    freq: dict[str, int] = {}
    forma: dict[str, str] = {}
    for n in achados:
        freq[n.lower()] = freq.get(n.lower(), 0) + 1
        forma.setdefault(n.lower(), n)
    # títulos sempre; o resto só se aparece 2+ vezes (palavra comum com maiúscula aparece uma vez), mais frequentes antes
    fortes = [forma[k] for k, c in sorted(freq.items(), key=lambda kv: -kv[1]) if c >= 2]
    vistos: list[str] = []
    for n in titulos + fortes:
        if n.lower() not in (v.lower() for v in vistos):
            vistos.append(n)
    return ", ".join(vistos[:maximo])


def transcrever(a: np.ndarray, roteiro: str | None = None) -> list[dict]:
    """Transcreve CADA trecho de fala isoladamente. Vendo o áudio inteiro, o Whisper 'corrige' a
    leitura e omite falsos começos; isolado, ele é obrigado a transcrever o que ouviu."""
    for p in (Path(sys.prefix) / "Lib" / "site-packages" / "nvidia").glob("*/bin"):
        os.add_dll_directory(str(p))
        os.environ["PATH"] = f"{p}{os.pathsep}{os.environ['PATH']}"
    from faster_whisper import WhisperModel

    modelo = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    dicas = ", ".join(x for x in (GLOSSARIO, nomes_do_roteiro(roteiro)) if x)
    a16 = reamostrar_16k(a)
    falas = []
    for ini, fim in trechos_de_fala(a):
        pedaco = a16[int(ini * 16000):int(fim * 16000)]
        segs, _ = modelo.transcribe(pedaco, language="pt", word_timestamps=True, vad_filter=False,
                                    condition_on_previous_text=False, temperature=0.0, hotwords=dicas)
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


def contagem_inicial(fala: dict, roteiro: str | None) -> dict | None:
    """Contagem de cabeça antes do capítulo ("1, 2, 3, Urgot"; "1, 2, 3, 4" sozinho): tira os números do começo da fala.
    Só vale se os números aparecem em ordem a partir de 1 (2 ou mais) e o roteiro NÃO tem essa contagem. Devolve a parte
    tirada; se a fala inteira era contagem, `fala["palavras"]` fica vazia (quem chama descarta a fala)."""
    ws = fala["palavras"]
    n = 0
    while n < len(ws) and normalizar(ws[n]["p"]) == UNIDADES[n + 1 if n + 1 < len(UNIDADES) else 0] and n < 5:
        n += 1
    if n < 2 or (roteiro and " ".join(UNIDADES[1:n + 1]) in normalizar(roteiro)):
        return None
    tirada = {"palavras": ws[:n], "i": fala["i"], "f": ws[n - 1]["f"], "texto": " ".join(w["p"] for w in ws[:n])}
    fala["palavras"] = ws[n:]
    if fala["palavras"]:
        fala["i"] = fala["palavras"][0]["i"]
        fala["texto"] = " ".join(w["p"] for w in fala["palavras"])
    return tirada


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
    if len(a.split()) < 2:
        return False  # palavra solta ("Urgot" = título do capítulo) nunca é "recomeço" de "O Urgot nasceu…" só por parecer
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
            parecidas = SequenceMatcher(None, normalizar(fs[k]["texto"]), normalizar(fs[j]["texto"])).ratio() >= 0.5
            if ini_j <= ini_k + 1 and fim_j > ini_k and parecidas:  # j relê o começo do trecho de k
                novos.add(k)  # ("Bora lá" × "vamos lá, vamos lá" não é releitura: é comentário solto)
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
    ops = SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    # Gravação PARCIAL (só uma seção do roteiro): o que ficou antes/depois do trecho lido não é "leitura diferente",
    # é texto ainda não gravado (vídeo 6, 2026-11-25: 3 blocos de ~1000 palavras "lidos" como "-"). Âncoras = trechos
    # iguais de 5+ palavras; só se comparam as palavras do roteiro entre a primeira e a última âncora.
    ancoras = [(i1, i2) for op, i1, i2, j1, j2 in ops if op == "equal" and i2 - i1 >= 5]
    ini, fim = (ancoras[0][0], ancoras[-1][1]) if ancoras else (0, len(a))
    saida = []
    for op, i1, i2, j1, j2 in ops:
        if op != "equal" and i1 >= ini and i2 <= fim:
            saida.append({"roteiro": " ".join(a[i1:i2]) or "-", "lido": " ".join(b[j1:j2]) or "-"})
    divergencias.nao_gravado = len(a) - (fim - ini)  # palavras do roteiro fora do trecho gravado
    return saida


# ---------------------------------------------------------------- montagem
def montar(a: np.ndarray, fs: list[dict], descartar: set[int]) -> tuple[np.ndarray, list[dict], dict]:
    mantidas = [f for k, f in enumerate(fs) if k not in descartar]
    pedacos, mapa, pausas = [], [], []
    cursor = 0.0
    fade = int(0.01 * SR)
    for k, f in enumerate(mantidas):
        if f.get("manual"):  # corte à mão no mini editor: exatamente o que o Felipe marcou, sem ajuste automático
            ini, fim = f["i"], f["f"]
            ini_pausa = ini
        else:
            ini, fim = refinar_bordas(a, f["i"], f["f"])
            ini = max(ini, f.get("piso", 0.0))  # começo cortado: não volta para dentro da palavra cortada
            if "teto" in f:
                fim = min(fim, f["teto"])  # fim cortado (frase largada): não avança sobre a respiração/palavra cortada
            ini_pausa = ini  # a pausa antes da fala termina aqui (antes da respiração, que é cortada)
            ini = max(ini, inicio_sem_respiracao(a, ini, fim))
        if k > 0:
            ant = mantidas[k - 1]
            fim_frase = ant["texto"].rstrip().endswith((".", "!", "?"))
            houve_regravacao = any(fs[d]["i"] > ant["f"] and fs[d]["f"] < f["i"] for d in descartar)
            fim_ant = ant["f"] if ant.get("manual") else refinar_bordas(a, ant["i"], ant["f"])[1]
            original = max(0.0, ini_pausa - fim_ant)
            if houve_regravacao:
                alvo = PAUSA_APOS_REGRAVACAO[0 if fim_frase else 1]
            else:
                alvo = max(PAUSA_MIN, min(original, PAUSA_MAX_FIM_FRASE if fim_frase else PAUSA_MAX_MEIO))
            if original - alvo > 0.05 or houve_regravacao:
                pausas.append({"em": round(fim_ant, 2), "de": round(original, 2), "para": round(alvo, 2)})
            # usa o FINAL da pausa original (respiração antes da frase), não silêncio artificial
            p0 = max(fim_ant, ini_pausa - alvo)
            pedacos.append(a[int(p0 * SR):int(ini_pausa * SR)])
            cursor += ini_pausa - p0
        fim = max(fim, ini + 0.05)  # teto/piso/respiração nunca deixam o trecho vazio
        trecho = a[int(ini * SR):int(fim * SR)].copy()
        fd = min(fade, len(trecho) // 2)
        if fd:
            trecho[:fd] *= np.linspace(0, 1, fd)
            trecho[-fd:] *= np.linspace(1, 0, fd)
        pedacos.append(trecho)
        for w in f["palavras"]:
            # palavra que o Whisper começou antes do corte (respiração colada nela): começa no corte, não antes
            mapa.append({"t": w["p"], "i": round(cursor + max(0.0, w["i"] - ini), 3),
                         "f": round(cursor + max(0.0, w["f"] - ini), 3)})
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
    fs = transcrever(a, roteiro)
    removidos = []
    contagens = set()
    for k, f in enumerate(fs):
        if d := contagem_inicial(f, roteiro):
            removidos.append({**d, "motivo": "contagem do capítulo"})
            f["inicio_cortado"] = d
            if not f["palavras"]:
                contagens.add(k)  # a fala era só a contagem: sai inteira
                f["palavras"], f["texto"] = d["palavras"], d["texto"]
                f["inicio_cortado"] = None
                removidos.pop()
            continue
        if d := recomeco_interno(f):
            removidos.append({**d, "motivo": "recomeço sem pausa"})
            f["inicio_cortado"] = d  # o Felipe pode devolver na linha do tempo
    for k, f in enumerate(fs):
        if d := cauda_abandonada(fs, k):
            removidos.append({**d, "motivo": "frase largada no fim"})
            f["fim_cortado"] = d
            f["teto"] = f["f"] + 0.10
        if f.get("inicio_cortado"):
            f["piso"] = piso_apos_corte(a, f["inicio_cortado"]["f"], f["i"])
    descartar = detectar_regravacoes(fs) | contagens
    motivo = {k: "regravação" for k in descartar} | {k: "contagem do capítulo" for k in contagens}
    if roteiro:
        fora, releitura, nao_era = filtrar_com_roteiro(fs, roteiro, descartar)
        descartar -= nao_era  # "regravação" que era a próxima frase do roteiro
        motivo = {k: m for k, m in motivo.items() if k not in nao_era}
        motivo |= {k: "fora do roteiro" for k in fora} | {k: "releitura (pelo roteiro)" for k in releitura}
        descartar |= fora | releitura | contagens  # contagem nunca é "resgatada" pela posição no roteiro
        motivo |= {k: "contagem do capítulo" for k in contagens}
    # todas as falas, cortadas ou não: a linha do tempo do painel corta/recupera sem transcrever de novo
    (pasta / "falas.json").write_text(json.dumps(
        [{"id": k, "i": f["i"], "f": f["f"], "texto": f["texto"], "palavras": f["palavras"], "cortada": k in descartar,
          "motivo": motivo.get(k), "inicio_cortado": f.get("inicio_cortado"), "fim_cortado": f.get("fim_cortado")}
         for k, f in enumerate(fs)],
        ensure_ascii=False), encoding="utf-8")
    removidos += [{**fs[k], "motivo": m} for k, m in motivo.items()]
    rel = _finalizar(a, fs, descartar, removidos, pasta, roteiro, passa_alta)
    (pasta / "decisoes_aplicadas.json").write_text("{}", encoding="utf-8")  # limpeza nova: nenhuma escolha aplicada ainda
    return rel


def remontar(gravacao: Path, pasta: Path, roteiro: str | None, decisoes: dict[str, str],
             passa_alta: bool = False) -> dict:
    """Refaz o áudio limpo com as decisões do Felipe na linha do tempo ({id: "manter" | "cortar" | "inicio"}),
    a partir das falas já transcritas (falas.json): segundos, não minutos."""
    preparar_ffmpeg()
    a = carregar(gravacao)
    falas = json.loads((pasta / "falas.json").read_text(encoding="utf-8"))
    fs, descartar, removidos = [], set(), []
    for x in falas:
        f = {"i": x["i"], "f": x["f"], "texto": x["texto"], "palavras": list(x["palavras"])}
        d = decisoes.get(str(x["id"]))
        if manual := decisoes.get(f"m{x['id']}"):
            # corte à mão (mini editor): vai EXATAMENTE de i a f; ignora cortes automáticos de começo/fim e as bordas
            mi, mf = (float(v) for v in manual.split(":"))
            f["palavras"] = [w for w in (list(x["palavras"]) + list((x.get("inicio_cortado") or {}).get("palavras", []))
                                         + list((x.get("fim_cortado") or {}).get("palavras", [])))
                             if mi - 0.02 <= (w["i"] + w["f"]) / 2 <= mf + 0.02]
            f["palavras"].sort(key=lambda w: w["i"])
            f["i"], f["f"], f["manual"] = mi, mf, True
            f["texto"] = " ".join(w["p"] for w in f["palavras"]) or x["texto"]
            fs.append(f)
            continue
        if x.get("inicio_cortado"):
            ic = x["inicio_cortado"]
            if d == "inicio":  # devolve o começo que o "recomeço sem pausa" tinha tirado
                f["palavras"] = ic["palavras"] + f["palavras"]
                f["i"] = ic["i"]
                f["texto"] = " ".join(w["p"] for w in f["palavras"])
            else:
                removidos.append({**ic, "motivo": "recomeço sem pausa"})
                f["piso"] = piso_apos_corte(a, ic["f"], f["i"])
        if x.get("fim_cortado"):
            fc = x["fim_cortado"]
            if d == "fim":  # devolve a frase largada no fim
                f["palavras"] = f["palavras"] + fc["palavras"]
                f["f"] = fc["f"]
                f["texto"] = " ".join(w["p"] for w in f["palavras"])
            else:
                removidos.append({**fc, "motivo": "frase largada no fim"})
                f["teto"] = x["f"] + 0.10
        cortada = x["cortada"] if d not in ("manter", "cortar") else d == "cortar"
        if cortada:
            descartar.add(len(fs))
            removidos.append({**f, "motivo": "cortado por você" if d == "cortar" else x.get("motivo") or "cortada"})
        fs.append(f)
    rel = _finalizar(a, fs, descartar, removidos, pasta, roteiro, passa_alta)
    # o que ESTE áudio já tem aplicado: o painel compara com as escolhas atuais para mostrar só o que está pendente
    (pasta / "decisoes_aplicadas.json").write_text(json.dumps(decisoes, ensure_ascii=False), encoding="utf-8")
    return rel


def _finalizar(a: np.ndarray, fs: list[dict], descartar: set[int], removidos: list[dict], pasta: Path,
               roteiro: str | None, passa_alta: bool) -> dict:
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
        relatorio["palavras_roteiro_nao_gravadas"] = getattr(divergencias, "nao_gravado", 0)
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
