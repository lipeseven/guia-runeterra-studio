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


TAREFAS = {"voz_guia": tarefa_voz_guia}
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
                abrir_pendencia(con, vid, f"erro_{nome}", nome, f"Falha na etapa “{nome}”", str(e)[:400])
                registrar(con, vid, f"Erro em {nome}: {e}", "alerta")
                con.commit()
        finally:
            ESTADO["executando"] = None
            FILA.task_done()


def iniciar() -> None:
    threading.Thread(target=_trabalhador, daemon=True, name="motor").start()


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

