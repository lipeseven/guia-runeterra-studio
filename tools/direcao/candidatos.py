"""Diretor — busca local (gratuita) de candidatos para cada necessidade do plano + folhas para a 2ª passada."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acervo"))
from comum import PASTA_ACERVO, PASTA_MINIATURAS, abrir_acervo  # noqa: E402

POR_NECESSIDADE = 4
PASTA_TOMADAS = Path(__file__).resolve().parents[2] / "dados" / "acervo" / "tomadas"


def necessidades(plano: dict, frases: list[dict]) -> list[dict]:
    """Tudo que precisa de mídia: cenas com busca e cada peça de mosaico."""
    saida = []
    for k, c in enumerate(plano["cenas"]):
        if c["tipo"] in ("capa", "dialogo") or not c.get("busca"):
            continue
        texto = frases[c["frase"]]["texto"]
        saida.append({"id": f"C{k}", "cena": k, "tipo": c["tipo"], "busca": c["busca"], "frase": texto,
                      "legenda": c.get("legenda")})
        for j, peca in enumerate(c.get("mosaico") or []):
            saida.append({"id": f"C{k}p{j}", "cena": k, "peca": j, "tipo": "peca", "busca": peca["busca"],
                          "frase": texto, "legenda": peca.get("palavra")})
    return saida


def _pontuar(con, mid: int, nota: float, busca: dict, tipo: str) -> float:
    r = con.execute("SELECT categoria, personagens, transparente, tipo FROM midias WHERE id=?", (mid,)).fetchone()
    pers = {p.lower() for p in json.loads(r["personagens"] or "[]")}
    alvo = {p.lower() for p in busca.get("personagens") or []}
    bonus = 0.0
    if alvo and pers & alvo:
        bonus += 0.08
    elif alvo and pers and not pers & alvo:
        bonus -= 0.05  # imagem claramente de OUTRO personagem
    if r["categoria"] in (busca.get("categorias") or []):
        bonus += 0.03
    if tipo == "recorte":
        bonus += 0.10 if r["transparente"] or r["categoria"] == "recorte" else -0.10
    if r["categoria"] == "canal":
        bonus -= 0.5  # material do canal (logos, thumbs) não é ilustração
    # memória de uso: imagem usada nos últimos vídeos publicados fica menos provável (não some de vez)
    recentes = [x[0] for x in con.execute(
        "SELECT video FROM uso_midia GROUP BY video ORDER BY MAX(publicado_em) DESC LIMIT 3").fetchall()]
    if recentes and con.execute(f"SELECT 1 FROM uso_midia WHERE midia_id=? AND video IN ({','.join('?' * len(recentes))})",
                                (mid, *recentes)).fetchone():
        bonus -= 0.06
    return nota + bonus


def buscar(con, nec: dict) -> list[dict]:
    from busca_semantica import buscar as buscar_imagens

    busca = nec["busca"]
    consulta = busca["o_que"] + (" " + " ".join(busca.get("personagens") or []) if busca.get("personagens") else "")
    if nec["tipo"] == "clipe":
        from indexar_clipes import buscar as buscar_tomadas
        tomadas = buscar_tomadas(consulta, 120)
        alvo = {p.lower() for p in busca.get("personagens") or []}
        if alvo:  # existindo clipe do personagem citado, a escolha fica entre eles
            def do_alvo(t):
                pers = con.execute("SELECT personagens FROM midias WHERE id=?", (t["midia_id"],)).fetchone()[0]
                return bool({p.lower() for p in json.loads(pers or "[]")} & alvo)
            proprios = [t for t in tomadas if do_alvo(t)]
            tomadas = proprios or tomadas
        for t in tomadas:
            t["nota"] = _pontuar(con, t["midia_id"], t["nota"], busca, "clipe")
        tomadas.sort(key=lambda t: -t["nota"])
        return [{"tipo": "tomada", "id": t["id"], "midia_id": t["midia_id"], "inicio": t["inicio"], "fim": t["fim"],
                 "nota": round(t["nota"], 3), "miniatura": str(PASTA_TOMADAS / f"{t['midia_id']}_{t['n']}.jpg"),
                 "nome": t["nome"]} for t in tomadas[:POR_NECESSIDADE]]
    achados = [(mid, _pontuar(con, mid, nota, busca, nec["tipo"])) for mid, nota in buscar_imagens(consulta, 60)]
    # imagens estáticas para cenas de imagem (vídeos do acervo entram via tomadas)
    tipos = {r["id"]: r["tipo"] for r in con.execute("SELECT id, tipo FROM midias")}
    achados = [a for a in achados if tipos.get(a[0]) in ("imagem", "gif")]
    achados.sort(key=lambda a: -a[1])
    saida = []
    for mid, nota in achados[:POR_NECESSIDADE]:
        nome = con.execute("SELECT nome FROM midias WHERE id=?", (mid,)).fetchone()["nome"]
        saida.append({"tipo": "midia", "id": mid, "nota": round(nota, 3), "nome": nome,
                      "miniatura": str(PASTA_MINIATURAS / f"{mid}.jpg")})
    return saida


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
                rotulo = cand["nome"] + (f" {cand['inicio']:.0f}-{cand['fim']:.0f}s" if cand["tipo"] == "tomada" else "")
                d.rectangle([x, y + H - 20, x + W, y + H], fill="#000")
                d.text((x + 4, y + H - 19), rotulo[:38], fill="#bbbbbb", font=f_texto)
        arq = destino / f"candidatos_{i // por_folha + 1:02d}.jpg"
        folha.save(arq, quality=84)
        caminhos.append(arq)
    return caminhos


def preparar(plano: dict, frases: list[dict], pasta_trabalho: Path) -> tuple[list[dict], list[Path]]:
    con = abrir_acervo()
    necs = necessidades(plano, frases)
    for n in necs:
        n["candidatos"] = buscar(con, n)
    return necs, folhas(necs, pasta_trabalho / "candidatos")
