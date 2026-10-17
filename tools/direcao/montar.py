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
from candidatos import id_da_cena  # noqa: E402
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

    def tomada(self, tomada_id: int, inicio: float | None = None) -> tuple[str, float]:
        """Recorte da tomada. `inicio` = segundo do vídeo original escolhido pelo Felipe no storyboard ("escolher o
        momento"): o clipe começa ali e vai até o fim do vídeo."""
        mid, ini, fim = self.con.execute("SELECT midia_id, inicio, fim FROM tomadas WHERE id=?", (tomada_id,)).fetchone()
        caminho, duracao = self.con.execute("SELECT caminho, duracao FROM midias WHERE id=?", (mid,)).fetchone()
        origem = PASTA_ACERVO / caminho
        destino = self.pasta / f"t{tomada_id}.mp4"
        if inicio is not None:
            ini, fim = float(inicio), float(duracao or fim)
            destino = self.pasta / f"t{tomada_id}_s{round(ini * 10)}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ini), "-to", str(fim), "-i", str(origem), "-an",
                        "-vf", "scale=1920:-2", "-c:v", "h264_nvenc", "-cq", "20", str(destino)], check=True)
        return f"{self.slug}/{destino.name}", round(fim - ini, 3)


FPS = 60  # igual ao Root.tsx

# efeitos sorteados que uma cena HERDA da versão anterior do rascunho (mesmo id e mesmo tipo): mexer numa cena não
# muda o visual das outras — e o render por blocos reaproveita os blocos que não mudaram
EFEITOS_HERDADOS = ("entrada_img", "entrada_legenda", "entrada_texto", "entrada_rotulo", "movimento", "lado",
                    "entrada", "separador", "inclinado", "zoom", "borda")  # "variante" não: hub agora é só "grade"


def _herdar(cena: dict, velha: dict | None) -> None:
    if not velha or velha.get("tipo") != cena.get("tipo"):
        return
    for k in EFEITOS_HERDADOS:
        if k in velha and k in cena:
            if k == "movimento" and (velha[k] or {}).get("tipo") == "parado":
                continue  # "parado" saiu do cardápio: a cena ganha um movimento novo
            cena[k] = velha[k]
    for item, iv in zip(cena.get("itens", []), velha.get("itens", [])):
        for k in ("entrada_img", "entrada_legenda", "movimento"):
            if k in iv and not (k == "movimento" and (iv[k] or {}).get("tipo") == "parado"):
                item[k] = iv[k]
    if cena["tipo"] == "mosaico" and len(cena.get("pecas", [])) == len(velha.get("pecas", [])):
        for p, pv in zip(cena["pecas"], velha["pecas"]):
            p.update({k: pv[k] for k in ("x", "y", "largura", "rotacao", "de_onde", "quadros") if k in pv})


def _folga(cid: str) -> int:
    """"Imperfeição humana" no corte (0 a 4 quadros antes da palavra), estável pelo id da cena."""
    import hashlib

    return int(hashlib.sha1(cid.encode()).hexdigest()[:8], 16) % 5


def montar(slug: str, roteiro: str, palavras: list[dict], frases: list[dict], plano: dict, necs: list[dict],
           escolhas: dict, capa: Path | None, circulos: list[dict], audio: Path,
           anterior: dict | None = None) -> tuple[dict, list[dict]]:
    """Devolve (trecho para o Remotion, pendências para o painel). `anterior` = direção da versão anterior
    (efeitos herdados por id de cena)."""
    preparar_ffmpeg()
    toks = roteiro.split()
    m = Midias(slug)
    var = Variador(semente=slug)
    pendencias: list[dict] = []
    nec_por_id = {n["id"]: n for n in necs}
    from candidatos import numeros_das_cenas

    numeros = numeros_das_cenas(plano, RAIZ / "projetos" / slug / "direcao")  # o número que o Felipe vê
    # BLOCOS DESACOPLADOS (Felipe, 2026-10-16): cada bloco (introdução/seção) é montado só com o que é dele —
    # a regra de não repetir imagem e o sorteio de efeitos recomeçam a cada bloco. Mexer no bloco 1 não tem
    # COMO mudar o bloco 5.
    usados_por_bloco: dict[str, set] = {}
    bloco_da_cena = {id_da_cena(c, k): c.get("secao") or "" for k, c in enumerate(plano["cenas"])}
    fontes: dict[str, list] = {}  # imagem automática que cada cena (necessidade) usou nesta versão
    fontes_velhas = (anterior or {}).get("fontes") or {}

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
        if e.get("fixa"):  # escolhida pelo Felipe no storyboard: vale mesmo se repetir e NÃO ocupa a imagem
            # (a escolha dele não empurra as cenas automáticas para outro candidato → não mexe em outros blocos)
            cand = n["candidatos"][e["escolha"] - 1]
            return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        usados = usados_por_bloco.setdefault(bloco_da_cena.get(n.get("cena"), ""), set())
        # cena automática que já tinha imagem na versão anterior MANTÉM essa imagem, sem condição
        antes = fontes_velhas.get(nec_id)
        cand = next((c for c in n["candidatos"] if [c["tipo"], c["id"]] == antes), None) if antes else None
        if cand:
            usados.add((cand["tipo"], cand["id"]))
            fontes[nec_id] = list(antes)
            return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        # cena nova: escolha do diretor; se já usada NESTE bloco, a próxima candidata livre do bloco
        ordem = [e["escolha"] - 1] + [i for i in range(len(n["candidatos"])) if i != e["escolha"] - 1]
        for i in ordem:
            cand = n["candidatos"][i]
            chave = (cand["tipo"], cand["id"])
            if chave not in usados:
                usados.add(chave)
                fontes[nec_id] = list(chave)
                return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        # todas as candidatas já usadas no bloco: melhor REPETIR a escolha do diretor do que deixar a cena sem imagem
        cand = n["candidatos"][e["escolha"] - 1]
        fontes[nec_id] = [cand["tipo"], cand["id"]]
        return {**cand, "foco": e.get("foco") or [0.5, 0.45]}

    nomes_capa = [x.get("nome", "").lower() for x in circulos]

    def secao_do_hub(n: int) -> dict | None:
        """Seção que começa nesta frase — o hub fecha no personagem dela. Tolera o diretor errar por 1 frase
        ("Evelynn." numa frase e a seção marcada na seguinte/anterior)."""
        perto = [s for s in secoes if abs(s["frase_inicial"] - n) <= 1]
        if perto:
            return min(perto, key=lambda s: (abs(s["frase_inicial"] - n), -s["frase_inicial"]))
        return next((s for s in secoes if s["frase_inicial"] >= n), None)

    def pecas_montadas(cid: str, c: dict, f: dict, de: int) -> list[dict]:
        saida = []
        for j, peca in enumerate(pecas_da_cena(c)):
            ep = escolhido(f"{cid}p{j}")
            if not (ep and ep["tipo"] == "midia"):
                continue
            pi = indice_na_frase(f, toks, peca.get("palavra"))
            saida.append({"de": pi if pi is not None else de, "midia": m.imagem(ep["id"]), "foco": ep["foco"],
                          "rotulo": peca.get("rotulo") or ""})
        saida.sort(key=lambda p: p["de"])
        return saida

    def sem_imagem(base: dict, legenda: str | None) -> dict:
        """Nenhuma imagem serviu: a cena entra assim mesmo, no tempo dela, como texto (a legenda ou um aviso), e o
        Felipe escolhe a imagem no storyboard — sem precisar de outra chamada ao Claude."""
        return {**base, "tipo": "texto", "texto": legenda or "[imagem pendente]", "fundo": "claro",
                "entrada_texto": {"efeito": "corte", "quadros": 1}, "sem_imagem": True}

    cenas = []
    bloco_atual = None
    for k, c in enumerate(plano["cenas"]):
        if c.get("removida"):
            continue
        if (c.get("secao") or "") != bloco_atual:  # sorteio de efeitos recomeça em cada bloco (desacoplados)
            bloco_atual = c.get("secao") or ""
            var.__init__(semente=f"{slug}:{bloco_atual}")
        f = frases[c["frase"]]
        de = indice_na_frase(f, toks, c.get("comeca_na_palavra")) or f["de"]
        legenda_em = indice_na_frase(f, toks, c.get("legenda_na_palavra"))
        cid = id_da_cena(c, k)
        base = {"k": k, "id": cid, "bloco": c.get("secao") or "", "de": de, "ate": de, "semente": cid,
                "secao": secao_da_frase(c["frase"])}
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
                # continuidade: a transição parte do ícone em que a anterior (abertura ou transição) parou
                anterior_ic = next((x["destaque"] for x in reversed(cenas) if x["tipo"] in ("capa", "hub")), None)
                cenas.append({**base, "secao": None, "tipo": "hub", "midia": capa_midia, "circulos": circulos,
                              "destaque": destaque, **var.hub(),
                              **({"origem": anterior_ic} if anterior_ic is not None else {})})
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
            pecas = pecas_montadas(cid, c, f, de)
            minimo = 2
            if len(pecas) >= minimo:
                pecas = pecas[:3] if tipo == "dividida" else pecas[:5]
                pecas[0]["de"] = de
                extra = var.dividida() if tipo == "dividida" else var.lista()
                cenas.append({**base, "tipo": tipo, "pecas": pecas, **extra})
            else:
                pendencias.append({"titulo": "Cena com poucas imagens",
                                   "texto": f"Cena {numeros.get(cid, k)} ({tipo}, “{f['texto'][:80]}…”): menos de 2 imagens serviram. "
                                            "No rascunho, um texto ocupa o lugar dela: escolha as imagens no storyboard."})
                cenas.append(sem_imagem(base, legenda))
            continue

        esc = escolhido(cid)
        if not esc:
            pendencias.append({"titulo": "Cena sem imagem boa",
                               "texto": f"Cena {numeros.get(cid, k)} (“{f['texto'][:90]}…”): nenhum candidato do acervo serviu. "
                                        "No rascunho, um texto ocupa o lugar dela: escolha a imagem no storyboard."})
            cenas.append(sem_imagem(base, legenda))
            continue

        if tipo == "clipe":
            if esc["tipo"] != "tomada":
                tipo = "telacheia"
            else:
                arquivo, dur = m.tomada(esc["id"], (escolhas.get(cid) or {}).get("inicio"))
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
            pecas = pecas_montadas(cid, c, f, de)
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

    # A capa só aparece durante a leitura do TÍTULO da seção (pedido do Felipe): se a cena seguinte começaria
    # depois (cenas sem imagem no meio), ela é antecipada para logo após o título.
    for a, b in zip(cenas, cenas[1:]):
        if a["tipo"] == "hub" and b["tipo"] not in ("hub", "capa"):
            titulo = next((f for f in frases if f["de"] <= a["de"] <= f["ate"]), None)
            if titulo and b["de"] > titulo["ate"] + 1:
                b["de"] = titulo["ate"] + 1
    for a, b in zip(cenas, cenas[1:]):
        a["ate"] = max(a["de"], b["de"] - 1)
    if cenas:
        cenas[-1]["ate"] = len(toks) - 1
    velhas = {c.get("id"): c for c in (anterior or {}).get("cenas", [])}
    for i, c in enumerate(cenas):
        _herdar(c, velhas.get(c["id"]))
        # quadro em que a cena começa (o Montagem.tsx usa este valor): o Python sabe onde cada bloco começa
        c["q"] = 0 if i == 0 else max(cenas[i - 1]["q"] + 1, int(palavras[c["de"]]["i"] * FPS + 0.5) - _folga(c["id"]))
    montadas = {c["k"] for c in cenas}
    sons = efeitos_sonoros(plano, frases, toks, palavras, montadas, m, var)
    trecho = {"audio": f"{slug}/voz.wav", "palavras": palavras, "cenas": cenas, "tema": modo, "sons": sons,
              "fontes": fontes}  # fora das cenas: não entra na impressão dos blocos
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
        pedidos.append({"k": k, "id": id_da_cena(c, k), "de": i, "t": palavras[i]["i"], "o_que": som["o_que"]})
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
        saida.append({"k": p["k"], "id": p["id"], "de": p["de"], "arquivo": f"{m.slug}/{destino.name}", "volume": round(volume, 3),
                      "categoria": cat, "o_que": p["o_que"]})
    busca.liberar()
    return saida


ULTIMO_RENDER: dict = {}  # estatística do último render por blocos (o motor mostra no histórico)


def _blocos_do_trecho(trecho: dict) -> list[dict]:
    """Intervalos de quadros de cada bloco (introdução + seções) — sequências de cenas com o mesmo "bloco"."""
    cenas, palavras = trecho["cenas"], trecho["palavras"]
    total = int(-(-((palavras[-1]["f"] + 0.5) * FPS) // 1))  # ceil, igual ao duracaoDoTrecho do Montagem.tsx
    grupos: list[list[dict]] = []
    for c in cenas:
        if grupos and grupos[-1][-1].get("bloco") == c.get("bloco"):
            grupos[-1].append(c)
        else:
            grupos.append([c])
    blocos = []
    for i, g in enumerate(grupos):
        inicio = 0 if i == 0 else g[0]["q"]
        fim = (grupos[i + 1][0]["q"] - 1) if i + 1 < len(grupos) else total - 1
        if fim >= inicio:
            blocos.append({"id": g[0].get("bloco"), "inicio": inicio, "fim": fim, "cenas": g})
    return blocos


def _impressao(bloco: dict, trecho: dict, codigo: str, capa: str, com_k: bool = False) -> str:
    """Tudo o que influencia os quadros do bloco: cenas, intervalo, tempos das palavras usadas, código das cenas e
    a capa. Igual → o .mp4 em cache vale. Sem "k" (posição da cena no plano inteiro, o Remotion não usa): dividir
    uma cena no bloco 2 mudava o "k" de todas as cenas seguintes e refazia o vídeo todo. `com_k` = impressão
    antiga, só para reaproveitar o cache feito antes desta correção."""
    import hashlib

    de = min(c["de"] for c in bloco["cenas"])
    ate = max(c["ate"] for c in bloco["cenas"])
    cenas = bloco["cenas"] if com_k else [{x: v for x, v in c.items() if x != "k"} for c in bloco["cenas"]]
    chave = json.dumps([bloco["inicio"], bloco["fim"], cenas, trecho["palavras"][de:ate + 2],
                        trecho.get("tema"), trecho.get("secao"), codigo, capa], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()[:20]


ARQUIVO_DA_CENA = {"capa": "Capa", "hub": "Hub", "cartao": "Cartao", "telacheia": "TelaCheia", "recorte": "Recorte",
                   "dialogo": "Dialogo", "clipe": "Clipe", "mosaico": "Mosaico", "dividida": "Dividida", "lista": "Lista",
                   "meio": "Meio", "texto": "Texto", "citacao": "Citacao"}


def _dependencias(arquivo: Path, pular_cenas: bool = False, vistos: set | None = None) -> set[Path]:
    """Arquivos do src/ que `arquivo` importa (recursivo, só imports relativos)."""
    vistos = vistos if vistos is not None else set()
    if arquivo in vistos or not arquivo.exists():
        return vistos
    vistos.add(arquivo)
    for alvo in re.findall(r"""from\s+["'](\.{1,2}/[^"']+)["']""", arquivo.read_text(encoding="utf-8")):
        base = (arquivo.parent / alvo).resolve()
        for cand in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.ts"):
            if cand.exists():
                if not (pular_cenas and cand.parent.name == "cenas"):
                    _dependencias(cand, pular_cenas, vistos)
                break
    return vistos


def _versao_do_codigo(tipos: set[str]) -> str:
    """Impressão do código Remotion que desenha ESTE bloco: a base comum (Montagem, efeitos, estilo, componentes…)
    + só os arquivos das cenas que aparecem nele. Mexer na Lista só refaz os blocos que têm lista."""
    import hashlib

    src = (VIDEO_APP / "src").resolve()
    arquivos = _dependencias(src / "Montagem.tsx", pular_cenas=True) | _dependencias(src / "Root.tsx", pular_cenas=True)
    for t in sorted(tipos):
        if t in ARQUIVO_DA_CENA:
            arquivos |= _dependencias(src / "cenas" / f"{ARQUIVO_DA_CENA[t]}.tsx")
    h = hashlib.sha1()
    for p in sorted(arquivos):
        h.update(p.relative_to(src).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def _rodar_render(pedido: Path, faltam: list[dict], progresso) -> tuple[int, str]:
    """Roda o render_blocos.mjs lendo o progresso linha a linha. Devolve (código de saída, saída de erro)."""
    import threading

    total = sum(b["fim"] - b["inicio"] + 1 for b in faltam) or 1
    feitos_antes = [sum(b["fim"] - b["inicio"] + 1 for b in faltam[:i]) for i in range(len(faltam))]
    p = subprocess.Popen(["node", "render_blocos.mjs", str(pedido)], cwd=VIDEO_APP, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    erros: list[str] = []
    threading.Thread(target=lambda: erros.extend(p.stderr), daemon=True).start()  # não deixa o stderr entupir
    for linha in p.stdout:
        partes = linha.split()
        if not progresso or not partes:
            continue
        if partes[0] == "PRONTO":
            progresso(0.0, f"preparando ({len(faltam)} bloco(s) para renderizar)")
        elif partes[0] == "PROG" and len(partes) == 3:
            i, q = int(partes[1]), int(partes[2])
            b = faltam[i]
            progresso(min(0.99, (feitos_antes[i] + q) / total),
                      f"bloco {i + 1} de {len(faltam)} · {(b.get('id') or 'introdução').replace('-', ' ')}")
        elif partes[0] == "AUDIO":
            progresso(0.99, "áudio pronto · juntando os blocos")
    return p.wait(), "".join(erros)


def _mixar_audio(trecho: dict, saida: Path) -> None:
    """Áudio do vídeo = voz + efeitos sonoros, igual ao Montagem.tsx (efeito 2 quadros antes da palavra, volume
    do efeito, duração da composição), mixado direto no FFmpeg. Os clipes de vídeo são sempre mudos."""
    publico = VIDEO_APP / "public"
    palavras = trecho["palavras"]
    duracao = int(-(-((palavras[-1]["f"] + 0.5) * FPS) // 1)) / FPS
    entradas = ["-i", str(publico / trecho["audio"])]
    filtros, rotulos = [], ["[0:a]"]
    for j, s in enumerate(trecho.get("sons") or [], start=1):
        quadro = max(0, round(palavras[min(s["de"], len(palavras) - 1)]["i"] * FPS) - 2)
        entradas += ["-i", str(publico / s["arquivo"])]
        ms = round(quadro / FPS * 1000)
        filtros.append(f"[{j}:a]aresample=48000,aformat=channel_layouts=stereo,volume={s['volume']},adelay={ms}:all=1[s{j}]")
        rotulos.append(f"[s{j}]")
    filtros.append("[0:a]aresample=48000,aformat=channel_layouts=stereo[voz]")
    rotulos[0] = "[voz]"
    filtros.append(f"{''.join(rotulos)}amix=inputs={len(rotulos)}:duration=first:normalize=0,"
                   f"apad,atrim=0:{duracao:.3f}[saida]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
                    "-map", "[saida]", "-ac", "2", "-c:a", "pcm_s16le", str(saida)], check=True)


def renderizar(trecho: dict, props: Path, saida: Path, progresso=None) -> float:
    """Renderiza o vídeo POR BLOCOS: cada bloco (introdução + seções) vira um .mp4 sem áudio em cache
    (trabalho/blocos/<impressão>.mp4); só os blocos que mudaram são renderizados. Depois junta tudo com o FFmpeg
    (sem recomprimir) e põe o áudio (voz + efeitos), renderizado inteiro à parte. Devolve os segundos gastos."""
    import hashlib
    import time

    if not all("q" in c for c in trecho["cenas"]):
        return _renderizar_inteiro(trecho, props, saida)
    props, saida = props.resolve(), saida.resolve()
    props.write_text(json.dumps({"trecho": trecho}, ensure_ascii=False), encoding="utf-8")
    t0 = time.time()
    cache = props.parent / "blocos"
    cache.mkdir(exist_ok=True)
    capa = next((p for p in (VIDEO_APP / "public").glob(f"{trecho['audio'].split('/')[0]}/capa.*")), None)
    capa_id = hashlib.sha1(capa.read_bytes()).hexdigest()[:12] if capa else ""
    blocos = _blocos_do_trecho(trecho)
    for b in blocos:
        codigo = _versao_do_codigo({c["tipo"] for c in b["cenas"]})  # só o código das cenas deste bloco
        b["arquivo"] = cache / f"{_impressao(b, trecho, codigo, capa_id)}.mp4"
        antigo = cache / f"{_impressao(b, trecho, codigo, capa_id, com_k=True)}.mp4"
        if not b["arquivo"].exists() and antigo.exists():  # cache feito antes da correção do "k": mesmo vídeo
            antigo.replace(b["arquivo"])
    faltam = [b for b in blocos if not b["arquivo"].exists()]
    audio = props.parent / "audio_render.wav"
    audio.unlink(missing_ok=True)  # um .wav velho não pode passar por "render ok"
    _mixar_audio(trecho, audio)  # FFmpeg, segundos (pelo Remotion levava ~9 min: ele percorre o vídeo inteiro)
    pedido = props.parent / "pedido_blocos.json"
    pedido.write_text(json.dumps({"props": str(props), "audio": None, "blocos": [
        {"inicio": b["inicio"], "fim": b["fim"], "saida": str(b["arquivo"].with_suffix(".tmp.mp4"))} for b in faltam]},
        ensure_ascii=False), encoding="utf-8")
    log = saida.with_name("render_erro.log")
    for tentativa in (1, 2):
        if not faltam:  # nada mudou na imagem: nem abre o Remotion
            break
        codigo, erro = _rodar_render(pedido, faltam, progresso)
        if codigo == 0 and all(b["arquivo"].with_suffix(".tmp.mp4").exists() for b in faltam):
            break
        texto = re.sub(r"\x1b\[[0-9;]*m", "", erro)
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n===== tentativa {tentativa} ({time.strftime('%H:%M:%S')}) =====\n{texto}")
    else:
        linhas = [ln.strip() for ln in texto.splitlines() if ln.strip() and not ln.strip().startswith("at ")]
        raise RuntimeError(f"Remotion falhou 2x. Resumo: {' | '.join(linhas[:4])[:300]} (log completo: {log.name})")
    for b in faltam:  # só vira cache depois de pronto (render interrompido não deixa bloco pela metade)
        b["arquivo"].with_suffix(".tmp.mp4").replace(b["arquivo"])
    lista = props.parent / "blocos.txt"
    lista.write_text("".join(f"file '{b['arquivo'].as_posix()}'\n" for b in blocos), encoding="utf-8")
    temporario = saida.with_name(saida.stem + "_renderizando.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    str(temporario)], check=True)
    temporario.replace(saida)
    usados = {b["arquivo"].name for b in blocos}
    for velho in cache.glob("*.mp4"):  # cache só dos blocos da versão atual
        if velho.name not in usados:
            velho.unlink(missing_ok=True)
    ULTIMO_RENDER.clear()
    ULTIMO_RENDER.update(blocos=len(blocos), renderizados=len(faltam), reaproveitados=len(blocos) - len(faltam))
    return time.time() - t0


def _renderizar_inteiro(trecho: dict, props: Path, saida: Path) -> float:
    """Render do vídeo inteiro numa passada (direções antigas, sem os quadros "q" por cena)."""
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
