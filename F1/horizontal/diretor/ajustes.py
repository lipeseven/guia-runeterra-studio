"""Ações diretas do storyboard (fase 7b): mudanças que o Felipe faz na cena e entram NA HORA na SPEC, sem modelo.

Na linha do storyboard do Runeterra (movimento, entrada, "a cena começa em", som), mas gravadas direto no `spec.json`
pelo `etapas.ajustar` (a SPEC continua aprovada: quem mexeu foi o Felipe). Qualquer outro pedido (texto ou voz) NÃO
passa por aqui: vira pedido da cena para o orquestrador (`painel.pedido_cena`).

Ações (`{"acao": ..., ...}`):
- `movimento` {tipo: parado|aproximar|afastar|pan_esq|pan_dir|subir|descer, intensidade?: 0.01–0.3, foco?: [x, y] 0–1}
  câmera da cena inteira (`montador/movimento.js`, igual nos dois motores);
- `transicao` {tipo: corte|fade|wipe|zoom, quadros?}: entrada da cena (kit/transicoes; quadros padrão de `comum.TRANSICOES`);
- `corte` {indice}: a cena começa na palavra `indice` (move o corte com a anterior; a anterior encolhe/cresce);
- `fim` {indice}: a cena termina antes da palavra `indice` (= `corte` da próxima);
- `sfx` {j?, categoria?, indice?, ponto?, intensidade?, remover?}: troca/move/remove o SFX `j` da cena, ou cria um novo
  (sem `j`: precisa de categoria e indice dentro da cena);
- `kit` {kit, param, valor}: parâmetro de kit que o kit já expõe como escolha fechada (`PARAMS_DIRETOS`).
"""
from __future__ import annotations

import copy
import hashlib

from comum import TRANSICOES, categorias_sfx
from esquema import validar

MOVIMENTOS = ("parado", "aproximar", "afastar", "pan_esq", "pan_dir", "subir", "descer")   # = montador/movimento.js
SFX_CATEGORIAS = ("impacto", "riser", "whoosh", "sino", "alerta", "pop", "clique", "tecla", "capitulo")
PARAMS_DIRETOS = {"gps": {"camera_gps": ("perseguicao", "fixa", "alta")}, "graficos": {"minimapa": (True, False)}}
ACOES = ("movimento", "transicao", "corte", "fim", "sfx", "kit")
ANCORA_PALAVRAS = 3   # `em` gravado = 3 palavras a partir do índice (literal do roteiro, menos ambíguo que 1 palavra)


def _em(palavras: list[dict], i: int) -> str:
    return " ".join(p["t"] for p in palavras[i:i + ANCORA_PALAVRAS])


def _novo_id(em: str, usados: set) -> str:
    """Mesma regra de `spec._id` (id = hash do trecho-âncora)."""
    pid = hashlib.sha1(em.encode()).hexdigest()[:8]
    while pid in usados:
        pid = hashlib.sha1(pid.encode()).hexdigest()[:8]
    return pid


def _mover_corte(s: dict, k: int, i: int, palavras: list[dict]) -> str:
    import spec as S   # noqa: PLC0415 (spec importa etapas; aqui só a regra dos tempos)

    cenas = s["cenas"]
    if k == 0:
        raise ValueError("a 1ª cena sempre começa na 1ª palavra")
    ant, c = cenas[k - 1], cenas[k]
    if not ant["i0"] < i < c["i1"]:
        raise ValueError(f"o corte precisa ficar entre a palavra {ant['i0'] + 1} e a {c['i1'] - 1} "
                         "(cada cena com pelo menos uma palavra)")
    velho = c["i0"]
    c["i0"] = i
    c["em"] = _em(palavras, i)
    c["id"] = _novo_id(c["em"], {x["id"] for x in cenas if x is not c})
    S.tempos_das_cenas(cenas, palavras)
    return f"cena começa em “{c['em']}” (antes na palavra {velho}, agora {i})"


def aplicar(spec: dict, cid: str, acao: dict, palavras: list[dict]) -> tuple[dict, str, str]:
    """(spec nova, descrição, id da cena depois da ação). Não grava nada. ValueError = ação recusada (mensagem clara)."""
    s = copy.deepcopy(spec)
    k = next((n for n, c in enumerate(s["cenas"]) if c["id"] == cid), None)
    if k is None:
        raise ValueError(f"cena {cid} não existe na SPEC (recarregue o storyboard)")
    c = s["cenas"][k]
    tipo = acao.get("acao")
    if tipo == "movimento":
        mv = acao.get("tipo")
        if mv not in MOVIMENTOS:
            raise ValueError(f"movimento inválido: {mv} (há: {', '.join(MOVIMENTOS)})")
        if mv == "parado":
            c.pop("movimento", None)
            desc = "sem movimento de câmera"
        else:
            m = {"tipo": mv}
            if acao.get("intensidade") is not None:
                m["intensidade"] = round(min(0.3, max(0.01, float(acao["intensidade"]))), 3)
            if acao.get("foco") is not None:
                fx, fy = acao["foco"]
                m["foco"] = [round(min(1, max(0, float(fx))), 3), round(min(1, max(0, float(fy))), 3)]
            c["movimento"] = m
            desc = f"movimento {mv}" + (f" ({m['intensidade']:.0%})" if "intensidade" in m else "")
    elif tipo == "transicao":
        tt = acao.get("tipo")
        if tt not in TRANSICOES:
            raise ValueError(f"transição inválida: {tt} (há: {', '.join(TRANSICOES)})")
        if k == 0 and tt != "corte":
            raise ValueError("a 1ª cena não tem transição de entrada")
        q = int(acao.get("quadros", TRANSICOES[tt])) if tt != "corte" else 0
        if tt != "corte" and not 6 <= q <= 60:
            raise ValueError("a transição precisa de 6 a 60 quadros")
        c["transicao"] = {"tipo": tt, "quadros": q}
        desc = f"entrada {tt}" + (f" {q} q" if q else "")
    elif tipo == "corte":
        desc = _mover_corte(s, k, int(acao["indice"]), palavras)
    elif tipo == "fim":
        if k + 1 >= len(s["cenas"]):
            raise ValueError("a última cena termina no fim da narração")
        desc = "fim da cena: " + _mover_corte(s, k + 1, int(acao["indice"]), palavras).replace("cena começa", "a próxima começa")
    elif tipo == "sfx":
        lista = c["sfx"]
        j = acao.get("j")
        if j is not None and not 0 <= int(j) < len(lista):
            raise ValueError(f"a cena não tem o SFX {j}")
        if acao.get("remover"):
            if j is None:
                raise ValueError("diga qual SFX remover")
            fora = lista.pop(int(j))
            desc = f"SFX {fora['categoria']} removido"
        else:
            e = dict(lista[int(j)]) if j is not None else {}
            if acao.get("categoria") is not None:
                cats = set(SFX_CATEGORIAS) | set(categorias_sfx())
                if acao["categoria"] not in cats:
                    raise ValueError(f"categoria de SFX inválida: {acao['categoria']}")
                e["categoria"] = acao["categoria"]
            if acao.get("indice") is not None:
                i = int(acao["indice"])
                if not c["i0"] <= i < c["i1"]:
                    raise ValueError("o SFX precisa cair numa palavra desta cena")
                e["i"], e["em"] = i, _em(palavras, i)
            if acao.get("ponto") is not None:
                if acao["ponto"] not in ("i", "f"):
                    raise ValueError("ponto do SFX: i (início da palavra) ou f (fim)")
                e["ponto"] = acao["ponto"]
            if acao.get("intensidade") is not None:
                e["intensidade"] = round(min(1.0, max(0.0, float(acao["intensidade"]))), 2)
            if "categoria" not in e or "i" not in e:
                raise ValueError("SFX novo precisa de categoria e da palavra (indice)")
            if j is None:
                lista.append(e)
            else:
                lista[int(j)] = e
            lista.sort(key=lambda x: x["i"])
            desc = f"SFX {e['categoria']} em “{e['em']}”" + (" (novo)" if j is None else "")
    elif tipo == "kit":
        kit, param, valor = acao.get("kit"), acao.get("param"), acao.get("valor")
        permitido = PARAMS_DIRETOS.get(kit, {}).get(param)
        if permitido is None:
            raise ValueError(f"{kit}.{param} não é ação direta (peça ao orquestrador)")
        if valor not in permitido:
            raise ValueError(f"{kit}.{param}: valor {valor!r} fora de {list(permitido)}")
        usos = [u for u in c["kits"] if u["kit"] == kit]
        if not usos:
            raise ValueError(f"a cena não usa o kit {kit}")
        for u in usos:
            u["params"][param] = valor
        desc = f"{kit}: {param} = {valor}"
    else:
        raise ValueError(f"ação direta desconhecida: {tipo} (há: {', '.join(ACOES)}; o resto vira pedido ao orquestrador)")
    erros = validar(s, "spec")
    if erros:
        raise ValueError("a ação deixaria a SPEC inválida: " + "; ".join(erros[:5]))
    return s, desc, c["id"]
