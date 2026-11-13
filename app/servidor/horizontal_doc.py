"""Card horizontal DOCUMENTAL (canal com `[horizontal_doc]` no canal.toml, ex.: Explicando F1).

Gancho mínimo do painel: o fluxo e o estado vivem no diretor do canal (`[horizontal_doc] diretor`, hoje
`F1/horizontal/diretor/`), no `estado.json` da pasta `<projeto>/horizontal/`. Este módulo só:
- chama a ponte do diretor (`painel.py`) num processo à parte (os módulos do diretor não são importados aqui);
- espelha o estado.json nas etapas e pendências do banco (cards e "Precisa de você");
- expõe a API das telas (ver/aprovar História, SPEC e Rascunho, pedidos por cena, passos do diretor).
Nada aqui chama o modelo: o que precisa do Claude vira prompt + pendência para o orquestrador.
"""
from __future__ import annotations

import json
import subprocess
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .banco import CANAL, RAIZ, atualizar_etapa, conectar, registrar

rota = APIRouter()

FORMATO = "horizontal_doc"
# etapa do diretor → chave da etapa no banco ("rascunho" já é do fluxo antigo do Runeterra)
CHAVE = {"historia": "historia", "spec": "spec", "ativos": "ativos", "verificacao": "verificacao", "rascunho": "rascunho_doc"}
TITULO = {"historia": "História", "spec": "SPEC", "ativos": "Ativos", "verificacao": "Verificação", "rascunho": "Rascunho"}
APROVACAO = {"historia", "spec", "rascunho"}
SEM_MONTADOR = "sem montador ainda"
PASSOS = ("historia", "spec", "ativos", "verificacao", "rascunho")


def ligado() -> bool:
    return bool(CANAL.get(FORMATO))


def _ponte():
    cfg = CANAL.get(FORMATO) or {}
    return RAIZ / cfg.get("diretor", "F1/horizontal/diretor") / "painel.py"


def chamar(pedido: dict, tempo: float = 120) -> dict:
    """Roda a ponte do diretor com o mesmo Python do servidor (.venv). Recusa da ponte → 409."""
    r = subprocess.run([sys.executable, str(_ponte())], input=json.dumps(pedido, ensure_ascii=False).encode("utf-8"),
                       capture_output=True, timeout=tempo)
    try:
        dados = json.loads(r.stdout.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(500, f"diretor falhou: {r.stderr.decode('utf-8', 'replace')[-600:]}") from None
    if not dados.get("ok"):
        raise HTTPException(409, dados.get("erro", "recusado"))
    return dados


def _card(con, vid: int):
    v = con.execute("SELECT id, slug, formato FROM videos WHERE id=?", (vid,)).fetchone()
    if not v:
        raise HTTPException(404, "vídeo não encontrado")
    if v["formato"] != FORMATO:
        raise HTTPException(404, "este card não é um documentário horizontal")
    return v


def _base(slug: str) -> dict:
    from .motor import PASTA_PROJETOS

    p = PASTA_PROJETOS / slug
    return {"pasta": str(p / "horizontal"), "slug": slug,
            "roteiro": str(p / "direcao" / "roteiro.txt"), "palavras": str(p / "direcao" / "tempos_voz.json")}


# ---------------------------------------------------------------- estado.json → banco
def _status_card(nome: str, reg: dict, montador: bool) -> tuple[str, str | None, str | None]:
    st, resumo = reg["status"], reg.get("resumo")
    if nome == "rascunho" and not montador:
        return "em_breve", SEM_MONTADOR, None
    if st == "pendente":
        return "pendente", None, None
    if st == "prompt_pronto":
        return "andamento", "aguardando o orquestrador", resumo
    if st == "gerado":
        return ("atencao", resumo, "aprove ★") if nome in APROVACAO else ("concluido", resumo, None)
    if st == "aprovado":
        return "concluido", resumo, "aprovado ★"
    if st == "mudanca_pedida":
        return "atencao", resumo, "mudança pedida: gerar nova versão"
    if st == "desatualizado":
        return "atencao", resumo, "desatualizado: a etapa anterior mudou"
    return "atencao", resumo, "falhou"   # falhou


def _abrir(con, vid: int, chave: str, etapa: str, titulo: str, texto: str) -> None:
    from .motor import abrir_pendencia

    linha = con.execute("SELECT id, texto FROM pendencias WHERE video_id=? AND chave=? AND resolvida=0", (vid, chave)).fetchone()
    if linha and linha["texto"] != texto:   # mesmo assunto, texto novo (ex.: outro prompt): atualiza
        con.execute("UPDATE pendencias SET titulo=?, texto=? WHERE id=?", (titulo, texto, linha["id"]))
        return
    abrir_pendencia(con, vid, chave, etapa, titulo, texto)


def _fechar_doc(con, vid: int, manter: set[str]) -> None:
    for r in con.execute("SELECT chave FROM pendencias WHERE video_id=? AND resolvida=0 AND chave LIKE 'doc_%'", (vid,)).fetchall():
        if r["chave"] not in manter:
            con.execute("UPDATE pendencias SET resolvida=1 WHERE video_id=? AND chave=? AND resolvida=0", (vid, r["chave"]))


def sincronizar(con, vid: int, r: dict) -> None:
    """Espelha o estado.json (resposta `resumo` da ponte) nas etapas e pendências do card."""
    estado, montador = r["estado"], r["montador"]
    for nome in PASSOS:
        status, resumo, detalhe = _status_card(nome, estado["etapas"][nome], montador)
        atual = con.execute("SELECT status, resumo, detalhe FROM etapas WHERE video_id=? AND chave=?", (vid, CHAVE[nome])).fetchone()
        if atual and (atual["status"], atual["resumo"], atual["detalhe"]) != (status, resumo, detalhe):
            atualizar_etapa(con, vid, CHAVE[nome], status, resumo, detalhe)
    manter = set()
    st_banco = {x["chave"]: x["status"] for x in con.execute("SELECT chave, status FROM etapas WHERE video_id=?", (vid,))}
    if st_banco.get("roteiro") == "concluido" and estado["etapas"]["historia"]["status"] == "pendente":
        manter.add("doc_historia")
        _abrir(con, vid, "doc_historia", "historia", "Gere a história do documentário",
               "No painel “Documentário”, clique em “Gerar prompt da História”"
               + ("" if st_banco.get("voz_ia") == "concluido" else " (sem a narração medida, os tempos ficam estimados)") + ".")
    for t in r["orquestrador"]:
        chave = f"doc_orq_{t['etapa']}"
        manter.add(chave)
        alvo = f"{TITULO[t['etapa']]}" + (" (pedidos por cena)" if t["cena"] else "")
        lista = [x for x in r["orquestrador"] if x["etapa"] == t["etapa"]]
        _abrir(con, vid, chave, CHAVE[t["etapa"]], f"Orquestrador: rodar o prompt da {alvo}",
               "Para o chat/orquestrador (o painel não chama o Claude): "
               + " | ".join(f"prompt {x['prompt']} → resposta JSON → {x['comando']}" for x in lista))
    for nome in ("historia", "spec"):
        if estado["etapas"][nome]["status"] == "gerado":
            manter.add(f"doc_aprovar_{nome}")
            _abrir(con, vid, f"doc_aprovar_{nome}", CHAVE[nome], f"Aprove a {TITULO[nome]} ★",
                   f"Confira a {TITULO[nome]} no painel “Documentário” e aprove, ou peça mudança"
                   + (" por cena." if nome == "spec" else "."))
    v = r.get("verificacao")
    if v and estado["etapas"]["verificacao"]["status"] in ("gerado", "falhou") and v["status"] != "aprovado":
        manter.add("doc_verificacao")
        c = v["contagem"]
        _abrir(con, vid, "doc_verificacao", "verificacao", f"Verificação {v['status']}",
               f"{c['erros']} erro(s), {c['pendencias']} pendência(s), {c['avisos']} aviso(s): veja no painel “Documentário”.")
    _fechar_doc(con, vid, manter)


def ler(con, vid: int) -> dict:
    v = _card(con, vid)
    r = chamar({"cmd": "resumo", **_base(v["slug"])})
    sincronizar(con, vid, r)
    con.commit()
    return r


def ao_mudar(con, vid: int) -> None:
    """Gancho do motor (roteiro aprovado, narração pronta): atualiza cards e pendências do documentário."""
    try:
        ler(con, vid)
    except HTTPException as e:
        registrar(con, vid, f"Documentário: {e.detail}", "alerta")


# ---------------------------------------------------------------- API das telas
@rota.get("/api/videos/{vid}/doc")
def ver(vid: int):
    with conectar() as con:
        return ler(con, vid)


@rota.post("/api/videos/{vid}/doc/passo/{passo}")
def rodar_passo(vid: int, passo: str):
    if passo not in PASSOS:
        raise HTTPException(400, "passo inválido")
    with conectar() as con:
        v = _card(con, vid)
        rot = con.execute("SELECT status FROM etapas WHERE video_id=? AND chave='roteiro'", (vid,)).fetchone()
        if passo in ("historia", "spec") and (not rot or rot["status"] != "concluido"):
            raise HTTPException(409, "aprove o roteiro antes (a história parte do roteiro aprovado)")
        r = chamar({"cmd": "passo", "passo": passo, **_base(v["slug"])}, tempo=600)["passo"]
        if r.get("do_cache"):
            registrar(con, vid, f"{TITULO[passo]}: resposta já guardada para o mesmo prompt (sem gastar cota)", "ok")
        elif r.get("precisa_modelo"):
            registrar(con, vid, f"{TITULO[passo]}: prompt pronto para o orquestrador", "info")
        else:
            registrar(con, vid, f"{TITULO[passo]}: " + (f"{r['status']}" if "status" in r else
                                                      ", ".join(f"{n} {k}" for k, n in r.get("resumo", {}).items() if n)), "info")
        return {"passo": r, **ler(con, vid)}


@rota.post("/api/videos/{vid}/doc/aprovar/{etapa}")
def aprovar(vid: int, etapa: str):
    if etapa not in APROVACAO:
        raise HTTPException(400, "só História, SPEC e Rascunho têm aprovação ★")
    with conectar() as con:
        v = _card(con, vid)
        chamar({"cmd": "aprovar", "etapa": etapa, **_base(v["slug"])})
        registrar(con, vid, f"{TITULO[etapa]} aprovada ★", "ok")
        return ler(con, vid)


class Pedido(BaseModel):
    etapa: str
    texto: str
    cena: str | None = None


@rota.post("/api/videos/{vid}/doc/pedido")
def pedir(vid: int, corpo: Pedido):
    with conectar() as con:
        v = _card(con, vid)
        chamar({"cmd": "pedir", "etapa": corpo.etapa, "texto": corpo.texto, "cena": corpo.cena, **_base(v["slug"])})
        registrar(con, vid, f"Pedido na {TITULO.get(corpo.etapa, corpo.etapa)}" + (f" (cena {corpo.cena})" if corpo.cena else "")
                  + f": {corpo.texto.strip()[:120]}", "info")
        return ler(con, vid)


@rota.delete("/api/videos/{vid}/doc/pedido/{pid}")
def retirar(vid: int, pid: str):
    with conectar() as con:
        v = _card(con, vid)
        chamar({"cmd": "retirar", "id": pid, **_base(v["slug"])})
        registrar(con, vid, f"Pedido {pid} retirado", "info")
        return ler(con, vid)
