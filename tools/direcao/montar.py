"""Diretor — montagem: plano + escolhas + tempos -> direção final (JSON do Remotion) + render do rascunho."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comum import PASTA_ACERVO, abrir_acervo, preparar_ffmpeg  # noqa: E402
from direcao.variacao import Variador  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planejar import pecas_da_cena  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
VIDEO_APP = RAIZ / "app" / "video"


def _norm(w: str) -> str:
    return re.sub(r"[^\wÀ-ú-]", "", w).lower()


def indice_na_frase(frase: dict, toks: list[str], palavra: str | None) -> int | None:
    if not palavra:
        return None
    alvo = _norm(palavra)
    for i in range(frase["de"], frase["ate"] + 1):
        if _norm(toks[i]) == alvo:
            return i
    return None


class Midias:
    """Copia mídias do acervo para app/video/public/<slug>/ (convertendo formatos que o Chrome do Remotion lê mal)."""

    def __init__(self, slug: str):
        self.slug = slug
        self.pasta = VIDEO_APP / "public" / slug
        if self.pasta.exists():
            shutil.rmtree(self.pasta)
        self.pasta.mkdir(parents=True)
        self.con = abrir_acervo()

    def imagem(self, mid: int) -> dict:
        caminho, autor = self.con.execute("SELECT caminho, autor FROM midias WHERE id=?", (mid,)).fetchone()
        midia = self.arquivo(PASTA_ACERVO / caminho, f"m{mid}")
        if autor:  # fan art: crédito do artista na própria cena (além da descrição)
            midia["credito"] = f"arte: {autor}"
        return midia

    def arquivo(self, origem: Path, nome: str) -> dict:
        ext = origem.suffix.lower()
        animado = False
        if ext == ".gif":
            with Image.open(origem) as im:
                animado = getattr(im, "n_frames", 1) > 1
        if ext in (".jpg", ".jpeg", ".png") or animado:  # GIF animado vai como GIF (o Remotion anima com <Gif>)
            destino = self.pasta / f"{nome}{'.jpg' if ext == '.jpeg' else ext}"
            shutil.copyfile(origem, destino)
        else:  # webp, avif, jfif, gif parado, jpg_large...
            destino = self.pasta / f"{nome}.png"
            with Image.open(origem) as im:
                im.seek(0)
                im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(destino)
        with Image.open(destino) as im:
            w, h = im.size
        return {"arquivo": f"{self.slug}/{destino.name}", "w": w, "h": h}

    def tomada(self, tomada_id: int) -> tuple[str, float]:
        mid, ini, fim = self.con.execute("SELECT midia_id, inicio, fim FROM tomadas WHERE id=?", (tomada_id,)).fetchone()
        origem = PASTA_ACERVO / self.con.execute("SELECT caminho FROM midias WHERE id=?", (mid,)).fetchone()[0]
        destino = self.pasta / f"t{tomada_id}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ini), "-to", str(fim), "-i", str(origem), "-an",
                        "-vf", "scale=1920:-2", "-c:v", "h264_nvenc", "-cq", "20", str(destino)], check=True)
        return f"{self.slug}/{destino.name}", round(fim - ini, 3)


def montar(slug: str, roteiro: str, palavras: list[dict], frases: list[dict], plano: dict, necs: list[dict],
           escolhas: dict, capa: Path | None, circulos: list[dict], audio: Path) -> tuple[dict, list[dict]]:
    """Devolve (trecho para o Remotion, pendências para o painel)."""
    preparar_ffmpeg()
    toks = roteiro.split()
    m = Midias(slug)
    var = Variador(semente=slug)
    pendencias: list[dict] = []
    nec_por_id = {n["id"]: n for n in necs}
    usados: set = set()

    shutil.copyfile(audio, m.pasta / "voz.wav")
    capa_midia = m.arquivo(capa, "capa") if capa else None

    def icone(nome: str | None) -> dict | None:
        c = next((c for c in circulos if nome and c.get("nome", "").lower() == nome.lower()), None)
        if not (c and capa_midia):
            return None
        return {"nome": c["nome"], "midia": capa_midia, "foco": [c["cx"], c["cy"]], "diametro": 2 * c["r"] * 0.93}

    secoes = sorted(plano.get("secoes", []), key=lambda s: s["frase_inicial"])
    # Fundo branco é a assinatura do canal (Felipe, 2026-10-14): o vídeo inteiro é sempre "claro";
    # o escuro fica só nas cenas de tela cheia e no "texto" com fundo escuro em ocasião especial.
    modo = "claro"

    def secao_da_frase(n: int) -> dict | None:
        atual = None
        for s in secoes:
            if s["frase_inicial"] <= n:
                atual = s
        ic = icone(atual.get("personagem_da_capa")) if atual else None
        return {"titulo": atual["titulo"], "icone": ic} if atual and ic else None

    def escolhido(nec_id: str) -> dict | None:
        """Candidato escolhido; se já foi usado, o próximo candidato ainda não usado."""
        n = nec_por_id.get(nec_id)
        e = escolhas.get(nec_id) or {}
        if not n or not e.get("escolha"):
            return None
        if e.get("fixa"):  # escolhida pelo Felipe no storyboard: vale mesmo se repetir
            cand = n["candidatos"][e["escolha"] - 1]
            usados.add((cand["tipo"], cand["id"]))
            return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        ordem = [e["escolha"] - 1] + [i for i in range(len(n["candidatos"])) if i != e["escolha"] - 1]
        for i in ordem:
            cand = n["candidatos"][i]
            chave = (cand["tipo"], cand["id"])
            if chave not in usados:
                usados.add(chave)
                return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        return None

    nomes_capa = [x.get("nome", "").lower() for x in circulos]

    def secao_do_hub(n: int) -> dict | None:
        """Seção que começa nesta frase — o hub fecha no personagem dela. Tolera o diretor errar por 1 frase
        ("Evelynn." numa frase e a seção marcada na seguinte/anterior)."""
        perto = [s for s in secoes if abs(s["frase_inicial"] - n) <= 1]
        if perto:
            return min(perto, key=lambda s: (abs(s["frase_inicial"] - n), -s["frase_inicial"]))
        return next((s for s in secoes if s["frase_inicial"] >= n), None)

    def pecas_montadas(k: int, c: dict, f: dict, de: int) -> list[dict]:
        saida = []
        for j, peca in enumerate(pecas_da_cena(c)):
            ep = escolhido(f"C{k}p{j}")
            if not (ep and ep["tipo"] == "midia"):
                continue
            pi = indice_na_frase(f, toks, peca.get("palavra"))
            saida.append({"de": pi if pi is not None else de, "midia": m.imagem(ep["id"]), "foco": ep["foco"],
                          "rotulo": peca.get("rotulo") or ""})
        saida.sort(key=lambda p: p["de"])
        return saida

    cenas = []
    for k, c in enumerate(plano["cenas"]):
        if c.get("removida"):
            continue
        f = frases[c["frase"]]
        de = indice_na_frase(f, toks, c.get("comeca_na_palavra")) or f["de"]
        legenda_em = indice_na_frase(f, toks, c.get("legenda_na_palavra"))
        base = {"k": k, "de": de, "ate": de, "semente": k, "secao": secao_da_frase(c["frase"])}
        tipo = c["tipo"]
        legenda = c.get("legenda") or ""

        if tipo in ("capa", "hub"):
            if not capa_midia or not circulos:
                continue
            s = (secoes[0] if secoes else None) if tipo == "capa" else secao_do_hub(c["frase"])
            alvo = ((s or {}).get("personagem_da_capa") or "").lower()
            if tipo == "hub" and alvo not in nomes_capa:
                continue  # seção sem ícone na capa: não há em quem fechar
            destaque = nomes_capa.index(alvo) if alvo in nomes_capa else 0
            if tipo == "capa":
                cenas.append({**base, "tipo": "capa", "midia": capa_midia, "circulos": circulos,
                              "destaque": destaque, "zoom": round(var.rng.uniform(2.3, 2.8), 2)})
            else:
                cenas.append({**base, "secao": None, "tipo": "hub", "midia": capa_midia, "circulos": circulos,
                              "destaque": destaque, **var.hub()})
            continue

        if tipo == "texto":
            if legenda:
                cenas.append({**base, "tipo": "texto", "texto": legenda,
                              "fundo": "escuro" if c.get("fundo") == "escuro" else "claro",
                              "entrada_texto": var.texto()})
            continue

        if tipo == "dialogo":
            d = c.get("dialogo") or {}
            esq, dir_ = icone(d.get("esquerda")), icone(d.get("direita"))
            if esq and dir_:
                destaques = [i for w in d.get("destaques", []) if (i := indice_na_frase(f, toks, w)) is not None]
                cenas.append({**base, "tipo": "dialogo", "esquerda": esq, "direita": dir_, "destaques": destaques})
                continue
            tipo = "cartao"  # sem ícones na capa: vira cartão

        if tipo in ("dividida", "lista"):
            pecas = pecas_montadas(k, c, f, de)
            minimo = 2
            if len(pecas) >= minimo:
                pecas = pecas[:3] if tipo == "dividida" else pecas[:5]
                pecas[0]["de"] = de
                extra = var.dividida() if tipo == "dividida" else var.lista()
                cenas.append({**base, "tipo": tipo, "pecas": pecas, **extra})
            else:
                pendencias.append({"titulo": "Cena com poucas imagens",
                                   "texto": f"Cena {k} ({tipo}, “{f['texto'][:80]}…”): menos de 2 imagens serviram. "
                                            "No rascunho, a cena anterior continua na tela."})
            continue

        esc = escolhido(f"C{k}")
        if not esc:
            pendencias.append({"titulo": "Cena sem imagem boa",
                               "texto": f"Cena {k} (“{f['texto'][:90]}…”): nenhum candidato do acervo serviu. "
                                        "No rascunho, a cena anterior continua na tela."})
            continue

        if tipo == "clipe":
            if esc["tipo"] != "tomada":
                tipo = "telacheia"
            else:
                arquivo, dur = m.tomada(esc["id"])
                cenas.append({**base, "tipo": "clipe", "arquivo": arquivo, "duracao_tomada": dur,
                              "movimento": var.movimento(), "entrada_img": var.imagem()})
                continue

        midia = m.imagem(esc["id"]) if esc["tipo"] == "midia" else None
        if midia is None:
            continue
        if tipo == "telacheia":
            cena = {**base, "tipo": "telacheia", "midia": midia, "foco": esc["foco"],
                    "movimento": var.movimento(), "entrada_img": var.imagem()}
            if c.get("rotulo"):
                cena.update({"rotulo": c["rotulo"], "subrotulo": c.get("subrotulo") or "",
                             "rotulo_em": legenda_em if legenda_em is not None else de, "entrada_rotulo": var.texto()})
            cenas.append(cena)
        elif tipo == "recorte":
            cenas.append({**base, "tipo": "recorte", "midia": midia, "legenda": legenda,
                          "legenda_em": legenda_em or de, "entrada_img": var.imagem(), "entrada_legenda": var.texto()})
        elif tipo == "meio" and legenda:
            cenas.append({**base, "tipo": "meio", "midia": midia, "foco": esc["foco"], "lado": var.lado(),
                          "texto": legenda, "texto_em": legenda_em if legenda_em is not None else de,
                          "entrada_img": var.imagem(), "entrada_texto": var.texto(), "movimento": var.movimento()})
        elif tipo == "citacao":
            destaques = [i for w in (c.get("destaques") or []) if (i := indice_na_frase(f, toks, w)) is not None]
            cenas.append({**base, "secao": None, "tipo": "citacao", "midia": midia, "foco": esc["foco"],
                          "autor": c.get("autor") or "", "destaques": destaques, "lado": var.lado_citacao(),
                          "movimento": var.movimento()})
        elif tipo == "mosaico":
            pecas = pecas_montadas(k, c, f, de)
            if len(pecas) >= 2:
                posicoes, borda = var.mosaico([p["midia"]["w"] / p["midia"]["h"] for p in pecas])
                cenas.append({**base, "tipo": "mosaico", "fundo": midia, "movimento": var.movimento(), "borda": borda,
                              "pecas": [{"de": p["de"], "midia": p["midia"], **pos} for p, pos in zip(pecas, posicoes)]})
            else:
                cenas.append({**base, "tipo": "telacheia", "midia": midia, "foco": esc["foco"],
                              "movimento": var.movimento(), "entrada_img": var.imagem()})
        else:  # cartao (padrão; também "meio" sem texto)
            cenas.append({**base, "tipo": "cartao", "itens": [
                {"de": de, "midia": midia, "legenda": legenda, "legenda_em": legenda_em,
                 "entrada_img": var.imagem(), "entrada_legenda": var.texto(), "movimento": var.movimento()}]})

    for a, b in zip(cenas, cenas[1:]):
        a["ate"] = max(a["de"], b["de"] - 1)
    if cenas:
        cenas[-1]["ate"] = len(toks) - 1
    montadas = {c["k"] for c in cenas}
    sons = efeitos_sonoros(plano, frases, toks, palavras, montadas, m, var)
    trecho = {"audio": f"{slug}/voz.wav", "palavras": palavras, "cenas": cenas, "tema": modo, "sons": sons}
    return trecho, pendencias


# volume de cada categoria (a voz está em -14 LUFS e os efeitos com pico em -3 dBFS): fica 12–18 dB abaixo
VOLUME_SOM = {"impacto": 0.40, "explosao": 0.40, "trovao": 0.36, "rugido": 0.36, "metal": 0.34, "sino": 0.34}
VOLUME_PADRAO = 0.30  # medido no render de teste: ~15 dB abaixo da voz
INTERVALO_MIN = 18.0  # segundos entre efeitos
SEGUNDOS_POR_SOM = 30.0  # teto: no máximo 1 efeito a cada 30 s de vídeo, em média


def efeitos_sonoros(plano: dict, frases: list[dict], toks: list[str], palavras: list[dict], montadas: set,
                    m: "Midias", var: Variador) -> list[dict]:
    """Efeitos pedidos pelo diretor → arquivos do catálogo (busca CLAP pela descrição), com as regras do canal
    garantidas aqui mesmo que o diretor exagere: intervalo mínimo, teto por duração, sem repetir o mesmo som."""
    pedidos = []
    for k, c in enumerate(plano["cenas"]):
        som = c.get("som")
        if c.get("removida") or k not in montadas or not (som and som.get("o_que")):
            continue
        f = frases[c["frase"]]
        i = indice_na_frase(f, toks, som.get("palavra"))
        i = i if i is not None else f["de"]
        pedidos.append({"k": k, "de": i, "t": palavras[i]["i"], "o_que": som["o_que"]})
    if not pedidos:
        return []
    duracao = palavras[-1]["f"]
    teto = max(1, int(duracao / SEGUNDOS_POR_SOM))
    aceitos, ultimo = [], -1e9
    for p in sorted(pedidos, key=lambda p: p["t"]):
        if p["t"] - ultimo >= INTERVALO_MIN and len(aceitos) < teto:
            aceitos.append(p)
            ultimo = p["t"]
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audio"))
        from sfx import PASTA as PASTA_SFX, Busca
        busca = Busca()
    except Exception as e:  # sem catálogo/CLAP: o vídeo sai sem efeitos, nunca quebra a montagem
        print("efeitos sonoros indisponíveis:", e)
        return []
    usados: set[int] = set()
    saida = []
    ultima_categoria = None
    for p in aceitos:
        achados = busca.buscar(p["o_que"], 6, evitar=usados)
        # não repete a categoria do efeito anterior se houver alternativa razoável
        achados.sort(key=lambda a: -(a[1] - (0.05 if busca.info[a[0]]["categoria"] == ultima_categoria else 0)))
        if not achados:
            continue
        sid = achados[0][0]
        usados.add(sid)
        cat = busca.info[sid]["categoria"]
        ultima_categoria = cat
        destino = m.pasta / f"s{sid}.wav"
        shutil.copyfile(PASTA_SFX / busca.info[sid]["arquivo"], destino)
        volume = VOLUME_SOM.get(cat, VOLUME_PADRAO) * var.rng.uniform(0.85, 1.12)
        saida.append({"k": p["k"], "de": p["de"], "arquivo": f"{m.slug}/{destino.name}", "volume": round(volume, 3),
                      "categoria": cat, "o_que": p["o_que"]})
    busca.liberar()
    return saida


def renderizar(trecho: dict, props: Path, saida: Path) -> float:
    """Renderiza a composição genérica "Video" com a direção dada. Devolve os segundos gastos."""
    import time

    props, saida = props.resolve(), saida.resolve()  # o Remotion roda com cwd em app/video
    props.write_text(json.dumps({"trecho": trecho}, ensure_ascii=False), encoding="utf-8")
    t0 = time.time()
    temporario = saida.with_name(saida.stem + "_renderizando.mp4")
    log = saida.with_name("render_erro.log")
    for tentativa in (1, 2):  # falhas momentâneas acontecem: tenta mais uma vez antes de desistir
        p = subprocess.run(["npx.cmd", "remotion", "render", "Video", str(temporario), f"--props={props}", "--log=error"],
                           cwd=VIDEO_APP, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0 and temporario.exists():
            temporario.replace(saida)
            return time.time() - t0
        texto = re.sub(r"\x1b\[[0-9;]*m", "", (p.stderr or "") + "\n" + (p.stdout or ""))
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n===== tentativa {tentativa} ({time.strftime('%H:%M:%S')}) =====\n{texto}")
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip() and not ln.strip().startswith("at ")]
    raise RuntimeError(f"Remotion falhou 2x. Resumo: {' | '.join(linhas[:4])[:300]} (log completo: {log.name})")
