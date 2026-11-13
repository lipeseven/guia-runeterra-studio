"""Etapa ATIVOS: o que cada cena da SPEC precisa e se já existe, sem inventar nada.

Por padrão só OLHA (offline, rápido): voltas do `kit/gps`, comparações do `kit/graficos`, resultados do `kit/imagens`
(o `<slug>.json` com `status`), banco do `kit/sfx`, modelos 3D em `F1/dados/modelos3d`. Para cada item: `pronto`,
`falta` (com o `comando` que produz), `nao_validado`, `reprovado` ou `nao_encontrado` (os três últimos vêm do
`kit/imagens`). `--produzir` roda os comandos que faltam (rede: OpenF1 e YouTube); o teste automático não usa rede.

    python ativos.py <pasta_do_projeto> [--produzir]
"""
from __future__ import annotations

import glob
import subprocess
import sys
import time
from pathlib import Path

import etapas
from comum import KIT, categorias_sfx, dados_f1, hash_dados, ler_json

PY = sys.executable


def _acima(rel: str) -> Path | None:
    """Pasta fora do Git (banco do SFX): nesta cópia ou numa pasta acima (worktree dentro do repositório principal)."""
    for base in [KIT.parents[2], *KIT.parents[2].parents]:
        p = base / rel
        if p.exists():
            return p
    return None


def _volta(v) -> str:
    return "*" if v == "melhor" else str(int(v))


def _um(padrao: str) -> Path | None:
    achados = sorted(glob.glob(padrao))
    return Path(achados[0]) if len(achados) == 1 else None


def _alinhamento(glb: str) -> Path | None:
    for p in sorted((KIT / "gps" / "pista").glob("*alinhamento*.json")):
        d = ler_json(p, {}) or {}
        if str(d.get("fonte", "")).startswith(glb):
            return p
    return None


class Resolvedor:
    def __init__(self, pasta: Path, historia: dict):
        self.pasta = Path(pasta)
        self.afs = {a["id"]: a for a in historia.get("afirmacoes", [])}
        self.itens: dict[str, dict] = {}

    def _add(self, cena: str, item: dict) -> dict:
        ja = self.itens.get(item["id"])
        if ja:
            if cena not in ja["cenas"]:
                ja["cenas"].append(cena)
            return ja
        item = {"cena": cena, "cenas": [cena], **item}
        self.itens[item["id"]] = item
        return item

    # ------------------------------------------------------------ por kit
    def gps(self, cena: str, p: dict) -> None:
        s = p.get("sessao")
        for carro in p.get("carros") or []:
            pil, v = carro.get("piloto"), carro.get("volta")
            arq = _um(str(KIT / "gps" / "voltas" / f"{s}_{pil}_{_volta(v)}.json"))
            it = {"id": f"volta_gps:{s}:{pil}:{v}", "tipo": "volta_gps", "descricao": f"GPS da volta {v} do carro {pil} (sessão {s})"}
            if arq:
                d = ler_json(arq, {})
                self._add(cena, {**it, "status": "pronto", "arquivo": str(arq),
                                 "dados": {"sigla": d.get("sigla"), "volta": d.get("volta"), "duracao": d.get("duracao"),
                                           "pista": d.get("pista")}})
                glb = p.get("pista") or d.get("pista")
                if glb:
                    self.pista(cena, glb)
            else:
                self._add(cena, {**it, "status": "falta", "arquivo": None,
                                 "comando": f"cd F1/horizontal/kit/gps && {Path(PY).name} py/openf1.py {s} {pil} && "
                                            f"{Path(PY).name} py/preparar_volta.py {s} {pil} {v}"})

    def pista(self, cena: str, glb: str) -> None:
        modelo = dados_f1() / "modelos3d" / glb
        ali = _alinhamento(glb)
        ok = modelo.exists() and ali is not None
        ev = [f"modelo {'existe' if modelo.exists() else 'NÃO existe'}: {modelo}",
              f"alinhamento OpenF1→modelo: {ali or 'NÃO existe (kit/gps/py/alinhar.py com o .glb desta pista)'}"]
        self._add(cena, {"id": f"pista:{glb}", "tipo": "pista", "descricao": f"pista 3D {glb} alinhada ao GPS",
                         "status": "pronto" if ok else "falta", "arquivo": str(modelo) if modelo.exists() else None,
                         "evidencia": ev, **({} if ok else {"comando": f"cd F1/horizontal/kit/gps && {Path(PY).name} py/alinhar.py <sessao> <piloto> <volta>  (com {glb})"})})

    def graficos(self, cena: str, p: dict) -> None:
        s, a, b = p.get("sessao"), p.get("a") or {}, p.get("b") or {}
        nome = f"{s}_{a.get('piloto')}-{_volta(a.get('volta'))}_{b.get('piloto')}-{_volta(b.get('volta'))}.json"
        arq = _um(str(KIT / "graficos" / "comparacoes" / nome))
        it = {"id": f"comparacao:{s}:{a.get('piloto')}-{a.get('volta')}:{b.get('piloto')}-{b.get('volta')}", "tipo": "comparacao",
              "descricao": f"comparação {a.get('piloto')} v{a.get('volta')} × {b.get('piloto')} v{b.get('volta')} (sessão {s})"}
        if arq:
            d = ler_json(arq, {})
            pil = {str(x["numero"]): {"sigla": x.get("sigla"), "volta": x.get("volta"), "tempo": x.get("tempo"),
                                      "setores": x.get("setores")} for x in d.get("pilotos", [])}
            self._add(cena, {**it, "status": "pronto", "arquivo": str(arq),
                             "dados": {"sessao": d.get("sessao"), "sessao_nome": d.get("sessao_nome"), "circuito": d.get("circuito"),
                                       "ano": d.get("ano"), "pilotos": pil, "fonte": d.get("fonte_curta")}})
        else:
            self._add(cena, {**it, "status": "falta", "arquivo": None,
                             "comando": f"{Path(PY).name} F1/horizontal/kit/graficos/py/preparar.py {s} {a.get('piloto')} {a.get('volta')} "
                                        f"{b.get('piloto')} {b.get('volta')}"})

    def imagens(self, cena: str, p: dict, produzir: bool = False) -> None:
        af = self.afs.get(str(p.get("afirmacao")))
        if not af or not af.get("verificavel") or not af.get("carros"):
            self._add(cena, {"id": f"imagem:{p.get('afirmacao')}", "tipo": "imagem", "status": "reprovado", "arquivo": None,
                             "descricao": f"imagem sem afirmação verificável ({p.get('afirmacao')})",
                             "evidencia": ["kit/imagens só valida contra sessão/piloto/volta de uma afirmação verificável"]})
            return
        carro = af["carros"][0]
        pedido = {"sessao": af["sessao"], "piloto": carro["piloto"], "volta": carro["volta"]}
        evento = p.get("evento") or af.get("evento")
        if evento:
            pedido["evento"] = evento
        slug = f"s{pedido['sessao']}_c{pedido['piloto']}_v{pedido['volta']}" + (f"_{evento}" if evento else "")
        destino = self.pasta / "ativos" / "imagens"
        res = ler_json(destino / f"{slug}.json")
        if res is None and produzir and carro["volta"] != "melhor":
            sys.path.insert(0, str(KIT / "imagens"))
            from imagens import achar  # rede (OpenF1 + YouTube) e OCR; minutos na 1ª vez
            res = achar(pedido, destino=destino, fontes=p.get("fontes"))
        it = {"id": f"imagem:{slug}", "tipo": "imagem", "afirmacao": af["id"],
              "descricao": f"trecho real: carro {pedido['piloto']}, volta {pedido['volta']}, sessão {pedido['sessao']}"
                           + (f", evento {evento}" if evento else "")}
        if res is None:
            self._add(cena, {**it, "status": "falta", "arquivo": None,
                             "comando": f"kit/imagens achar({pedido}, destino='{destino}')"})
            return
        st = {"validado": "pronto"}.get(res.get("status"), res.get("status"))
        if st not in ("pronto", "nao_validado", "reprovado", "nao_encontrado"):
            st = "nao_validado"
        if st == "pronto" and not res.get("validado"):
            st = "nao_validado"
        self._add(cena, {**it, "status": st, "arquivo": res.get("arquivo"),
                         "evidencia": [str(x) for x in (res.get("evidencia") or [])][:12],
                         "dados": {"credito": res.get("credito"), "quadro": res.get("quadro")}})

    def sfx(self, cena: str, categoria: str) -> None:
        cats = categorias_sfx()
        for cat in (["riser", "impacto"] if categoria == "capitulo" else [categoria]):
            it = {"id": f"sfx:{cat}", "tipo": "sfx", "descricao": f"banco do kit/sfx, categoria {cat}"}
            if cat not in cats:
                self._add(cena, {**it, "status": "reprovado", "arquivo": None, "evidencia": [f"categoria '{cat}' não existe no catálogo"]})
                continue
            banco = _acima(f"F1/horizontal/kit/sfx/banco/{cat}")
            wavs = sorted(banco.glob("*.wav")) if banco else []
            if wavs:
                self._add(cena, {**it, "status": "pronto", "arquivo": str(banco), "dados": {"variacoes": len(wavs)}})
            else:
                self._add(cena, {**it, "status": "falta", "arquivo": None,
                                 "comando": f"{Path(PY).name} F1/horizontal/kit/sfx/gerar.py  (banco fica fora do Git)"})

    def arquivo(self, cena: str, tipo: str, caminho: str, descricao: str) -> None:
        cands = [Path(caminho), self.pasta / "ativos" / caminho, dados_f1() / "modelos3d" / caminho]
        achado = next((c for c in cands if c.is_absolute() and c.exists() or c.exists()), None)
        self._add(cena, {"id": f"{tipo}:{caminho}", "tipo": tipo, "descricao": descricao,
                         "status": "pronto" if achado else "falta", "arquivo": str(achado) if achado else None,
                         **({} if achado else {"comando": f"pôr o arquivo em F1/dados/modelos3d/ ou em <projeto>/ativos/: {caminho}"})})


def resolver(spec: dict, historia: dict, pasta: Path, produzir: bool = False) -> dict:
    r = Resolvedor(pasta, historia)
    for c in spec["cenas"]:
        for uso in c["kits"]:
            k, p = uso.get("kit"), uso.get("params") or {}
            if k == "gps":
                r.gps(c["id"], p)
            elif k == "graficos":
                r.graficos(c["id"], p)
            elif k == "imagens":
                r.imagens(c["id"], p, produzir)
            elif k == "modelo3d":
                r.arquivo(c["id"], "modelo3d", str(p.get("arquivo")), f"modelo 3D {p.get('arquivo')}")
            elif k == "cartoes" and p.get("foto"):
                r.arquivo(c["id"], "imagem", str(p["foto"]), f"foto do cartão {p.get('nome', '')}".strip())
        for s in c["sfx"]:
            r.sfx(c["id"], s["categoria"])
        if c["transicao"]["tipo"] in ("wipe", "zoom"):
            r.sfx(c["id"], "whoosh")   # SFX padrão do kit/transicoes
    itens = list(r.itens.values())
    resumo = {k: sum(1 for i in itens if i["status"] == k) for k in ("pronto", "falta", "nao_validado", "reprovado", "nao_encontrado")}
    return {"versao": 1, "spec_hash": hash_dados(spec), "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "resumo": resumo, "itens": itens}


def produzir_faltas(ativos: dict) -> list[str]:
    """Roda os comandos de shell dos itens que faltam (OpenF1/preparar). Imagens são produzidas em `resolver(produzir=True)`."""
    log = []
    raiz = KIT.parents[2]
    for it in ativos["itens"]:
        cmd = it.get("comando")
        if it["status"] == "falta" and cmd and not cmd.startswith("kit/") and "<" not in cmd and "pôr o arquivo" not in cmd:
            cmd = cmd.replace(Path(PY).name, f'"{PY}"', 2)
            r = subprocess.run(cmd, shell=True, cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace")
            log.append(f"{it['id']}: {'ok' if r.returncode == 0 else 'falhou ' + r.stderr.strip()[-300:]}")
    return log


def aplicar(pasta: Path, produzir: bool = False) -> dict:
    pasta = Path(pasta)
    spec, historia = ler_json(pasta / "spec.json"), ler_json(pasta / "historia.json")
    a = resolver(spec, historia, pasta, produzir)
    if produzir and a["resumo"]["falta"]:
        for linha in produzir_faltas(a):
            print(" ", linha)
        a = resolver(spec, historia, pasta, produzir)
    res = a["resumo"]
    etapas.registrar(pasta, "ativos", a, base=spec, resumo=", ".join(f"{v} {k}" for k, v in res.items() if v))
    return a


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    a = aplicar(Path(sys.argv[1]), "--produzir" in sys.argv)
    print(a["resumo"])
    for it in a["itens"]:
        if it["status"] != "pronto":
            print(f"  {it['status']:15} {it['id']}  {it.get('comando', '')}")
