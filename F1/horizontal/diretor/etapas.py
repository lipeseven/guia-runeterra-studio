"""Fluxo do horizontal documental e o `estado.json` de cada vídeo (protocolo de arquivos; ver README.md).

O painel e o orquestrador só leem/escrevem arquivos na pasta do projeto (`F1/dados/projetos/<slug>/horizontal/`).
Cada etapa grava o próprio arquivo e o hash dele; a etapa seguinte guarda `base_hash` (o hash de onde veio). Se uma
etapa anterior muda depois, as seguintes ficam `desatualizado` (nada velho passa por aprovado).
"""
from __future__ import annotations

import time
from pathlib import Path

from comum import gravar_json, hash_dados, ler_json
from esquema import exigir

# (nome, arquivo, precisa de aprovação do Felipe ★)
ETAPAS = [
    ("historia", "historia.json", True),
    ("spec", "spec.json", True),
    ("ativos", "ativos.json", False),
    ("verificacao", "verificacao/verificacao.json", False),
    ("rascunho", "rascunho/rascunho.json", True),
]
NOMES = [e[0] for e in ETAPAS]
ARQUIVO = {e[0]: e[1] for e in ETAPAS}
APROVACAO = {e[0]: e[2] for e in ETAPAS}


def agora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def novo(slug: str) -> dict:
    return {"versao": 1, "slug": slug, "etapa_atual": "historia",
            "etapas": {n: {"status": "pendente", "arquivo": ARQUIVO[n]} for n in NOMES},
            "pedidos": [], "historico": [{"em": agora(), "evento": "criado"}]}


def ler(pasta: Path, slug: str | None = None) -> dict:
    e = ler_json(Path(pasta) / "estado.json")
    if e is None:
        e = novo(slug or Path(pasta).parent.name)
    exigir(e, "estado")
    return e


def gravar(pasta: Path, estado: dict) -> Path:
    estado["etapa_atual"] = _atual(estado)
    exigir(estado, "estado")
    return gravar_json(Path(pasta) / "estado.json", estado)


def _atual(estado: dict) -> str:
    for n in NOMES:
        st = estado["etapas"][n]["status"]
        ok = st == "aprovado" or (not APROVACAO[n] and st == "gerado")
        if not ok:
            return n
    return "pronto"


def _log(estado: dict, evento: str) -> None:
    estado["historico"].append({"em": agora(), "evento": evento})
    del estado["historico"][:-200]


def registrar(pasta: Path, etapa: str, dados: dict, base: dict | None = None, resumo: str = "") -> dict:
    """Etapa gerou o arquivo: grava, marca `gerado`, guarda hash/base_hash e desatualiza as etapas depois dela."""
    pasta = Path(pasta)
    estado = ler(pasta)
    gravar_json(pasta / ARQUIVO[etapa], dados)
    h = hash_dados(dados)
    anterior = estado["etapas"][etapa].get("hash")
    reg = {"status": "gerado", "arquivo": ARQUIVO[etapa], "hash": h, "atualizado_em": agora()}
    if base is not None:
        reg["base_hash"] = hash_dados(base)
    if resumo:
        reg["resumo"] = resumo
    estado["etapas"][etapa] = reg
    if anterior != h:
        for n in NOMES[NOMES.index(etapa) + 1:]:
            if estado["etapas"][n]["status"] not in ("pendente",):
                estado["etapas"][n]["status"] = "desatualizado"
    _log(estado, f"{etapa}: gerado {h}")
    gravar(pasta, estado)
    return estado


def marcar(pasta: Path, etapa: str, status: str, resumo: str = "") -> dict:
    estado = ler(pasta)
    estado["etapas"][etapa]["status"] = status
    estado["etapas"][etapa]["atualizado_em"] = agora()
    if resumo:
        estado["etapas"][etapa]["resumo"] = resumo
    _log(estado, f"{etapa}: {status}")
    gravar(pasta, estado)
    return estado


def aprovar(pasta: Path, etapa: str) -> dict:
    """★ Aprovação do Felipe. Recusa se o arquivo mudou depois de gerado ou se a etapa anterior não está aprovada/gerada."""
    pasta = Path(pasta)
    estado = ler(pasta)
    reg = estado["etapas"][etapa]
    if reg["status"] not in ("gerado", "mudanca_pedida"):
        raise ValueError(f"{etapa} está '{reg['status']}': só se aprova o que foi gerado")
    dados = ler_json(pasta / ARQUIVO[etapa])
    if dados is None or hash_dados(dados) != reg.get("hash"):
        raise ValueError(f"{ARQUIVO[etapa]} mudou depois de gerado: gere/registre de novo antes de aprovar")
    k = NOMES.index(etapa)
    if k:
        ant = NOMES[k - 1]
        st = estado["etapas"][ant]["status"]
        if not (st == "aprovado" or (not APROVACAO[ant] and st == "gerado")):
            raise ValueError(f"etapa anterior ({ant}) está '{st}'")
    reg["status"], reg["aprovado_em"] = "aprovado", agora()
    _log(estado, f"{etapa}: aprovado")
    gravar(pasta, estado)
    return estado


def ajustar(pasta: Path, etapa: str, dados: dict, evento: str) -> dict:
    """Ação direta do Felipe no arquivo da etapa (storyboard → spec.json): grava e atualiza o hash SEM mudar o status
    (aprovado continua aprovado: quem mexeu foi ele). As etapas depois dela que já tinham saído ficam `desatualizado`
    (o painel roda Ativos/Verificação de novo na hora; o Rascunho espera a próxima montagem)."""
    pasta = Path(pasta)
    estado = ler(pasta)
    reg = estado["etapas"][etapa]
    if reg["status"] not in ("gerado", "aprovado"):
        raise ValueError(f"{etapa} está '{reg['status']}': ação direta só em {etapa} gerada/aprovada")
    gravar_json(pasta / ARQUIVO[etapa], dados)
    h = hash_dados(dados)
    if reg.get("hash") != h:
        reg["hash"], reg["atualizado_em"] = h, agora()
        if reg["status"] == "aprovado":
            reg["aprovado_em"] = agora()
        for n in NOMES[NOMES.index(etapa) + 1:]:
            if estado["etapas"][n]["status"] in ("gerado", "aprovado", "falhou"):
                estado["etapas"][n]["status"] = "desatualizado"
    _log(estado, f"{etapa}: ajuste direto — {evento}")
    gravar(pasta, estado)
    return estado


def pedir(pasta: Path, etapa: str, texto: str, cena: str | None = None) -> dict:
    """Pedido de mudança do Felipe (por cena na SPEC). A etapa volta para `mudanca_pedida`."""
    estado = ler(pasta)
    p = {"id": f"p{len(estado['pedidos']) + 1}", "etapa": etapa, "texto": texto, "status": "aberto", "criado_em": agora()}
    if cena:
        p["cena"] = cena
    estado["pedidos"].append(p)
    if estado["etapas"][etapa]["status"] in ("gerado", "aprovado"):
        estado["etapas"][etapa]["status"] = "mudanca_pedida"
    _log(estado, f"{etapa}: pedido {p['id']}" + (f" (cena {cena})" if cena else ""))
    gravar(pasta, estado)
    return estado


def pedidos_abertos(estado: dict, etapa: str) -> list[dict]:
    return [p for p in estado["pedidos"] if p["etapa"] == etapa and p["status"] == "aberto"]


def atender(pasta: Path, ids: list[str], resposta: str = "") -> dict:
    estado = ler(pasta)
    for p in estado["pedidos"]:
        if p["id"] in ids:
            p["status"] = "atendido"
            if resposta:
                p["resposta"] = resposta
    gravar(pasta, estado)
    return estado
