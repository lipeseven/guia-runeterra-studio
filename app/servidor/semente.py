"""Popula o painel com o que JÁ existe de verdade no projeto (roda só com o banco vazio)."""
from __future__ import annotations

import json
import re
import sqlite3

from .banco import RAIZ, atualizar_etapa, criar_video, pendencia, registrar


def _ler(caminho):
    p = RAIZ / caminho
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _mmss(s: float) -> str:
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def popular(con: sqlite3.Connection) -> None:
    if con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]:
        return

    # 1) Vídeo já publicado (feito à mão, antes do sistema)
    v = criar_video(con, "Todos os DEMÔNIOS de League of Legends Explicados em 22 minutos", "publicado",
                    capa="dados/prototipo/ref/capa.jpg")
    for chave in ("roteiro", "gravacao", "render", "publicacao"):
        atualizar_etapa(con, v, chave, "concluido", "feito à mão", "antes do Studio")
    atualizar_etapa(con, v, "render", "concluido", "22:00 · 327 cenas", "feito à mão")
    registrar(con, v, "Vídeo publicado no canal (feito à mão)", "ok", "2026-10-11T20:00:00")

    # 2) Teste do Fiddlesticks (gravação "suja" + protótipo de ressincronização)
    v = criar_video(con, "Fiddlesticks — teste de gravação", "montagem", capa="dados/prototipo/ref/capa.jpg")
    roteiro = (RAIZ / "dados/teste_gravacao/roteiro.txt")
    if roteiro.exists():
        txt = roteiro.read_text(encoding="utf-8")
        pars = [p for p in txt.split("\n\n") if p.strip()]
        n_palavras = len(re.findall(r"\w+", txt))
        atualizar_etapa(con, v, "roteiro", "concluido", f"{len(pars)} parágrafos · {n_palavras} palavras",
                        "roteiro.txt", {"arquivo": "dados/teste_gravacao/roteiro.txt"})
    guia = _ler("dados/teste_gravacao/voz_guia.json")
    if guia:
        atualizar_etapa(con, v, "voz_guia", "concluido", f"{_mmss(guia['duracao'])} · {', '.join(guia['motores'])}",
                        f"{guia['ppm_original']} → 162 palavras/min", guia)
    atualizar_etapa(con, v, "direcao", "andamento", "5 cenas (protótipo manual)", "diretor automático: próxima fase")
    if (RAIZ / "dados/teste_gravacao/FiddleGuia.mp4").exists():
        atualizar_etapa(con, v, "rascunho", "concluido", "0:22 · 5 cenas", "FiddleGuia.mp4",
                        {"video": "dados/teste_gravacao/FiddleGuia.mp4"})
    rel = _ler("dados/teste_gravacao/resultado/relatorio.json")
    if rel:
        atualizar_etapa(con, v, "gravacao", "atencao",
                        f"{_mmss(rel['duracao_original'])} → {_mmss(rel['duracao_limpa'])} · {len(rel['removidos'])} cortes",
                        f"{len(rel.get('pausas_encurtadas', []))} pausas encurtadas · -14 LUFS", rel)
        divs = rel.get("divergencias_do_roteiro", [])
        if divs:
            pendencia(con, v, "Leitura diferente do roteiro",
                      " · ".join(f"“{d['roteiro']}” → “{d['lido']}”" for d in divs) + ". Confirme se pode ficar assim.",
                      "gravacao")
        registrar(con, v, f"Gravação limpa: {len(rel['removidos'])} cortes, {rel['duracao_original']}s → {rel['duracao_limpa']}s", "ok")
    if (RAIZ / "dados/teste_gravacao/FiddleReal.mp4").exists():
        atualizar_etapa(con, v, "ressincronizacao", "concluido", "5 cenas realinhadas", "mesma direção, sua voz")
        atualizar_etapa(con, v, "render", "concluido", "0:25 · prévia", "FiddleReal.mp4",
                        {"video": "dados/teste_gravacao/FiddleReal.mp4"})
        registrar(con, v, "Ressincronização: direção realinhada à gravação", "ok")
    con.commit()
