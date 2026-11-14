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

from canal import CANAL  # noqa: E402

AVISOS = {  # aviso legal no fim da descrição, por canal (canal.toml: aviso_legal)
    "f1": ("F1, FORMULA ONE, FORMULA 1 e as marcas relacionadas pertencem à Formula One Licensing B.V. "
           "Este é um canal independente, sem afiliação com a Fórmula 1 ou com a FIA."),
    "riot": ("O Guia de Runeterra foi criado sob a política “Legal Jibber Jabber” da Riot Games, usando recursos "
             "pertencentes à Riot Games. A Riot Games não endossa nem patrocina este projeto."),
}
AVISO_LEGAL = AVISOS.get(CANAL.get("aviso_legal", ""), "")


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


SISTEMA = f"""Você escreve os textos de YouTube do canal brasileiro "{CANAL['nome']}" ({CANAL['assunto']}).
Tom: português do Brasil, natural, curioso, sem clickbait mentiroso, sem emojis em excesso.
Padrão de título que funciona no canal: "{CANAL['exemplo_titulo']}"
(tema forte, uma palavra em CAIXA ALTA no máximo, promessa clara, até ~70 caracteres).
Responda SOMENTE com JSON."""


def _creditos_animacao(pasta: Path) -> list[str]:
    """Vídeo animado: fotos de pessoas aprovadas (Commons) e o modelo 3D do carro (CC BY pede crédito)."""
    if not (pasta / "direcao" / "vertical.json").exists():
        return []
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    import fotos

    linhas = fotos.creditos(pasta)
    from canal import CANAL

    cfg = CANAL.get("horizontal") or {}
    if cfg.get("carro") and json.loads((pasta / "direcao" / "vertical.json").read_text(encoding="utf-8")).get("formato") == "horizontal":
        modelo = fotos.credito_modelo(RAIZ / cfg.get("modelos", "") / cfg["carro"])
        if modelo:
            linhas.append(modelo)
    return linhas


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
    extras = _creditos_animacao(pasta)
    if extras:
        partes.append("Créditos:\n" + "\n".join(f"• {c}" for c in extras))
    if AVISO_LEGAL:
        partes.append(AVISO_LEGAL)
    return {"titulos": r["titulos"], "titulo": r["titulos"][0], "descricao": "\n\n".join(partes),
            "tags": r["tags"], "comentario_fixado": r.get("comentario_fixado", ""), "capitulos": caps,
            "midias_usadas": len(ids)}


# ---------------------------------------------------------------- documentário do F1 (fase 7c)
# Os mesmos textos (títulos, descrição, tags, comentário fixado), mas: capítulos tirados da SPEC (cena de abertura de
# cada capítulo da História, nos tempos da sua gravação), miniatura = sugestão de texto/enquadramento + um quadro do
# vídeo final na cena escolhida, créditos dos ativos (OpenF1, imagens validadas, SFX CC BY) e, se houver chave da YouTube
# Data API no .env (YOUTUBE_API_KEY), os vídeos parecidos que já existem entram no prompt. Sem chave: pula, sem erro.
# O prompt vai pelo orquestrador (o motor roda esta tarefa dentro de `pelo_orquestrador`: nada de `claude -p`).
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/"


def capitulos_doc(pasta: Path) -> list[dict]:
    """Um capítulo por capítulo da História, no início da 1ª cena dele na SPEC (tempos da narração que vale). Regras do
    YouTube: 1º em 0:00, ≥ 3 capítulos, cada um ≥ 10 s: capítulo curto junta com o anterior; menos de 3 = nenhum."""
    h = pasta / "horizontal"
    try:
        hist = json.loads((h / "historia.json").read_text(encoding="utf-8"))
        spec = json.loads((h / "spec.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    titulos = {c["id"]: c["titulo"] for c in hist.get("capitulos", [])}
    caps: list[dict] = []
    for c in spec.get("cenas", []):
        if not caps or caps[-1]["id"] != c.get("capitulo"):
            caps.append({"id": c.get("capitulo"), "titulo": titulos.get(c.get("capitulo"), "Capítulo"), "inicio": float(c["t0"])})
    if not caps:
        return []
    caps[0]["inicio"] = 0.0
    fim = float(spec["cenas"][-1]["t1"])
    ok = list(caps)

    def dur(k: int) -> float:
        return (ok[k + 1]["inicio"] if k + 1 < len(ok) else fim) - ok[k]["inicio"]

    while len(ok) > 1:   # capítulo curto some e o tempo dele fica com o anterior (o 1º fica: 0:00 é obrigatório)
        curtos = [k for k in range(len(ok)) if dur(k) < 10]
        if not curtos:
            break
        ok.pop(curtos[0] if curtos[0] > 0 else 1)
    if len(ok) < 3:
        return []
    return [{"titulo": c["titulo"], "inicio": round(c["inicio"], 1), "tempo": _mmss(c["inicio"]), "capitulo": c["id"]} for c in ok]


def _chave_youtube() -> str | None:
    import os

    from dotenv import dotenv_values

    return os.environ.get("YOUTUBE_API_KEY") or dotenv_values(RAIZ / ".env").get("YOUTUBE_API_KEY") or None


def _youtube(recurso: str, params: dict) -> dict:
    import urllib.parse
    import urllib.request

    with urllib.request.urlopen(YOUTUBE_API + recurso + "?" + urllib.parse.urlencode(params), timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def concorrentes(pasta: Path, consulta: str) -> dict:
    """Vídeos que já existem sobre o tema (título, canal, visualizações), pela YouTube Data API v3, só com a chave
    configurada. Cache em direcao/concorrentes.json (o prompt fica igual entre retomadas do orquestrador)."""
    arq = pasta / "direcao" / "concorrentes.json"
    if arq.exists():
        guardado = json.loads(arq.read_text(encoding="utf-8"))
        if guardado.get("consulta") == consulta and guardado.get("status") != "erro":
            return guardado
    chave = _chave_youtube()
    if not chave:
        return {"consulta": consulta, "status": "sem_chave", "itens": [],
                "aviso": "pesquisa de concorrentes pulada: sem YOUTUBE_API_KEY no .env"}
    try:
        busca = _youtube("search", {"part": "snippet", "type": "video", "maxResults": 10, "q": consulta,
                                    "relevanceLanguage": "pt", "regionCode": "BR", "key": chave})
        ids = [i["id"]["videoId"] for i in busca.get("items", []) if i.get("id", {}).get("videoId")]
        stats = {v["id"]: v for v in _youtube("videos", {"part": "statistics,contentDetails", "id": ",".join(ids), "key": chave}
                                              ).get("items", [])} if ids else {}
        itens = [{"titulo": i["snippet"]["title"], "canal": i["snippet"]["channelTitle"],
                  "publicado": i["snippet"].get("publishedAt", "")[:10],
                  "views": int(stats.get(i["id"]["videoId"], {}).get("statistics", {}).get("viewCount", 0) or 0),
                  "url": f"https://www.youtube.com/watch?v={i['id']['videoId']}"}
                 for i in busca.get("items", []) if i.get("id", {}).get("videoId")]
        r = {"consulta": consulta, "status": "ok", "itens": sorted(itens, key=lambda x: -x["views"])}
    except Exception as e:   # noqa: BLE001 — rede/cota/chave inválida: a publicação segue sem a pesquisa
        return {"consulta": consulta, "status": "erro", "itens": [], "aviso": f"pesquisa de concorrentes falhou: {str(e)[:200]}"}
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def _creditos_doc(pasta: Path) -> list[str]:
    h = pasta / "horizontal"
    linhas = ["Dados de cronometragem e telemetria: OpenF1 (openf1.org), projeto aberto e não oficial."]
    try:
        ativos = json.loads((h / "ativos.json").read_text(encoding="utf-8"))
        linhas += sorted({str(i["dados"]["credito"]) for i in ativos.get("itens", []) if (i.get("dados") or {}).get("credito")})
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    try:
        linhas += json.loads((h / "final" / "final.json").read_text(encoding="utf-8")).get("creditos_sfx") or []
    except (OSError, json.JSONDecodeError):
        pass
    return linhas


def quadro_miniatura(pasta: Path, final: Path | None, t: float) -> Path | None:
    """Quadro do vídeo final no tempo t → saida/miniatura_base.jpg (1280×720): a base da miniatura (o texto sugerido vai
    por cima no editor do Felipe; nada é desenhado aqui)."""
    import subprocess

    if not final or not final.exists():
        return None
    destino = pasta / "saida" / "miniatura_base.jpg"
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                         capture_output=True, text=True).stdout.strip()
    if dur:   # nunca depois do fim (ex.: SPEC mais longa que o final antigo)
        t = min(t, max(0.0, float(dur) - 0.1))
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(final), "-frames:v", "1",
                        "-vf", "scale=1280:720", "-q:v", "2", str(destino)], capture_output=True)
    return destino if r.returncode == 0 and destino.exists() else None


SISTEMA_DOC = SISTEMA + """
Documentário de F1 com gráficos e dados (OpenF1). A miniatura: texto curto (até 4 palavras), uma ideia só; enquadramento
diz o que aparece e onde (ex.: "gráfico de velocidade à direita, texto grande à esquerda"); escolha a CENA do vídeo cujo
quadro serve de base."""


def gerar_textos_doc(pasta: Path, titulo_card: str, duracao: float, final: Path | None) -> dict:
    from claude_cli import chamar_json

    h = pasta / "horizontal"
    roteiro = (pasta / "direcao" / "roteiro.txt").read_text(encoding="utf-8")
    spec = json.loads((h / "spec.json").read_text(encoding="utf-8"))
    hist = json.loads((h / "historia.json").read_text(encoding="utf-8")) if (h / "historia.json").exists() else {}
    caps = capitulos_doc(pasta)
    conc = concorrentes(pasta, titulo_card)
    cenas = "\n".join(f"- {c['id']} ({_mmss(c['t0'])}): {c.get('objetivo', '')}" + (f" | na tela: {' / '.join(c['texto'])}" if c.get("texto") else "")
                      for c in spec["cenas"][:80])
    viz = ("\n\nVÍDEOS QUE JÁ EXISTEM SOBRE O TEMA (YouTube, mais vistos primeiro; NÃO copie títulos, diferencie-se):\n"
           + "\n".join(f"- {i['titulo']} · {i['canal']} · {i['views']:,} views".replace(",", ".") for i in conc["itens"][:10])
           if conc["status"] == "ok" and conc["itens"] else "")
    prompt = (f"Título provisório do Felipe: {titulo_card}\nDuração: {_mmss(duracao)} ({round(duracao / 60)} minutos)\n"
              f"Tese da história: {hist.get('tese', '')}\n"
              f"Capítulos: {', '.join(c['titulo'] for c in caps) or 'sem capítulos (vídeo curto)'}\n\n"
              f"CENAS (id, início, o que mostra):\n{cenas}{viz}\n\nROTEIRO:\n{roteiro[:9000]}\n\n"
              'Responda: {"titulos": [6 opções], "gancho": "2 a 3 frases para abrir a descrição, sem spoiler do final", '
              '"tags": [10 a 15 tags], "comentario_fixado": "uma pergunta para a comunidade comentar", '
              '"miniatura": {"texto": "até 4 palavras", "enquadramento": "o que aparece e onde", "cena": "id de uma cena acima"}}')
    r = chamar_json(prompt, SISTEMA_DOC, modelo="sonnet", etiqueta="publicacao-doc")
    partes = [str(r["gancho"]).strip()]
    if caps:
        partes.append("Capítulos:\n" + "\n".join(f"{c['tempo']} {c['titulo']}" for c in caps))
    cred = _creditos_doc(pasta)
    if cred:
        partes.append("Créditos:\n" + "\n".join(f"• {c}" for c in cred))
    if AVISO_LEGAL:
        partes.append(AVISO_LEGAL)
    mini = r.get("miniatura") or {}
    por_id = {c["id"]: c for c in spec["cenas"]}
    cena = por_id.get(str(mini.get("cena"))) or max(spec["cenas"], key=lambda c: len(c.get("kits", [])))
    t = round((cena["t0"] + cena["t1"]) / 2, 2)
    return {"titulos": r["titulos"], "titulo": r["titulos"][0], "descricao": "\n\n".join(partes), "tags": r["tags"],
            "comentario_fixado": r.get("comentario_fixado", ""), "capitulos": caps, "midias_usadas": 0,
            "miniatura": {"texto": str(mini.get("texto", "")), "enquadramento": str(mini.get("enquadramento", "")),
                          "cena": cena["id"], "tempo": _mmss(t), "t": t,
                          "cena_trocada": str(mini.get("cena")) not in por_id},
            "concorrentes": conc, "_quadro": quadro_miniatura(pasta, final, t)}


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


def encerramento() -> Path:
    """Cena de encerramento fixa do canal (fora do Git): Runeterra = Runeterra/dados/encerramento/encerramento.mp4."""
    from canal import caminho

    return caminho("dados_acervo").parent / "encerramento" / "encerramento.mp4"


def com_encerramento(pasta: Path) -> Path | None:
    """Vídeo para subir: o último final_vN.mp4 + a cena de encerramento → final_vN_publicar.mp4 (o final fica
    intacto). Só o encerramento é recodificado (no formato do final); a junção não recomprime o vídeo."""
    import subprocess

    from comum import preparar_ffmpeg

    fim = encerramento()
    finais = [p for p in (pasta / "saida").glob("final_v*.mp4") if p.stem.split("_v")[1].isdigit()]
    if not fim.exists() or not finais:
        return None
    final = max(finais, key=lambda p: int(p.stem.split("_v")[1]))
    preparar_ffmpeg()
    sonda = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,time_base,sample_rate",
         "-of", "json", str(final)], capture_output=True, check=True).stdout)["streams"]
    v = next(s for s in sonda if s["codec_type"] == "video")
    a = next((s for s in sonda if s["codec_type"] == "audio"), {"sample_rate": "48000"})
    trab = pasta / "trabalho"
    trab.mkdir(exist_ok=True)
    ajustado = trab / "encerramento_ajustado.mp4"
    escala = (f"scale={v['width']}:{v['height']}:force_original_aspect_ratio=decrease,"
              f"pad={v['width']}:{v['height']}:(ow-iw)/2:(oh-ih)/2:white,fps={v['r_frame_rate']},format=yuv420p")
    base = ["ffmpeg", "-v", "error", "-y", "-i", str(fim), "-vf", escala,
            "-video_track_timescale", v["time_base"].split("/")[1],
            "-c:a", "aac", "-b:a", "192k", "-ar", a["sample_rate"], "-ac", "2"]
    try:
        subprocess.run(base + ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18", str(ajustado)], check=True)
    except subprocess.CalledProcessError:  # sem NVENC
        subprocess.run(base + ["-c:v", "libx264", "-crf", "17", str(ajustado)], check=True)
    lista = trab / "publicar.txt"
    lista.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in (final, ajustado)), encoding="utf-8")
    saida = final.with_name(f"{final.stem}_publicar.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    "-movflags", "+faststart", str(saida)], check=True)
    return saida


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


def esquecer_uso(slug: str) -> None:
    """Card excluído: tira o vídeo da memória de uso de mídias e sons."""
    from comum import abrir_acervo

    con = abrir_acervo()
    con.execute("DELETE FROM uso_midia WHERE video=?", (slug,))
    con.execute("DELETE FROM uso_som WHERE video=?", (slug,))
    con.commit()


def tamanhos(pasta: Path) -> dict:
    def t(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0

    publico = RAIZ / "app" / "video" / "public" / pasta.name
    return {"trabalho": t(pasta / "trabalho") + t(publico), "saida": t(pasta / "saida"),
            "entrada": t(pasta / "entrada"), "direcao": t(pasta / "direcao")}


def arquivar(pasta: Path) -> dict:
    """Vídeo publicado não se mexe mais: tudo vai para a Lixeira do Windows (recuperável), menos a capa,
    que fica em Runeterra/dados/projetos/<slug>/capa.* para o card do quadro. Chamar DEPOIS de registrar_uso (que lê a direção)."""
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
    em_uso = []  # ANTES de mover qualquer coisa: no Windows, pasta com arquivo aberto (player, editor) não se renomeia
    for a in alvos:
        if a.exists():
            teste = a.with_name(a.name + ".teste_arquivar")
            try:
                a.rename(teste)
                teste.rename(a)
            except OSError:
                em_uso.append(a.name)
    if em_uso:
        raise RuntimeError(f"há arquivo aberto em outro programa dentro de {', '.join(em_uso)} (feche o player/editor "
                           "e tente de novo; nada foi arquivado)")
    for a in alvos:
        if a.exists():
            send2trash(str(a.resolve()))
    return {"liberado": antes, "capa": guardada.relative_to(RAIZ).as_posix() if guardada else None}
