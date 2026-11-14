# Amplia o banco de SFX pela API do Freesound (token do .env: FREESOUND_API_KEY; nunca impresso nem gravado).
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\freesound.py buscar      # busca, baixa prévias, mede, filtra, escolhe
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\freesound.py folhas      # espectrogramas dos escolhidos (exemplo/saida/)
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\freesound.py baixar      # só baixa o que freesound.json lista (sem busca/chave)
#
# Regras:
# - licença: só CC0 (preferida) e CC BY (crédito automático: autor/url/licença no catálogo → Banco.creditos → descrição).
#   CC BY-NC e Sampling+ ficam de fora (o canal é monetizado). A licença é conferida pela URL que a API devolve.
# - áudio: a prévia "hq" (ogg ~192 kbps; mp3 128 kbps de reserva). O original exigiria OAuth2 por usuário.
# - cache das prévias FORA do Git: dados/comum/freesound_cache/<id>.<ext>. O banco continua fora do Git; o que fica no
#   Git é freesound.json (ids, autor, licença, url, url da prévia, medidas): gerar.py regera sem buscar e sem chave.
# - rejeição automática: nome/tags/descrição com voz, música ou marca; corte (clipping) no arquivo; silêncio demais;
#   ruído de fundo alto (sons que deviam ser limpos); banda estreita (gravação ruim) onde o som devia ter agudos;
#   não chega ao loudness da categoria sem esmagar; estéreo desequilibrado; riser sem crescendo; e o CLAP local
#   (laion/larger_clap_general) classificando fala, canto ou música. Entre os aprovados, ganha quem o CLAP acha mais
#   parecido com a descrição da categoria, no máximo 3 do mesmo autor por categoria.
# - API: 1 requisição por ~1,1 s (limite do Freesound: 60/min, 2000/dia); a busca toda usa ~80 requisições.
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gerar  # noqa: E402
import medir  # noqa: E402

LISTA = AQUI / "freesound.json"
CACHE = gerar.DADOS / "comum" / "freesound_cache"     # fora do Git (no worktree: o do repositório principal)
SAIDA = AQUI / "exemplo" / "saida" / "freesound"
API = "https://freesound.org/apiv2/search/text/"

# total desejado por categoria (existentes + novos). Sobra acima do mínimo (15 / 8) para o Felipe poder reprovar alguns.
META = {"impacto": 17, "riser": 17, "whoosh": 17, "sino": 17, "alerta": 17, "pop": 17, "clique": 17, "tecla": 17}
META_NOVAS = 10

# categoria -> buscas, faixa de duração do original (s), descrição para o CLAP, recorte, limites dos filtros.
#   claro=True: som que devia ser limpo (ruído de fundo <= -35 dB do pico) e com agudos (rolloff 95% >= 5 kHz).
CONF: dict[str, dict] = {
    "impacto": {"q": ["cinematic impact hit", "trailer hit impact", "impact boom hit", "hit impact designed"],
                "dur": (0.4, 6), "clap": "a powerful cinematic impact hit sound effect", "claro": False},
    "riser": {"q": ["riser cinematic", "tension riser", "uplifter riser sweep", "reverse cymbal", "riser build up"],
              "dur": (1.2, 10), "clap": "a rising cinematic riser building tension, crescendo", "claro": False},
    "whoosh": {"q": ["whoosh", "swoosh fast", "whoosh transition", "air whoosh pass"],
               "dur": (0.3, 4), "clap": "a fast whoosh of air passing by, transition sound effect", "claro": False},
    "sino": {"q": ["bell ding", "single chime", "ding notification", "glass ding", "triangle hit"],
             "dur": (0.3, 6), "clap": "a single clear bell ding chime", "claro": True},
    "alerta": {"q": ["alert beep", "error beep", "warning beep", "buzzer short", "ui alert"],
               "dur": (0.15, 4), "clap": "a short electronic alert beep, warning signal", "claro": True},
    "pop": {"q": ["pop ui", "bubble pop", "cork pop", "pop sound effect", "plop"],
            "dur": (0.05, 2), "clap": "a short soft pop sound effect", "claro": True},
    "clique": {"q": ["click ui", "mouse click", "button click", "switch click", "click"],
               "dur": (0.03, 2), "clap": "a single short crisp click of a button", "claro": True, "recorte": ("fatia", 0)},
    "tecla": {"q": ["keyboard key press", "typewriter key", "mechanical keyboard key", "keyboard typing", "keystroke"],
              "dur": (0.05, 8), "clap": "a single key press on a computer keyboard", "claro": True, "recorte": ("fatia", 0)},
    # ---- novas
    "motor": {"q": ["race car pass by", "racing car fly by", "race car accelerating", "formula car engine",
                    "car engine rev distant", "motorsport pass by"],
              "dur": (1.5, 30), "clap": "a racing car engine roaring past at high speed in the distance", "claro": False},
    "pneu": {"q": ["tire screech", "tyre skid", "brake squeal", "car skid", "car braking"],
             "dur": (0.5, 10), "clap": "car tires screeching and skidding while braking hard", "claro": False},
    "radio": {"q": ["radio static", "walkie talkie beep", "radio squelch", "radio noise burst", "radio interference"],
              "dur": (0.2, 6), "clap": "short radio static noise and squelch beep, no voice", "claro": False},
    "cronometro": {"q": ["clock tick", "stopwatch click", "timer tick", "ticking clock", "stopwatch"],
                   "dur": (0.05, 12), "clap": "a single mechanical clock tick", "claro": True, "recorte": ("fatia", 0)},
    "grafico": {"q": ["ui swoosh", "interface whoosh short", "swipe sound", "short swish", "ui transition"],
                "dur": (0.15, 2), "clap": "a short light user interface swish, data sliding in", "claro": True},
    "obturador": {"q": ["camera shutter", "camera click shutter", "dslr shutter", "photo camera"],
                  "dur": (0.05, 3), "clap": "a photo camera shutter click", "claro": True},
    "whoosh_grave": {"q": ["deep whoosh", "low whoosh cinematic", "bass whoosh", "heavy swoosh", "cinematic whoosh deep"],
                     "dur": (0.5, 5), "clap": "a deep heavy low cinematic whoosh", "claro": False},
    "boom": {"q": ["sub boom", "sub drop", "low boom bass", "cinematic boom deep", "deep boom"],
             "dur": (0.5, 8), "clap": "a deep sub bass boom, low frequency rumble hit", "claro": False},
    "box": {"q": ["impact wrench", "air wrench", "pit stop", "pneumatic wrench", "air gun tool garage"],
            "dur": (0.4, 20), "clap": "a pneumatic impact wrench in a garage, pit stop wheel gun", "claro": False},
    "multidao": {"q": ["crowd cheering distant", "stadium crowd", "crowd ambience distant", "crowd cheer applause",
                       "race crowd"],
                 "dur": (4, 60), "clap": "a large distant crowd cheering in a stadium", "claro": False, "voz_ok": True},
}

# palavras que barram o som já pelo texto (voz, música, marca reconhecível)
_VOZ = (r"\b(voices?|vocals?|speech|speak\w*|spoken|talk\w*|words?|sing|singing|songs?|choir|rap|announc\w*|comment\w*|"
        r"narrat\w*|whisper\w*|laugh\w*|scream\w*|female|male|man|woman|kids?|child\w*|baby|cough\w*|breath\w*)\b")
_VOZ_MULTIDAO = r"\b(speech|speak\w*|spoken|talk\w*|announc\w*|comment\w*|narrat\w*|sing|singing|songs?|chant\w*|anthem|choir)\b"
_MUSICA = r"\b(music\w*|melod\w*|chords?|guitar|piano|beats?|drum ?loops?|\d*bpm|stingers?|jingles?|ringtones?|tunes?|orchestra\w*|songs?)\b"
_MARCA = (r"windows|microsoft|apple|iphone|\bios\b|\bmac\b|android|samsung|nokia|skype|whatsapp|discord|facebook|netflix|"
          r"nintendo|mario|zelda|sega|sonic|playstation|xbox|pokemon|star ?wars|lightsaber|thx|mortal kombat|"
          r"tv show|game show|\bf1 ?tv\b|broadcast|\bfate\b|anime|\bmlb\b|\bnfl\b|\bnba\b|\bfifa\b")


def _texto(s: dict) -> str:
    return " ".join([s.get("name", ""), " ".join(s.get("tags", [])), (s.get("description") or "")[:400]]).lower()


def _barrado(s: dict, cat: str) -> str | None:
    t = _texto(s)
    for nome, rx in (("voz", _VOZ_MULTIDAO if CONF[cat].get("voz_ok") else _VOZ), ("musica", _MUSICA), ("marca", _MARCA)):
        m = re.search(rx, t)
        if m:
            return f"{nome}: '{m.group(0)}'"
    return None


def licenca(url: str) -> str | None:
    """'CC0' / 'CC BY 4.0' / 'CC BY 3.0' pela URL da licença; None para NC, Sampling+ e o resto."""
    u = url.lower()
    if "publicdomain/zero" in u:
        return "CC0"
    m = re.search(r"/licenses/by/(\d\.\d)", u)
    return f"CC BY {m.group(1)}" if m else None


def _chave() -> str:
    from dotenv import dotenv_values

    for raiz in (gerar.RAIZ, _raiz_principal()):
        if raiz and (raiz / ".env").is_file():
            v = dotenv_values(raiz / ".env").get("FREESOUND_API_KEY")
            if v:
                return v
    raise SystemExit("FREESOUND_API_KEY não encontrada no .env")


def _raiz_principal() -> Path | None:
    """Raiz do repositório principal (num worktree o .env só existe lá)."""
    try:
        r = subprocess.run(["git", "-C", str(AQUI), "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True)
        return Path(r.stdout.strip()).resolve().parent
    except Exception:
        return None


# ------------------------------------------------------------------------------------------- rede
def baixar_previa(sid: int, url: str) -> Path:
    """Baixa (uma vez) a prévia para o cache. Sem chave: a URL da prévia é pública."""
    import httpx

    ext = url.rsplit(".", 1)[-1]
    p = CACHE / f"{sid}.{ext}"
    if p.is_file() and p.stat().st_size > 1000:
        return p
    CACHE.mkdir(parents=True, exist_ok=True)
    for tentativa in range(3):
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            r.raise_for_status()
            p.write_bytes(r.content)
            time.sleep(0.3)
            return p
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(3)
    return p


class Api:
    def __init__(self) -> None:
        import httpx

        self.cli = httpx.Client(timeout=60)
        self.chave = _chave()
        self.ult = 0.0
        self.n = 0

    def buscar(self, consulta: str, dur: tuple[float, float], pagina: int = 1) -> list[dict]:
        espera = 1.1 - (time.time() - self.ult)
        if espera > 0:
            time.sleep(espera)
        self.ult = time.time()
        self.n += 1
        r = self.cli.get(API, params={
            "query": consulta, "token": self.chave, "page_size": 60, "page": pagina, "sort": "score",
            "filter": f'duration:[{dur[0]} TO {dur[1]}] license:("Creative Commons 0" OR "Attribution")',
            "fields": "id,name,username,license,duration,previews,url,tags,description,avg_rating,num_downloads,channels"})
        if r.status_code == 429:
            time.sleep(60)
            return self.buscar(consulta, dur, pagina)
        r.raise_for_status()
        return r.json().get("results", [])


# ------------------------------------------------------------------------------------------- medidas
def _clipping(x: np.ndarray) -> int:
    """Quantos trechos de >= 3 amostras seguidas grudadas no máximo (arquivo cortado). Só conta se o pico >= 0,95."""
    a = np.abs(x).max(1)
    p = a.max()
    if p < 0.95:
        return 0
    perto = a >= p * 0.997
    d = np.diff(np.concatenate([[0], perto.astype(np.int8), [0]]))
    ini, fim = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    return int(((fim - ini) >= 3).sum())


def _espectro_db(m: np.ndarray, n: int = 4096) -> np.ndarray:
    if len(m) < n:
        m = np.concatenate([m, np.zeros(n - len(m))])
    quadros = np.lib.stride_tricks.sliding_window_view(m, n)[:: n // 2] * np.hanning(n)
    return 10 * np.log10((np.abs(np.fft.rfft(quadros, axis=1)) ** 2).mean(0) + 1e-20)


def _corte_hz(x: np.ndarray) -> float:
    """Frequência acima da qual o espectro médio fica 70 dB abaixo do seu máximo: denuncia gravação de banda
    estreita (telefone, 8/11/22 kHz reamostrado). Som grave mas bem gravado ainda tem algo acima de 8 kHz."""
    s = _espectro_db(x.mean(1))
    s = np.convolve(s, np.ones(9) / 9, mode="same")
    vivo = np.nonzero(s > s.max() - 70)[0]
    return float(vivo[-1] * medir.SR / 4096) if len(vivo) else 0.0


def _chiado(x: np.ndarray) -> tuple[float, float]:
    """(nível dB rel. pico, planura espectral) dos 10% de janelas de 20 ms mais quietas. Ruído de fundo = quieto
    pouco abaixo do pico E de espectro plano (chiado); um bipe contínuo é alto mas tonal (planura baixa)."""
    m = x.mean(1)
    n = 1024
    if len(m) < n * 4:
        return -99.0, 0.0
    q = np.lib.stride_tricks.sliding_window_view(m, n)[::n]
    rms = np.sqrt((q ** 2).mean(1) + 1e-20)
    sel = q[rms <= np.percentile(rms, 10)]
    p = (np.abs(np.fft.rfft(sel * np.hanning(n), axis=1)) ** 2).mean(0)[5:340] + 1e-20   # ~230 Hz a 16 kHz
    plan = float(np.exp(np.log(p).mean()) / p.mean())
    return round(float(20 * np.log10(np.percentile(rms, 10) / rms.max())), 1), round(plan, 3)


def medir_candidato(x: np.ndarray, cat: str) -> tuple[dict, np.ndarray | None]:
    """Medidas + motivo de rejeição (ou None) + o som já preparado e normalizado como o gerar.py fará."""
    c = gerar.CATEGORIAS[cat]
    conf = CONF[cat]
    med: dict = {"clipping": _clipping(x)}
    med["ruido_db"], med["ruido_planura"] = _chiado(x)
    try:
        y = gerar._preparar(x, cat, conf.get("recorte"))
    except IndexError:                                   # "fatia" sem golpe detectável
        return {**med, "motivo": "sem golpe para fatiar"}, None
    med["dur"] = round(len(y) / medir.SR, 3)
    minimo = {"riser": 1.2, "multidao": 3.0, "box": 0.4, "motor": 1.2}.get(cat, 0.25 if cat not in gerar.TRANSIENTES else 0.02)
    if med["clipping"] >= 3:
        return {**med, "motivo": f"clipping ({med['clipping']} trechos)"}, None
    if med["dur"] < minimo:
        return {**med, "motivo": f"curto ({med['dur']} s)"}, None
    env = 20 * np.log10(medir.envelope(y) + 1e-12)
    med["silencio"] = round(float((env < env.max() - 45).mean()), 2)
    if cat not in gerar.TRANSIENTES and med["silencio"] > 0.5:
        return {**med, "motivo": f"silêncio demais ({med['silencio']:.0%})"}, None
    med["corte_hz"] = round(_corte_hz(y))
    if conf["claro"] and med["ruido_db"] > -35 and med["ruido_planura"] > 0.25:
        return {**med, "motivo": f"ruído de fundo alto ({med['ruido_db']} dB, planura {med['ruido_planura']})"}, None
    if cat not in ("boom", "radio") and med["corte_hz"] < 8000:
        return {**med, "motivo": f"banda estreita ({med['corte_hz']} Hz)"}, None
    z = gerar.normalizar(y, c["alvo_lufs_m"], max_reducao_db=6.0 if cat in gerar.TRANSIENTES else 4.0)
    z = np.clip(np.round(z * 32767) / 32768, -1, 1)     # como fica no WAV de 16 bits
    med["lufs_m"] = round(medir.lufs_m_max(z), 2)
    lo, hi = c["faixa_lufs_m"]
    if not lo <= med["lufs_m"] <= hi:
        return {**med, "motivo": f"loudness {med['lufs_m']} fora de [{lo}, {hi}]"}, None
    if medir.pico_verdadeiro_db(z) > -1.0:
        return {**med, "motivo": "pico verdadeiro > -1 dBTP"}, None
    l, r = medir.lufs_canais(z)
    if not (l > -60 and r > -60 and abs(l - r) <= 6.0):
        return {**med, "motivo": f"estéreo desequilibrado (L {l:.1f}, R {r:.1f})"}, None
    if cat == "riser":
        e = 20 * np.log10(medir.envelope(z) + 1e-12)
        k = int(round(gerar._pico_s(z, cat) / 0.01))
        if not (k >= 30 and e[max(0, k - 100)] <= e[max(0, k - 2):k + 3].max() - 4):
            return {**med, "motivo": "riser sem crescendo"}, None
    return med, z


# Revisão por nome/medidas (feita em 2026-11-14 sobre a 1ª escolha automática): sai e o próximo da fila entra.
REVISAO = {
    810174: "batida de carro, não freada", 398111: "raspão/batida, não freada",
    626247: "loop percussivo com bpm (música)", 875968: "'stinger' de interface, musical",
    423118: "tiro de railgun, não whoosh", 833371: "referência a anime (Fate/stay night) no nome",
    169279: "estática de AM em 1010 kHz: pode ter voz/música de estação ao fundo",
    649156: "MLB: arquibancada com possível locutor/sistema de som",
}


class Ouvido:
    """Detector de fala com o Whisper local (large-v3-turbo, o mesmo do resto do sistema): transcreve os primeiros
    30 s do som já preparado; texto confiante (no_speech < 0,5, logprob > -0,8, >= 2 palavras) = tem voz."""

    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        self.m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")

    def fala(self, sid: int, previa: str, cat: str) -> str:
        from scipy.signal import resample_poly

        x = gerar._preparar(medir.ler(str(baixar_previa(sid, previa))), cat, CONF[cat].get("recorte"))
        if len(x) < 0.3 * medir.SR:
            return ""
        a = resample_poly(x.mean(1), 1, 3).astype(np.float32)[: 16000 * 30]
        segs, _ = self.m.transcribe(a, beam_size=1, vad_filter=False, condition_on_previous_text=False)
        txt = [s.text.strip() for s in segs if s.no_speech_prob < 0.5 and s.avg_logprob > -0.8]
        txt = " ".join(t for t in txt if len(re.findall(r"\w+", t)) >= 2)
        return txt


# ------------------------------------------------------------------------------------------- busca
def buscar(sem_rede: bool = False) -> None:
    sys.path.insert(0, str(gerar.RAIZ / "tools" / "audio"))
    from clap import Clap

    existentes = {i: 0 for i in META}
    for _, (cat, _f, _r, _m) in gerar.EXTERNOS.items():
        existentes[cat] = existentes.get(cat, 0) + 1
    for nome, (cat, _fn, _kw) in __import__("sintese").RECEITAS.items():
        existentes[cat] = existentes.get(cat, 0) + 1
    usados = {int(m["url"].rstrip("/").rsplit("/", 1)[-1]) for _, (_c, _f, _r, m) in gerar.EXTERNOS.items()
              if "freesound.org" in m.get("url", "")}
    cache_meta = SAIDA / "candidatos.json"
    SAIDA.mkdir(parents=True, exist_ok=True)
    cands: dict[str, list[dict]] = json.loads(cache_meta.read_text(encoding="utf-8")) if cache_meta.is_file() else {}

    api = None if sem_rede else Api()
    for cat, conf in CONF.items():
        if cat in cands:
            continue
        vistos, lista = set(), []
        for q in conf["q"]:
            for s in api.buscar(q, conf["dur"]):
                if s["id"] in vistos or s["id"] in usados:
                    continue
                vistos.add(s["id"])
                lista.append({**{k: s.get(k) for k in ("id", "name", "username", "license", "duration", "url", "tags",
                                                       "avg_rating", "num_downloads")},
                              "description": (s.get("description") or "")[:400], "consulta": q,
                              "previa": s["previews"].get("preview-hq-ogg") or s["previews"]["preview-hq-mp3"]})
        cands[cat] = lista
        cache_meta.write_text(json.dumps(cands, ensure_ascii=False), encoding="utf-8")
        print(f"{cat:13} {len(lista)} candidatos (API: {api.n} requisições)", flush=True)

    clap = Clap()
    rot_neg = {"fala": "a person speaking, human voice talking", "canto": "a person singing",
               "musica": "music with melody, instruments and rhythm"}
    t_neg = clap.textos(list(rot_neg.values()))
    ouvido = Ouvido()
    escolhidos, relatorio = [], {}
    ja = set()
    for cat, conf in CONF.items():
        alvo = (META.get(cat, META_NOVAS) - existentes.get(cat, 0)) if cat in META else META_NOVAS
        t_cat = clap.textos([conf["clap"]])
        aprovados, rejeitados = [], {}
        # ordem da API intercalada entre as buscas (relevância), e só baixa até ter 4x o necessário aprovados
        por_q: dict[str, list[dict]] = {}
        for s in cands[cat]:
            por_q.setdefault(s["consulta"], []).append(s)
        fila = [s for grupo in zip(*[iter_pad(v, max(map(len, por_q.values()))) for v in por_q.values()]) for s in grupo if s]
        for s in fila:
            if len(aprovados) >= alvo * 4 or s["id"] in ja:
                continue
            if s["id"] in REVISAO:
                rejeitados[s["id"]] = "revisão: " + REVISAO[s["id"]]
                continue
            lic = licenca(s["license"])
            if not lic:
                rejeitados[s["id"]] = "licença"
                continue
            b = _barrado(s, cat)
            if b:
                rejeitados[s["id"]] = b
                continue
            try:
                x = medir.ler(str(baixar_previa(s["id"], s["previa"])))
            except Exception as e:
                rejeitados[s["id"]] = f"download/decodificação: {e}"[:80]
                continue
            med, z = medir_candidato(x, cat)
            if z is None:
                rejeitados[s["id"]] = med["motivo"]
                continue
            mono = z.mean(1).astype(np.float32)[: int(10 * medir.SR)]
            va = clap.audios([mono], medir.SR)[0]
            logits = np.concatenate([[va @ t_cat[0]], t_neg @ va]) * 100
            p = np.exp(logits - logits.max())
            p /= p.sum()
            med.update(clap_sim=round(float(va @ t_cat[0]), 4), p_cat=round(float(p[0]), 3), p_fala=round(float(p[1]), 3),
                       p_canto=round(float(p[2]), 3), p_musica=round(float(p[3]), 3))
            lim_voz = 0.6 if conf.get("voz_ok") else 0.25
            if med["p_fala"] + med["p_canto"] > lim_voz:
                rejeitados[s["id"]] = f"CLAP voz ({med['p_fala'] + med['p_canto']:.2f})"
                continue
            if med["p_musica"] > 0.5:
                rejeitados[s["id"]] = f"CLAP música ({med['p_musica']:.2f})"
                continue
            aprovados.append({**s, "licenca": lic, "medidas": med})
        aprovados.sort(key=lambda a: -a["medidas"]["clap_sim"])
        por_autor: dict[str, int] = {}
        sel = []
        for a in aprovados:
            if len(sel) >= alvo:
                break
            if por_autor.get(a["username"], 0) >= 3:
                continue
            texto = ouvido.fala(a["id"], a["previa"], cat)
            a["medidas"]["whisper"] = texto
            if texto:
                rejeitados[a["id"]] = f"whisper: fala '{texto[:30]}'"
                continue
            por_autor[a["username"]] = por_autor.get(a["username"], 0) + 1
            sel.append(a)
            ja.add(a["id"])
        for k, a in enumerate(sel):
            escolhidos.append({
                "id": f"{cat}_fs{a['id']}", "categoria": cat, "freesound_id": a["id"], "nome": a["name"],
                "autor": a["username"], "licenca": a["licenca"], "licenca_url": a["license"], "url": a["url"],
                "previa": a["previa"], "recorte": list(conf["recorte"]) if conf.get("recorte") else None,
                "consulta": a["consulta"], "medidas": a["medidas"]})
        motivos: dict[str, int] = {}
        for m in rejeitados.values():
            chave = re.split(r" \(| -?\d|:", m)[0]
            motivos[chave] = motivos.get(chave, 0) + 1
        relatorio[cat] = {"candidatos": len(cands[cat]), "avaliados": len(aprovados) + len(rejeitados),
                          "aprovados": len(aprovados), "escolhidos": len(sel), "pedidos": alvo, "rejeicoes": motivos}
        print(f"{cat:13} escolhidos {len(sel)}/{alvo}  aprovados {len(aprovados)}  rejeitados {motivos}", flush=True)
    clap.liberar()
    LISTA.write_text(json.dumps({
        "versao": 1, "fonte": "Freesound API v2 (busca por texto); prévia hq; só CC0 e CC BY",
        "buscas": {c: v["q"] for c, v in CONF.items()}, "relatorio": relatorio,
        "itens": sorted(escolhidos, key=lambda e: (list(CONF).index(e["categoria"]), e["id"]))},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("API:", api.n if api else 0, "requisições;", len(escolhidos), "sons escolhidos")


def iter_pad(v: list, n: int) -> list:
    return v + [None] * (n - len(v))


def baixar() -> None:
    for it in json.loads(LISTA.read_text(encoding="utf-8"))["itens"]:
        baixar_previa(it["freesound_id"], it["previa"])


# ------------------------------------------------------------------------------------------- folhas
def folhas() -> None:
    """Uma folha PNG por categoria: espectrograma (0–16 kHz, escala log) + envelope de cada som do banco."""
    from PIL import Image, ImageDraw

    cat = json.loads(gerar.CATALOGO.read_text(encoding="utf-8"))
    SAIDA.mkdir(parents=True, exist_ok=True)
    for c in cat["categorias"]:
        itens = [i for i in cat["itens"] if i["categoria"] == c]
        larg, alt, col = 300, 120, 4
        linhas = (len(itens) + col - 1) // col
        img = Image.new("RGB", (col * larg, linhas * (alt + 14)), "white")
        d = ImageDraw.Draw(img)
        for k, i in enumerate(itens):
            x = medir.ler(str(AQUI / i["arquivo"])).mean(1)
            n = 1024
            if len(x) < n * 2:
                x = np.concatenate([x, np.zeros(n * 2 - len(x))])
            q = np.lib.stride_tricks.sliding_window_view(x, n)[:: max(1, (len(x) - n) // larg)][:larg] * np.hanning(n)
            S = 20 * np.log10(np.abs(np.fft.rfft(q, axis=1)) + 1e-9)
            fbin = np.linspace(0, 1, alt)
            idx = np.clip((20 * (16000 / 20) ** fbin) / (medir.SR / 2) * (n // 2), 0, n // 2).astype(int)
            S = S[:, idx].T[::-1]
            S = np.clip((S - (S.max() - 80)) / 80, 0, 1)
            im = Image.fromarray((255 * (1 - S)).astype(np.uint8)).resize((larg - 6, alt))
            ox, oy = (k % col) * larg, (k // col) * (alt + 14)
            img.paste(im.convert("RGB"), (ox, oy + 14))
            d.text((ox + 2, oy + 1), f"{i['id'][:34]} {i['duracao_s']}s", fill="black")
            px = ox + int(i["pico_s"] / max(i["duracao_s"], 1e-3) * (larg - 6))
            d.line([(px, oy + 14), (px, oy + 14 + alt)], fill="red")
        img.save(SAIDA / f"folha_{c}.png")
        print(SAIDA / f"folha_{c}.png")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "buscar":
        buscar()
    elif cmd == "baixar":
        baixar()
    elif cmd == "folhas":
        folhas()
    else:
        print(__doc__ or "uso: freesound.py buscar | baixar | folhas")
