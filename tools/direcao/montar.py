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
        origem = PASTA_ACERVO / self.con.execute("SELECT caminho FROM midias WHERE id=?", (mid,)).fetchone()[0]
        return self.arquivo(origem, f"m{mid}")

    def arquivo(self, origem: Path, nome: str) -> dict:
        ext = origem.suffix.lower()
        if ext in (".jpg", ".jpeg", ".png"):
            destino = self.pasta / f"{nome}{'.jpg' if ext == '.jpeg' else ext}"
            shutil.copyfile(origem, destino)
        else:  # webp, avif, jfif, gif (1º quadro), jpg_large...
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
        ordem = [e["escolha"] - 1] + [i for i in range(len(n["candidatos"])) if i != e["escolha"] - 1]
        for i in ordem:
            cand = n["candidatos"][i]
            chave = (cand["tipo"], cand["id"])
            if chave not in usados:
                usados.add(chave)
                return {**cand, "foco": e.get("foco") or [0.5, 0.45]}
        return None

    cenas = []
    for k, c in enumerate(plano["cenas"]):
        f = frases[c["frase"]]
        de = indice_na_frase(f, toks, c.get("comeca_na_palavra")) or f["de"]
        legenda_em = indice_na_frase(f, toks, c.get("legenda_na_palavra"))
        base = {"de": de, "ate": de, "semente": k, "secao": secao_da_frase(c["frase"])}
        tipo = c["tipo"]

        if tipo == "capa":
            if not capa_midia:
                continue
            nomes = [x.get("nome", "").lower() for x in circulos]
            alvo = (secoes[0].get("personagem_da_capa") or "").lower() if secoes else ""
            cenas.append({**base, "tipo": "capa", "midia": capa_midia, "circulos": circulos,
                          "destaque": nomes.index(alvo) if alvo in nomes else 0, "zoom": round(var.rng.uniform(2.3, 2.8), 2)})
            continue

        if tipo == "dialogo":
            d = c.get("dialogo") or {}
            esq, dir_ = icone(d.get("esquerda")), icone(d.get("direita"))
            if esq and dir_:
                destaques = [i for w in d.get("destaques", []) if (i := indice_na_frase(f, toks, w)) is not None]
                cenas.append({**base, "tipo": "dialogo", "esquerda": esq, "direita": dir_, "destaques": destaques})
                continue
            tipo = "cartao"  # sem ícones na capa: vira cartão

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
            cenas.append({**base, "tipo": "telacheia", "midia": midia, "foco": esc["foco"],
                          "movimento": var.movimento(), "entrada_img": var.imagem()})
        elif tipo == "recorte":
            cenas.append({**base, "tipo": "recorte", "midia": midia, "legenda": c.get("legenda") or "",
                          "legenda_em": legenda_em or de, "entrada_img": var.imagem(), "entrada_legenda": var.texto()})
        elif tipo == "mosaico":
            pecas = []
            for j, peca in enumerate(c.get("mosaico") or []):
                ep = escolhido(f"C{k}p{j}")
                pi = indice_na_frase(f, toks, peca.get("palavra"))
                if ep and ep["tipo"] == "midia":
                    pecas.append({"de": pi if pi is not None else de, "midia": m.imagem(ep["id"])})
            if len(pecas) >= 2:
                posicoes, borda = var.mosaico([p["midia"]["w"] / p["midia"]["h"] for p in pecas])
                cenas.append({**base, "tipo": "mosaico", "fundo": midia, "movimento": var.movimento(), "borda": borda,
                              "pecas": [{**p, **pos} for p, pos in zip(pecas, posicoes)]})
            else:
                cenas.append({**base, "tipo": "telacheia", "midia": midia, "foco": esc["foco"],
                              "movimento": var.movimento(), "entrada_img": var.imagem()})
        else:  # cartao (padrão)
            cenas.append({**base, "tipo": "cartao", "itens": [
                {"de": de, "midia": midia, "legenda": c.get("legenda") or "", "legenda_em": legenda_em,
                 "entrada_img": var.imagem(), "entrada_legenda": var.texto(), "movimento": var.movimento()}]})

    for a, b in zip(cenas, cenas[1:]):
        a["ate"] = max(a["de"], b["de"] - 1)
    if cenas:
        cenas[-1]["ate"] = len(toks) - 1
    trecho = {"audio": f"{slug}/voz.wav", "palavras": palavras, "cenas": cenas}
    return trecho, pendencias


def renderizar(trecho: dict, props: Path, saida: Path) -> float:
    """Renderiza a composição genérica "Video" com a direção dada. Devolve os segundos gastos."""
    import time

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
