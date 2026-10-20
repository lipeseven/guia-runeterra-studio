"""Diretor — busca local (gratuita) de candidatos para cada necessidade do plano + folhas para a 2ª passada."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acervo"))
from comum import DADOS_ACERVO, PASTA_ACERVO, PASTA_MINIATURAS, abrir_acervo  # noqa: E402

POR_NECESSIDADE = 4
PASTA_TOMADAS = DADOS_ACERVO / "tomadas"


SEM_MIDIA = ("capa", "hub", "dialogo", "texto", "ficha")  # ficha: imagem e dados vêm da Pokédex
SEM_MIDIA_PRINCIPAL = ("dividida", "lista", "rajada")  # só as peças têm imagem


def necessidades(plano: dict, frases: list[dict]) -> list[dict]:
    """Tudo que precisa de mídia: cenas com busca e cada peça de mosaico/dividida/lista."""
    from planejar import pecas_da_cena

    saida = []
    for k, c in enumerate(plano["cenas"]):
        if c["tipo"] in SEM_MIDIA:
            continue
        cid = id_da_cena(c, k)
        texto = frases[c["frase"]]["texto"]
        if c.get("busca") and c["tipo"] not in SEM_MIDIA_PRINCIPAL:
            saida.append({"id": cid, "cena": cid, "tipo": c["tipo"], "busca": c["busca"], "frase": texto,
                          "legenda": c.get("legenda") or c.get("rotulo")})
        if c["tipo"] in ("mosaico", "dividida", "lista", "rajada"):
            for j, peca in enumerate(pecas_da_cena(c)):
                if peca.get("busca"):
                    saida.append({"id": f"{cid}p{j}", "cena": cid, "peca": j, "tipo": "peca", "busca": peca["busca"],
                                  "frase": texto, "legenda": peca.get("rotulo") or peca.get("palavra")})
    return saida


def id_da_cena(c: dict, k: int) -> str:
    """Id estável da cena (planos por bloco); planos antigos usavam a posição ("C12")."""
    return c.get("id") or f"C{k}"


def numeros_das_cenas(plano: dict, dirc: Path) -> dict[str, str]:
    """Número que o Felipe vê no storyboard ("cena 40"). Fixo para sempre (direcao/numeros.json): dividir, remover
    ou acrescentar cenas não renumera as outras. Cena dividida: a original fica "40", as novas "40.1", "40.2"…
    (o id delas é "<id da original>-xxxx"); outra cena nova ganha o número da cena anterior + ".1", ".2"…"""
    arq = dirc / "numeros.json"
    nums: dict[str, str] = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    ids = [id_da_cena(c, k) for k, c in enumerate(plano.get("cenas", []))]
    if not nums:  # 1ª vez: a numeração que o Felipe já está vendo no storyboard (posição no plano)
        nums = {cid: str(k) for k, cid in enumerate(ids)}
    usados = set(nums.values())

    def proximo(base: str) -> str:
        j = 1
        while f"{base}.{j}" in usados:
            j += 1
        usados.add(f"{base}.{j}")
        return f"{base}.{j}"

    mudou = False
    anterior = None
    for cid in ids:
        if cid not in nums:
            pai = next((p for p in nums if cid.startswith(p + "-")), None)
            base = nums[pai] if pai else (nums[anterior] if anterior else "0")
            nums[cid] = proximo(base.split(".")[0] if not pai else base)
            mudou = True
        anterior = cid
    if mudou or not arq.exists():
        arq.write_text(json.dumps(nums, ensure_ascii=False, indent=1), encoding="utf-8")
    return nums


class Acervo:
    """Metadados do acervo carregados UMA vez por direção (a busca agora compara com o acervo inteiro)."""

    def __init__(self, con):
        self.con = con
        # só o que ainda existe na pasta do acervo (arquivo renomeado/apagado pelo Felipe quebraria a montagem)
        self.info = {r["id"]: {"nome": r["nome"], "tipo": r["tipo"], "categoria": r["categoria"],
                               "transparente": r["transparente"],
                               "pers": {_sem_acento(p) for p in json.loads(r["personagens"] or "[]")}}
                     for r in con.execute("SELECT id, caminho, nome, tipo, categoria, transparente, personagens FROM midias")
                     if (PASTA_ACERVO / r["caminho"]).exists()}
        # vocabulário: todo personagem/lugar/facção etiquetado no acervo ("xolaani", "camavor", "noxus"…)
        self.vocab = sorted({p for i in self.info.values() for p in i["pers"]}, key=len, reverse=True)
        self.usadas_no_video: set[int] = set()  # imagens já escolhidas em outras cenas DESTE vídeo

    def alvos(self, nec: dict) -> set[str]:
        """Quem a cena pede: os personagens da busca (tolerando grafia: "Zolani" → "xolaani") + nomes do acervo
        citados na descrição ou na frase narrada ("Camavor", "Ionia")."""
        import difflib
        import re

        busca = nec["busca"]
        alvos = set()
        for p in busca.get("personagens") or []:
            n = _sem_acento(p)
            perto = difflib.get_close_matches(n, self.vocab, n=1, cutoff=0.75)
            alvos.add(perto[0] if perto else n)
        texto = " " + re.sub(r"[^a-z0-9]+", " ", _sem_acento(busca.get("o_que", "") + " " + nec.get("frase", ""))) + " "
        for v in self.vocab:
            if len(v) >= 4 and f" {v} " in texto:
                alvos.add(v)
        return alvos

    def pontuar(self, mid: int, nota: float, alvos: set[str], busca: dict, tipo: str) -> float:
        i = self.info.get(mid)
        if i is None:
            return nota
        bonus = 0.0
        if alvos and i["pers"] & alvos:
            bonus += 0.12
        elif alvos and i["pers"]:
            bonus -= 0.05  # imagem claramente de OUTRO personagem/lugar
        if i["categoria"] in (busca.get("categorias") or []):
            bonus += 0.03
        if tipo == "recorte":
            bonus += 0.10 if i["transparente"] or i["categoria"] == "recorte" else -0.10
        if i["categoria"] == "canal":
            bonus -= 0.5  # material do canal (logos, thumbs) não é ilustração
        # repetir de um vídeo para outro não é problema (Felipe, 2026-10-20); o que cansa é repetir no MESMO vídeo:
        # imagem já escolhida em outra cena dele desce na lista (a montagem ainda impede repetir dentro do bloco)
        if mid in self.usadas_no_video:
            bonus -= 0.08
        return nota + bonus


def _sem_acento(t: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


def _imagens(ac: Acervo, nec: dict, alvos: set[str], consulta: str) -> list[dict]:
    from busca_semantica import buscar as buscar_imagens

    busca = nec["busca"]
    achados = [(mid, ac.pontuar(mid, nota, alvos, busca, nec["tipo"]))
               for mid, nota in buscar_imagens(consulta, len(ac.info))  # o acervo inteiro, não só o top 60
               if ac.info.get(mid, {}).get("tipo") in ("imagem", "gif")]
    achados.sort(key=lambda a: -a[1])
    escolhidos = achados[:POR_NECESSIDADE]
    # a cena pede alguém que existe no acervo: pelo menos 2 dos candidatos são dele(s)
    if alvos:
        do_alvo = [a for a in achados if ac.info[a[0]]["pers"] & alvos]
        minimo = min(2, len(do_alvo))
        faltam = minimo - sum(1 for a in escolhidos if ac.info[a[0]]["pers"] & alvos)
        if faltam > 0:
            extras = [a for a in do_alvo if a not in escolhidos][:faltam]
            escolhidos = [a for a in escolhidos if ac.info[a[0]]["pers"] & alvos] + \
                [a for a in escolhidos if not ac.info[a[0]]["pers"] & alvos][:POR_NECESSIDADE - minimo] + extras
            escolhidos.sort(key=lambda a: -a[1])
    return [{"tipo": "midia", "id": mid, "nota": round(nota, 3), "nome": ac.info[mid]["nome"],
             "miniatura": str(PASTA_MINIATURAS / f"{mid}.jpg")} for mid, nota in escolhidos]


def _arquivo_pedido(ac: Acervo, nec: dict) -> int | None:
    """Arquivo do acervo citado pelo nome pelo Felipe ("illaoi2.gif" → id da mídia)."""
    nome = _sem_acento(str((nec["busca"] or {}).get("arquivo") or ""))
    if not nome:
        return None
    imagens = {mid: i for mid, i in ac.info.items() if i["tipo"] in ("imagem", "gif")}
    for mid, i in imagens.items():
        if _sem_acento(i["nome"]) == nome:
            return mid
    base = nome.rsplit(".", 1)[0]  # sem extensão: "illaoi2" acha "illaoi2.gif"
    return next((mid for mid, i in imagens.items() if _sem_acento(i["nome"]).rsplit(".", 1)[0] == base), None)


def escolha_fixa(nec: dict) -> dict | None:
    """Se o 1º candidato é o arquivo que o Felipe pediu, a escolha já está feita (não vai ao Claude)."""
    c = (nec.get("candidatos") or [None])[0]
    if c and c.get("pedido"):
        return {"escolha": 1, "foco": [0.5, 0.45], "fixa": True, "motivo": "arquivo pedido pelo Felipe"}
    return None


def buscar(ac: Acervo, nec: dict) -> list[dict]:
    busca = nec["busca"]
    pedido = _arquivo_pedido(ac, nec)
    if pedido is not None:
        i = ac.info[pedido]
        fixo = {"tipo": "midia", "id": pedido, "nota": 1.0, "nome": i["nome"], "pedido": True,
                "miniatura": str(PASTA_MINIATURAS / f"{pedido}.jpg")}
        resto = [c for c in buscar(ac, {**nec, "busca": {k: v for k, v in busca.items() if k != "arquivo"}})
                 if not (c["tipo"] == "midia" and c["id"] == pedido)]
        return [fixo] + resto[:POR_NECESSIDADE - 1]
    alvos = ac.alvos(nec)
    consulta = busca["o_que"] + (" " + " ".join(busca.get("personagens") or []) if busca.get("personagens") else "")
    if nec["tipo"] == "clipe":
        from indexar_clipes import buscar as buscar_tomadas
        tomadas = buscar_tomadas(consulta, 120)
        if alvos:  # existindo clipe do personagem citado, a escolha fica entre eles
            proprios = [t for t in tomadas if ac.info.get(t["midia_id"], {}).get("pers", set()) & alvos]
            if not proprios and any(i["pers"] & alvos for i in ac.info.values()):
                return _imagens(ac, nec, alvos, consulta)  # sem clipe dele: imagem dele, não clipe de outro
            tomadas = proprios or tomadas
        for t in tomadas:
            t["nota"] = ac.pontuar(t["midia_id"], t["nota"], alvos, busca, "clipe")
        tomadas.sort(key=lambda t: -t["nota"])
        return [{"tipo": "tomada", "id": t["id"], "midia_id": t["midia_id"], "inicio": t["inicio"], "fim": t["fim"],
                 "nota": round(t["nota"], 3), "miniatura": str(PASTA_TOMADAS / f"{t['midia_id']}_{t['n']}.jpg"),
                 "nome": t["nome"]} for t in tomadas[:POR_NECESSIDADE]]
    return _imagens(ac, nec, alvos, consulta)


def folhas(necs: list[dict], destino: Path, por_folha: int = 7) -> list[Path]:
    """Uma linha por necessidade: texto à esquerda, 4 candidatos numerados à direita."""
    destino.mkdir(parents=True, exist_ok=True)
    f_titulo = ImageFont.truetype("arialbd.ttf", 17)
    f_texto = ImageFont.truetype("arial.ttf", 15)
    f_num = ImageFont.truetype("arialbd.ttf", 26)
    W_TXT, W, H = 380, 288, 162
    caminhos = []
    for i in range(0, len(necs), por_folha):
        lote = necs[i:i + por_folha]
        folha = Image.new("RGB", (W_TXT + POR_NECESSIDADE * (W + 8), len(lote) * (H + 10)), "#1b1b1b")
        d = ImageDraw.Draw(folha)
        for r, n in enumerate(lote):
            y = r * (H + 10)
            d.text((8, y + 6), f"{n['id']} · {n['tipo']}", fill="#ffd400", font=f_titulo)
            linhas, atual = [], ""
            for palavra in (n["frase"][:150] + ("…" if len(n["frase"]) > 150 else "")).split():
                if len(atual) + len(palavra) > 40:
                    linhas.append(atual)
                    atual = palavra
                else:
                    atual = f"{atual} {palavra}".strip()
            linhas.append(atual)
            for k, ln in enumerate(linhas[:5]):
                d.text((8, y + 30 + k * 18), ln, fill="#dddddd", font=f_texto)
            if n.get("legenda"):
                d.text((8, y + H - 22), f"legenda: {n['legenda']}"[:44], fill="#7fd1ff", font=f_texto)
            for c, cand in enumerate(n["candidatos"]):
                x = W_TXT + c * (W + 8)
                try:
                    im = ImageOps.contain(Image.open(cand["miniatura"]).convert("RGB"), (W, H))
                    folha.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
                except OSError:
                    d.rectangle([x, y, x + W, y + H], outline="#555")
                d.rectangle([x, y, x + 34, y + 32], fill="#000")
                d.text((x + 9, y + 2), str(c + 1), fill="#ffd400", font=f_num)
                # nome do arquivo: diz de qual personagem/vídeo o candidato vem
                rotulo = cand["nome"] + (f" {cand['inicio']:.0f}-{cand['fim']:.0f}s"  # clipe posto à mão: sem início/fim
                                         if cand["tipo"] == "tomada" and "inicio" in cand and "fim" in cand else "")
                d.rectangle([x, y + H - 20, x + W, y + H], fill="#000")
                d.text((x + 4, y + H - 19), rotulo[:38], fill="#bbbbbb", font=f_texto)
        arq = destino / f"candidatos_{i // por_folha + 1:02d}.jpg"
        folha.save(arq, quality=84)
        caminhos.append(arq)
    return caminhos


def _manual(c: dict) -> bool:
    """Candidato acrescentado pelo Felipe (busca do storyboard): marcado "manual" (ou, nos antigos, nota exata 1.0)."""
    return bool(c.get("manual")) or (c.get("tipo") == "midia" and c.get("nota") == 1.0)


def preparar(plano: dict, frases: list[dict], pasta_trabalho: Path, anteriores: list[dict] | None = None,
             escolhas: dict | None = None, blocos_iguais: set[str] | None = None) -> tuple[list[dict], list[dict], list[Path]]:
    """Candidatos de todas as necessidades + quais ainda precisam da escolha do Claude. Devolve (todas, as que
    precisam de escolha, folhas só dessas). Por cena:
      escolha feita e busca igual        → reaproveita candidatos e escolha (a escolha aponta para a POSIÇÃO)
      "folha não recebida" (falha nossa) → mesmos candidatos, volta para a escolha
      recusada de verdade                → busca de novo; só volta ao Claude se vierem candidatos DIFERENTES
      nova ou busca mudou                → busca e escolha
    `blocos_iguais`: capítulos que não mudaram nesta direção — recusa neles continua valendo (blocos desacoplados:
    mexer num capítulo não pode trocar imagem/enquadramento dos outros nem gastar cota com eles)."""
    import shutil

    from escolher import NAO_VIU

    escolhas = escolhas or {}
    ac = Acervo(abrir_acervo())
    for nid, e in escolhas.items():  # o que este vídeo já usa (para as cenas novas não repetirem)
        v = next((n for n in (anteriores or []) if n["id"] == nid), None)
        k = (e or {}).get("escolha")
        if v and k and 0 < k <= len(v.get("candidatos", [])) and v["candidatos"][k - 1]["tipo"] == "midia":
            ac.usadas_no_video.add(v["candidatos"][k - 1]["id"])
    velhas = {n["id"]: n for n in (anteriores or [])}
    bloco_da_cena = {id_da_cena(c, k): c.get("secao") for k, c in enumerate(plano.get("cenas", []))}
    necs, sem_escolha = [], []
    for n in necessidades(plano, frases):
        v = velhas.get(n["id"])
        e = escolhas.get(n["id"])
        mesma = bool(v and v.get("busca") == n["busca"] and v.get("candidatos"))
        if mesma and e and e.get("escolha"):
            n["candidatos"] = v["candidatos"]
        elif mesma and e and NAO_VIU.search(e.get("motivo") or ""):
            n["candidatos"] = v["candidatos"]
            sem_escolha.append(n)
        elif mesma and e and bloco_da_cena.get(n.get("cena")) in (blocos_iguais or set()):
            n["candidatos"] = v["candidatos"]  # capítulo intocado: fica como estava
        elif mesma and e:  # recusada: a busca melhorou?
            n["candidatos"] = buscar(ac, n)
            if [c["id"] for c in n["candidatos"]] != [c["id"] for c in v["candidatos"]]:
                sem_escolha.append(n)
            else:
                n["candidatos"] = v["candidatos"]  # mesmos candidatos: a recusa continua valendo (0 cota)
        else:
            n["candidatos"] = buscar(ac, n)
            fixa = escolha_fixa(n)
            if fixa:
                escolhas[n["id"]] = fixa  # arquivo pedido pelo Felipe (nota/pedido): não vai ao Claude
            else:
                sem_escolha.append(n)
        if v:  # imagens que o FELIPE pôs pela busca do storyboard nunca se perdem (a escolha dele aponta para elas)
            ids = {(c["tipo"], c["id"]) for c in n["candidatos"]}
            for c in v.get("candidatos", []):
                if _manual(c) and (c["tipo"], c["id"]) not in ids:
                    n["candidatos"].append(c)
        necs.append(n)
    # necessidades criadas pelo Felipe no storyboard (juntar cenas, outra metade do meio a meio, item buscado à mão)
    # não saem do plano do diretor: continuam enquanto a cena existir
    cenas_vivas = {id_da_cena(c, k) for k, c in enumerate(plano.get("cenas", []))}
    geradas = {n["id"] for n in necs}
    for v in anteriores or []:
        if v["id"] not in geradas and v.get("cena") in cenas_vivas and any(_manual(c) or v["tipo"] in ("peca", "metade")
                                                                          for c in v.get("candidatos", [])):
            necs.append(v)
    destino = pasta_trabalho / "candidatos"
    if destino.exists():
        shutil.rmtree(destino)  # folhas antigas não podem ir de novo para o Claude
    return necs, sem_escolha, folhas(sem_escolha, destino) if sem_escolha else []
