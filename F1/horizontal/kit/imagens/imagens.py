# kit/imagens — busca de trechos reais da corrida com VALIDAÇÃO contra o OpenF1.
#
#   achar({"sessao": 11412, "piloto": 16, "volta": 55, "evento": None}) ->
#       {"arquivo", "quadro", "validado", "status", "evidencia", "credito", ...}
#
# Passos: (1) OpenF1: janela da volta do piloto no relógio da sessão e valores do contador da TV que cabem nela;
# (2) fontes: canais oficiais (padrão: FORMULA 1) cujo título não contradiz a sessão; (3) varredura barata: um quadro
# a cada 10 s por busca HTTP (nada de baixar o vídeo), OCR do contador "LAP C/71"; (4) refino a cada 1 s em volta dos
# acertos (OCR do quadro inteiro: nomes, REPLAY, bandeiras); (5) recorte SÓ do trecho escolhido; (6) validação de novo
# sobre o ARQUIVO recortado (quadro a quadro) + legendas da narração; (7) FONTES.txt e JSON com a evidência.
# Se nada bate: arquivo = None e status "nao_encontrado" (com o que cada vídeo mostra). Nunca devolve a volta errada
# como certa: trecho que não passa vira NAO_VALIDADO_*.mp4 (ou é apagado, se a imagem contradiz a afirmação).
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fonte_video  # noqa: E402
import leitura  # noqa: E402
import openf1  # noqa: E402
import relogio  # noqa: E402
import validar as V  # noqa: E402
from caminhos import CACHE, DADOS  # noqa: E402

CANAIS_OFICIAIS = ("FORMULA 1",)
REGIAO_CONTADOR = (0.0, 0.0, 0.32, 0.30)   # canto superior esquerdo (contador "LAP C/71" sob o logo)


def _mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def _faixas(ns: list[int]) -> str:
    ns = sorted(set(ns))
    if not ns:
        return "nenhuma"
    out, a = [], ns[0]
    for x, y in zip(ns, ns[1:] + [None]):
        if y != x + 1:
            out.append(f"{a}" if a == x else f"{a}–{x}")
            a = y
    return ", ".join(out)


# ---------------------------------------------------------------- varredura (barata) e refino
def varrer(url: str, total: int, passo: float = 10.0, ini: float = 2.0, fim: float | None = None) -> list[dict]:
    """Contador de volta a cada `passo` s, lendo só o canto do contador. Cache por vídeo."""
    meta = fonte_video.info(url)
    fim = fim or float(meta.get("duration") or 0)
    arq = CACHE / "varreduras" / f"{meta['id']}_{passo:g}_{ini:g}_{fim:g}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    fl = fonte_video.fluxo(url)
    ts = [round(ini + i * passo, 3) for i in range(int((fim - ini) / passo) + 1) if ini + i * passo < fim - 0.5]
    with ThreadPoolExecutor(6) as ex:
        quadros = list(ex.map(lambda t: (t, fonte_video.quadro(fl, t)), ts))
    def ler_todos(regiao):
        saida = []
        for t, img in quadros:
            txt = [x["texto"] for x in leitura.ler(img, regiao)] if img is not None else []
            saida.append({"t": t, "volta": leitura.volta_do_texto(txt, total), "textos": txt})
        return saida
    saida = ler_todos(REGIAO_CONTADOR)
    if not any(s["volta"] for s in saida):
        # vídeos de câmera onboard põem "LAP 42" em outro lugar: lê o quadro inteiro (mais lento)
        saida = ler_todos(None)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
    return saida


def refinar(url: str, total: int, t0: float, t1: float, passo: float = 1.0) -> list[dict]:
    """OCR do quadro inteiro a cada `passo` s em [t0, t1] (nomes, REPLAY, bandeiras). Cache."""
    meta = fonte_video.info(url)
    arq = CACHE / "varreduras" / f"{meta['id']}_fino_{t0:g}_{t1:g}_{passo:g}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    fl = fonte_video.fluxo(url)
    ts = [round(t0 + i * passo, 3) for i in range(int((t1 - t0) / passo) + 1)]
    with ThreadPoolExecutor(6) as ex:
        quadros = list(ex.map(lambda t: (t, fonte_video.quadro(fl, t)), ts))
    saida = []
    for t, img in quadros:
        txt = [x["texto"] for x in leitura.ler(img)] if img is not None else []
        saida.append({"t": t, "volta": leitura.volta_do_texto(txt, total), "textos": txt})
    arq.write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
    return saida


def _cortes(quadros: list[tuple[float, object]], limiar: float = 0.55) -> list[bool]:
    """Corte de câmera entre quadros vizinhos (correlação do histograma HSV abaixo do limiar)."""
    import cv2
    hs, saida = [], []
    for _, img in quadros:
        hsv = cv2.cvtColor(cv2.resize(img, (320, 180)), cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        hs.append(cv2.normalize(h, h).flatten())
    for i in range(len(hs)):
        saida.append(i > 0 and cv2.compareHist(hs[i - 1], hs[i], cv2.HISTCMP_CORREL) < limiar)
    return saida


# ---------------------------------------------------------------- validação de um arquivo local
def observar_arquivo(caminho: Path, passo: float = 0.5) -> list[dict]:
    quadros = fonte_video.quadros_arquivo(Path(caminho), passo)
    cortes = _cortes(quadros)
    obs = []
    for (t, img), corte in zip(quadros, cortes):
        obs.append({"t": t, "textos": [x["texto"] for x in leitura.ler(img)], "corte": bool(corte)})
    return obs


def validar_arquivo(caminho: str | Path, afirmacao: dict, url_fonte: str, ini_na_fonte: float | None = None,
                    pacote: dict | None = None) -> dict:
    """Valida um trecho JÁ baixado (ex.: o rh_20.mp4 do teste HyperFrames). ini_na_fonte = onde ele começa no vídeo
    original (para alinhar as legendas da narração); sem ele a narração não entra como evidência."""
    pacote = pacote or openf1.pacote(int(afirmacao["sessao"]))
    meta = fonte_video.info(url_fonte)
    obs = observar_arquivo(Path(caminho))
    leg = []
    if ini_na_fonte is not None:
        dur = obs[-1]["t"] + 0.5 if obs else 0
        leg = [{"i": l["i"] - ini_na_fonte, "f": l["f"] - ini_na_fonte, "texto": l["texto"]}
               for l in fonte_video.legendas(url_fonte) if l["f"] > ini_na_fonte - 2 and l["i"] < ini_na_fonte + dur + 2]
    r = V.validar(afirmacao, pacote, meta, obs, leg)
    r["observacoes"] = [{"t": o["t"], "volta": leitura.volta_do_texto(o["textos"], relogio.total_voltas(pacote["voltas"])),
                         "corte": o["corte"], "marcas": leitura.marcas(o["textos"])} for o in obs]
    return r


# ---------------------------------------------------------------- fontes
def candidatos(pacote: dict, afirmacao: dict, canais=CANAIS_OFICIAIS, maximo: int = 4) -> list[dict]:
    s = pacote["sessao"]
    p = pacote["pilotos"].get(str(afirmacao["piloto"]), {})
    gp = s.get("meeting_name") or f"{s.get('location')} Grand Prix"
    palavra = {"race": "race", "sprint": "sprint", "qualifying": "qualifying"}.get(V._tipo_sessao(s), "")
    consultas = [f"{s.get('year')} {gp} {palavra} highlights", f"{s.get('year')} {gp} {p.get('last_name', '')}",
                 f"{s.get('year')} {gp} onboard"]
    vistos, saida = set(), []
    for q in consultas:
        for e in fonte_video.buscar(q, 12):
            if e["id"] in vistos or e["channel"] not in canais:
                continue
            vistos.add(e["id"])
            if (e.get("duration") or 0) > 1500:
                continue
            if V.checar_sessao(pacote, {"title": e["title"]}, [])["status"] == "falhou":
                continue
            saida.append(e)
    nome = leitura.normalizar(p.get("last_name", "x"))
    saida.sort(key=lambda e: ("HIGHLIGHTS" not in leitura.normalizar(e["title"]), nome not in leitura.normalizar(e["title"])))
    return saida[:maximo]


# ---------------------------------------------------------------- escolha do trecho
def _peso(c: int | None, jan, voltas) -> float:
    if not c:
        return 0.0
    jc = relogio.janela_contador(c, voltas)
    return relogio.cruzamento(jc, jan) / max(1e-6, jc[1] - jc[0]) if jc else 0.0


def escolher(finos: list[dict], esperados: list[int], jan, voltas, sobrenome: str, dur: float) -> tuple[float, float] | None:
    """Melhor janela de `dur` s: todo contador legível dentro do esperado, sem REPLAY, peso pela fração da volta
    certa + bônus para o nome do piloto na tela."""
    melhor, nota_m = None, 0.0
    ts = [f["t"] for f in finos]
    for a in ts:
        b = a + dur
        dentro = [f for f in finos if a <= f["t"] <= b]
        cs = [f["volta"] for f in dentro if f.get("volta")]
        if not cs or any(c not in esperados for c in cs):
            continue
        if any("replay" in leitura.marcas(f["textos"]) for f in dentro):
            continue
        nota = sum(_peso(c, jan, voltas) for c in cs) / len(dentro)
        # bônus pela fração de quadros com o nome do piloto (prefere o plano em que ele é o assunto)
        nota += sum(leitura.tem_nome(f["textos"], sobrenome) for f in dentro) / len(dentro)
        if nota > nota_m:
            melhor, nota_m = (a, b), nota
    return melhor


# ---------------------------------------------------------------- API
def achar(afirmacao: dict, destino: str | Path | None = None, fontes: list[str] | None = None,
          duracao: float = 5.0, canais=CANAIS_OFICIAIS, passo: float = 10.0) -> dict:
    """afirmacao = {"sessao": session_key, "piloto": número, "volta": n, "evento": opcional}.
    fontes = URLs a usar (senão busca nos canais oficiais). destino = pasta de saída (padrão F1/dados/imagens/<slug>)."""
    afirmacao = {"evento": None, **afirmacao}
    sk, piloto, n = int(afirmacao["sessao"]), int(afirmacao["piloto"]), int(afirmacao["volta"])
    pacote = openf1.pacote(sk)
    voltas = pacote["voltas"]
    total = relogio.total_voltas(voltas)
    slug = f"s{sk}_c{piloto}_v{n}" + (f"_{afirmacao['evento']}" if afirmacao.get("evento") else "")
    destino = Path(destino) if destino else DADOS / slug
    destino.mkdir(parents=True, exist_ok=True)
    p = pacote["pilotos"].get(str(piloto), {})
    sobrenome = p.get("last_name", "")
    jan = relogio.janela_volta(voltas, piloto, n)
    base = {"afirmacao": afirmacao, "arquivo": None, "quadro": None, "validado": False, "credito": None}
    if not jan:
        r = {**base, "status": "reprovado", "evidencia": [f"OpenF1 não tem a volta {n} do carro {piloto} na sessão {sk}"]}
        return _gravar(destino, slug, r)
    esperados = relogio.contadores_esperados(jan, voltas)
    evid = [f"OpenF1: volta {n} de {sobrenome or piloto} = {relogio.hora(jan[0])}–{relogio.hora(jan[1])} UTC; "
            f"contador da TV (volta do líder) nesse intervalo: {esperados} de {total}"]
    urls = fontes or [c["webpage_url"] for c in candidatos(pacote, afirmacao, canais)]
    tentativas, melhor_nv = [], None
    for url in urls:
        meta = fonte_video.info(url)
        if not fontes and meta.get("channel") not in canais:
            continue
        cs = V.checar_sessao(pacote, meta, [])
        if cs["status"] == "falhou":
            evid.append(f"{meta['id']} \"{meta['title']}\": descartado ({cs['detalhe']})")
            continue
        grossa = varrer(url, total, passo)
        vistas = [g["volta"] for g in grossa if g["volta"]]
        acertos = [g["t"] for g in grossa if g["volta"] in esperados]
        evid.append(f"{meta['id']} \"{meta['title']}\": contador lido em {len(vistas)}/{len(grossa)} quadros "
                    f"(a cada {passo:g} s); voltas vistas: {_faixas(vistas)}; no intervalo pedido: {len(acertos)}")
        if not acertos:
            continue
        # refino: um bloco por grupo de acertos vizinhos (máx. 3 blocos)
        blocos = []
        for t in acertos:
            if blocos and t - blocos[-1][1] <= passo:
                blocos[-1][1] = t
            else:
                blocos.append([t, t])
        finos = []
        for a, b in blocos[:3]:
            finos += refinar(url, total, max(0.0, a - passo + 1), min(float(meta["duration"]) - 1, b + passo - 1))
        janela = escolher(finos, esperados, jan, voltas, sobrenome, duracao)
        if not janela:
            evid.append(f"{meta['id']}: nenhum trecho de {duracao:g} s só com contador {esperados} e sem replay")
            continue
        tentativas.append((url, meta, janela))
        r = _recortar_e_validar(afirmacao, pacote, url, meta, janela, destino, slug)
        r["evidencia"] = evid + r["evidencia"]
        if r["validado"]:
            return _gravar(destino, slug, r)
        evid = r["evidencia"]  # tenta a próxima fonte, guardando o que já viu
        if r.get("arquivo"):
            melhor_nv = r
    if tentativas and melhor_nv:
        return _gravar(destino, slug, {**melhor_nv, "evidencia": evid})
    r = {**base, "status": "nao_encontrado" if not tentativas else "reprovado",
         "evidencia": evid + ([] if tentativas else [f"nenhuma fonte mostra o contador {esperados}: "
                                                    "sem imagem real validada para esta afirmação"])}
    return _gravar(destino, slug, r)


def _recortar_e_validar(afirmacao, pacote, url, meta, janela, destino: Path, slug: str) -> dict:
    a, b = janela
    tmp = destino / f"_tmp_{slug}.mp4"
    fonte_video.recortar(url, a, b - a, tmp)
    obs = observar_arquivo(tmp)
    leg = [{"i": l["i"] - a, "f": l["f"] - a, "texto": l["texto"]}
           for l in fonte_video.legendas(url) if l["f"] > a - 2 and l["i"] < b + 2]
    v = V.validar(afirmacao, pacote, meta, obs, leg)
    prefixo = {"validado": "", "nao_validado": "NAO_VALIDADO_", "reprovado": "REPROVADO_"}[v["status"]]
    final = destino / f"{prefixo}{slug}.mp4"
    quadro = None
    if v["status"] == "reprovado":
        tmp.unlink(missing_ok=True)      # a imagem contradiz a afirmação: não fica nem por engano
        final = None
    else:
        final.unlink(missing_ok=True)
        tmp.rename(final)
        # quadro de referência: o primeiro com contador legível (recorte de frame para cartão/still)
        import cv2
        tq = next((o["t"] for o in obs if leitura.volta_do_texto(o["textos"], relogio.total_voltas(pacote["voltas"]))),
                  obs[len(obs) // 2]["t"])
        img = fonte_video.quadro(str(final), tq)
        if img is not None:
            quadro = final.with_suffix(".png")
            cv2.imwrite(str(quadro), img)
    credito = (f"YouTube {meta['id']} \"{meta['title']}\" (canal {meta.get('channel')}), {_mmss(a)}–{_mmss(b)}, "
               f"baixado em {date.today().isoformat()} com yt-dlp; dados de validação: OpenF1 (api.openf1.org), "
               f"sessão {afirmacao['sessao']}")
    cortes = [o["t"] for o in obs if o.get("corte")]
    evid = [f"trecho escolhido: {meta['id']} {_mmss(a)}–{_mmss(b)}"
            + (f" (cortes de câmera em t = {cortes} s: conferir se todos os planos servem)" if cortes else "")
            ] + v["evidencia"]
    return {"afirmacao": afirmacao, "arquivo": str(final) if final else None, "quadro": str(quadro) if quadro else None,
            "validado": v["validado"], "status": v["status"], "evidencia": evid, "credito": credito,
            "fonte": {"url": meta.get("webpage_url"), "ini": a, "fim": b}, "checagens": v["checagens"]}


def _gravar(destino: Path, slug: str, r: dict) -> dict:
    (destino / f"{slug}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if r.get("arquivo") and r.get("credito"):
        marca = "" if r["validado"] else " [NÃO VALIDADO: não usar sem conferir]"
        linha = f"- {Path(r['arquivo']).name} = {r['credito']}{marca}\n"
        fontes = destino / "FONTES.txt"
        atual = fontes.read_text(encoding="utf-8") if fontes.exists() else (
            "Trechos de vídeo externo (kit/imagens). Cada linha: arquivo = origem, trecho, data, validação.\n")
        if linha not in atual:
            fontes.write_text(atual + linha, encoding="utf-8")
    return r
