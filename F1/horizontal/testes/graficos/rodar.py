"""Verificação automática do kit/graficos + render nos DOIS motores + folhas de sequência a 60 q/s.

Passos:
 1. regera kit/graficos/graficos.global.js (esbuild) e roda a checagem geométrica do kit (cli.ts checar) no tema claro
    (a cena de exemplo) e no escuro (mesma cena, tema trocado);
 2. DADOS PLOTADOS = DADOS DA FONTE, com conta independente do kit (numpy, direto do cache bruto do OpenF1):
    - laps: tempos de volta e de setor do JSON = os do /v1/laps; amostras brutas do JSON = as do /v1/car_data;
    - refaz a distância (integral da velocidade) e confere as séries da grade;
    - pega a GEOMETRIA montada pelo kit (pontos em px), desfaz a escala do eixo e compara cada ponto com a fonte
      (velocidade, acelerador, marcha em degrau, vantagem acumulada), as barras de freio com o freio bruto, as barras de
      setor com os tempos oficiais, as barras do normalizado com as métricas refeitas aqui, e os números escritos;
    - curvas nomeadas: cada curva lenta tem de estar a ≤ 60 m de um mínimo local de velocidade;
    - minimapa: o traçado anda no sentido anti-horário (Interlagos) e o trecho destacado corresponde à distância;
 3. mede as caixas REAIS dos textos no Chrome (getBBox na horizontal, tinta de measureText na vertical) com o estado
    final de cada gráfico: nenhum par se sobrepõe, todos dentro da área, e a estimativa do kit não fica menor que o real;
 4. renderiza a cena em PNG quadro a quadro no Remotion e no HyperFrames e mede nos PIXELS: nada desenhado fora da
    área de cada gráfico (todos os quadros), o desenho progressivo só avança e bate com o cursor do kit, e as âncoras de
    tempo do delta (`ritmo`) caem no ponto certo; compara os dois motores;
 5. folhas de sequência (JPG) nesta pasta + resultado.json.

Rodar:  .venv\\Scripts\\python.exe F1\\horizontal\\testes\\graficos\\rodar.py [--sem-render] [--so-dados]
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
HORIZ = AQUI.parents[1]
KIT = HORIZ / "kit" / "graficos"
GPS = HORIZ / "kit" / "gps"
RAIZ = HORIZ.parents[1]
SAIDA = AQUI / "saida"
HF_VERSAO = "hyperframes@0.9.20"
CENA = KIT / "exemplo" / "cena.json"


def node_modules() -> Path:
    for base in [RAIZ, *RAIZ.parents]:
        p = base / "F1" / "video" / "node_modules"
        if (p / "@remotion" / "cli").is_dir():
            return p
    raise SystemExit("F1/video/node_modules não encontrado (rode npm install em F1/video na pasta principal)")


NM = node_modules()
NAVEGADOR = NM / ".remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print((r.stdout or "")[-3000:], (r.stderr or "")[-3000:])
        raise SystemExit(f"falhou: {' '.join(map(str, cmd[:4]))}")
    return r


def construir_global() -> None:
    esbuild = NM / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    sh([esbuild, "graficos.ts", "--bundle", "--format=iife", "--global-name=Graficos", "--target=es2019", "--charset=utf8",
        "--banner:js=// GERADO por F1/horizontal/testes/graficos/rodar.py (esbuild de graficos.ts). Não editar à mão.",
        "--outfile=graficos.global.js", "--log-level=warning"], cwd=KIT)


def kit_json(cmd: str, cena: Path, *args: str):
    return json.loads(sh(["node", KIT / "cli.ts", cmd, cena, *args]).stdout)


# ============================================================== 2. dados plotados = fonte
def ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


class Falhas(list):
    def conferir(self, cond: bool, msg: str) -> bool:
        if not cond:
            self.append(msg)
        return cond


def fonte_bruta(D: dict) -> dict:
    """Do cache do OpenF1 (kit/gps/cache) se houver; senão das amostras brutas guardadas no JSON (avisado)."""
    cache = GPS / "cache" / str(D["sessao"])
    out = {"origem": "cache OpenF1" if cache.is_dir() else "amostras brutas do JSON (cache ausente)"}
    for P in D["pilotos"]:
        n = P["numero"]
        if cache.is_dir():
            laps = json.loads((cache / f"laps_driver_number-{n}.json").read_text(encoding="utf-8"))
            lap = next(l for l in laps if l["lap_number"] == P["volta"])
            cd = sorted(json.loads((cache / f"car_data_driver_number-{n}.json").read_text(encoding="utf-8")), key=lambda r: r["date"])
            t0 = ts(lap["date_start"])
            tt = np.array([ts(r["date"]) - t0 for r in cd])
            i0 = max(0, int(np.searchsorted(tt, 0.0)) - 1)
            i1 = min(len(cd), int(np.searchsorted(tt, lap["lap_duration"])) + 1)
            sel = cd[i0:i1]
            out[P["sigla"]] = {"lap": lap, "t": tt[i0:i1], "vel": np.array([r["speed"] for r in sel], float),
                               "acel": np.array([r["throttle"] for r in sel], float), "freio": np.array([r["brake"] for r in sel], float),
                               "marcha": np.array([r["n_gear"] for r in sel], float), "date": [r["date"] for r in sel]}
        else:
            b = P["bruto"]
            out[P["sigla"]] = {"lap": {"lap_duration": P["tempo"], "duration_sector_1": P["setores"][0], "duration_sector_2": P["setores"][1],
                                       "duration_sector_3": P["setores"][2]},
                               "t": np.array(b["t"]), "vel": np.array(b["vel"], float), "acel": np.array(b["acel"], float),
                               "freio": np.array(b["freio"], float), "marcha": np.array(b["marcha"], float), "date": b["date"]}
        F = out[P["sigla"]]
        # distância refeita aqui (independente do preparar.py): trapézio da velocidade, 0 em t=0, comprimento em t=fim
        v = F["vel"] / 3.6
        acc = np.concatenate([[0.0], np.cumsum(np.diff(F["t"]) * (v[1:] + v[:-1]) / 2)])
        a0, a1 = np.interp(0.0, F["t"], acc), np.interp(F["lap"]["lap_duration"], F["t"], acc)
        F["d"] = (acc - a0) / (a1 - a0) * D["comprimento_m"]
        F["tempo_em"] = lambda d, F=F: np.interp(d, F["d"], F["t"])
    return out


def degrau(F: dict, campo: str, d: float) -> float:
    i = int(np.clip(np.searchsorted(F["d"], d, side="right") - 1, 0, len(F["d"]) - 1))
    return float(F[campo][i])


def fmt(v: float, casas: int = 0) -> str:
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if v < 0 and abs(v) >= 0.5 * 10 ** -casas else "") + s


def conferir_dados(D: dict, mont: dict, falhas: Falhas) -> dict:
    F = fonte_bruta(D)
    rel: dict = {"origem": F["origem"], "series": {}, "barras": {}, "textos": [], "curvas": {}}
    g = np.array(D["grade_d"])
    for P in D["pilotos"]:
        S, lap = F[P["sigla"]], F[P["sigla"]]["lap"]
        falhas.conferir(P["tempo"] == lap["lap_duration"], f"{P['sigla']}: tempo de volta {P['tempo']} ≠ laps {lap['lap_duration']}")
        falhas.conferir(P["setores"] == [lap["duration_sector_1"], lap["duration_sector_2"], lap["duration_sector_3"]], f"{P['sigla']}: setores ≠ laps")
        if F["origem"].startswith("cache"):
            falhas.conferir(P["bruto"]["date"] == S["date"] and P["bruto"]["vel"] == S["vel"].tolist(), f"{P['sigla']}: amostras brutas do JSON ≠ car_data do OpenF1")
        # séries da grade × fonte refeita
        e = {c: float(np.max(np.abs(np.array(P[c]) - np.interp(g, S["d"], S[c] if c != "acel" else np.clip(S["acel"], 0, 100))))) for c in ("vel", "acel")}
        e["t"] = float(np.max(np.abs(np.array(P["t"]) - S["tempo_em"](g))))
        rel["series"][f"{P['sigla']}_grade"] = {k: round(v, 4) for k, v in e.items()}
        falhas.conferir(e["vel"] < 0.02 and e["acel"] < 0.06 and e["t"] < 0.001, f"{P['sigla']}: grade ≠ fonte refeita {e}")
    A, B = D["pilotos"]
    FA, FB = F[A["sigla"]], F[B["sigla"]]
    vant = lambda d: FB["tempo_em"](d) - FA["tempo_em"](d)  # >0: A à frente
    falhas.conferir(abs(-D["delta"][-1] - (B["tempo"] - A["tempo"])) < 1e-6, f"delta final {D['delta'][-1]} ≠ diferença dos tempos de volta")
    campo_painel = {"acel": "acelerador", "marcha": "marcha", "vel": "velocidade"}
    for G in mont["graficos"]:
        gid, tipo = G["spec"]["id"], G["spec"]["tipo"]
        for e in G["elementos"]:
            if e["tipo"] == "linha" and e.get("serie"):
                sr = e["serie"]
                eixo = G["eixos"][0] if tipo in ("velocidade", "delta") else next(x for x in G["eixos"] if x["nome"] == campo_painel[sr["campo"]])
                pts = np.array(e["pts"])
                d = eixo["d0"] + (pts[:, 0] - eixo["x0"]) / (eixo["x1"] - eixo["x0"]) * (eixo["d1"] - eixo["d0"])
                v = eixo["v0"] + (pts[:, 1] - eixo["y0"]) / (eixo["y1"] - eixo["y0"]) * (eixo["v1"] - eixo["v0"])
                if sr["campo"] == "vantagem":
                    ref = vant(d)
                    err = np.abs(v - ref)
                    tol = 0.0015
                elif sr.get("degrau"):
                    Fp = F[sr["piloto"]]
                    # num degrau cada x tem dois pontos (antes/depois da troca): vale o valor bruto de um dos lados
                    err = np.array([min(abs(vv - degrau(Fp, sr["campo"], dd - 1e-6)), abs(vv - degrau(Fp, sr["campo"], dd + 1e-6)),
                                        abs(vv - degrau(Fp, sr["campo"], dd - D["passo_m"]))) for dd, vv in zip(d, v)])
                    tol = 1e-6
                else:
                    Fp = F[sr["piloto"]]
                    y = np.clip(Fp[sr["campo"]], 0, 100) if sr["campo"] == "acel" else Fp[sr["campo"]]
                    err = np.abs(v - np.interp(d, Fp["d"], y))
                    tol = 0.06 if sr["campo"] == "acel" else 0.02
                rel["series"][e["id"]] = {"pontos": len(pts), "erro_max": round(float(err.max()), 5), "unidade": sr["campo"],
                                          "d": [round(float(d.min()), 1), round(float(d.max()), 1)]}
                falhas.conferir(float(err.max()) <= tol, f"{e['id']}: ponto plotado difere da fonte em {err.max():.4f} ({sr['campo']})")
        textos = {e["id"].split(":", 1)[1]: e["texto"] for e in G["elementos"] if e["tipo"] == "texto"}
        rets = {e["id"].split(":", 1)[1]: e for e in G["elementos"] if e["tipo"] == "ret"}
        if tipo == "setores":
            pares = [(A["setores"][k], B["setores"][k]) for k in range(3)] + [(A["tempo"], B["tempo"])]
            for k, (a, b) in enumerate(pares):
                r = rets[f"barra-{k}"]
                lado_ok = (r["revela"] == "esq") == (a < b)
                falhas.conferir(abs(r["w"] / r["escala"] - abs(a - b)) < 1e-9 and lado_ok, f"setores: barra {k} ≠ |{a}−{b}| ou lado errado")
                falhas.conferir(textos[f"val-{k}"] == f"{fmt(abs(a - b), 3)} s", f"setores: texto {textos[f'val-{k}']!r}")
                rel["barras"][f"setor{k + 1}"] = {"lec_menos_ant_s": round(a - b, 3), "px": round(r["w"], 2), "texto": textos[f"val-{k}"]}
        if tipo == "normalizado":
            d0, d1 = G["spec"].get("trecho") or [0, D["comprimento_m"]]
            for m in G["spec"].get("metricas") or ["vmax", "vmin", "vmedia", "acelPleno", "freando"]:
                va, vb = (metrica_py(F[P["sigla"]], m, d0, d1) for P in (A, B))
                maior = m != "freando"
                aM = va > vb if maior else va < vb
                mel, pio = (va, vb) if aM else (vb, va)
                pct = abs((mel - pio) / pio * 100 if maior else (pio - mel) / pio * 100)
                rel["barras"][m] = {A["sigla"]: round(va, 3), B["sigla"]: round(vb, 3), "vantagem_pct": round(pct, 3), "texto": textos.get(f"val-{m}")}
                if f"barra-{m}" in rets:
                    r = rets[f"barra-{m}"]
                    falhas.conferir(abs(r["w"] / r["escala"] - pct) < 1e-3 and (r["revela"] == "esq") == aM, f"normalizado {m}: barra {r['w'] / r['escala']:.4f}% ≠ {pct:.4f}%")
                else:
                    falhas.conferir(textos.get(f"val-{m}") == "empate", f"normalizado {m}: sem barra e sem 'empate'")
                casas = {"vmax": 0, "vmin": 0, "vmedia": 2, "acelPleno": 1, "freando": 2}[m]
                u = "%" if m == "acelPleno" else " km/h" if m.startswith("v") else " s"
                esperado = f"{A['sigla']} {fmt(va, casas)}{u} · {B['sigla']} {fmt(vb, casas)}{u}"
                # número escrito = valor da fonte arredondado (tolerância de meia unidade da última casa + 1e-4,
                # porque um valor como 19,1249999 × 19,1250001 pode arredondar para lados diferentes)
                nums = [float(x.replace(".", "").replace(",", ".")) for x in re.findall(r"\d[\d.]*,?\d*", textos.get(f"real-{m}", ""))]
                ok = len(nums) == 2 and all(abs(n - v) <= 0.5 * 10 ** -casas + 1e-4 for n, v in zip(nums, (va, vb)))
                falhas.conferir(ok, f"normalizado {m}: texto {textos.get(f'real-{m}')!r} ≠ {esperado!r}")
        if tipo == "telemetria":
            d0, d1 = G["spec"]["trecho"]
            for j, P in enumerate((A, B)):
                Fp = F[P["sigla"]]
                faixas = [(r["x"], r["x"] + r["w"]) for k, r in rets.items() if k.startswith(f"freio-{j}-")]
                eixo = next(x for x in G["eixos"] if x["nome"] == "freio")
                xs = lambda d: eixo["x0"] + (d - eixo["d0"]) / (eixo["d1"] - eixo["d0"]) * (eixo["x1"] - eixo["x0"])
                erros = 0
                for d in g[(g >= d0) & (g <= d1)]:
                    on = degrau(Fp, "freio", d) > 0
                    coberto = any(a - 0.01 <= xs(d) <= b + 0.01 for a, b in faixas)
                    erros += on != coberto
                rel["barras"][f"freio_{P['sigla']}"] = {"faixas": len(faixas), "pontos_errados": erros}
                falhas.conferir(erros == 0, f"telemetria: freio de {P['sigla']} desenhado ≠ fonte em {erros} pontos")
        for chave, txt in textos.items():
            mm = re.match(r"(\w+) ganha ([\d,]+) s aqui", txt)
            if mm:
                faixa = next(e for e in G["elementos"] if e["id"].endswith("destaque-faixa"))
                eixo = G["eixos"][0]
                dd = [eixo["d0"] + (x - eixo["x0"]) / (eixo["x1"] - eixo["x0"]) * (eixo["d1"] - eixo["d0"]) for x in (faixa["x"], faixa["x"] + faixa["w"])]
                ganho = vant(dd[1]) - vant(dd[0])  # >0: A ganhou
                quem = A["sigla"] if ganho > 0 else B["sigla"]
                esperado = f"{quem} ganha {fmt(abs(ganho), 3)} s aqui"
                rel["textos"].append({"grafico": gid, "texto": txt, "esperado": esperado, "trecho_m": [round(x, 1) for x in dd]})
                falhas.conferir(txt == esperado, f"{gid}: destaque {txt!r} ≠ fonte {esperado!r}")
            if chave == "fim-delta":
                esperado = f"{fmt(abs(vant(D['comprimento_m'])), 3)} s"
                falhas.conferir(txt == esperado, f"{gid}: valor final {txt!r} ≠ {esperado!r}")
    # curvas nomeadas × mínimo local de velocidade (curvas lentas)
    for P in (A, B):
        Fp = F[P["sigla"]]
        v = np.interp(g, Fp["d"], Fp["vel"])
        mins = [g[i] for i in range(10, len(v) - 10) if v[i] == v[i - 10:i + 11].min() and v[max(0, i - 60):i + 61].max() - v[i] > 25]
        for c in D["curvas"]:
            if not c["nome"]:
                continue
            perto = min((abs(m - c["d"]) for m in mins), default=1e9)
            vmin = float(v[(g > c["d"] - 80) & (g < c["d"] + 80)].min())
            # ≤ 60 m de um mínimo: curva de frenagem no lugar certo; > 150 m: curva feita sem tirar (sem mínimo perto);
            # entre 60 e 150 m: distância da curva desalinhada da telemetria → falha
            tipo_c = "frenagem" if perto <= 60 else "sem mínimo perto (de pé embaixo)" if perto > 150 else "DESALINHADA"
            rel["curvas"].setdefault(c["nome"], {})[P["sigla"]] = {"dist_ao_minimo_m": round(float(perto), 1), "vmin_kmh": round(vmin), "tipo": tipo_c}
            falhas.conferir(tipo_c != "DESALINHADA", f"curva {c['nome']} ({c['d']} m) a {perto:.0f} m do mínimo de velocidade de {P['sigla']}")
    # minimapa: sentido e trecho
    tr = D.get("tracado")
    if tr:
        x, z = np.array(tr["x"]), np.array(tr["z"])
        area2 = float(np.sum(x * np.roll(z, -1) - np.roll(x, -1) * z)) / 2  # na tela (z para baixo): <0 = anti-horário
        rel["minimapa"] = {"area_assinada_tela": round(area2, 1), "sentido": "anti-horário" if area2 < 0 else "horário",
                           "pontos": len(x), "d_final": tr["d"][-1]}
        falhas.conferir(area2 < 0, "minimapa: traçado no sentido horário (Interlagos é anti-horário: pista espelhada?)")
        falhas.conferir(abs(tr["d"][-1] - D["comprimento_m"]) < 15 and tr["d"][0] < 15, "minimapa: distância do traçado não cobre a volta")
    return rel


def metrica_py(F: dict, m: str, d0: float, d1: float) -> float:
    sel = (F["d"] >= d0) & (F["d"] <= d1)
    if m == "vmedia":
        return (d1 - d0) / (F["tempo_em"](d1) - F["tempo_em"](d0)) * 3.6
    if m == "vmax":
        return float(F["vel"][sel].max())
    if m == "vmin":
        return float(F["vel"][sel].min())
    idx = np.nonzero(sel)[0]
    if m == "acelPleno":
        dd = np.diff(F["d"][idx])
        cheio = (F["acel"][idx][:-1] >= 98) & (F["acel"][idx][1:] >= 98)
        return float(100 * dd[cheio].sum() / dd.sum())
    dt = np.diff(F["t"][idx])
    return float(dt[F["freio"][idx][:-1] > 0].sum())


# ============================================================== 3. caixas reais dos textos no Chrome
MEDIR_JS = r"""
(function () {
  var cena = window.__CENA, specs = cena.graficos.map(function (g) { return Object.assign({ tema: cena.tema }, g); });
  var m = Graficos.montar(specs, window.__DADOS, window.__LARGURAS);
  var svg = document.getElementById("g"), cam = CamadaGrafico.criar(svg, m);
  var cv = document.createElement("canvas").getContext("2d"), out = {};
  m.graficos.forEach(function (g) {
    cam.render(g.fim + 0.01);
    var lista = [];
    g.elementos.forEach(function (e) {
      if (e.tipo !== "texto") return;
      var n = cam.nos[e.id];
      if (+n.getAttribute("opacity") <= 0) return;
      var bb = n.getBBox();
      cv.font = e.peso + " " + e.tam + "px " + m.fonteCss;
      var mt = cv.measureText(e.texto);
      lista.push({ id: e.id, texto: e.texto, x: bb.x, w: bb.width, y: e.y - mt.actualBoundingBoxAscent,
                   h: mt.actualBoundingBoxAscent + mt.actualBoundingBoxDescent, est: e.caixa, fonte: document.fonts.check(cv.font) });
    });
    out[g.spec.id] = { area: g.spec.area, textos: lista };
  });
  document.getElementById("saida").textContent = JSON.stringify(out);
})();
"""


def projeto_hf(dest: Path, cena_arq: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "assets").mkdir(parents=True)
    shutil.copy2(HORIZ / "hyperframes" / "graficos" / "exemplo" / "index.html", dest / "index.html")
    shutil.copy2(KIT / "graficos.global.js", dest / "assets" / "graficos.global.js")
    shutil.copy2(HORIZ / "hyperframes" / "graficos" / "camada.js", dest / "assets" / "camada.js")
    cena = json.loads(cena_arq.read_text(encoding="utf-8"))
    (dest / "assets" / "cena.js").write_text("window.__CENA = " + json.dumps(cena, ensure_ascii=False) + ";", encoding="utf-8")
    (dest / "assets" / "dados.js").write_text("window.__DADOS = " + (KIT / cena["dados"]).read_text(encoding="utf-8") + ";", encoding="utf-8")
    (dest / "assets" / "larguras.js").write_text("window.__LARGURAS = " + (KIT / "fonte" / "segoe_larguras.json").read_text(encoding="utf-8") + ";", encoding="utf-8")
    (dest / "package.json").write_text(json.dumps({"name": "exemplo-graficos", "private": True, "type": "module"}), encoding="utf-8")


def medir_textos(falhas: Falhas) -> dict:
    proj = SAIDA / "medir"
    projeto_hf(proj, CENA)
    html = ("<!doctype html><meta charset='utf-8'><body style='margin:0'>"
            "<svg id='g' width='1920' height='1080' viewBox='0 0 1920 1080'></svg><pre id='saida'></pre>"
            "<script src='assets/graficos.global.js'></script><script src='assets/camada.js'></script>"
            "<script src='assets/cena.js'></script><script src='assets/dados.js'></script><script src='assets/larguras.js'></script>"
            f"<script>{MEDIR_JS}</script></body>")
    (proj / "medir.html").write_text(html, encoding="utf-8")
    r = sh([NAVEGADOR, "--headless", "--disable-gpu", "--allow-file-access-from-files", "--virtual-time-budget=8000",
            "--dump-dom", (proj / "medir.html").as_uri()])
    m = re.search(r"<pre id=\"saida\">(.*?)</pre>", r.stdout, re.S)
    if not m or not m.group(1).strip():
        falhas.append("medição de textos no Chrome não retornou nada")
        return {}
    import html as H
    dados = json.loads(H.unescape(m.group(1)))
    rel = {}
    for gid, G in dados.items():
        a, ts_ = G["area"], G["textos"]
        menor, sobre, fora, subest = 1e9, [], [], 0.0
        for i in range(len(ts_)):
            p = ts_[i]
            if p["x"] < a["x"] or p["y"] < a["y"] or p["x"] + p["w"] > a["x"] + a["w"] or p["y"] + p["h"] > a["y"] + a["h"]:
                fora.append(p["texto"])
            e = p["est"]
            subest = max(subest, e["x"] - p["x"], (p["x"] + p["w"]) - (e["x"] + e["w"]), e["y"] - p["y"], (p["y"] + p["h"]) - (e["y"] + e["h"]))
            for j in range(i + 1, len(ts_)):
                q = ts_[j]
                folga = max(q["x"] - (p["x"] + p["w"]), p["x"] - (q["x"] + q["w"]), q["y"] - (p["y"] + p["h"]), p["y"] - (q["y"] + q["h"]))
                menor = min(menor, folga)
                if folga < 2:
                    sobre.append(f"{p['texto']!r} × {q['texto']!r} ({folga:.1f} px)")
        rel[gid] = {"textos": len(ts_), "menor_folga_real_px": round(menor, 1), "sobrepostos": sobre, "fora_da_area": fora,
                    "real_maior_que_estimado_px": round(subest, 2)}
        falhas.conferir(not sobre, f"{gid}: textos sobrepostos no Chrome: {sobre[:4]}")
        falhas.conferir(not fora, f"{gid}: texto fora da área: {fora[:4]}")
        falhas.conferir(subest <= 2.0, f"{gid}: caixa real passa {subest:.1f} px da estimada pelo kit")
    return rel


# ============================================================== 4. render e pixels
def render_remotion(dest: Path) -> None:
    if not (HORIZ / "remotion" / "node_modules" / "remotion").is_dir():
        junc = HORIZ / "remotion" / "graficos" / "node_modules"
        if not junc.exists():
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junc), str(NM)], check=True, capture_output=True)
    if dest.exists():
        shutil.rmtree(dest)
    sh(["node", NM / "@remotion" / "cli" / "remotion-cli.js", "render", "index.tsx", "ExemploGraficos", dest, "--sequence",
        "--image-format=png", f"--browser-executable={NAVEGADOR}", "--log=error"], cwd=HORIZ / "remotion" / "graficos" / "exemplo")


def render_hyperframes(dest: Path) -> None:
    proj = SAIDA / "hf_projeto"
    projeto_hf(proj, CENA)
    if dest.exists():
        shutil.rmtree(dest)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    sh([npx, "--yes", HF_VERSAO, "render", "--format", "png-sequence", "--output", dest, "--quiet"], cwd=proj)


def medir_pixels(motor: str, arqs: list[Path], cena: dict, mont: dict, falhas: Falhas) -> dict:
    fps = cena["fps"]
    fundo = np.array([int(cena_fundo(mont)[i:i + 2], 16) for i in (1, 3, 5)])
    rel = {"motor": motor, "quadros": len(arqs), "fora_da_area_px": 0, "pior_fora": None, "cursor": {}}
    falhas.conferir(len(arqs) == round(cena["duracao"] * fps) + 1, f"{motor}: {len(arqs)} quadros (esperado {round(cena['duracao'] * fps) + 1})")
    graf = mont["graficos"]
    for q, arq in enumerate(arqs):
        t = q / fps
        img = np.asarray(Image.open(arq).convert("RGB")).astype(np.int16)
        tinta = np.abs(img - fundo).sum(-1) > 24
        ativos = [G for G in graf if G["spec"]["em"] <= t < G["spec"].get("ate", 1e9)]
        dentro = np.zeros(tinta.shape, bool)
        for G in ativos:
            a = G["spec"]["area"]
            dentro[int(a["y"]):int(math.ceil(a["y"] + a["h"])), int(a["x"]):int(math.ceil(a["x"] + a["w"]))] = True
        n = int((tinta & ~dentro).sum())
        if n:
            rel["fora_da_area_px"] += n
            if not rel["pior_fora"] or n > rel["pior_fora"][1]:
                rel["pior_fora"] = [q, n]
        # desenho progressivo: x mais à direita da série A dentro do plot (cor da equipe) × cursor do kit
        for G in ativos:
            if not G["cursor"] or G["spec"]["tipo"] not in ("velocidade", "delta"):
                continue
            pl, cur = G["plot"], G["cursor"]
            # todas as séries (uma linha pode estar por baixo da outra na ponta): o pixel mais à direita de qualquer uma
            cores = [np.array([int(e["cor"][i:i + 2], 16) for i in (1, 3, 5)]) for e in G["elementos"] if e.get("serie") and e["papel"] == "dado"]
            y0, y1 = int(pl["y"]) + 2, int(pl["y"] + pl["h"]) - 2
            x0, x1 = int(pl["x"]), int(pl["x"] + pl["w"]) + 3
            sub = img[y0:y1, x0:x1]
            mask = np.any([np.abs(sub - cor).sum(-1) < 60 for cor in cores], axis=0)
            cols = np.nonzero(mask.any(0))[0]
            xm = float(x0 + cols.max()) if len(cols) else None
            dc = float(np.interp(t, [r["t"] for r in cur["ritmo"]], [r["d"] for r in cur["ritmo"]]))
            xk = cur["x0"] + (dc - cur["d0"]) / (cur["d1"] - cur["d0"]) * (cur["x1"] - cur["x0"]) if t >= cur["ritmo"][0]["t"] else None
            rel["cursor"].setdefault(G["spec"]["id"], []).append([q, xm, xk])
    for gid, serie in rel["cursor"].items():
        recuos = sum(1 for a, b in zip(serie, serie[1:]) if a[1] is not None and b[1] is not None and b[1] < a[1] - 1.5)
        errs = [abs(xm - xk) for _, xm, xk in serie if xm is not None and xk is not None]
        # a linha tem largura (ponta redonda): o pixel colorido mais à direita fica até ~meia largura além do cursor
        rel["cursor"][gid] = {"quadros": len(serie), "recuos": recuos, "erro_max_px": round(max(errs), 2) if errs else None,
                              "amostras": serie[:: max(1, len(serie) // 12)]}
        falhas.conferir(recuos == 0, f"{motor} {gid}: desenho recuou em {recuos} quadros")
        falhas.conferir(bool(errs) and max(errs) <= 4.5, f"{motor} {gid}: ponta do desenho longe do cursor do kit ({max(errs) if errs else '-'} px)")
    falhas.conferir(rel["fora_da_area_px"] == 0, f"{motor}: {rel['fora_da_area_px']} px desenhados fora da área (pior {rel['pior_fora']})")
    return rel


def cena_fundo(mont: dict) -> str:
    return {"claro": "#f2f1ed", "escuro": "#141518"}[mont["graficos"][0]["tema"]]


def comparar(a: list[Path], b: list[Path]) -> dict:
    difs = []
    for q in range(0, min(len(a), len(b)), 10):
        A = np.asarray(Image.open(a[q]).convert("RGB")).astype(np.int16)
        B = np.asarray(Image.open(b[q]).convert("RGB")).astype(np.int16)
        difs.append((float(np.abs(A - B).mean()), q))
    return {"media": round(sum(d for d, _ in difs) / len(difs), 3), "pior": {"q": max(difs)[1], "dif": round(max(difs)[0], 3)}}


# ============================================================== 5. folhas
FONTE_ROT = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)


def folha(arqs: list[Path], idx: list[int], larg: int, cols: int, titulo: str, out: Path, rotulos: dict | None = None) -> None:
    ims = []
    for q in idx:
        im = Image.open(arqs[q]).convert("RGB")
        im = im.resize((larg, round(im.height * larg / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        rot = f"q{q} {q / 60:.3f}s" + (f" {rotulos[q]}" if rotulos and q in rotulos else "")
        d.rectangle([0, 0, 12 * len(rot) + 10, 30], fill=(20, 20, 20))
        d.text((6, 3), rot, font=FONTE_ROT, fill=(255, 255, 255))
        ims.append(im)
    rows = math.ceil(len(ims) / cols)
    W, H = ims[0].size
    sheet = Image.new("RGB", (cols * W + (cols + 1) * 4, rows * H + (rows + 1) * 4 + 44), (90, 90, 90))
    ImageDraw.Draw(sheet).text((8, 8), titulo, font=FONTE_ROT, fill=(255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, (4 + (i % cols) * (W + 4), 48 + (i // cols) * (H + 4)))
    sheet.save(out, quality=86)


def folhas(motor: str, arqs: list[Path], mont: dict) -> None:
    for G in mont["graficos"]:
        gid, em = G["spec"]["id"], G["spec"]["em"]
        q0 = round(em * 60)
        qf = min(len(arqs) - 1, round((G["fim"] + 0.05) * 60))
        # entrada: 1 a cada 6 quadros do início ao fim do desenho (o desenho progressivo inteiro) + quadro final
        idx = list(range(q0, qf, max(1, (qf - q0) // 23)))[:23] + [qf]
        rot = {}
        if G["spec"].get("ritmo"):
            for r in G["spec"]["ritmo"]:
                qq = round(r["t"] * 60)
                idx.append(qq)
                rot[qq] = f"âncora d={r['d']} m"
            idx = sorted(set(idx))
        folha(arqs, idx, 480, 6, f"{motor}: gráfico '{gid}' ({G['spec']['tipo']}), entrada quadro a quadro (60 q/s) até o fim do desenho",
              AQUI / f"folha_{motor}_{gid}.jpg", rot)
    # 24 quadros SEGUIDOS a 60 q/s no meio do desenho da velocidade (suavidade do avanço)
    G = mont["graficos"][0]
    qm = round((G["cursor"]["ritmo"][0]["t"] + 1.2) * 60)
    folha(arqs, list(range(qm, qm + 24)), 480, 6, f"{motor}: 24 quadros seguidos a 60 q/s no meio do desenho da velocidade", AQUI / f"folha_{motor}_seguidos_60qs.jpg")


# ============================================================== principal
def main() -> None:
    sem_render, so_dados = "--sem-render" in sys.argv, "--so-dados" in sys.argv
    SAIDA.mkdir(exist_ok=True)
    falhas = Falhas()
    construir_global()
    cena = json.loads(CENA.read_text(encoding="utf-8"))
    D = json.loads((KIT / cena["dados"]).read_text(encoding="utf-8"))
    # 1. checagem geométrica nos dois temas
    escuro = SAIDA / "cena_escuro.json"
    escuro.write_text(json.dumps({**cena, "tema": "escuro"}, ensure_ascii=False), encoding="utf-8")
    rel_kit = {"claro": kit_json("checar", CENA), "escuro": kit_json("checar", escuro)}
    for tema, r in rel_kit.items():
        falhas.extend(f"kit ({tema}): {f}" for f in r["falhas"])
        falhas.extend(f"kit ({tema}) aviso: {a}" for a in r["avisos"])
    mont = kit_json("montar", CENA)
    # 2. dados = fonte (claro e escuro montam a mesma geometria; confere os dois)
    rel_dados = conferir_dados(D, mont, falhas)
    f2 = Falhas()
    conferir_dados(D, kit_json("montar", escuro), f2)
    falhas.extend(f"tema escuro: {f}" for f in f2)
    # 3. textos reais no Chrome
    rel_textos = medir_textos(falhas)
    resultado = {"kit": rel_kit, "dados": rel_dados, "textos_chrome": rel_textos}
    if not so_dados:
        pastas = {"remotion": SAIDA / "remotion", "hyperframes": SAIDA / "hyperframes"}
        if not sem_render:
            render_remotion(pastas["remotion"])
            render_hyperframes(pastas["hyperframes"])
        arqs = {k: sorted(p.rglob("*.png")) for k, p in pastas.items()}
        resultado["pixels"] = {k: medir_pixels(k, v, cena, mont, falhas) for k, v in arqs.items()}
        resultado["remotion_vs_hyperframes"] = comparar(arqs["remotion"], arqs["hyperframes"])
        for k, v in arqs.items():
            folhas(k, v, mont)
    resultado["falhas"] = list(falhas)
    (AQUI / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("dados:", json.dumps({k: v for k, v in rel_dados["series"].items() if "erro_max" in v}, ensure_ascii=False)[:1500])
    print("barras:", json.dumps(rel_dados["barras"], ensure_ascii=False))
    print("textos:", json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("textos", "menor_folga_real_px", "real_maior_que_estimado_px")} for k, v in rel_textos.items()}, ensure_ascii=False))
    if "pixels" in resultado:
        for k, p in resultado["pixels"].items():
            print(k, "fora:", p["fora_da_area_px"], {g: {kk: vv for kk, vv in c.items() if kk != "amostras"} for g, c in p["cursor"].items()})
        print("remotion×hyperframes:", resultado["remotion_vs_hyperframes"])
    print("FALHAS:" if falhas else "OK: nenhuma falha", *falhas, sep="\n  ")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
