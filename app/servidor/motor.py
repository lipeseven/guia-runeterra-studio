"""Motor (orquestrador): reage às ações do Felipe no painel e roda as etapas sozinho.

Regra: anda sozinho enquanto não precisa do Felipe; quando precisa, cria uma pendência
("Precisa de você") e para. Tarefas pesadas rodam numa fila, uma de cada vez (a GPU é uma só).
"""
from __future__ import annotations

import json
import queue
import re
import sys
import threading
import traceback
from pathlib import Path

from .banco import RAIZ, agora, atualizar_etapa, conectar, registrar

sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "tools" / "audio"))

PASTA_PROJETOS = RAIZ / "projetos"
PPM_FELIPE = 162
SUBPASTAS = ("entrada", "trabalho", "direcao", "saida")


# ---------------------------------------------------------------- pastas e pendências
def pasta_do_video(slug: str) -> Path:
    p = PASTA_PROJETOS / slug
    for s in SUBPASTAS:
        (p / s).mkdir(parents=True, exist_ok=True)
    return p


def abrir_pendencia(con, vid: int, chave: str, etapa: str, titulo: str, texto: str) -> None:
    """Cria a pendência se ainda não houver uma aberta com a mesma chave."""
    if not con.execute("SELECT 1 FROM pendencias WHERE video_id=? AND chave=? AND resolvida=0", (vid, chave)).fetchone():
        con.execute("INSERT INTO pendencias (video_id, etapa, chave, titulo, texto, criada_em) VALUES (?,?,?,?,?,?)",
                    (vid, etapa, chave, titulo, texto, agora()))


def fechar_pendencia(con, vid: int, chave: str) -> None:
    con.execute("UPDATE pendencias SET resolvida=1 WHERE video_id=? AND chave=? AND resolvida=0", (vid, chave))


# ---------------------------------------------------------------- gatilhos
PENDENCIAS_DO_ROTEIRO = ("enviar_roteiro", "aprovar_roteiro")


def ao_mover(con, vid: int, para: str) -> None:
    v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    etapa = con.execute("SELECT status, resumo FROM etapas WHERE video_id=? AND chave='roteiro'", (vid,)).fetchone()
    tem_roteiro = (PASTA_PROJETOS / v["slug"] / "direcao" / "roteiro.txt").exists()

    if para == "ideia":
        # Ideia = estacionado: nada cobra ação do Felipe. O roteiro enviado continua guardado.
        abertas = con.execute("SELECT COUNT(*) FROM pendencias WHERE video_id=? AND resolvida=0 AND chave IN (?,?)",
                              (vid, *PENDENCIAS_DO_ROTEIRO)).fetchone()[0]
        for chave in PENDENCIAS_DO_ROTEIRO:
            fechar_pendencia(con, vid, chave)
        if etapa["status"] == "atencao":
            con.execute("UPDATE etapas SET status='pendente', resumo=?, detalhe=?, atualizado_em=? WHERE video_id=? AND chave='roteiro'",
                        (etapa["resumo"] if tem_roteiro else None, "estacionado em Ideia" if tem_roteiro else None, agora(), vid))
        if abertas:
            registrar(con, vid, "Estacionado em Ideia: pendências recolhidas", "info")

    elif para == "roteiro" and etapa["status"] != "concluido":
        pasta_do_video(v["slug"])
        if not tem_roteiro:
            atualizar_etapa(con, vid, "roteiro", "atencao", "aguardando roteiro", "envie o .txt")
            abrir_pendencia(con, vid, "enviar_roteiro", "roteiro", "Envie o roteiro",
                            "Arraste o .txt do roteiro no painel “Roteiro”, logo abaixo.")
            registrar(con, vid, "Pasta do vídeo pronta; aguardando roteiro", "info")
        else:  # voltou de Ideia com roteiro já enviado, mas não aprovado
            con.execute("UPDATE etapas SET status='atencao', detalhe=?, atualizado_em=? WHERE video_id=? AND chave='roteiro'",
                        ("aguardando aprovação", agora(), vid))
            abrir_pendencia(con, vid, "aprovar_roteiro", "roteiro", "Aprove o roteiro",
                            "Confira o texto no painel “Roteiro” e clique em “Aprovar roteiro”.")

    if para == "gravacao":
        pasta_do_video(v["slug"])
        st = {r["chave"]: r["status"] for r in con.execute("SELECT chave, status FROM etapas WHERE video_id=?", (vid,))}
        if st.get("rascunho") == "atencao":  # mover para Gravação = rascunho aceito
            con.execute("UPDATE etapas SET status='concluido', atualizado_em=? WHERE video_id=? AND chave='rascunho'", (agora(), vid))
            fechar_pendencia(con, vid, "ver_rascunho")
            registrar(con, vid, "Rascunho aceito (card movido para Gravação)", "ok")
        if st.get("gravacao") not in ("andamento", "concluido"):
            atualizar_etapa(con, vid, "gravacao", "atencao", "aguardando gravação", "envie o áudio ou vídeo")
            abrir_pendencia(con, vid, "enviar_gravacao", "gravacao", "Envie sua gravação",
                            "Arraste o arquivo (áudio ou vídeo) no painel “Gravação”, ou coloque-o na pasta entrada/ "
                            "do vídeo e clique em “Já coloquei na pasta”.")
            registrar(con, vid, "Aguardando a gravação", "info")
    else:
        fechar_pendencia(con, vid, "enviar_gravacao")  # saiu da coluna Gravação: não cobra mais


def estatisticas(texto: str) -> dict:
    pars = [p for p in re.split(r"\n\s*\n", texto) if p.strip()]
    palavras = len(re.findall(r"\w+", texto))
    segundos = palavras / PPM_FELIPE * 60
    return {"paragrafos": len(pars), "palavras": palavras, "segundos": round(segundos)}


def mmss(s: float) -> str:
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def receber_roteiro(con, vid: int, texto: str, nome: str) -> dict:
    v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    pasta = pasta_do_video(v["slug"]) / "direcao"
    texto = texto.replace("\r\n", "\n").strip() + "\n"
    versoes = sorted(pasta.glob("roteiro_v*.txt"))
    n = len(versoes) + 1
    (pasta / f"roteiro_v{n}.txt").write_text(texto, encoding="utf-8")  # histórico de versões
    (pasta / "roteiro.txt").write_text(texto, encoding="utf-8")
    est = estatisticas(texto)
    atualizar_etapa(con, vid, "roteiro", "atencao",
                    f"{est['paragrafos']} parágrafos · {est['palavras']} palavras",
                    f"~{mmss(est['segundos'])} narrado · v{n}", {**est, "versao": n, "arquivo_original": nome})
    # um roteiro novo invalida o que veio depois dele
    con.execute("UPDATE etapas SET status='pendente', resumo=NULL, detalhe=NULL WHERE video_id=? AND chave='voz_guia'", (vid,))
    fechar_pendencia(con, vid, "enviar_roteiro")
    abrir_pendencia(con, vid, "aprovar_roteiro", "roteiro", "Aprove o roteiro",
                    f"Versão {n}: {est['palavras']} palavras, ~{mmss(est['segundos'])} narrado. "
                    "Confira o texto no painel “Roteiro” e clique em “Aprovar roteiro”.")
    registrar(con, vid, f"Roteiro v{n} recebido ({nome})", "info")
    return est


def receber_capa(con, vid: int, conteudo: bytes, ext: str) -> dict:
    """Guarda a capa (grade de ícones feita pelo Felipe) e detecta os círculos dos personagens.
    Os NOMES de cada círculo são lidos pelo diretor (Claude) na etapa de Direção."""
    from capa import detectar

    v = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()
    pasta = pasta_do_video(v["slug"]) / "direcao"
    for antiga in pasta.glob("capa.*"):
        antiga.unlink()
    arquivo = pasta / f"capa{ext}"
    arquivo.write_bytes(conteudo)
    circulos, _ = detectar(str(arquivo))
    rel = f"projetos/{v['slug']}/direcao/{arquivo.name}"
    # capa nova precisa de nova aprovação (o Felipe confere os círculos detectados)
    con.execute("UPDATE videos SET capa=?, capa_aprovada=0, atualizado_em=? WHERE id=?", (rel, agora(), vid))
    abrir_pendencia(con, vid, "aprovar_capa", "direcao", "Aprove a capa",
                    f"{len(circulos)} ícones detectados. Confira os círculos numerados no painel “Capa” e clique em “Aprovar capa”.")
    (pasta / "capa_circulos.json").write_text(json.dumps(circulos, indent=1), encoding="utf-8")
    registrar(con, vid, f"Capa recebida: {len(circulos)} ícones detectados", "ok" if circulos else "alerta")
    return {"capa": rel, "icones": len(circulos)}


def aprovar_roteiro(con, vid: int) -> None:
    atualizar_etapa_status(con, vid, "roteiro", "concluido")
    fechar_pendencia(con, vid, "aprovar_roteiro")
    registrar(con, vid, "Roteiro aprovado", "ok")
    FILA.put((vid, "voz_guia"))


def aprovar_capa(con, vid: int) -> None:
    con.execute("UPDATE videos SET capa_aprovada=1, atualizado_em=? WHERE id=?", (agora(), vid))
    fechar_pendencia(con, vid, "aprovar_capa")
    registrar(con, vid, "Capa aprovada", "ok")
    verificar_direcao(con, vid)


def condicoes_direcao(con, vid: int) -> dict:
    """O que a Direção precisa para começar sozinha (mostrado no quadro "Próximo passo")."""
    st = {r["chave"]: r["status"] for r in con.execute("SELECT chave, status FROM etapas WHERE video_id=?", (vid,))}
    v = con.execute("SELECT capa, capa_aprovada FROM videos WHERE id=?", (vid,)).fetchone()
    return {"roteiro_aprovado": st.get("roteiro") == "concluido",
            "voz_guia_pronta": st.get("voz_guia") == "concluido",
            "capa_aprovada": bool(v["capa"] and v["capa_aprovada"])}


def verificar_direcao(con, vid: int) -> None:
    """Chamado sempre que uma condição muda: se todas estão ok, a Direção começa sozinha."""
    if not all(condicoes_direcao(con, vid).values()):
        return
    if "direcao" in TAREFAS:
        if con.execute("SELECT status FROM etapas WHERE video_id=? AND chave='direcao'", (vid,)).fetchone()["status"] == "pendente":
            atualizar_etapa(con, vid, "direcao", "andamento", "na fila", "aguardando a vez na GPU")  # evita entrar 2x
            registrar(con, vid, "Direção na fila", "info")
            FILA.put((vid, "direcao"))
    else:  # diretor ainda em construção: avisa sem fingir que está trabalhando
        atualizar_etapa(con, vid, "direcao", "pendente", "pronto para dirigir", "diretor em construção")
        registrar(con, vid, "Tudo pronto para a direção (diretor em construção)", "info")


def atualizar_etapa_status(con, vid: int, chave: str, status: str) -> None:
    con.execute("UPDATE etapas SET status=?, atualizado_em=? WHERE video_id=? AND chave=?", (status, agora(), vid, chave))


# ---------------------------------------------------------------- tarefas (fila)
def tarefa_voz_guia(vid: int) -> None:
    from voz_guia import gerar

    with conectar() as con:
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
        atualizar_etapa(con, vid, "voz_guia", "andamento", "gerando…", "Fish Audio")
        registrar(con, vid, "Voz guia: gerando", "info")
        con.commit()
    pasta = PASTA_PROJETOS / slug
    roteiro = (pasta / "direcao" / "roteiro.txt").read_text(encoding="utf-8")
    info = gerar(roteiro, pasta / "trabalho" / "voz_guia.wav")
    with conectar() as con:
        atualizar_etapa(con, vid, "voz_guia", "concluido", f"{mmss(info['duracao'])} · {', '.join(info['motores'])}",
                        f"{info['ppm_original']} → {PPM_FELIPE} palavras/min",
                        {**info, "audio": f"projetos/{slug}/trabalho/voz_guia.wav"})
        registrar(con, vid, f"Voz guia pronta ({mmss(info['duracao'])})", "ok")
        verificar_direcao(con, vid)
        con.commit()


def ler_nomes_da_capa(capa: Path, detectar, chamar_json) -> tuple[list[dict], list[str]]:
    """Detecta os círculos (local) e pede ao Claude só os NOMES, na ordem de leitura (1 chamada barata)."""
    circulos, _ = detectar(str(capa))
    nomes = chamar_json("Esta é a capa do vídeo: ícones redondos de personagens com o nome embaixo. Liste os nomes na "
                        'ordem de leitura (linha a linha, da esquerda para a direita). Responda só JSON: {"nomes": [...]}',
                        "Você lê imagens com precisão.", modelo="sonnet", imagens=[capa], etiqueta="capa-nomes")["nomes"]
    for c, n in zip(circulos, nomes):
        c["nome"] = n
    return circulos, nomes


def tarefa_direcao(vid: int) -> None:
    """Diretor completo: tempos -> plano (Claude) -> candidatos (local) -> escolha (Claude, imagens) -> montagem -> rascunho."""
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from candidatos import preparar
    from capa import detectar
    from claude_cli import chamar_json
    from escolher import escolher
    from planejar import frases_do_roteiro, planejar
    from tempos import tempos_da_narracao

    with conectar() as con:
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
    pasta = PASTA_PROJETOS / slug
    dirc, trab = pasta / "direcao", pasta / "trabalho"

    def passo(n: int, texto: str) -> None:
        with conectar() as con:
            atualizar_etapa(con, vid, "direcao", "andamento", f"{n}/5 · {texto}", "diretor trabalhando")
            registrar(con, vid, f"Direção {n}/5: {texto}", "info")
            con.commit()

    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    passo(1, "medindo tempos da voz guia")
    palavras = tempos_da_narracao(trab / "voz_guia.wav", roteiro, dirc / "tempos_guia.json")

    capa = next(iter(sorted(dirc.glob("capa.*"))))
    arq_circ = dirc / "capa_circulos.json"
    salvos = json.loads(arq_circ.read_text(encoding="utf-8")) if arq_circ.exists() else []
    if salvos and all(c.get("nome") for c in salvos) and arq_circ.stat().st_mtime >= capa.stat().st_mtime:
        circulos, nomes = salvos, [c["nome"] for c in salvos]
    else:
        circulos, nomes = ler_nomes_da_capa(capa, detectar, chamar_json)
        arq_circ.write_text(json.dumps(circulos, ensure_ascii=False, indent=1), encoding="utf-8")

    # Retomada: se um passo já foi feito DEPOIS da última mudança no que ele depende, reaproveita
    # (um erro no render não pode gastar a cota do Claude de novo).
    def recente(arq: Path, *depende: Path) -> bool:
        return arq.exists() and all(arq.stat().st_mtime >= d.stat().st_mtime for d in depende if d.exists())

    arq_plano, arq_cand, arq_esc = dirc / "plano.json", dirc / "candidatos.json", dirc / "escolhas.json"
    frases = frases_do_roteiro(roteiro, palavras)
    if recente(arq_plano, dirc / "roteiro.txt", capa):
        plano = json.loads(arq_plano.read_text(encoding="utf-8"))
    else:
        passo(2, "planejando as cenas (Claude)")
        plano, frases = planejar(roteiro, palavras, nomes)
        arq_plano.write_text(json.dumps(plano, ensure_ascii=False, indent=1), encoding="utf-8")

    folhas = sorted((trab / "candidatos").glob("candidatos_*.jpg"))
    if recente(arq_cand, arq_plano) and folhas:
        necs = json.loads(arq_cand.read_text(encoding="utf-8"))
    else:
        passo(3, "buscando mídias no acervo")
        necs, folhas = preparar(plano, frases, trab)
        arq_cand.write_text(json.dumps(necs, ensure_ascii=False, indent=1), encoding="utf-8")

    if recente(arq_esc, arq_cand):
        escolhas = json.loads(arq_esc.read_text(encoding="utf-8"))
    else:
        passo(4, "escolhendo as imagens (Claude)")
        escolhas = escolher(necs, folhas)
        arq_esc.write_text(json.dumps(escolhas, ensure_ascii=False, indent=1), encoding="utf-8")

    passo(5, "renderizando o rascunho")
    montar_e_renderizar(vid, slug, palavras, frases, plano, necs, escolhas, capa, circulos, primeira_vez=True)


def proxima_versao(pasta: Path, prefixo: str = "rascunho") -> int:
    """Número da próxima versão (rascunho_v1.mp4, v2, … ou final_v1.mp4…; o antigo rascunho.mp4 conta como v1)."""
    nums = [int(p.stem.split("_v")[1]) for p in pasta.glob(f"{prefixo}_v*.mp4") if p.stem.split("_v")[1].isdigit()]
    if (pasta / f"{prefixo}.mp4").exists():
        nums.append(1)
    return max(nums, default=0) + 1


def montar_e_renderizar(vid: int, slug: str, palavras, frases, plano, necs, escolhas, capa, circulos,
                        primeira_vez: bool) -> None:
    """Aplica os ajustes do storyboard, monta a direção, renderiza o rascunho e atualiza o painel."""
    from montar import montar, renderizar

    from .storyboard import aplicar

    pasta = PASTA_PROJETOS / slug
    dirc, trab = pasta / "direcao", pasta / "trabalho"
    ajustes = json.loads((dirc / "ajustes.json").read_text(encoding="utf-8")) if (dirc / "ajustes.json").exists() else {}
    plano_final, escolhas_finais = aplicar(plano, escolhas, ajustes)
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    trecho, pendencias = montar(slug, roteiro, palavras, frases, plano_final, necs, escolhas_finais, capa, circulos,
                                trab / "voz_guia.wav")
    (dirc / "direcao.json").write_text(json.dumps(trecho, ensure_ascii=False, indent=1), encoding="utf-8")
    # Cada versão ganha o PRÓPRIO arquivo. Nunca renomear/sobrescrever a anterior: ela pode estar aberta
    # no player do painel, e o Windows não deixa mexer em arquivo em uso.
    versao = proxima_versao(trab)
    arquivo = trab / f"rascunho_v{versao}.mp4"
    segundos = renderizar(trecho, trab / "props.json", arquivo)

    with conectar() as con:
        tipos = {}
        for c in trecho["cenas"]:
            tipos[c["tipo"]] = tipos.get(c["tipo"], 0) + 1
        resumo_tipos = " · ".join(f"{n} {t}" for t, n in sorted(tipos.items(), key=lambda x: -x[1]))
        atualizar_etapa(con, vid, "direcao", "concluido", f"{len(trecho['cenas'])} cenas", resumo_tipos,
                        {"tipos": tipos, "observacoes": plano.get("observacoes")})
        atualizar_etapa(con, vid, "rascunho", "atencao",
                        f"{mmss(palavras[-1]['f'])} · {len(trecho['cenas'])} cenas" if primeira_vez else f"v{versao} pronto · valide",
                        f"v{versao} · render em {mmss(segundos)}",
                        {"video": f"projetos/{slug}/trabalho/{arquivo.name}", "versao": versao})
        con.execute("UPDATE pendencias SET resolvida=1 WHERE video_id=? AND chave='cena_sem_imagem' AND resolvida=0", (vid,))
        for p in pendencias:
            con.execute("INSERT INTO pendencias (video_id, etapa, chave, titulo, texto, criada_em) VALUES (?,?,?,?,?,?)",
                        (vid, "midias", "cena_sem_imagem", p["titulo"], p["texto"], agora()))
        if primeira_vez and plano.get("observacoes"):
            abrir_pendencia(con, vid, "obs_diretor", "direcao", "Observações do diretor", plano["observacoes"])
        abrir_pendencia(con, vid, "ver_rascunho", "rascunho",
                        "Assista o rascunho" if primeira_vez else f"Novo rascunho pronto (v{versao}): assista e valide",
                        "O rascunho (com a voz guia) está na Prévia. Para trocar imagens, legendas ou pedir mudanças, "
                        "abra o storyboard. Se estiver tudo certo, aprove.")
        registrar(con, vid, f"Rascunho v{versao} pronto: {len(trecho['cenas'])} cenas, render em {mmss(segundos)}", "ok")
        con.commit()


# ---------------------------------------------------------------- gravação
EXT_GRAVACAO = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".mp4", ".mkv", ".mov", ".webm"}


def gravacao_na_pasta(slug: str) -> Path | None:
    """Arquivo de gravação mais recente na pasta entrada/ do vídeo."""
    entrada = PASTA_PROJETOS / slug / "entrada"
    arquivos = [p for p in entrada.glob("*") if p.is_file() and p.suffix.lower() in EXT_GRAVACAO] if entrada.exists() else []
    return max(arquivos, key=lambda p: p.stat().st_mtime) if arquivos else None


def receber_gravacao(con, vid: int, arquivo: Path) -> None:
    for chave in ("enviar_gravacao", "aprovar_gravacao", "leitura_diferente"):  # gravação nova substitui a anterior
        fechar_pendencia(con, vid, chave)
    atualizar_etapa(con, vid, "gravacao", "andamento", "na fila", arquivo.name)
    registrar(con, vid, f"Gravação recebida: {arquivo.name} ({arquivo.stat().st_size / 1e6:.0f} MB)", "info")
    FILA.put((vid, "gravacao"))


def tarefa_gravacao(vid: int) -> None:
    """Limpa a gravação e PARA: o Felipe confere o áudio limpo antes de qualquer realinhamento/render."""
    from limpar_gravacao import limpar

    with conectar() as con:
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
    pasta = PASTA_PROJETOS / slug
    dirc, trab = pasta / "direcao", pasta / "trabalho"
    original = gravacao_na_pasta(slug)
    if original is None:
        raise RuntimeError("nenhuma gravação encontrada na pasta entrada/ do vídeo")
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")

    def etapa(chave: str, status: str, resumo: str, detalhe: str, dados: dict | None = None) -> None:
        with conectar() as con:
            atualizar_etapa(con, vid, chave, status, resumo, detalhe, dados)
            con.commit()

    # 1) limpeza: regravações, falas fora do roteiro, pausas, volume (timbre intocado)
    etapa("gravacao", "andamento", "limpando a gravação…", original.name)
    rel = limpar(original, trab / "gravacao", roteiro)
    rel_orig = f"projetos/{slug}/entrada/{original.name}"
    rel_limpa = f"projetos/{slug}/trabalho/gravacao/limpa.wav"
    divergencias = rel.get("divergencias_do_roteiro", [])
    with conectar() as con:
        atualizar_etapa(con, vid, "gravacao", "atencao" if divergencias else "concluido",
                        f"{mmss(rel['duracao_original'])} → {mmss(rel['duracao_limpa'])} · {len(rel['removidos'])} cortes",
                        f"{len(rel.get('pausas_encurtadas', []))} pausas encurtadas · -14 LUFS",
                        {"original": rel_orig, "audio": rel_limpa, "relatorio": rel})
        if divergencias:
            abrir_pendencia(con, vid, "leitura_diferente", "gravacao", "Leitura diferente do roteiro",
                            " · ".join(f"“{d['roteiro']}” → “{d['lido']}”" for d in divergencias[:12])
                            + ". Nada foi cortado por isso; confirme se pode ficar assim.")
        registrar(con, vid, f"Gravação limpa: {len(rel['removidos'])} cortes, {rel['duracao_original']}s → {rel['duracao_limpa']}s", "ok")
        # Ponto de controle do Felipe: nada de ressincronizar/renderizar sobre um corte errado.
        con.execute("UPDATE etapas SET status='atencao' WHERE video_id=? AND chave='gravacao'", (vid,))
        abrir_pendencia(con, vid, "aprovar_gravacao", "gravacao", "Confira a gravação limpa",
                        f"{len(rel['removidos'])} cortes, {mmss(rel['duracao_original'])} → {mmss(rel['duracao_limpa'])}. "
                        "Ouça o áudio limpo no painel “Gravação” (dá para ver cada corte). Se estiver bom, aprove: "
                        "aí o sistema realinha as cenas à sua voz e renderiza.")
        con.commit()


def aprovar_gravacao(con, vid: int) -> None:
    fechar_pendencia(con, vid, "aprovar_gravacao")
    fechar_pendencia(con, vid, "leitura_diferente")  # aprovar o áudio = aceitar a leitura como está
    atualizar_etapa_status(con, vid, "gravacao", "concluido")
    atualizar_etapa(con, vid, "ressincronizacao", "andamento", "na fila", "aguardando a vez na GPU")
    registrar(con, vid, "Gravação limpa aprovada", "ok")
    FILA.put((vid, "final"))


def tarefa_final(vid: int) -> None:
    """Depois da gravação aprovada: realinha a direção à voz do Felipe e renderiza com a narração real."""
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from alinhar import alinhar
    from montar import montar, renderizar
    from planejar import frases_do_roteiro

    from .storyboard import aplicar

    with conectar() as con:
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
    pasta = PASTA_PROJETOS / slug
    dirc, trab, saida = pasta / "direcao", pasta / "trabalho", pasta / "saida"
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")

    def etapa(chave: str, status: str, resumo: str, detalhe: str, dados: dict | None = None) -> None:
        with conectar() as con:
            atualizar_etapa(con, vid, chave, status, resumo, detalhe, dados)
            con.commit()

    # 2) ressincronização: a direção aponta para palavras do roteiro; só trocam os tempos
    etapa("ressincronizacao", "andamento", "alinhando à sua voz…", "palavras do roteiro")
    palavras = alinhar(roteiro, json.loads((trab / "gravacao" / "palavras.json").read_text(encoding="utf-8")))
    (dirc / "tempos_gravacao.json").write_text(json.dumps(palavras, ensure_ascii=False, indent=1), encoding="utf-8")
    estimadas = sum(1 for w in palavras if w.get("estimado"))

    # 3) render com a narração real (mesma direção aprovada no storyboard)
    ler = lambda nome: json.loads((dirc / nome).read_text(encoding="utf-8"))  # noqa: E731
    ajustes = ler("ajustes.json") if (dirc / "ajustes.json").exists() else {}
    plano, escolhas = aplicar(ler("plano.json"), ler("escolhas.json"), ajustes)
    capa = next(iter(sorted(dirc.glob("capa.*"))))
    frases = frases_do_roteiro(roteiro, palavras)
    trecho, _ = montar(slug, roteiro, palavras, frases, plano, ler("candidatos.json"), escolhas, capa,
                       ler("capa_circulos.json"), trab / "gravacao" / "limpa.wav")
    (dirc / "direcao_final.json").write_text(json.dumps(trecho, ensure_ascii=False, indent=1), encoding="utf-8")
    etapa("ressincronizacao", "concluido", f"{len(trecho['cenas'])} cenas realinhadas",
          f"{estimadas} palavras com tempo estimado" if estimadas else "todas as palavras encontradas")
    etapa("render", "andamento", "renderizando com a sua voz…", "Remotion + NVENC")
    versao = proxima_versao(saida, "final")
    arquivo = saida / f"final_v{versao}.mp4"
    segundos = renderizar(trecho, trab / "props_final.json", arquivo)

    with conectar() as con:
        atualizar_etapa(con, vid, "render", "atencao", f"{mmss(palavras[-1]['f'])} · v{versao}",
                        f"render em {mmss(segundos)}", {"video": f"projetos/{slug}/saida/{arquivo.name}", "versao": versao})
        abrir_pendencia(con, vid, "ver_final", "render", "Assista o vídeo com a sua voz",
                        "O vídeo foi montado com a sua narração (limpa) e a direção aprovada no storyboard. "
                        "Confira na Prévia. Se precisar trocar algo, use o storyboard e gere de novo.")
        con.execute("UPDATE videos SET coluna='revisao', atualizado_em=? WHERE id=?", (agora(), vid))
        registrar(con, vid, f"Vídeo com a sua voz pronto (v{versao}, render em {mmss(segundos)}) → Revisão", "ok")
        con.commit()


def tarefa_rascunho(vid: int) -> None:
    """Refaz o rascunho com os ajustes do storyboard. Só chama o Claude se houver pedidos ao diretor."""
    sys.path.insert(0, str(RAIZ / "tools" / "direcao"))
    from planejar import frases_do_roteiro
    from revisar import revisar

    from .storyboard import pendentes_para_o_diretor

    with conectar() as con:
        slug = con.execute("SELECT slug FROM videos WHERE id=?", (vid,)).fetchone()["slug"]
    pasta = PASTA_PROJETOS / slug
    dirc, trab = pasta / "direcao", pasta / "trabalho"
    ler = lambda nome: json.loads((dirc / nome).read_text(encoding="utf-8"))  # noqa: E731
    roteiro = (dirc / "roteiro.txt").read_text(encoding="utf-8")
    palavras, plano, necs, escolhas = ler("tempos_guia.json"), ler("plano.json"), ler("candidatos.json"), ler("escolhas.json")
    ajustes = ler("ajustes.json") if (dirc / "ajustes.json").exists() else {}
    frases = frases_do_roteiro(roteiro, palavras)
    capa = next(iter(sorted(dirc.glob("capa.*"))))
    circulos = ler("capa_circulos.json") if (dirc / "capa_circulos.json").exists() else []
    if not circulos or not all(c.get("nome") for c in circulos):
        from capa import detectar
        from claude_cli import chamar_json
        circulos, _ = ler_nomes_da_capa(capa, detectar, chamar_json)
        (dirc / "capa_circulos.json").write_text(json.dumps(circulos, ensure_ascii=False, indent=1), encoding="utf-8")
    ks = pendentes_para_o_diretor(ajustes)
    with conectar() as con:
        atualizar_etapa(con, vid, "direcao", "andamento",
                        f"refazendo {len(ks)} cena(s) (Claude)" if ks else "aplicando seus ajustes", "storyboard")
        fechar_pendencia(con, vid, "ver_rascunho")
        con.commit()
    if ks:
        revisar(plano, frases, necs, escolhas, ajustes, ks, trab, [c.get("nome", "") for c in circulos])
        for nome, dado in (("plano.json", plano), ("candidatos.json", necs), ("escolhas.json", escolhas),
                           ("ajustes.json", ajustes)):
            (dirc / nome).write_text(json.dumps(dado, ensure_ascii=False, indent=1), encoding="utf-8")
    with conectar() as con:
        atualizar_etapa(con, vid, "direcao", "andamento", "renderizando o novo rascunho", "storyboard")
        dados = json.loads(con.execute("SELECT dados FROM etapas WHERE video_id=? AND chave='rascunho'", (vid,)).fetchone()["dados"] or "{}")
        atualizar_etapa(con, vid, "rascunho", "andamento", f"gerando v{dados.get('versao', 1) + 1}…", "renderizando", dados)
        con.commit()
    montar_e_renderizar(vid, slug, palavras, frases, plano, necs, escolhas, capa, circulos, primeira_vez=False)


TAREFAS = {"voz_guia": tarefa_voz_guia, "direcao": tarefa_direcao, "rascunho": tarefa_rascunho,
           "gravacao": tarefa_gravacao, "final": tarefa_final}
FILA: "queue.Queue[tuple[int, str]]" = queue.Queue()
ESTADO = {"executando": None}


def _trabalhador() -> None:
    while True:
        vid, nome = FILA.get()
        ESTADO["executando"] = {"video": vid, "tarefa": nome, "desde": agora()}
        try:
            TAREFAS[nome](vid)
        except Exception as e:  # erro vira pendência visível, nunca some em silêncio
            traceback.print_exc()
            with conectar() as con:
                atualizar_etapa_status(con, vid, nome, "atencao")
                # nada pode ficar "girando" depois de uma falha (ex.: Direção presa em andamento)
                con.execute("UPDATE etapas SET status='atencao', atualizado_em=? WHERE video_id=? AND status='andamento'",
                            (agora(), vid))
                abrir_pendencia(con, vid, f"erro_{nome}", nome, f"Falha na etapa “{nome}”", str(e)[:400])
                registrar(con, vid, f"Erro em {nome}: {e}", "alerta")
                con.commit()
        finally:
            ESTADO["executando"] = None
            FILA.task_done()


def tentar_de_novo(con, vid: int, etapa: str) -> None:
    """Pendência de erro resolvida = refazer a etapa que falhou."""
    con.execute("UPDATE etapas SET status='pendente', atualizado_em=? WHERE video_id=? AND chave=?", (agora(), vid, etapa))
    registrar(con, vid, f"Tentando de novo: {etapa}", "info")
    if etapa == "direcao":
        verificar_direcao(con, vid)
    elif etapa in TAREFAS:
        FILA.put((vid, etapa))


def iniciar() -> None:
    threading.Thread(target=_trabalhador, daemon=True, name="motor").start()
    # Vídeos que ficaram "prontos para dirigir" enquanto o diretor não existia (ou o servidor estava desligado).
    with conectar() as con:
        for v in con.execute("SELECT id FROM videos").fetchall():
            verificar_direcao(con, v["id"])
        con.commit()


def situacao() -> dict:
    return {"executando": ESTADO["executando"], "na_fila": FILA.qsize()}


def ler_capa(slug: str) -> dict:
    pasta = PASTA_PROJETOS / slug / "direcao"
    arq = next(iter(sorted(pasta.glob("capa.*"))), None) if pasta.exists() else None
    circ = pasta / "capa_circulos.json"
    return {"capa": f"projetos/{slug}/direcao/{arq.name}" if arq else None,
            "circulos": json.loads(circ.read_text(encoding="utf-8")) if circ.exists() else []}


def ler_roteiro(slug: str) -> str | None:
    p = PASTA_PROJETOS / slug / "direcao" / "roteiro.txt"
    return p.read_text(encoding="utf-8") if p.exists() else None

