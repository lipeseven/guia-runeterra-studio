"""Publicação: textos para o YouTube (títulos, descrição com capítulos e créditos, tags), thumbnail,
memória de uso de mídias e limpeza de arquivos depois de publicado."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .banco import RAIZ

sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "tools" / "direcao"))

AVISO_RIOT = ("O Guia de Runeterra foi criado sob a política “Legal Jibber Jabber” da Riot Games, usando recursos "
              "pertencentes à Riot Games. A Riot Games não endossa nem patrocina este projeto.")


def _mmss(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def capitulos(pasta: Path) -> list[dict]:
    """Um capítulo por seção do plano, no tempo real da gravação. Regras do YouTube: o 1º em 0:00,
    pelo menos 3 capítulos e cada um com 10 s ou mais — senão, não devolve nenhum."""
    from planejar import frases_do_roteiro

    dirc = pasta / "direcao"
    tempos = dirc / "tempos_gravacao.json"
    if not tempos.exists() or not (dirc / "plano.json").exists():
        return []
    palavras = json.loads(tempos.read_text(encoding="utf-8"))
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    frases = frases_do_roteiro(roteiro, palavras)
    plano = json.loads((dirc / "plano.json").read_text(encoding="utf-8"))
    caps = [{"titulo": "Introdução", "inicio": 0.0}]
    for s in sorted(plano.get("secoes", []), key=lambda s: s["frase_inicial"]):
        if 0 <= s["frase_inicial"] < len(frases):
            t = palavras[frases[s["frase_inicial"]]["de"]]["i"]
            if t < 1:
                caps[0]["titulo"] = s["titulo"]
            else:
                caps.append({"titulo": s["titulo"], "inicio": round(t, 1)})
    fim = palavras[-1]["f"]
    duracoes = [b["inicio"] - a["inicio"] for a, b in zip(caps, caps[1:])] + [fim - caps[-1]["inicio"]]
    if len(caps) < 3 or min(duracoes) < 10:
        return []
    return [{**c, "tempo": _mmss(c["inicio"])} for c in caps]


def midias_usadas(pasta: Path) -> list[int]:
    """Ids do acervo usados no vídeo final (imagens m<id> e tomadas t<id> → mídia de origem)."""
    from comum import abrir_acervo

    final = pasta / "direcao" / "direcao_final.json"
    if not final.exists():
        final = pasta / "direcao" / "direcao.json"
    if not final.exists():
        return []
    texto = final.read_text(encoding="utf-8")
    ids = {int(m) for m in re.findall(r"/m(\d+)\.", texto)}
    tomadas = {int(t) for t in re.findall(r"/t(\d+)\.mp4", texto)}
    if tomadas:
        con = abrir_acervo()
        for t in tomadas:
            r = con.execute("SELECT midia_id FROM tomadas WHERE id=?", (t,)).fetchone()
            if r:
                ids.add(r[0])
    return sorted(ids)


def sons_usados(pasta: Path) -> list[int]:
    """Ids do catálogo de efeitos sonoros usados no vídeo final (arquivos s<id>.wav)."""
    final = pasta / "direcao" / "direcao_final.json"
    if not final.exists():
        final = pasta / "direcao" / "direcao.json"
    if not final.exists():
        return []
    return sorted({int(s) for s in re.findall(r"/s(\d+)\.wav", final.read_text(encoding="utf-8"))})


def creditos_sons(ids: list[int]) -> list[str]:
    """CC BY exige crédito; CC0 e os gerados localmente não (mas não custa nada não listar)."""
    from comum import abrir_acervo

    con = abrir_acervo()
    linhas = []
    for sid in ids:
        r = con.execute("SELECT descricao, autor, url, licenca FROM sons WHERE id=?", (sid,)).fetchone()
        if r and r["autor"] and (r["licenca"] or "").startswith("CC BY"):
            linhas.append(f"\"{r['descricao']}\" por {r['autor']} — {r['url']} ({r['licenca']})")
    return sorted(set(linhas))


def creditos(ids: list[int]) -> list[str]:
    from comum import abrir_acervo

    con = abrir_acervo()
    linhas = []
    for mid in ids:
        r = con.execute("SELECT nome, autor, url, licenca FROM midias WHERE id=?", (mid,)).fetchone()
        if r and r["autor"]:
            linhas.append(f"{r['autor']}" + (f" — {r['url']}" if r["url"] else "") + (f" ({r['licenca']})" if r["licenca"] else ""))
    return sorted(set(linhas))


SISTEMA = """Você escreve os textos de YouTube do canal brasileiro "Guia de Runeterra" (lore de League of Legends).
Tom: português do Brasil, natural, curioso, sem clickbait mentiroso, sem emojis em excesso.
Padrão de título que funciona no canal: "Todos os DEMÔNIOS de League of Legends Explicados em 22 minutos"
(tema forte, uma palavra em CAIXA ALTA no máximo, promessa clara, até ~70 caracteres).
Responda SOMENTE com JSON."""


def gerar_textos(pasta: Path, titulo_card: str, duracao: float) -> dict:
    from claude_cli import chamar_json

    dirc = pasta / "direcao"
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    plano = json.loads((dirc / "plano.json").read_text(encoding="utf-8")) if (dirc / "plano.json").exists() else {}
    caps = capitulos(pasta)
    secoes = ", ".join(s["titulo"] for s in plano.get("secoes", []))
    prompt = (f"Título provisório do Felipe: {titulo_card}\nDuração: {_mmss(duracao)} ({round(duracao / 60)} minutos)\n"
              f"Seções do vídeo: {secoes or 'uma só'}\n\nROTEIRO:\n{roteiro[:9000]}\n\n"
              'Responda: {"titulos": [5 opções], "gancho": "2 a 3 frases para abrir a descrição, sem spoiler do final", '
              '"tags": [10 a 15 tags], "comentario_fixado": "uma pergunta para a comunidade comentar"}')
    r = chamar_json(prompt, SISTEMA, modelo="sonnet", etiqueta="publicacao-textos")
    ids = midias_usadas(pasta)
    cred = creditos(ids)
    partes = [r["gancho"].strip()]
    if caps:
        partes.append("Capítulos:\n" + "\n".join(f"{c['tempo']} {c['titulo']}" for c in caps))
    if cred:
        partes.append("Artes de fãs usadas (créditos):\n" + "\n".join(f"• {c}" for c in cred))
    cred_sons = creditos_sons(sons_usados(pasta))
    if cred_sons:
        partes.append("Efeitos sonoros (freesound.org):\n" + "\n".join(f"• {c}" for c in cred_sons))
    partes.append(AVISO_RIOT)
    return {"titulos": r["titulos"], "titulo": r["titulos"][0], "descricao": "\n\n".join(partes),
            "tags": r["tags"], "comentario_fixado": r.get("comentario_fixado", ""), "capitulos": caps,
            "midias_usadas": len(ids)}


def exportar_thumbnail(pasta: Path) -> Path | None:
    """A capa do Felipe no tamanho do YouTube (1280x720, recorte central se a proporção for diferente)."""
    from PIL import Image, ImageOps

    capa = next(iter(sorted((pasta / "direcao").glob("capa.*"))), None)
    if not capa:
        return None
    destino = pasta / "saida" / "thumbnail.jpg"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(capa) as im:
        ImageOps.fit(im.convert("RGB"), (1280, 720), Image.LANCZOS).save(destino, quality=92)
    return destino


def registrar_uso(pasta: Path, slug: str, quando: str) -> int:
    from comum import abrir_acervo

    ids = midias_usadas(pasta)
    con = abrir_acervo()
    con.executemany("INSERT OR REPLACE INTO uso_midia (midia_id, video, publicado_em) VALUES (?,?,?)",
                    [(i, slug, quando) for i in ids])
    con.executemany("INSERT OR REPLACE INTO uso_som (som_id, video, publicado_em) VALUES (?,?,?)",
                    [(s, slug, quando) for s in sons_usados(pasta)])
    con.commit()
    return len(ids)


def tamanhos(pasta: Path) -> dict:
    def t(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0

    publico = RAIZ / "app" / "video" / "public" / pasta.name
    return {"trabalho": t(pasta / "trabalho") + t(publico), "saida": t(pasta / "saida"),
            "entrada": t(pasta / "entrada"), "direcao": t(pasta / "direcao")}


def arquivar(pasta: Path) -> dict:
    """Vídeo publicado não se mexe mais: tudo vai para a Lixeira do Windows (recuperável), menos a capa,
    que fica em projetos/<slug>/capa.* para o card do quadro. Chamar DEPOIS de registrar_uso (que lê a direção)."""
    import shutil

    from send2trash import send2trash

    antes = sum(tamanhos(pasta).values())
    capa = next(iter(sorted((pasta / "direcao").glob("capa.*"))), None) or next(iter(sorted(pasta.glob("capa.*"))), None)
    guardada = None
    if capa:
        guardada = pasta / f"capa{capa.suffix}"
        if capa != guardada:
            shutil.copy2(capa, guardada)
    alvos = [p for p in pasta.iterdir() if p != guardada] if pasta.exists() else []
    alvos.append(RAIZ / "app" / "video" / "public" / pasta.name)
    for a in alvos:
        if a.exists():
            send2trash(str(a.resolve()))
    return {"liberado": antes, "capa": guardada.relative_to(RAIZ).as_posix() if guardada else None}
