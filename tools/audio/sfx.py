"""Catálogo local de efeitos sonoros (Fase 8).

Regra do canal (guia de estilo §8): efeito é tempero RARO e com sentido — o catálogo é variado para que o
mesmo som não se repita, não para encher o vídeo.

Fontes:
- Freesound (API, chave no .env): SÓ licenças CC0 e CC BY (o canal é monetizado; CC BY-NC fica de fora).
  Usa a prévia em alta qualidade (mp3 ~128 kbps, não precisa de OAuth). CC BY → crédito na descrição.
- Stable Audio Open (local, GPU): gera o que o catálogo não tem. Licença Stability Community (uso comercial ok
  abaixo de US$ 1 mi/ano de receita).
Cada som é aparado (silêncio do início), limitado a ~6 s com fade e normalizado no pico (-3 dBFS).

    .venv\\Scripts\\python.exe tools\\audio\\sfx.py catalogar        # baixa do Freesound + completa gerando
    .venv\\Scripts\\python.exe tools\\audio\\sfx.py gerar "prompt" 3 categoria
    .venv\\Scripts\\python.exe tools\\audio\\sfx.py indexar          # vetores CLAP que faltam
    .venv\\Scripts\\python.exe tools\\audio\\sfx.py buscar "deep cinematic boom"
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # clap.py
from comum import RAIZ, abrir_acervo, preparar_ffmpeg  # noqa: E402

PASTA = RAIZ / "dados" / "sfx"
SR = 44100
MAX_SEG = 6.0
POR_CATEGORIA = 5
MINIMO = 3  # abaixo disso, completa gerando com o Stable Audio Open

# categoria → (busca no Freesound, prompt para gerar, duração ao gerar)
CATEGORIAS = {
    "impacto": ("cinematic impact boom", "deep cinematic boom impact hit with low rumble tail, sound effect", 3.0),
    "golpe": ("sword slash swoosh", "fast sword slash swoosh, sound effect", 1.5),
    "metal": ("sword clash metal", "two swords clashing, metal clang ring, sound effect", 2.0),
    "magia": ("magic spell shimmer", "magical spell cast, sparkling shimmer, sound effect", 3.0),
    "magia_sombria": ("dark magic spell", "dark evil magic spell, ominous low hum and whoosh, sound effect", 3.0),
    "explosao": ("explosion distant", "big explosion with debris, sound effect", 3.0),
    "criatura": ("monster growl", "deep monster growl, creature snarl, sound effect", 2.5),
    "rugido": ("monster roar", "huge beast roar, sound effect", 3.0),
    "corvos": ("crows cawing", "a flock of crows cawing, dark eerie echo, sound effect", 4.0),
    "sussurro": ("creepy whisper", "creepy ghostly whispers, horror, sound effect", 4.0),
    "sino": ("church bell toll", "single deep church bell toll with long reverb, sound effect", 4.0),
    "trovao": ("thunder crack", "loud thunder crack and rumble, sound effect", 4.0),
    "vidro": ("glass shatter", "glass shattering, sound effect", 2.0),
    "coracao": ("heartbeat", "slow heavy heartbeat, sound effect", 4.0),
    "fogo": ("fire whoosh", "fire burst whoosh, flames, sound effect", 2.5),
    "gelo": ("ice crack", "ice cracking and freezing, sound effect", 2.5),
    "risada": ("evil laugh", "evil villain laugh echo, sound effect", 3.0),
    "porta": ("dungeon door creak", "heavy old wooden dungeon door creaking open, sound effect", 3.0),
    "correntes": ("chains rattle", "heavy metal chains rattling, sound effect", 2.5),
    "agua": ("water splash deep", "big water splash, deep ocean, sound effect", 2.5),
    "vento": ("eerie wind", "eerie howling wind, dark atmosphere, sound effect", 5.0),
    "whoosh": ("whoosh transition", "fast cinematic whoosh, sound effect", 1.5),
}

def _preparar(bruto: np.ndarray) -> np.ndarray:
    """Mono, sem silêncio no início, até MAX_SEG com fade de saída, pico em -3 dBFS."""
    a = bruto.mean(1) if bruto.ndim == 2 else bruto
    env = np.abs(a)
    limiar = env.max() * 0.03
    ini = int(np.argmax(env > limiar)) if env.max() > 0 else 0
    a = a[max(0, ini - int(0.01 * SR)):]
    fim_util = len(a) - int(np.argmax(np.abs(a[::-1]) > limiar))  # corta a cauda em silêncio
    a = a[:max(1, fim_util + int(0.15 * SR))]
    if len(a) > MAX_SEG * SR:
        a = a[:int(MAX_SEG * SR)]
        n = int(0.6 * SR)
        a[-n:] *= np.linspace(1, 0, n)
    pico = np.abs(a).max()
    return (a / pico * 10 ** (-3 / 20)).astype(np.float32) if pico > 0 else a.astype(np.float32)


def _decodificar(origem: Path) -> np.ndarray:
    preparar_ffmpeg()
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", str(origem), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(bruto, dtype=np.float32).copy()  # frombuffer é só leitura


def _salvar(con, audio: np.ndarray, categoria: str, nome: str, **campos) -> int | None:
    destino = PASTA / categoria / f"{nome}.wav"
    destino.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destino, audio, SR)
    rel = destino.relative_to(PASTA).as_posix()
    if con.execute("SELECT 1 FROM sons WHERE arquivo=?", (rel,)).fetchone():
        return None
    return con.execute("INSERT INTO sons (arquivo, categoria, duracao, descricao, origem, autor, url, licenca) "
                       "VALUES (?,?,?,?,?,?,?,?)",
                       (rel, categoria, round(len(audio) / SR, 2), campos.get("descricao"), campos["origem"],
                        campos.get("autor"), campos.get("url"), campos.get("licenca"))).lastrowid


def freesound(con, categoria: str, consulta: str, n: int = POR_CATEGORIA) -> int:
    import httpx
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
    r = httpx.get("https://freesound.org/apiv2/search/text/", timeout=60, params={
        "query": consulta, "token": os.environ["FREESOUND_API_KEY"], "page_size": 40, "sort": "rating_desc",
        "filter": 'duration:[0.3 TO 8] license:("Creative Commons 0" OR "Attribution")',
        "fields": "id,name,username,license,duration,previews,url,tags"})
    r.raise_for_status()
    novos = 0
    for s in r.json()["results"]:
        if novos >= n:
            break
        url_lic = s["license"].lower()  # vem como URL: .../publicdomain/zero/1.0/ ou .../licenses/by/4.0/
        lic = "CC0" if "publicdomain/zero" in url_lic else "CC BY" if "/licenses/by/" in url_lic else None
        if not lic:  # by-nc, sampling+ etc.: fora (canal monetizado)
            continue
        nome = f"fs{s['id']}"
        if (PASTA / categoria / f"{nome}.wav").exists():
            continue
        tmp = PASTA / "_tmp.mp3"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp.write_bytes(httpx.get(s["previews"]["preview-hq-mp3"], timeout=60, follow_redirects=True).content)
            audio = _preparar(_decodificar(tmp))
        except Exception as e:  # um arquivo ruim não derruba o catálogo
            print(f"  pulei {nome}: {e}")
            continue
        if len(audio) < 0.2 * SR:
            continue
        if _salvar(con, audio, categoria, nome, origem="freesound", descricao=s["name"], autor=s["username"],
                   url=s["url"], licenca=lic + (" 4.0" if lic == "CC BY" and "4.0" in s["license"] else "")):
            novos += 1
        time.sleep(1.1)  # limite da API: 60 req/min
    (PASTA / "_tmp.mp3").unlink(missing_ok=True)
    con.commit()
    return novos


class Gerador:
    """Stable Audio Open via diffusers (5,9 GB de VRAM; ~30 s por efeito na RTX 4060)."""

    def __init__(self) -> None:
        import torch
        from diffusers import StableAudioPipeline
        from huggingface_hub import snapshot_download

        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        pasta = snapshot_download("stabilityai/stable-audio-open-1.0", allow_patterns=[
            "model_index.json", "projection_model/*", "scheduler/*", "text_encoder/*", "tokenizer/*",
            "transformer/*", "vae/*"])
        self.torch = torch
        self.pipe = StableAudioPipeline.from_pretrained(pasta, dtype=torch.float16).to("cuda")

    def gerar(self, prompt: str, segundos: float, semente: int) -> np.ndarray:
        from scipy.signal import resample_poly

        a = self.pipe(prompt, negative_prompt="music, melody, speech, voice, low quality, noise", num_inference_steps=100,
                      audio_end_in_s=segundos, generator=self.torch.Generator("cuda").manual_seed(semente)).audios[0]
        mono = a.float().mean(0).cpu().numpy()
        return _preparar(resample_poly(mono, SR, self.pipe.vae.sampling_rate).astype(np.float32))

    def liberar(self) -> None:
        del self.pipe
        self.torch.cuda.empty_cache()


def gerar(con, gerador: Gerador, categoria: str, prompt: str, segundos: float, semente: int) -> int | None:
    audio = gerador.gerar(prompt, segundos, semente)
    sid = _salvar(con, audio, categoria, f"gerado_{semente}", origem="gerado", descricao=prompt,
                  licenca="Stability Community")
    con.commit()
    return sid


def indexar(con) -> int:
    """Vetor CLAP de cada som que ainda não tem (busca por descrição)."""
    from clap import Clap

    faltam = con.execute("SELECT id, arquivo FROM sons WHERE vetor IS NULL").fetchall()
    if not faltam:
        return 0
    clap = Clap()
    trechos = [sf.read(PASTA / r["arquivo"], dtype="float32")[0] for r in faltam]
    vetores = clap.audios(trechos, SR)
    for r, v in zip(faltam, vetores):
        con.execute("UPDATE sons SET vetor=? WHERE id=?", (v.astype(np.float32).tobytes(), r["id"]))
    con.commit()
    clap.liberar()
    return len(faltam)


class Busca:
    """Acha efeitos pela descrição em inglês. Carregue uma vez por vídeo (o CLAP leva alguns segundos)."""

    def __init__(self) -> None:
        from clap import Clap

        self.con = abrir_acervo()
        linhas = self.con.execute("SELECT id, arquivo, categoria, vetor FROM sons WHERE vetor IS NOT NULL").fetchall()
        self.ids = [r["id"] for r in linhas]
        self.info = {r["id"]: dict(arquivo=r["arquivo"], categoria=r["categoria"]) for r in linhas}
        self.matriz = np.stack([np.frombuffer(r["vetor"], dtype=np.float32) for r in linhas]) if linhas else None
        self.clap = Clap()
        # texto de cada categoria (busca do Freesound + prompt): a categoria certa reforça o som certo
        self.cats = list(CATEGORIAS)
        self.vet_cats = self.clap.textos([f"{q}. {p}" for q, p, _ in CATEGORIAS.values()])
        self.cat_idx = np.array([self.cats.index(self.info[i]["categoria"]) if self.info[i]["categoria"] in self.cats
                                 else 0 for i in self.ids]) if linhas else None
        recentes = [x[0] for x in self.con.execute(
            "SELECT video FROM uso_som GROUP BY video ORDER BY MAX(publicado_em) DESC LIMIT 3").fetchall()]
        self.recentes = {x[0] for x in self.con.execute(
            f"SELECT som_id FROM uso_som WHERE video IN ({','.join('?' * len(recentes))})", recentes)} if recentes else set()

    def buscar(self, descricao: str, n: int = 5, evitar: set[int] = frozenset()) -> list[tuple[int, float]]:
        if self.matriz is None:
            return []
        q = self.clap.textos([descricao])[0]
        sim_cat = self.vet_cats @ q  # texto×texto: quão bem o pedido casa com cada categoria
        sim_cat = (sim_cat - sim_cat.max())  # 0 para a melhor categoria, negativo para as outras
        notas = self.matriz @ q + 0.6 * sim_cat[self.cat_idx]
        for i, sid in enumerate(self.ids):  # variedade: já usados neste vídeo / nos últimos publicados pesam contra
            if sid in evitar:
                notas[i] -= 0.15
            elif sid in self.recentes:
                notas[i] -= 0.04
        ordem = np.argsort(-notas)[:n]
        return [(self.ids[i], float(notas[i])) for i in ordem]

    def liberar(self) -> None:
        self.clap.liberar()


def catalogar() -> None:
    con = abrir_acervo()
    for cat, (consulta, _, _) in CATEGORIAS.items():
        n = freesound(con, cat, consulta)
        total = con.execute("SELECT COUNT(*) FROM sons WHERE categoria=?", (cat,)).fetchone()[0]
        print(f"{cat:14} +{n} do Freesound (total {total})", flush=True)
    faltando = {cat: MINIMO - con.execute("SELECT COUNT(*) FROM sons WHERE categoria=?", (cat,)).fetchone()[0]
                for cat in CATEGORIAS}
    faltando = {c: q for c, q in faltando.items() if q > 0}
    if faltando:
        g = Gerador()
        for cat, q in faltando.items():
            _, prompt, seg = CATEGORIAS[cat]
            for k in range(q):
                gerar(con, g, cat, prompt, seg, semente=hash((cat, k)) % 100000)
            print(f"{cat:14} +{q} gerados", flush=True)
        g.liberar()
    print("indexados:", indexar(con))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "catalogar":
        catalogar()
    elif cmd == "gerar":
        con = abrir_acervo()
        g = Gerador()
        print(gerar(con, g, sys.argv[4], sys.argv[2], float(sys.argv[3]), semente=int(time.time()) % 100000))
        print("indexados:", indexar(con))
    elif cmd == "indexar":
        print(indexar(abrir_acervo()))
    elif cmd == "buscar":
        b = Busca()
        for sid, nota in b.buscar(" ".join(sys.argv[2:]), 8):
            print(f"{nota:.3f}  {b.info[sid]['arquivo']}")
    else:
        print(__doc__)
