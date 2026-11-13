"""Receitas de cena: uma cena da SPEC → o pedido de render do motor marcado nela (Remotion ou HyperFrames).

Cada receita traduz os `kits[].params` da cena (o vocabulário do diretor, ver `../diretor/README.md`) para a entrada do
kit no motor, sem inventar nada: dados vêm dos arquivos dos kits (comparações, voltas do GPS, pistas, modelos 3D).
Se falta um arquivo, `FaltaAtivo` diz qual e o comando que o produz; se o par motor × kit ainda não tem receita,
`SemReceita` diz qual (o montador nunca "inventa" uma cena parecida).

Tempos: cada cena é renderizada no próprio relógio, `tau = (quadro - pre) / 60` (0 = 1ª palavra da cena); os `pre`
quadros antes de 0 (sobreposição da transição de entrada) seguram o quadro 0, e os `pos` quadros depois do fim
continuam a animação (sobreposição da transição de saída). Coordenadas das cenas: 1920 × 1080 (escala na saída).

Receitas de hoje (o resto dá `SemReceita` com mensagem clara):
| motor       | kit       | o que desenha |
|-------------|-----------|---------------|
| remotion    | graficos  | 1 gráfico do kit/graficos (velocidade, setores, delta, telemetria, normalizado) em tela cheia |
| remotion    | anotacao  | os `texto` da cena em tipografia grande + anotações à mão (oval, sublinhado, riscado, corrigido) |
| hyperframes | gps       | carros pelo GPS do OpenF1 na pista (.glb alinhado ou pista plana), câmera perseguindo ou fixa |
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from PIL import ImageFont

AQUI = Path(__file__).resolve().parent             # F1/horizontal/montador
HORIZ = AQUI.parent
KIT = HORIZ / "kit"
FPS = 60
BASE_W, BASE_H = 1920, 1080

# modelo 3D do carro por equipe (F1/dados/modelos3d); equipe fora da lista = FaltaAtivo
CARROS = {"Ferrari": "ferrari_sf26.glb", "Mercedes": "2026_mercedes_w17.glb", "Red Bull Racing": "2026_red_bull_racing_rb22.glb"}
FONTE_TITULO = r"C:\Windows\Fonts\ariblk.ttf"      # "Arial Black" (o Chrome do motor usa o mesmo arquivo)
FONTE_LINHA = r"C:\Windows\Fonts\arialbd.ttf"       # "Arial" 700
ANOTACOES_UM_ALVO = ("oval", "sublinhado", "riscado", "corrigido")


class FaltaAtivo(Exception):
    """Arquivo que a cena precisa e não existe (com o comando que o produz)."""


class SemReceita(Exception):
    """Par motor × kit (ou tipo) que o montador ainda não sabe renderizar."""


def dados_f1() -> Path:
    for base in [HORIZ.parent, *HORIZ.parent.parents]:
        c = base / "dados" if base.name == "F1" else base / "F1" / "dados"
        if (c / "modelos3d").is_dir():
            return c
    return HORIZ.parent / "dados"


_MEMO_HASH = Path(tempfile.gettempdir()) / "f1_horizontal_hash_arquivos.json"   # o storyboard planeja a cada leitura


def hash_arquivo(p: Path) -> str:
    """sha1 do conteúdo; arquivos grandes (modelos 3D) lembrados por caminho + tamanho + data (não relê a cada plano)."""
    p = Path(p)
    st = p.stat()
    if st.st_size < 2_000_000:
        return hashlib.sha1(p.read_bytes()).hexdigest()[:16]
    chave = f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}"
    try:
        memo = json.loads(_MEMO_HASH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        memo = {}
    if chave not in memo:
        memo[chave] = hashlib.sha1(p.read_bytes()).hexdigest()[:16]
        try:
            _MEMO_HASH.write_text(json.dumps(memo), encoding="utf-8")
        except OSError:
            pass
    return memo[chave]


def _volta(v) -> str:
    return str(int(v))


def _t_palavra(palavras: list[dict], i: int | None, t0: float, padrao: float) -> float:
    if i is None or not (0 <= int(i) < len(palavras)):
        return padrao
    return max(0.0, float(palavras[int(i)]["i"]) - t0)


# ---------------------------------------------------------------- Remotion: graficos
def _graficos(cena: dict, p: dict, palavras: list[dict], dur: float) -> tuple[dict, list[Path]]:
    s, a, b = p.get("sessao"), p.get("a") or {}, p.get("b") or {}
    if str(a.get("volta")) == "melhor" or str(b.get("volta")) == "melhor":
        raise SemReceita("graficos com volta 'melhor': resolva a volta (número) nos ativos antes de montar")
    nome = f"{s}_{a.get('piloto')}-{_volta(a.get('volta'))}_{b.get('piloto')}-{_volta(b.get('volta'))}.json"
    arq = KIT / "graficos" / "comparacoes" / nome
    if not arq.exists():
        raise FaltaAtivo(f"comparação {nome} (kit/graficos) — produzir: python F1/horizontal/kit/graficos/py/preparar.py "
                         f"{s} {a.get('piloto')} {a.get('volta')} {b.get('piloto')} {b.get('volta')}")
    spec = {"id": "g", "tipo": p["tipo"], "area": {"x": 60, "y": 40, "w": 1800, "h": 1000}, "em": 0.0,
            "destaque": p.get("destaque", "auto"), "curvas": p.get("curvas", True), "minimapa": bool(p.get("minimapa", False))}
    for k in ("trecho", "dur", "titulo", "subtitulo", "paineis", "metricas", "tema", "destaqueEm", "setores"):
        if k in p:
            spec[k] = p[k]
    if p.get("ritmo"):
        spec["ritmo"] = [{"t": round(_t_palavra(palavras, r.get("i"), cena["t0"], float(r.get("t", 0))), 4), "d": float(r["d"])}
                         for r in p["ritmo"]]
        if "dur" not in spec:
            spec["dur"] = max(0.5, spec["ritmo"][-1]["t"])
    camada = {"kit": "graficos", "specs": [spec], "dados": json.loads(arq.read_text(encoding="utf-8")),
              "larguras": json.loads((KIT / "graficos" / "fonte" / "segoe_larguras.json").read_text(encoding="utf-8"))}
    return camada, [arq]


# ---------------------------------------------------------------- Remotion: anotacao (+ textos da cena)
def _layout_textos(textos: list[str]) -> tuple[list[dict], dict]:
    """Textos da cena centralizados: o 1º grande (Arial Black 150), os outros em Arial 700 54. Caixas medidas na fonte
    real (mesmo .ttf que o Chrome usa), para o kit/anotacao ancorar em caixa ESTÁVEL."""
    linhas, alvos = [], {}
    if not textos:
        return linhas, alvos
    specs = [(t, FONTE_TITULO, "Arial Black", 900, 150) if k == 0 else (t, FONTE_LINHA, "Arial", 700, 54) for k, t in enumerate(textos)]
    # 1ª linha com folga grande embaixo: o oval/sublinhado do título não pode cruzar a linha seguinte
    alturas = [tam * (1.9 if k == 0 else 1.6) for k, (_, _, _, _, tam) in enumerate(specs)]
    y = BASE_H / 2 - sum(alturas) / 2
    for k, ((texto, ttf, familia, peso, tam), h) in enumerate(zip(specs, alturas)):
        f = ImageFont.truetype(ttf, tam)
        w = f.getlength(texto)
        x = (BASE_W - w) / 2
        base = y + h * 0.78
        l, t, r, bb = f.getbbox(texto, anchor="ls")
        linhas.append({"texto": texto, "fonte": familia, "peso": peso, "tamanho": tam, "x": round(x, 2), "y": round(base, 2)})
        alvos[f"t{k}"] = {"caixa": {"x": round(x + l, 2), "y": round(base + t, 2), "w": round(r - l, 2), "h": round(bb - t, 2)},
                          "texto": True}
        y += h
    return linhas, alvos


def _anotacao(cena: dict, usos: list[dict], palavras: list[dict], dur: float) -> tuple[dict, list[Path]]:
    textos = cena.get("texto") or []
    if not textos:
        raise SemReceita("anotacao no Remotion precisa de `texto` na cena (a anotação fica presa a um texto da tela)")
    linhas, alvos = _layout_textos(textos)
    anots = []
    for k, p in enumerate(usos):
        tipo = p.get("tipo")
        if tipo not in ANOTACOES_UM_ALVO:
            raise SemReceita(f"anotacao tipo '{tipo}' ainda sem receita no montador (há: {', '.join(ANOTACOES_UM_ALVO)})")
        alvo = int(p.get("alvo", 0)) if str(p.get("alvo", 0)).isdigit() else 0
        if f"t{alvo}" not in alvos:
            raise SemReceita(f"anotacao: alvo {alvo} não é um texto da cena (há {len(textos)})")
        a = {"id": f"a{k}", "tipo": tipo, "alvo": f"t{alvo}", "em": round(_t_palavra(palavras, p.get("i"), cena["t0"], 0.3 + k), 4)}
        if tipo == "corrigido":
            if not p.get("texto"):
                raise SemReceita("anotacao corrigido precisa de `texto` (o número certo)")
            a["texto"] = str(p["texto"])
        if "folga" in p and tipo in ("oval", "sublinhado"):
            a["folga"] = p["folga"]
        anots.append(a)
    fonte = KIT / "anotacao" / "fonte" / "caveat_traco.json"
    cen = {"largura": BASE_W, "altura": BASE_H, "fps": FPS, "duracao": round(dur, 4), "alvos": alvos, "anotacoes": anots}
    return {"kit": "anotacao", "cena": cen, "linhas": linhas, "fonte": json.loads(fonte.read_text(encoding="utf-8"))}, [fonte]


# ---------------------------------------------------------------- HyperFrames: gps
def _gps(cena: dict, p: dict, dur: float) -> tuple[dict, dict, list[Path]]:
    s = p.get("sessao")
    carros = p.get("carros") or []
    if not carros:
        raise SemReceita("gps sem carros")
    voltas, arquivos, assets = [], [], {}
    d = dados_f1() / "modelos3d"
    for c in carros:
        if str(c.get("volta")) == "melhor":
            raise SemReceita("gps com volta 'melhor': resolva a volta (número) nos ativos antes de montar")
        nome = f"{s}_{c.get('piloto')}_{_volta(c.get('volta'))}.json"
        arq = KIT / "gps" / "voltas" / nome
        if not arq.exists():
            raise FaltaAtivo(f"GPS {nome} (kit/gps) — produzir: cd F1/horizontal/kit/gps && python py/openf1.py {s} {c.get('piloto')} "
                             f"&& python py/preparar_volta.py {s} {c.get('piloto')} {c.get('volta')}")
        v = json.loads(arq.read_text(encoding="utf-8"))
        modelo = CARROS.get(v.get("equipe"))
        if not modelo or not (d / modelo).exists():
            raise FaltaAtivo(f"modelo 3D do carro da equipe {v.get('equipe')!r} (F1/dados/modelos3d; montador/receitas.py CARROS)")
        voltas.append({"arquivo": f"voltas/{nome}", "carro": modelo})
        assets[f"voltas/{nome}"] = arq
        assets[modelo] = d / modelo
        arquivos += [arq, d / modelo]
        pista = v.get("pista")
    if str(pista).endswith(".glb"):
        if not (d / pista).exists():
            raise FaltaAtivo(f"modelo da pista {pista} (F1/dados/modelos3d)")
        cfg_pista = {"glb": pista}
        assets[pista] = d / pista
        arquivos.append(d / pista)
    else:
        pp = KIT / "gps" / "pista" / str(pista)
        if not pp.exists():
            raise FaltaAtivo(f"pista plana {pista} (kit/gps/pista) — produzir: python py/preparar_volta.py ...")
        cfg_pista = {"plana": f"pista/{pista}"}
        assets[f"pista/{pista}"] = pp
        arquivos.append(pp)
    cfg = {"voltas": voltas, "pista": cfg_pista, "inicio": float(p.get("inicio", 0.0)), "fator": float(p.get("fator", 1.0)),
           "rastro": float(p.get("rastro", 2.5)), "camera": p.get("camera_gps", "perseguicao"), "distancia": float(p.get("distancia", 0.5)),
           "duracao": round(dur, 4)}
    if cfg["camera"] not in ("perseguicao", "fixa"):
        raise SemReceita(f"gps: camera_gps '{cfg['camera']}' (há: perseguicao, fixa)")
    return cfg, assets, arquivos


# ---------------------------------------------------------------- entrada
FONTES_CODIGO = {
    ("remotion", "graficos"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "graficos" / "CamadaGrafico.tsx",
                               KIT / "graficos" / "graficos.ts"],
    ("remotion", "anotacao"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "anotacao" / "CamadaAnotacao.tsx",
                               KIT / "anotacao" / "anotacao.ts"],
    ("hyperframes", "gps"): [AQUI / "hyperframes" / "gps.html", KIT / "gps" / "src" / "gps.js", KIT / "gps" / "src" / "gps_three.js",
                             KIT / "gps" / "exemplo" / "cena_exemplo.js"],
}


def receita(cena: dict, palavras: list[dict], pre: int, pos: int) -> dict:
    """Pedido de render de UMA cena. `hash` muda se qualquer coisa que muda os pixels mudar (entrada, dados, código)."""
    motor = cena["motor"]
    quadros = pre + int(round(cena["t1"] * FPS)) - int(round(cena["t0"] * FPS)) + pos
    dur = quadros / FPS
    usos = cena.get("kits") or []
    kits = sorted({u["kit"] for u in usos})
    if not usos:
        raise SemReceita("cena sem kit: o montador ainda não tem cena só de texto")
    arquivos: list[Path] = []
    job = {"motor": motor, "cena": cena["id"], "quadros": quadros, "pre": pre, "pos": pos, "kits": kits}
    if motor == "remotion":
        camadas = []
        graf = [u["params"] for u in usos if u["kit"] == "graficos"]
        anot = [u["params"] for u in usos if u["kit"] == "anotacao"]
        outros = [k for k in kits if k not in ("graficos", "anotacao")]
        if outros:
            raise SemReceita(f"kit {', '.join(outros)} ainda sem receita no Remotion (há: graficos, anotacao)")
        if len(graf) > 1:
            raise SemReceita("mais de um gráfico na mesma cena: divida em cenas")
        if graf:
            c, a = _graficos(cena, graf[0], palavras, dur)
            camadas.append(c)
            arquivos += a
        if anot:
            c, a = _anotacao(cena, anot, palavras, dur)
            camadas.append(c)
            arquivos += a
        job["props"] = {"quadros": quadros, "pre": pre, "camadas": camadas}
        if cena.get("movimento"):   # câmera da cena inteira (ação direta do storyboard; montador/movimento.js)
            job["props"].update(movimento=cena["movimento"], L=quadros - pre - pos)
    elif motor == "hyperframes":
        outros = [k for k in kits if k != "gps"]
        if outros:
            raise SemReceita(f"kit {', '.join(outros)} ainda sem receita no HyperFrames (há: gps)")
        if len(usos) > 1:
            raise SemReceita("mais de um uso de gps na mesma cena: junte os carros em um só")
        cfg, assets, a = _gps(cena, usos[0]["params"], dur)
        cfg.update({"quadros": quadros, "pre": pre})
        if cena.get("movimento"):
            cfg.update(movimento=cena["movimento"], L=quadros - pre - pos)
        job["cfg"] = cfg
        job["assets"] = {k: str(v) for k, v in assets.items()}
        arquivos += a
    else:
        raise SemReceita(f"motor desconhecido: {motor}")
    codigo = sorted({str(f) for k in kits for f in FONTES_CODIGO.get((motor, k), [])}
                    | {str(AQUI / "receitas.py"), str(AQUI / "segmentos.py"), str(AQUI / "movimento.js")})
    h = hashlib.sha1()
    h.update(json.dumps({k: v for k, v in job.items() if k not in ("assets",)}, sort_keys=True, ensure_ascii=False).encode())
    for f in sorted({str(x) for x in arquivos}) + codigo:
        h.update(f.encode() if not Path(f).exists() else hash_arquivo(Path(f)).encode())
    job["hash"] = h.hexdigest()[:12]
    return job
