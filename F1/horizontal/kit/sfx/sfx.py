# API do banco de SFX do horizontal (independente de motor).
#
#   from sfx import Banco, mixar
#   b = Banco()                                   # lê catalogo.json
#   ev = b.para("impacto", 13.0, 0.8)             # pico do som cai em 13,0 s
#   ev = b.para_palavra("clique", palavras, "1,481")   # palavras.json do projeto: [{"t"|"p", "i", "f"}]
#   evs = b.capitulo(16.2)                        # riser terminando em 16,2 s + impacto em 16,2 s
#   mixar(evs, 20.0, "trilho.wav")               # numpy;  mixar_ffmpeg(...) faz o mesmo pelo ffmpeg
#   para_hyperframes(evs) / para_json(evs)        # <audio data-start> do HyperFrames / lista para o Remotion (sfx.ts)
#
# Categorias (catalogo.json): impacto, riser, whoosh, sino, alerta, pop, clique, tecla e, para F1 documental, motor,
# pneu, radio, cronometro, grafico, obturador, whoosh_grave, boom, box, multidao (as mesmas em sfx.ts: CATEGORIAS).
#
# Regras:
# - categoria de ambiente (ancora="inicio" no catálogo, hoje só multidao): pico_s = 0, o som começa na palavra.
# - a âncora é o PICO do som (pico_s do catálogo): o início real = t - pico_s (riser termina na palavra, whoosh
#   passa no meio dela, impacto/clique batem nela). Se o início ficar antes de 0, o começo do arquivo é pulado.
# - intensidade 0..1 → ganho de -9 dB a 0 dB, somado ao volume_db da categoria. Duração cortada em dur_max da
#   categoria (ou no dur pedido) com saída suave de 30 ms.
# - escolha da variação: determinística (hash FNV-1a de "semente:categoria:contagem"), sem repetir as 2 últimas
#   da categoria. A MESMA regra está em sfx.ts: Python e TS escolhem os mesmos arquivos para o mesmo pedido.
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import medir  # noqa: E402

CATALOGO = AQUI / "catalogo.json"
SR = medir.SR
SAIDA_S = 0.03


@dataclass
class Evento:
    id: str
    categoria: str
    arquivo: str          # relativo à pasta do kit (banco/<cat>/<id>.wav)
    t: float              # âncora (s): onde o pico do som cai
    inicio: float         # onde o som começa a tocar na linha do tempo (s, >= 0)
    corte_ini: float      # quanto do começo do arquivo é pulado (s)
    dur: float            # quanto toca (s)
    ganho_db: float
    palavra: str | None = None

    @property
    def volume(self) -> float:
        return 10 ** (self.ganho_db / 20)


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.casefold())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w,.]+", "", s).strip(".,")


def achar_palavra(palavras: list[dict], alvo: str | int, ocorrencia: int = 1) -> dict:
    """Palavra de palavras.json por índice (int) ou por texto (sem acento/caixa/pontuação; n-ésima ocorrência)."""
    if isinstance(alvo, int):
        return palavras[alvo]
    achadas = [p for p in palavras if _norm(p.get("t", p.get("p", ""))) == _norm(alvo)]
    if len(achadas) < ocorrencia:
        raise ValueError(f"palavra-âncora não encontrada: {alvo!r} (ocorrência {ocorrencia})")
    return achadas[ocorrencia - 1]


class Banco:
    def __init__(self, catalogo: str | Path = CATALOGO, semente: int = 0):
        self.cat = json.loads(Path(catalogo).read_text(encoding="utf-8"))
        self.categorias: dict = self.cat["categorias"]
        self.itens = {i["id"]: i for i in self.cat["itens"]}
        self.por_cat: dict[str, list[str]] = {}
        for i in self.cat["itens"]:
            self.por_cat.setdefault(i["categoria"], []).append(i["id"])
        for v in self.por_cat.values():
            v.sort()
        self.semente = semente
        self._conta: dict[str, int] = {}
        self._recentes: dict[str, list[str]] = {}

    def escolher(self, categoria: str) -> str:
        ids = self.por_cat[categoria]
        k = self._conta.get(categoria, 0)
        self._conta[categoria] = k + 1
        h = fnv1a(f"{self.semente}:{categoria}:{k}")
        rec = self._recentes.setdefault(categoria, [])
        evita = set(rec[-min(2, len(ids) - 1):]) if len(ids) > 1 else set()
        for j in range(len(ids)):
            cand = ids[(h + j) % len(ids)]
            if cand not in evita:
                break
        rec.append(cand)
        return cand

    def para(self, categoria: str, t: float, intensidade: float = 0.7, variacao: str | None = None,
             dur: float | None = None, palavra: str | None = None) -> Evento:
        if categoria not in self.categorias:
            raise ValueError(f"categoria desconhecida: {categoria} (há: {', '.join(self.categorias)})")
        c = self.categorias[categoria]
        iid = variacao or self.escolher(categoria)
        it = self.itens[iid]
        inicio = t - it["pico_s"]
        corte = max(0.0, -inicio)
        inicio = max(0.0, inicio)
        d = min(it["duracao_s"] - corte, c["dur_max"], dur if dur else 1e9)
        ganho = c["volume_db"] - 9.0 * (1.0 - min(1.0, max(0.0, intensidade)))
        return Evento(iid, categoria, it["arquivo"], round(t, 4), round(inicio, 4), round(corte, 4),
                      round(d, 4), round(ganho, 2), palavra)

    def para_palavra(self, categoria: str, palavras: list[dict], alvo: str | int, intensidade: float = 0.7,
                     ocorrencia: int = 1, ponto: str = "i", **kw) -> Evento:
        """Âncora numa palavra de palavras.json ([{"t"|"p": texto, "i": início, "f": fim}]): por índice (int) ou
        texto (sem acento/caixa/pontuação; ocorrencia = n-ésima vez). ponto 'i' = início da palavra, 'f' = fim."""
        p = achar_palavra(palavras, alvo, ocorrencia)
        return self.para(categoria, float(p[ponto]), intensidade, palavra=p.get("t", p.get("p")), **kw)

    def creditos(self, eventos: list[Evento]) -> list[str]:
        """Linhas de crédito (descrição do vídeo) dos sons CC BY usados nos eventos."""
        vistos, out = set(), []
        for e in eventos:
            it = self.itens[e.id]
            if it.get("credito_obrigatorio") and it["url"] not in vistos:
                vistos.add(it["url"])
                out.append(f'"{it["descricao"]}" de {it["autor"]} ({it["url"]}), {it["licenca"]}')
        return out

    def capitulo(self, t: float, intensidade: float = 0.9) -> list[Evento]:
        """Riser + impacto (a combinação elogiada no teste Remotion, ~16–17 s): o riser termina em t e o impacto bate em t."""
        return [self.para("riser", t, intensidade), self.para("impacto", t, intensidade)]

    def de_pedidos(self, pedidos: list[dict], palavras: list[dict] | None = None) -> list[Evento]:
        """Pedidos do SPEC: [{"categoria", "palavra": texto|índice | "t": s, "intensidade"?, "ocorrencia"?, "dur"?}].
        categoria "capitulo" vira riser + impacto."""
        out: list[Evento] = []
        for p in pedidos:
            if "t" in p:
                t = float(p["t"])
            else:
                t = float(achar_palavra(palavras or [], p["palavra"], p.get("ocorrencia", 1))[p.get("ponto", "i")])
            if p["categoria"] == "capitulo":
                out += self.capitulo(t, p.get("intensidade", 0.9))
            else:
                out.append(self.para(p["categoria"], t, p.get("intensidade", 0.7), p.get("variacao"), p.get("dur"),
                                     palavra=str(p.get("palavra")) if "palavra" in p else None))
        return out


# ------------------------------------------------------------------------------------------- mixagem
def _carregar(arquivo: str, cache: dict) -> np.ndarray:
    if arquivo not in cache:
        cache[arquivo] = medir.ler(str(AQUI / arquivo)).astype(np.float64)
    return cache[arquivo]


def mixar(eventos: list[Evento], dur: float, saida: str | Path | None = None, limitar: bool = True) -> np.ndarray:
    """Soma os eventos numa faixa estéreo de dur segundos (float64). Limitador a -1,5 dBFS só se passar."""
    n = int(round(dur * SR))
    mix = np.zeros((n, 2))
    cache: dict = {}
    for e in eventos:
        x = _carregar(e.arquivo, cache)
        a = int(round(e.corte_ini * SR))
        m = int(round(e.dur * SR))
        seg = x[a:a + m].copy()
        f = min(len(seg), int(SAIDA_S * SR))
        if f:
            seg[-f:] *= np.linspace(1, 0, f)[:, None]
        seg *= e.volume
        p = int(round(e.inicio * SR))
        if p >= n:
            continue
        seg = seg[: n - p]
        mix[p:p + len(seg)] += seg
    if limitar and medir.pico_amostra_db(mix) > -1.5:
        mix = medir.limitar(mix, -1.5)
    if saida:
        medir.gravar(str(saida), mix)
    return mix


def mixar_ffmpeg(eventos: list[Evento], dur: float, saida: str | Path) -> None:
    """Mesma mixagem feita só pelo ffmpeg (atrim + afade + volume + adelay em amostras + amix sem normalizar)."""
    entradas, filtros, rot = [], [], []
    for k, e in enumerate(eventos):
        entradas += ["-i", str(AQUI / e.arquivo)]
        atraso = int(round(e.inicio * SR))
        filtros.append(
            f"[{k}:a]aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"atrim=start_sample={int(round(e.corte_ini * SR))}:end_sample={int(round((e.corte_ini + e.dur) * SR))},"
            f"asetpts=PTS-STARTPTS,afade=t=out:st={max(0.0, e.dur - SAIDA_S):.5f}:d={SAIDA_S},"
            f"volume={e.ganho_db}dB,adelay={atraso}S|{atraso}S[a{k}]")
        rot.append(f"[a{k}]")
    filtros.append(f"{''.join(rot)}amix=inputs={len(eventos)}:normalize=0:duration=longest,"
                   f"apad=whole_len={int(round(dur * SR))},atrim=end_sample={int(round(dur * SR))}[out]")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(";\n".join(filtros))
        script = fh.name
    cmd = ["ffmpeg", "-y", "-v", "error", *entradas, "-/filter_complex", script, "-map", "[out]",
           "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(saida)]
    subprocess.run(cmd, check=True)
    Path(script).unlink(missing_ok=True)


# ------------------------------------------------------------------------------------------- motores
def para_json(eventos: list[Evento]) -> list[dict]:
    """Lista simples (o que o Remotion/sfx.ts e o montador consomem)."""
    return [asdict(e) for e in eventos]


def para_hyperframes(eventos: list[Evento], prefixo: str = "assets/sfx/", trilha_inicial: int = 20) -> str:
    """Tags <audio> do HyperFrames (data-start, data-duration, data-media-start, data-volume). Cada som numa
    trilha própria, alternando entre 4 trilhas (o HyperFrames não sobrepõe clipes na mesma trilha)."""
    linhas = []
    fim_trilha: dict[int, float] = {}
    for k, e in enumerate(eventos):
        tr = next(t for t in range(trilha_inicial, trilha_inicial + 64) if fim_trilha.get(t, -1) <= e.inicio)
        fim_trilha[tr] = e.inicio + e.dur
        nome = Path(e.arquivo).name
        linhas.append(
            f'<audio id="sfx-{k:02d}" class="clip" src="{prefixo}{nome}" data-start="{e.inicio:.3f}" '
            f'data-duration="{e.dur:.3f}"' + (f' data-media-start="{e.corte_ini:.3f}"' if e.corte_ini else "")
            + f' data-track-index="{tr}" data-volume="{min(1.0, e.volume):.4f}"></audio>')
    return "\n".join(linhas)


if __name__ == "__main__":
    b = Banco()
    for c, ids in b.por_cat.items():
        print(f"{c:8} {len(ids):2}  {', '.join(ids)}")
