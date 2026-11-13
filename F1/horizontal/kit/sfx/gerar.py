# Gera (ou regera) o banco de SFX do horizontal: banco/<categoria>/<id>.wav + catalogo.json.
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\gerar.py
# Fontes, nesta ordem de preferência:
#   1. sons dos testes elogiados pelo Felipe (Remotion: dados/comum/sfx; HyperFrames: biblioteca Pixabay do hyperframes)
#   2. sons livres do banco comum (Freesound CC0 / CC BY, Stable Audio Open) já baixados em dados/comum/sfx
#   3. síntese procedural (sintese.py), 100% reproduzível
# Todo arquivo sai em WAV 48 kHz estéreo 16 bits, cortado (silêncio inicial, duração máxima da categoria) e
# normalizado pelo loudness momentâneo máximo (LUFS-M máx) alvo da categoria, com pico verdadeiro <= -1 dBTP.
# O banco fica FORA do Git (licença Pixabay não permite redistribuir os arquivos soltos e o total passa de 5 MB);
# o catalogo.json (no Git) diz o que deve existir e este script refaz tudo a partir das fontes locais.
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import medir  # noqa: E402
import sintese  # noqa: E402

RAIZ = AQUI.parents[3]                       # raiz do repositório
BANCO = AQUI / "banco"
CATALOGO = AQUI / "catalogo.json"
COMUM = RAIZ / "dados" / "comum" / "sfx"
CASA = Path.home()
# A biblioteca de SFX do HyperFrames (Pixabay) aparece em mais de um lugar; usa o primeiro que tiver o arquivo.
PASTAS_HF = [CASA / "teste-motores/hyperframes/assets/audio",
             CASA / "hyperframes-teste/_fonte/skills/media-use/audio/assets/sfx",
             *map(Path, sorted(glob.glob(str(CASA / "AppData/Local/npm-cache/_npx/*/node_modules/hyperframes/dist/skills/media-use/audio/assets/sfx"))))]

# Categorias: alvo e faixa aceita de loudness (LUFS-M máx), duração máxima, volume de mixagem padrão (dB, somado
# ao ganho da intensidade). O ponto que cai na palavra-âncora é o pico do envelope (pico_s no catálogo).
# Faixas: ±1 dB para sons com corpo; mais largas para transientes (clique, tecla, pop), que têm 20–150 ms: o
# LUFS-M (janela de 400 ms) deles só sobe esmagando o ataque, então o limitador corta no máximo 6 dB (4 dB nas outras) e o que
# sobrar fica abaixo do alvo, dentro da faixa.
CATEGORIAS = {
    "impacto": {"alvo_lufs_m": -12.0, "faixa_lufs_m": [-13.0, -11.0], "dur_max": 2.5, "volume_db": 0.0,
                "uso": "peso de revelação: número grande, frase-tese, os dois carros lado a lado"},
    "riser": {"alvo_lufs_m": -15.0, "faixa_lufs_m": [-16.0, -14.0], "dur_max": 3.2, "volume_db": -2.0,
              "uso": "crescendo antes de capítulo ou algo grandioso; o pico (fim) cai na palavra; combine com impacto"},
    "whoosh": {"alvo_lufs_m": -16.0, "faixa_lufs_m": [-17.0, -15.0], "dur_max": 3.0, "volume_db": -3.0,
               "uso": "troca de cena, câmera que voa, cartão que atravessa"},
    "sino": {"alvo_lufs_m": -18.0, "faixa_lufs_m": [-19.0, -17.0], "dur_max": 2.6, "volume_db": -4.0,
             "uso": "fecho, nome do canal no fim, confirmação positiva"},
    "alerta": {"alvo_lufs_m": -18.0, "faixa_lufs_m": [-19.0, -17.0], "dur_max": 1.8, "volume_db": -5.0,
               "uso": "erro, penalidade, bandeira, rádio da equipe, dado que contradiz"},
    "pop": {"alvo_lufs_m": -20.0, "faixa_lufs_m": [-25.0, -19.0], "dur_max": 0.8, "volume_db": -5.0,
            "uso": "etiqueta/tag/selo aparecendo"},
    "clique": {"alvo_lufs_m": -22.0, "faixa_lufs_m": [-27.0, -21.0], "dur_max": 0.45, "volume_db": -6.0,
               "uso": "informação entrando na tela (clique, clique), item de lista, ponto no gráfico"},
    "tecla": {"alvo_lufs_m": -24.0, "faixa_lufs_m": [-30.0, -23.0], "dur_max": 0.35, "volume_db": -7.0,
              "uso": "uma tecla antes de um texto entrar; em sequência para texto digitado"},
}

PIXABAY = {"licenca": "Pixabay Content License", "credito_obrigatorio": False,
           "autor": "Pixabay (biblioteca de SFX do HyperFrames)",
           "url": "https://pixabay.com/service/license-summary/"}
STABLE = {"licenca": "Stability AI Community License", "credito_obrigatorio": False, "autor": "Stable Audio Open (gerado localmente)"}


def fs(num: int, autor: str, licenca: str, descricao: str) -> dict:
    return {"autor": autor, "licenca": licenca, "descricao": descricao,
            "url": f"https://freesound.org/people/{autor}/sounds/{num}/",
            "credito_obrigatorio": licenca.startswith("CC BY")}


# id -> (categoria, fonte, recorte, metadados). fonte: ("comum", "pasta/arquivo") | ("hf", "arquivo.mp3").
# recorte: None | (ini_s, fim_s) | ("fatia", n) = n-ésimo golpe detectado no arquivo.
EXTERNOS: dict[str, tuple] = {
    # --- impacto
    "impacto_remotion_14s": ("impacto", ("comum", "impacto/fs531129.wav"), None,
                             {**fs(531129, "ryusa", "CC BY 4.0", "Impact Gunshot Explosion Boom Cinematic Flanger"),
                              "nota": "elogiado: teste Remotion ~14 s (cena '1,481 s')"}),
    "impacto_hf_grave": ("impacto", ("hf", "impact-bass-1.mp3"), None,
                         {**PIXABAY, "descricao": "impact-bass-1", "nota": "elogiado: teste HyperFrames ~13 s (os dois carros)"}),
    "impacto_hf_grave_2": ("impacto", ("hf", "impact-bass-2.mp3"), None, {**PIXABAY, "descricao": "impact-bass-2 (com pequeno inchaço antes)"}),
    "impacto_fs755054": ("impacto", ("comum", "impacto/fs755054.wav"), None, fs(755054, "AudioPapkin", "CC0", "Sound Design Elements Impact SFX PS 017")),
    "impacto_fs748752": ("impacto", ("comum", "impacto/fs748752.wav"), None, fs(748752, "AudioPapkin", "CC0", "Sound Design Elements SFX PS 002")),
    "impacto_fs804681": ("impacto", ("comum", "impacto/fs804681.wav"), None, fs(804681, "johnjohnfm", "CC0", "PLASMA IMPACT ONE")),
    "impacto_fs751347": ("impacto", ("comum", "impacto/fs751347.wav"), None, fs(751347, "AudioPapkin", "CC0", "Sound Design Elements Impact SFX PS 009")),
    # --- riser (pico no fim)
    "riser_hf": ("riser", ("hf", "riser.mp3"), (2.2, 3.9),
                 {**PIXABAY, "descricao": "riser.mp3, 2,2–3,9 s (o arquivo de '10 s' só tem som até ~4,1 s)"}),
    "riser_hf_longo": ("riser", ("hf", "riser.mp3"), (0.8, 3.9), {**PIXABAY, "descricao": "riser.mp3, 0,8–3,9 s"}),
    "riser_hit_fs757897": ("riser", ("comum", "impacto/fs757897.wav"), None,
                           {**fs(757897, "AudioPapkin", "CC0", "Riser Hit sfx 108"), "nota": "riser que termina em batida"}),
    "riser_hit_fs754771": ("riser", ("comum", "impacto/fs754771.wav"), None,
                           {**fs(754771, "AudioPapkin", "CC0", "Riser Hit sfx 097"), "nota": "riser que termina em batida"}),
    "riser_power_up_fs683185": ("riser", ("comum", "whoosh/fs683185.wav"), None, fs(683185, "NearTheAtmoshphere", "CC0", "Power Up")),
    # --- whoosh
    "whoosh_capitulo_remotion": ("whoosh", ("comum", "whoosh/fs475893.wav"), None,
                                 {**fs(475893, "EpicSoundEffects", "CC0", "ESE - WHOOSH - EPIC - Sword Smith"),
                                  "nota": "elogiado: teste Remotion ~16–17 s e ~47–48 s (entrada de capítulo, com o riser da trilha)"}),
    "whoosh_hf_troca_cena": ("whoosh", ("hf", "whoosh-cinematic.mp3"), None,
                             {**PIXABAY, "descricao": "whoosh-cinematic", "nota": "elogiado: troca de cena no teste HyperFrames"}),
    "whoosh_hf": ("whoosh", ("hf", "whoosh.mp3"), None, {**PIXABAY, "descricao": "whoosh"}),
    "whoosh_remotion_1": ("whoosh", ("comum", "whoosh/fs277234.wav"), None, fs(277234, "raaghav81", "CC BY 4.0", "Sweep-005")),
    "whoosh_remotion_2": ("whoosh", ("comum", "whoosh/fs416462.wav"), None, fs(416462, "SoundFlakes", "CC BY 4.0", "Deep_Swoosh - 9")),
    "whoosh_fs812685": ("whoosh", ("comum", "whoosh/fs812685.wav"), None, fs(812685, "AudioPapkin", "CC0", "Sound Design Elements Whoosh SFX 048")),
    "whoosh_fs786514": ("whoosh", ("comum", "whoosh/fs786514.wav"), None, fs(786514, "migoreng1", "CC0", "swoosh_v2")),
    "whoosh_gerado_64400": ("whoosh", ("comum", "whoosh/gerado_64400.wav"), None, {**STABLE, "descricao": "fast cinematic whoosh"}),
    # --- clique
    "clique_hf_suave": ("clique", ("hf", "click-soft.mp3"), None,
                        {**PIXABAY, "descricao": "click-soft", "nota": "elogiado: 'clique, clique' quando informação entra (HyperFrames)"}),
    "clique_remotion": ("clique", ("comum", "clique/fs161544.wav"), None, fs(161544, "DasDeer", "CC BY 4.0", "Button.wav")),
    "clique_fs220197": ("clique", ("comum", "clique/fs220197.wav"), None, fs(220197, "GameAudio", "CC0", "Click - Basic")),
    "clique_fs410359": ("clique", ("comum", "clique/fs410359.wav"), None, fs(410359, "BenjaminNelan", "CC0", "Torch Click 1")),
    "clique_gerado_6460": ("clique", ("comum", "clique/gerado_6460.wav"), None, {**STABLE, "descricao": "crisp plastic button click"}),
    "clique_gerado_4885": ("clique", ("comum", "clique/gerado_4885.wav"), None, {**STABLE, "descricao": "crisp plastic button click"}),
    # --- tecla
    "tecla_hf": ("tecla", ("hf", "key-press.mp3"), None,
                 {**PIXABAY, "descricao": "key-press", "nota": "família do 'som de tecla antes do texto' elogiado (HyperFrames)"}),
    "tecla_hf_digitando_1": ("tecla", ("hf", "typing.mp3"), ("fatia", 0), {**PIXABAY, "descricao": "typing.mp3, 1º toque"}),
    "tecla_hf_digitando_2": ("tecla", ("hf", "typing.mp3"), ("fatia", 2), {**PIXABAY, "descricao": "typing.mp3, 3º toque"}),
    "tecla_hf_digitando_3": ("tecla", ("hf", "typing.mp3"), ("fatia", 4), {**PIXABAY, "descricao": "typing.mp3, 5º toque"}),
    # --- sino
    "sino_hf_ping_final": ("sino", ("hf", "ping.mp3"), None,
                           {**PIXABAY, "descricao": "ping", "nota": "elogiado: sininho com o nome do canal no fim (HyperFrames)"}),
    "sino_hf_chime": ("sino", ("hf", "chime.mp3"), None, {**PIXABAY, "descricao": "chime"}),
    "sino_hf_brilho": ("sino", ("hf", "sparkle.mp3"), None, {**PIXABAY, "descricao": "sparkle"}),
    # --- pop
    "pop_hf": ("pop", ("hf", "pop.mp3"), None, {**PIXABAY, "descricao": "pop"}),
    "pop_remotion": ("pop", ("comum", "pop/fs553519.wav"), None, fs(553519, "newlocknew", "CC BY 4.0", "Pop down impact_1")),
    "pop_fs849841": ("pop", ("comum", "pop/fs849841.wav"), None, fs(849841, "JeffPearson", "CC0", "ui-popup-sfx")),
    "pop_fs696560_a": ("pop", ("comum", "pop/fs696560.wav"), ("fatia", 0), fs(696560, "Funky_Audio", "CC0", "UIClick clay pop (1º golpe)")),
    "pop_fs696560_b": ("pop", ("comum", "pop/fs696560.wav"), ("fatia", 3), fs(696560, "Funky_Audio", "CC0", "UIClick clay pop (4º golpe)")),
    # --- alerta
    "alerta_hf_erro": ("alerta", ("hf", "error.mp3"), None, {**PIXABAY, "descricao": "error"}),
    "alerta_hf_notificacao": ("alerta", ("hf", "notification.mp3"), None, {**PIXABAY, "descricao": "notification"}),
    "alerta_fs859155": ("alerta", ("comum", "alerta/fs859155.wav"), None, fs(859155, "TommasoMotteran", "CC0", "UI Interaction Error Beep")),
    "alerta_fs536748": ("alerta", ("comum", "alerta/fs536748.wav"), None, fs(536748, "egomassive", "CC0", "Phone.ogg")),
    "alerta_fs634089": ("alerta", ("comum", "alerta/fs634089.wav"), None, fs(634089, "aj_heels", "CC BY 4.0", "TimerComplete01")),
}

# NÃO reaproveitar: o "som da asa abrindo" do teste Remotion (mecanico.wav = seletor/fs669142.wav), reprovado pelo Felipe.
TRANSIENTES = {"clique", "tecla", "pop"}
EXCLUIDOS = {"seletor/fs669142.wav": "mecanico.wav do teste Remotion: 'SFX do movimento da asa ficou muito ruim'"}


def _achar_hf(nome: str) -> Path | None:
    for p in PASTAS_HF:
        if (p / nome).is_file():
            return p / nome
    return None


def _sem_silencio_inicial(x: np.ndarray, limiar_db: float = -45.0) -> np.ndarray:
    a = np.abs(x).max(1)
    lim = a.max() * 10 ** (limiar_db / 20)
    i = int(np.argmax(a > lim))
    return x[max(0, i - int(0.002 * medir.SR)):]


def _golpes(x: np.ndarray, separa_s: float = 0.08) -> list[int]:
    """Inícios dos golpes (picos do envelope de 10 ms acima de 30% do máximo, separados por >= 80 ms)."""
    env = medir.envelope(x)
    lim = env.max() * 0.3
    ini, ult = [], -10**9
    for i in range(1, len(env)):
        if env[i] > lim and env[i - 1] <= lim and (i - ult) * 0.01 >= separa_s:
            ini.append(i)
            ult = i
    return [max(0, int((i - 1) * 0.01 * medir.SR)) for i in ini]


def _preparar(x: np.ndarray, cat: str, recorte) -> np.ndarray:
    sr = medir.SR
    if isinstance(recorte, tuple) and recorte and recorte[0] == "fatia":
        g = _golpes(x)
        k = min(recorte[1], len(g) - 1)
        fim = g[k + 1] if k + 1 < len(g) else len(x)
        x = x[g[k]: min(fim, g[k] + int(CATEGORIAS[cat]["dur_max"] * sr))]
    elif recorte:
        x = x[int(recorte[0] * sr): int(recorte[1] * sr)]
    dmax = int(CATEGORIAS[cat]["dur_max"] * sr)
    if cat == "riser":
        if len(x) > dmax:                         # riser: guarda o FINAL (onde está o pico)
            x = x[-dmax:]
            x = x * np.minimum(1, np.arange(len(x)) / (0.2 * sr))[:, None]
    else:
        x = _sem_silencio_inicial(x)
        if len(x) > dmax:
            x = x[:dmax].copy()
            n = int(0.08 * sr)
            x[-n:] *= np.linspace(1, 0, n)[:, None]
    # corta cauda abaixo de -60 dB do pico
    a = np.abs(x).max(1)
    vivo = np.nonzero(a > a.max() * 10 ** (-60 / 20))[0]
    if len(vivo):
        x = x[: min(len(x), vivo[-1] + int(0.01 * sr))]
    return x


def normalizar(x: np.ndarray, alvo: float, teto_tp: float = -1.0, max_reducao_db: float = 4.0) -> np.ndarray:
    """Leva o LUFS-M máx ao alvo. O ganho é limitado para que o limitador (teto teto_tp-1 dB) nunca corte mais
    que max_reducao_db do pico original; duas rodadas compensam a perda de loudness causada pelo limitador."""
    x = x.astype(np.float64)
    teto = teto_tp - 1.0
    g = 0.0
    for _ in range(3):
        y = x * 10 ** (g / 20)
        g_max = teto + max_reducao_db - medir.pico_amostra_db(x)
        g = min(g + alvo - medir.lufs_m_max(_lim(y, teto)), g_max)
    return _lim(x * 10 ** (g / 20), teto)


def _lim(y: np.ndarray, teto: float) -> np.ndarray:
    return medir.limitar(y, teto) if medir.pico_amostra_db(y) > teto - 0.3 else y


def _pico_s(x: np.ndarray, cat: str) -> float:
    """Ponto que cai na palavra: máximo do envelope de 10 ms. No riser, o ÚLTIMO instante a 1 dB do máximo (fim do
    crescendo, ou a batida no caso dos 'riser hit')."""
    env = 20 * np.log10(medir.envelope(x) + 1e-12)
    if cat == "riser":
        return round(float(np.nonzero(env >= env.max() - 1.0)[0][-1]) * 0.01, 3)
    return round(float(np.argmax(env)) * 0.01, 3)


def gerar() -> dict:
    itens, faltando = [], []
    fontes: list[tuple[str, str, np.ndarray | None, dict]] = []
    for nome, (cat, fn, kw) in sintese.RECEITAS.items():
        fontes.append((nome, cat, fn(**kw), {"origem": "sintese", "licenca": "própria (síntese procedural, sintese.py)",
                                             "autor": "kit/sfx/sintese.py", "credito_obrigatorio": False,
                                             "descricao": f"{fn.__name__}({', '.join(f'{k}={v}' for k, v in kw.items())})",
                                             **({"nota": "riser da trilha do teste Remotion (elogiado em ~16–17 s e ~47–48 s)"}
                                                if nome == "riser_trilha_remotion" else {})}))
    for nome, (cat, (tipo, rel), recorte, meta) in EXTERNOS.items():
        assert rel not in EXCLUIDOS, rel
        p = (COMUM / rel) if tipo == "comum" else _achar_hf(rel)
        if not p or not p.is_file():
            faltando.append(f"{nome}: {rel}")
            continue
        origem = "pixabay-hyperframes" if tipo == "hf" else ("stable-audio" if "gerado_" in rel else "freesound")
        fontes.append((nome, cat, None, {**meta, "origem": origem, "fonte_local": str(p), "recorte": recorte, "_x": p}))

    for nome, cat, x, meta in fontes:
        p = meta.pop("_x", None)
        recorte = meta.get("recorte")
        if x is None:
            x = medir.ler(str(p))
        x = _preparar(x, cat, recorte)
        y = normalizar(x, CATEGORIAS[cat]["alvo_lufs_m"], max_reducao_db=6.0 if cat in TRANSIENTES else 4.0)
        destino = BANCO / cat / f"{nome}.wav"
        destino.parent.mkdir(parents=True, exist_ok=True)
        medir.gravar(str(destino), y, semente=sum(map(ord, nome)))
        y = medir.ler(str(destino))  # mede o que ficou no disco (16 bits)
        if "fonte_local" in meta:
            meta["fonte_local"] = os.path.relpath(meta["fonte_local"], CASA).replace("\\", "/")
            meta["fonte_local"] = "~/" + meta["fonte_local"]
        if meta.get("recorte") is None:
            meta.pop("recorte", None)
        itens.append({
            "id": nome, "categoria": cat, "arquivo": f"banco/{cat}/{nome}.wav",
            "duracao_s": round(len(y) / medir.SR, 3), "pico_s": _pico_s(y, cat),
            "lufs_m_max": round(medir.lufs_m_max(y), 2), "lufs_integrado": round(medir.lufs_integrado(y), 2),
            "pico_verdadeiro_dbtp": round(medir.pico_verdadeiro_db(y), 2),
            **meta,
        })
        print(f"{cat:8} {nome:28} {itens[-1]['duracao_s']:5.2f}s  M={itens[-1]['lufs_m_max']:6.1f}  TP={itens[-1]['pico_verdadeiro_dbtp']:5.1f}", flush=True)
    itens.sort(key=lambda i: (list(CATEGORIAS).index(i["categoria"]), i["id"]))
    cat_json = {
        "versao": 1,
        "formato": "WAV PCM 16 bits, 48 kHz, estéreo",
        "medida": "lufs_m_max = loudness momentânea máxima (BS.1770-4, janela 400 ms); alvo por categoria ±1 dB; pico verdadeiro <= -1 dBTP",
        "categorias": CATEGORIAS,
        "excluidos": EXCLUIDOS,
        "itens": itens,
    }
    if faltando:
        cat_json["faltando"] = faltando
        print("FALTANDO (fonte local não encontrada):", *faltando, sep="\n  ")
    CATALOGO.write_text(json.dumps(cat_json, ensure_ascii=False, indent=1), encoding="utf-8")
    return cat_json


if __name__ == "__main__":
    c = gerar()
    from collections import Counter
    print(dict(Counter(i["categoria"] for i in c["itens"])))
