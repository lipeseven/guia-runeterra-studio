"""Efeitos sonoros e fundo musical dos vídeos de referência (depois de separar_sons.py).

Para cada vídeo:
- EVENTOS: picos no áudio sem voz (bateria+graves+outros) bem acima do fundo → classificados pelo CLAP
  (laion/larger_clap_general, local) → volume relativo à voz, ataque, duração, distância do corte de cena
  mais próximo e a palavra narrada naquele instante.
- LEITO: janelas de 10 s do fundo contínuo classificadas (música, ambiente, silêncio...) e o volume vs. voz.
Saída: <slug>/som/eventos.json, dados/analise_referencias/sons_resumo.json e exemplos .wav por tipo em
dados/analise_referencias/sons_exemplos/ (para ouvir).

    .venv\\Scripts\\python.exe tools\\analise_referencias\\analisar_sons.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.ndimage import median_filter
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import RAIZ  # noqa: E402

sys.path.insert(0, str(RAIZ / "tools"))
from canal import caminho  # noqa: E402

PASTA = caminho("analise")
EXEMPLOS = PASTA / "sons_exemplos"
SR = 44100
PASSO = 0.01  # 10 ms

# rótulo → descrição em inglês para o CLAP
EVENTOS = {
    "whoosh": "a fast whoosh swoosh transition sound effect",
    "impacto": "a deep cinematic boom impact hit",
    "pop": "a short soft pop or click sound effect",
    "riser": "a rising tension riser build-up sound effect",
    "magia": "a magical sparkle shimmer chime sound effect",
    "espada": "a sword slash or metal clang sound effect",
    "explosao": "an explosion or fire burst sound",
    "criatura": "a monster growl or roar",
    "trovao": "thunder or lightning crack",
    "batida": "a heartbeat or drum hit",
    "sino": "a bell or gong ring",
    "risada": "an evil laugh",
    "vidro": "glass breaking or shattering",
    "multidao": "a crowd or battle noise",
    "musica": "a musical note or melody from background music",
    "fala": "a person speaking",
}
LEITO = {
    "musica": "background music with melody",
    "musica_tensa": "dark tense cinematic background music",
    "ambiente": "dark ambient drone atmosphere",
    "silencio": "silence or very quiet room tone",
    "fala": "a person speaking",
}


class Clap:
    def __init__(self) -> None:
        from transformers import ClapModel, ClapProcessor

        nome = "laion/larger_clap_general"
        self.proc = ClapProcessor.from_pretrained(nome)
        self.modelo = ClapModel.from_pretrained(nome).cuda().eval()

    @torch.no_grad()
    def textos(self, descricoes: list[str]) -> torch.Tensor:
        e = self.proc(text=descricoes, return_tensors="pt", padding=True).to("cuda")
        t = self.modelo.get_text_features(**e)
        t = t.pooler_output if hasattr(t, "pooler_output") else t
        return torch.nn.functional.normalize(t, dim=-1)

    @torch.no_grad()
    def audios(self, trechos: list[np.ndarray]) -> torch.Tensor:
        saida = []
        for k in range(0, len(trechos), 32):
            lote = [resample_poly(x, 48000, SR).astype(np.float32) for x in trechos[k:k + 32]]
            e = self.proc(audio=lote, sampling_rate=48000, return_tensors="pt").to("cuda")
            a = self.modelo.get_audio_features(**e)
            a = a.pooler_output if hasattr(a, "pooler_output") else a
            saida.append(torch.nn.functional.normalize(a, dim=-1))
        return torch.cat(saida) if saida else torch.empty(0)

    def classificar(self, trechos: list[np.ndarray], rotulos: dict[str, str]) -> list[tuple[str, float]]:
        if not trechos:
            return []
        t = self.textos(list(rotulos.values()))
        p = (self.audios(trechos) @ t.T * 100).softmax(-1).cpu().numpy()
        nomes = list(rotulos)
        return [(nomes[i], float(linha[i])) for linha, i in zip(p, p.argmax(1))]


def envelope_db(a: np.ndarray) -> np.ndarray:
    j = int(SR * PASSO)
    n = len(a) // j
    q = a[: n * j].reshape(n, j) ** 2
    rms = np.sqrt((q + np.roll(q, 1, axis=0)).mean(1) / 2)  # janela de 20 ms
    return 20 * np.log10(rms + 1e-9)


def detectar_eventos(db: np.ndarray) -> list[tuple[int, int, int]]:
    """(início, pico, fim) em quadros de 10 ms: subida ≥9 dB acima do fundo local (mediana de 4 s)."""
    fundo = median_filter(db, size=400, mode="nearest")
    ativo = (db > fundo + 9) & (db > -42)
    eventos, k, n = [], 0, len(db)
    while k < n:
        if not ativo[k]:
            k += 1
            continue
        ini = k
        fim = k
        while fim < n and (db[fim] > fundo[fim] + 4) and fim - ini < 800:  # no máx. 8 s
            fim += 1
        # junta com o próximo se o buraco for < 200 ms
        while True:
            prox = next((m for m in range(fim, min(n, fim + 20)) if ativo[m]), None)
            if prox is None:
                break
            fim = prox
            while fim < n and db[fim] > fundo[fim] + 4 and fim - ini < 800:
                fim += 1
        if fim - ini >= 6:  # ≥ 60 ms
            pico = ini + int(np.argmax(db[ini:fim]))
            eventos.append((ini, pico, fim))
        k = fim + 1
    return eventos


def palavras(pasta: Path) -> list[dict]:
    arq = pasta / "transcricao.json"
    if not arq.exists():
        return []
    return [p for s in json.loads(arq.read_text(encoding="utf-8"))["segmentos"] for p in s.get("palavras", [])]


def analisar(pasta: Path, clap: Clap) -> dict:
    som = pasta / "som"
    nv = sum(sf.read(som / f"{n}.flac", dtype="float32")[0] for n in ("drums", "bass", "other"))
    voz = sf.read(som / "vocals.flac", dtype="float32")[0]
    db, db_voz = envelope_db(nv), envelope_db(voz)
    duracao = len(nv) / SR
    voz_ativa = db_voz > np.percentile(db_voz, 60) - 12
    nivel_voz = float(np.median(db_voz[voz_ativa]))
    cortes = np.array([c["inicio"] for c in json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))["cenas"]])
    pal = palavras(pasta)
    inicios_pal = np.array([p["i"] for p in pal]) if pal else np.array([])

    brutos = detectar_eventos(db)
    trechos = []
    for ini, _, fim in brutos:
        a = max(0, int((ini * PASSO - 0.05) * SR))
        b = a + int(max(1.0, min(5.0, (fim - ini) * PASSO + 0.1)) * SR)
        trechos.append(nv[a:b])
    rotulos = clap.classificar(trechos, EVENTOS)

    eventos = []
    for (ini, pico, fim), (tipo, conf), trecho in zip(brutos, rotulos, trechos):
        t = ini * PASSO
        dist = float(np.min(np.abs(cortes - t))) if len(cortes) else None
        w = None
        if len(inicios_pal):
            k = int(np.argmin(np.abs(inicios_pal - t)))
            if abs(inicios_pal[k] - t) < 0.6:
                w = {"palavra": pal[k]["p"], "delta": round(t - pal[k]["i"], 2),
                     "inicio_de_frase": k == 0 or pal[k - 1]["p"].rstrip().endswith((".", "?", "!"))}
        # O Demucs deixa vazar consoantes (P, T, K) da voz para a bateria: evento curto em cima da fala = vazamento.
        # Conferido: esses "pops" aparecem até no vídeo do Felipe, que não tem efeito nenhum.
        voz_ali = float(np.max(db_voz[max(0, ini - 3):ini + 8])) - nivel_voz
        vazamento = (fim - ini) * PASSO < 0.35 and voz_ali > -15
        if vazamento:
            tipo = "vazamento_voz"
        eventos.append({"t": round(t, 2), "dur": round((fim - ini) * PASSO, 2), "ataque": round((pico - ini) * PASSO, 2),
                        "tipo": tipo, "conf": round(conf, 2), "pico_db": round(float(db[pico]), 1),
                        "vs_voz_db": round(float(db[pico]) - nivel_voz, 1),
                        "corte_mais_proximo": round(dist, 2) if dist is not None else None, "palavra": w,
                        "_trecho": trecho})

    # leito: janelas de 10 s do fundo contínuo (bass+other), nível = mediana da janela
    leito_trechos, leito_db = [], []
    for s in range(0, int(duracao) - 10, 10):
        leito_trechos.append(nv[s * SR:(s + 10) * SR])
        leito_db.append(float(np.median(db[int(s / PASSO):int((s + 10) / PASSO)])))
    leito = [{"t": s * 10, "tipo": tp, "conf": round(c, 2), "vs_voz_db": round(d - nivel_voz, 1)}
             for s, ((tp, c), d) in enumerate(zip(clap.classificar(leito_trechos, LEITO), leito_db))]
    return {"duracao": round(duracao, 1), "nivel_voz_db": round(nivel_voz, 1), "eventos": eventos, "leito": leito}


def resumir(nome: str, r: dict) -> dict:
    ev = [e for e in r["eventos"] if e["tipo"] not in ("fala", "vazamento_voz")]
    minutos = r["duracao"] / 60
    perto = [e for e in ev if e["corte_mais_proximo"] is not None and e["corte_mais_proximo"] <= 0.15]
    com_pal = [e for e in ev if e["palavra"]]
    leito_tipos = Counter(x["tipo"] for x in r["leito"])
    return {
        "video": nome, "minutos": round(minutos, 1),
        "eventos": len(ev), "eventos_por_minuto": round(len(ev) / minutos, 2),
        "tipos": dict(Counter(e["tipo"] for e in ev).most_common()),
        "pct_no_corte": round(100 * len(perto) / max(1, len(ev))),
        "pct_em_inicio_de_frase": round(100 * sum(e["palavra"]["inicio_de_frase"] for e in com_pal) / max(1, len(ev))),
        "vazamentos_descartados": sum(e["tipo"] == "vazamento_voz" for e in r["eventos"]),
        "vs_voz_db_mediana": round(float(np.median([e["vs_voz_db"] for e in ev])), 1) if ev else None,
        # leito abaixo de -35 dB da voz é resíduo da separação, não trilha audível
        "pct_tempo_com_leito_audivel": round(100 * sum(x["vs_voz_db"] > -35 for x in r["leito"]) / max(1, len(r["leito"]))),
        "leito": {k: round(100 * v / max(1, len(r["leito"]))) for k, v in leito_tipos.most_common()},
        "leito_vs_voz_db": round(float(np.median([x["vs_voz_db"] for x in r["leito"]])), 1) if r["leito"] else None,
    }


def main() -> None:
    clap = Clap()
    EXEMPLOS.mkdir(exist_ok=True)
    resumo, melhores = [], {}
    for pasta in sorted(p for p in PASTA.iterdir() if (p / "som" / "vocals.flac").exists()):
        print(pasta.name, flush=True)
        r = analisar(pasta, clap)
        for e in r["eventos"]:
            if e["tipo"] not in ("fala", "vazamento_voz"):
                melhores.setdefault(e["tipo"], []).append((e["conf"], pasta.name, e))
        limpos = {**r, "eventos": [{k: v for k, v in e.items() if k != "_trecho"} for e in r["eventos"]]}
        (pasta / "som" / "eventos.json").write_text(json.dumps(limpos, ensure_ascii=False, indent=1), encoding="utf-8")
        resumo.append(resumir(pasta.name, r))
        print("  ", resumo[-1], flush=True)
    for tipo, lista in melhores.items():  # 3 exemplos mais "certos" de cada tipo, para ouvir
        for n, (conf, video, e) in enumerate(sorted(lista, key=lambda x: -x[0])[:3], 1):
            sf.write(EXEMPLOS / f"{tipo}_{n}_{video[:30]}_{e['t']:.0f}s.wav", e["_trecho"], SR)
    (PASTA / "sons_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
