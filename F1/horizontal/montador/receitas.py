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
| remotion    | cartoes   | cartão de capítulo em tela cheia ("PARTE 0N", título, traçado da sessão) |
| remotion    | foco      | desfoca tudo menos um `texto` da cena (índice) ou uma caixa {x,y,w,h}; anotações ficam nítidas |
| hyperframes | gps       | carros pelo GPS do OpenF1 na pista (.glb alinhado ou pista plana), câmera perseguindo, fixa ou alta; HUD (sigla, km/h) e rodapé |
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


# ---------------------------------------------------------------- Remotion: cartoes (capítulo)
def _tracado_sessao(sessao) -> tuple[dict | None, list[Path]]:
    """Traçado do circuito para o cartão de capítulo: o `tracado` (x, z do OpenF1) de uma comparação do kit/graficos da
    mesma sessão. Sem comparação da sessão = cartão sem traçado (não é erro)."""
    if sessao is None:
        return None, []
    for arq in sorted((KIT / "graficos" / "comparacoes").glob(f"{sessao}_*.json")):
        tr = json.loads(arq.read_text(encoding="utf-8")).get("tracado") or {}
        xs, zs = tr.get("x") or [], tr.get("z") or []
        if len(xs) < 10:
            continue
        x0, z0 = min(xs), min(zs)
        w, h = max(xs) - x0, max(zs) - z0
        d = "M" + " L".join(f"{x - x0:.1f} {z - z0:.1f}" for x, z in zip(xs, zs)) + " Z"
        return {"d": d, "largura": round(w, 1), "altura": round(h, 1)}, [arq]
    return None, []


def _cartoes(cena: dict, usos: list[dict], palavras: list[dict], dur: float) -> tuple[dict, list[Path]]:
    """Cartão de capítulo em tela cheia ("PARTE 0N" + título + traçado da sessão se houver). Pessoa (precisa de foto
    validada) e tag (precisa de âncora na tela) ainda não têm receita."""
    cartoes, arquivos = [], []
    for k, p in enumerate(usos):
        tipo = p.get("tipo")
        if tipo != "capitulo":
            raise SemReceita(f"cartoes tipo '{tipo}' ainda sem receita no montador (há: capitulo)")
        if not p.get("titulo") or p.get("numero") is None:
            raise SemReceita("cartoes capitulo precisa de `numero` e `titulo`")
        c = {"tipo": "capitulo", "id": f"c{k}", "em": round(_t_palavra(palavras, p.get("i"), cena["t0"], 0.0), 4),
             "ate": round(dur + 1.0, 4), "numero": int(p["numero"]), "titulo": str(p["titulo"])}
        if p.get("cor"):
            c["cor"] = p["cor"]
        if p.get("tracado", True):
            tr, a = _tracado_sessao(p.get("sessao"))
            if tr:
                c["tracado"] = tr
                arquivos += a
        cartoes.append(c)
    return {"kit": "cartoes", "cena": {"largura": BASE_W, "altura": BASE_H, "fps": FPS, "duracao": round(dur + 1.0, 4),
                                       "margem": 48, "cartoes": cartoes}}, arquivos


# ---------------------------------------------------------------- Remotion: duelo (cartoes tipo "duelo")
def _pilotos_sessao(sessao) -> dict:
    """{numero: {sigla, nome, equipe, cor}} das comparações do kit/graficos da sessão (cores já no padrão do kit)."""
    out = {}
    for arq in sorted((KIT / "graficos" / "comparacoes").glob(f"{sessao}_*.json")):
        for p in json.loads(arq.read_text(encoding="utf-8")).get("pilotos", []):
            out[str(p["numero"])] = {k: p.get(k) for k in ("sigla", "nome", "equipe", "cor")}
    return out


def _duelo(cena: dict, p: dict, palavras: list[dict], dur: float) -> tuple[dict, list[Path]]:
    """Dois números lado a lado, um cartão por piloto na cor da equipe ("30.008 contra 30.030" com QUEM é quem).
    params: {tipo: duelo, titulo, sessao, unidade?, lados: [{piloto, valor, em}, {piloto, valor, em}], destaque: 0|1|None,
    rodape?}. Cada lado entra seco na própria palavra (`em` → `i`). Uso real (rodada 1): números ditos que não ficavam na
    tela, 6 cenas de texto preto iguais e "30.008 contra 30.030" sem dizer quem é quem."""
    lados = p.get("lados") or []
    if len(lados) != 2 or not p.get("titulo"):
        raise SemReceita("duelo precisa de `titulo` e de 2 `lados` [{piloto, valor, em}]")
    pil = _pilotos_sessao(p.get("sessao"))
    out = []
    for k, l in enumerate(lados):
        info = pil.get(str(l.get("piloto")), {})
        if not info:
            raise FaltaAtivo(f"duelo: piloto {l.get('piloto')} sem comparação da sessão {p.get('sessao')} (kit/graficos/py/preparar.py)")
        out.append({"sigla": info.get("sigla"), "nome": (info.get("nome") or "").title(), "equipe": info.get("equipe"),
                    "cor": l.get("cor") or info.get("cor"), "valor": str(l["valor"]),
                    "em": round(_t_palavra(palavras, l.get("i"), cena["t0"], 0.25 + 0.6 * k), 4)})
    camada = {"kit": "duelo", "titulo": str(p["titulo"]), "unidade": str(p.get("unidade", "")), "lados": out,
              "destaque": p.get("destaque"), "rodape": str(p.get("rodape", "")),
              "destaqueEm": round(_t_palavra(palavras, p.get("i"), cena["t0"], max(x["em"] for x in out) + 0.4), 4)}
    return camada, sorted((KIT / "graficos" / "comparacoes").glob(f"{p.get('sessao')}_*.json"))


# ---------------------------------------------------------------- Remotion: foco (num texto da cena)
def _foco(cena: dict, usos: list[dict], palavras: list[dict], alvos: dict, dur: float) -> dict:
    """Desfoca tudo menos o alvo. Alvo = índice de um `texto` da cena (caixa medida na fonte, estável) ou caixa
    {x, y, w, h} em px de 1920×1080. Entra na palavra `i` (ou 0,3 s) e fica até o fim da cena."""
    focos = []
    for k, p in enumerate(usos):
        alvo = p.get("alvo", 0)
        if isinstance(alvo, dict) and all(c in alvo for c in ("x", "y", "w", "h")):
            caixa = {c: float(alvo[c]) for c in ("x", "y", "w", "h")}
        elif str(alvo).isdigit() and f"t{int(alvo)}" in alvos:
            caixa = alvos[f"t{int(alvo)}"]["caixa"]
        else:
            raise SemReceita(f"foco: alvo {alvo!r} não é um texto da cena nem uma caixa {{x,y,w,h}}")
        em = _t_palavra(palavras, p.get("i"), cena["t0"], 0.3)
        focos.append({"id": f"f{k}", "em": round(em, 4), "ate": round(dur + 1.0, 4), "alvo": {"caixa": caixa},
                      "blur": float(p.get("blur", 10)), "escurecer": float(p.get("escurecer", 0.10)),
                      "folga": float(p.get("folga", 18)), "forma": p.get("forma", "caixa")})
    return {"kit": "foco", "cena": {"largura": BASE_W, "altura": BASE_H, "fps": FPS, "duracao": round(dur + 1.0, 4), "focos": focos}}


# ---------------------------------------------------------------- HyperFrames: gps
def _gps(cena: dict, p: dict, dur: float, palavras: list[dict] | None = None) -> tuple[dict, dict, list[Path]]:
    palavras = palavras or []
    s = p.get("sessao")
    carros = p.get("carros") or []
    if not carros:
        raise SemReceita("gps sem carros")
    voltas, arquivos, assets, voltas_json = [], [], {}, []
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
        voltas_json.append(v)
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
           "duracao": round(dur, 4), "hud": bool(p.get("hud", True)), "nota": _nota_gps(p, voltas_json),
           # rodada 1 (placar 73,8): mundo em volta da pista plana, etiqueta por carro, minimapa, número da curva,
           # velocidade segurada na palavra (marcar) e rótulo ancorado na fala (rotulos)
           "mundo": bool(p.get("mundo", True)), "minimapa": bool(p.get("minimapa", True)),
           "etiquetas": bool(p.get("etiquetas", True)), "curvas": _curvas_gps(voltas_json, p),
           "marcas": [{"t": round(_t_palavra(palavras, m.get("i"), cena["t0"], 0.0), 4), "dur": float(m.get("dur", 1.6))}
                      for m in p.get("marcar") or []],
           "rotulos": [{"t": round(_t_palavra(palavras, r.get("i"), cena["t0"], 0.0), 4), "texto": str(r["texto"])}
                       for r in p.get("rotulos") or [] if r.get("texto")]}
    arquivos += [x for x in [KIT / "graficos" / "pista" / f"{voltas_json[0].get('circuito')}.json"] if x.exists()]
    if cfg["camera"] not in CAMERAS_GPS:
        raise SemReceita(f"gps: camera_gps '{cfg['camera']}' (há: {', '.join(CAMERAS_GPS)})")
    return cfg, assets, arquivos


CAMERAS_GPS = ("perseguicao", "fixa", "alta")


def _curvas_gps(voltas: list[dict], p: dict) -> list[dict]:
    """Placas de número de curva na pista: as curvas NUMERADAS de kit/graficos/pista/<circuito>.json (as mesmas dos
    gráficos, conferidas na telemetria), como fração da volta. `curvas: false` na SPEC tira; lista de números filtra."""
    pedido = p.get("curvas", True)
    if not voltas or pedido is False:
        return []
    arq = KIT / "graficos" / "pista" / f"{voltas[0].get('circuito')}.json"
    if not arq.exists():
        return []
    d = json.loads(arq.read_text(encoding="utf-8"))
    L = float(d.get("comprimento_m") or 0)
    return [{"n": c["n"], "frac": round(float(c["d"]) / L, 5)} for c in d.get("curvas", [])
            if L and (pedido is True or c["n"] in pedido)]
SESSAO_PT = {"Qualifying": "classificação", "Race": "corrida", "Sprint": "sprint", "Sprint Qualifying": "classificação sprint",
             "Practice 1": "TL1", "Practice 2": "TL2", "Practice 3": "TL3"}


def _nota_gps(p: dict, voltas: list[dict]) -> str:
    """Rodapé da cena GPS: o relógio (tempo real / acelerado / câmera lenta) e a fonte. `nota` na SPEC substitui;
    `nota: ""` tira. Uso real (card "Nove milésimos", 2026-11-14): a cena GPS não dizia se era tempo real."""
    if "nota" in p:
        return str(p["nota"] or "")
    f = float(p.get("fator", 1.0))
    rel = "tempo real" if abs(f - 1) < 1e-6 else (f"acelerado {f:g}×" if f > 1 else f"câmera lenta {1 / f:g}×").replace(".", ",")
    v = voltas[0] if voltas else {}
    sessao = SESSAO_PT.get(str(v.get("sessao_nome")), v.get("sessao_nome"))
    fonte = " ".join(str(x) for x in (v.get("circuito"), v.get("ano"), sessao) if x)
    return f"{rel} · Dados: OpenF1" + (f" · {fonte}" if fonte else "")


# ---------------------------------------------------------------- entrada
FONTES_CODIGO = {
    ("remotion", "graficos"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "graficos" / "CamadaGrafico.tsx",
                               KIT / "graficos" / "graficos.ts"],
    ("remotion", "anotacao"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "anotacao" / "CamadaAnotacao.tsx",
                               KIT / "anotacao" / "anotacao.ts"],
    ("remotion", "cartoes"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "cartoes" / "CamadaCartoes.tsx",
                              KIT / "cartoes" / "cartoes.ts", KIT / "cartoes" / "larguras.ts"],
    ("remotion", "foco"): [HORIZ / "remotion" / "cena" / "index.tsx", HORIZ / "remotion" / "foco" / "CamadaFoco.tsx",
                           KIT / "foco" / "foco.ts", HORIZ / "remotion" / "anotacao" / "CamadaAnotacao.tsx"],
    ("hyperframes", "gps"): [AQUI / "hyperframes" / "gps.html", KIT / "gps" / "src" / "gps.js", KIT / "gps" / "src" / "gps_three.js", KIT / "gps" / "src" / "gps_mundo.js",
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
        cart = [u["params"] for u in usos if u["kit"] == "cartoes" and u["params"].get("tipo") != "duelo"]
        duelo = [u["params"] for u in usos if u["kit"] == "cartoes" and u["params"].get("tipo") == "duelo"]
        foco = [u["params"] for u in usos if u["kit"] == "foco"]
        if duelo:
            if len(duelo) > 1 or graf or cart or anot or foco:
                raise SemReceita("duelo ocupa a tela: uma por cena, sem gráfico/cartão/anotação/foco")
            c, a = _duelo(cena, duelo[0], palavras, dur)
            camadas.append(c)
            arquivos += a
        outros = [k for k in kits if k not in ("graficos", "anotacao", "cartoes", "foco")]
        if outros:
            raise SemReceita(f"kit {', '.join(outros)} ainda sem receita no Remotion (há: graficos, anotacao, cartoes, foco)")
        if len(graf) > 1:
            raise SemReceita("mais de um gráfico na mesma cena: divida em cenas")
        if cart and (graf or anot or foco):
            raise SemReceita("cartão de capítulo ocupa a tela cheia: não junte com gráfico, anotação ou foco na mesma cena")
        if graf:
            c, a = _graficos(cena, graf[0], palavras, dur)
            camadas.append(c)
            arquivos += a
        if cart:
            c, a = _cartoes(cena, cart, palavras, dur)
            camadas.append(c)
            arquivos += a
        if anot or (foco and cena.get("texto") and not graf):
            # textos da cena (+ anotações): o foco num texto precisa dos textos desenhados mesmo sem anotação
            c, a = _anotacao(cena, anot, palavras, dur)
            camadas.append(c)
            arquivos += a
        if foco:
            _, alvos = _layout_textos(cena.get("texto") or []) if not graf else ([], {})
            camadas.append(_foco(cena, foco, palavras, alvos, dur))
        job["props"] = {"quadros": quadros, "pre": pre, "camadas": camadas}
        if cena.get("movimento"):   # câmera da cena inteira (ação direta do storyboard; montador/movimento.js)
            job["props"].update(movimento=cena["movimento"], L=quadros - pre - pos)
    elif motor == "hyperframes":
        outros = [k for k in kits if k != "gps"]
        if outros:
            raise SemReceita(f"kit {', '.join(outros)} ainda sem receita no HyperFrames (há: gps)")
        if len(usos) > 1:
            raise SemReceita("mais de um uso de gps na mesma cena: junte os carros em um só")
        cfg, assets, a = _gps(cena, usos[0]["params"], dur, palavras)
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
