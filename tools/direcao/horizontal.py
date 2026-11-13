"""Diretor do vídeo horizontal animado (Explicando F1: `[horizontal]` no canal.toml).

O Claude escolhe as cenas da biblioteca do horizontal (F1/video/src/horizontal: estúdio, pista, pessoa, capítulo,
palavra solta) com parâmetros em JSON, citando TRECHOS do roteiro; a validação converte cada trecho no índice da palavra
(direção presa à palavra) e, no render, em segundos da voz. O roteiro é dirigido por blocos (parágrafos somando até
~220 palavras), cada um com cache pelo conteúdo: mudar um parágrafo só manda aquele bloco de novo ao Claude.
Resultado em direcao/vertical.json do vídeo (mesmo arquivo do vertical: o painel "Animação" e o motor servem aos dois).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import time
from pathlib import Path

from canal import CANAL, RAIZ, caminho
from claude_cli import chamar_json
import vertical
from vertical import _briefing, frases, localizar

CFG = CANAL.get("horizontal", {})
FPS = int(CFG.get("fps", 30))  # quadros por segundo do horizontal (igual ao Root.tsx); o vertical tem o seu
MODELO = CFG.get("modelo", "sonnet")
TIPOS = {"estudio", "pista", "pessoa", "capitulo", "solta"}
MODOS = {"claro", "cheio", "escuro", "tecnico"}
CAM_ESTUDIO = {"orbita", "aproximar", "deslizar", "chegada", "frente", "traseira", "perfil", "cima", "baixo", "detalhe", "passagem",
               "atravessar"}
CAM_PISTA = {"helicoptero", "drone", "lado", "passagem", "pov"}
ENTRADAS = {"corte", "empurrar", "glitch", "cortina", "cor"}
ANOTACOES = {"seta", "circulo", "sublinhado", "riscado", "chave", "nota", "corrigido", "caixa", "x", "check", "marca"}
ATRASO_PALAVRA = 0.25  # a palavra gigante entra logo depois de falada (0–1 s nas referências)
PALAVRAS_POR_BLOCO = 220


def _doc(nome: str) -> str:
    p = caminho("docs") / nome
    return p.read_text(encoding="utf-8") if p.exists() else ""


def sistema() -> str:
    return (f"Você é o diretor dos vídeos horizontais (16:9, longos) do canal \"{CANAL['nome']}\" ({CANAL['assunto']}). "
            "Monte cada trecho com as cenas da biblioteca, no estilo da folha do horizontal: palavra-chave gigante atrás "
            "do carro, anotações à mão que comentam a fala, respiros na pista, ritmo que alterna blocos densos e respiros. "
            "A tela muda a cada 2–3 s nos blocos de análise. Números só os que a fala diz. Nunca invente citação de pessoa "
            "real. Responda SOMENTE JSON.")


def _docs() -> str:
    return (f"# Folha de estilo do horizontal\n{_doc('folha_horizontal.md')}\n\n{_doc(CFG.get('api', 'api_horizontal.md'))}\n\n")


# ------------------------------------------------------------------------------------------------ blocos do roteiro
def blocos_do_roteiro(palavras: list[dict]) -> list[tuple[int, int]]:
    """(primeira, última+1) palavra de cada bloco: parágrafos inteiros, até ~220 palavras por bloco.
    Parágrafo = frase que termina e a seguinte começa depois de uma pausa longa ou de linha em branco no roteiro."""
    cortes = [k + 1 for k, p in enumerate(palavras[:-1]) if p.get("paragrafo")]
    if not cortes:  # sem marca de parágrafo: corta em frases a cada ~220 palavras
        cortes = [k + 1 for k, p in enumerate(palavras[:-1]) if re.search(r"[.!?]$", p["t"])]
    saida, ini, ultimo = [], 0, 0
    for c in cortes + [len(palavras)]:
        if c - ini >= PALAVRAS_POR_BLOCO and ultimo > ini:
            saida.append((ini, ultimo))
            ini = ultimo
        ultimo = c
    saida.append((ini, len(palavras)))
    return [b for b in saida if b[1] > b[0]]


def marcar_paragrafos(roteiro: str, palavras: list[dict]) -> list[dict]:
    """Marca a última palavra de cada parágrafo do roteiro (linha em branco) na tabela de tempos."""
    fins, n = set(), 0
    for par in re.split(r"\n\s*\n", roteiro.strip()):
        n += len(par.split())
        fins.add(n - 1)
    return [{**p, "paragrafo": k in fins} for k, p in enumerate(palavras)]


# ------------------------------------------------------------------------------------------------ validação
def _num(v, padrao: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return padrao


def _ponto(v, padrao: list[float]) -> list[float]:
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return [_num(v[0], padrao[0], 0, 1920), _num(v[1], padrao[1], 0, 1080)]
    return padrao


def resolver(brutos: list[dict], palavras: list[dict], inicio: int = 0, fim: int | None = None, ids: set[str] | None = None,
             primeiro: bool = False) -> tuple[list[dict], list[str]]:
    """Trechos → índices de palavra (sub-itens guardam o índice em `i`); parâmetros conferidos. Cena com trecho que não
    existe no roteiro sai (vira aviso)."""
    fim = len(palavras) if fim is None else fim
    planos, avisos, ult, ids = [], [], inicio - 1, ids if ids is not None else set()
    for n, b in enumerate(brutos):
        if not isinstance(b, dict) or b.get("tipo") not in TIPOS:
            avisos.append(f"cena {n + 1}: tipo desconhecido ({b.get('tipo') if isinstance(b, dict) else b}), ignorada")
            continue
        i = inicio if primeiro and not planos else localizar(palavras[:fim], b.get("em"), ult + 1)
        if i is None:
            avisos.append(f"cena {n + 1}: trecho não encontrado no roteiro: \"{b.get('em')}\"")
            continue
        ult = i
        p = {k: v for k, v in b.items() if k not in ("id", "i")}
        p["em"] = b.get("em") or " ".join(w["t"] for w in palavras[i:i + 4])
        p["i"] = i
        pid = b.get("id") if isinstance(b.get("id"), str) and b["id"] not in ids else hashlib.sha1(f"{p['tipo']}|{p['em']}|{i}".encode()).hexdigest()[:8]
        while pid in ids:
            pid = hashlib.sha1(pid.encode()).hexdigest()[:8]
        ids.add(pid)
        p["id"] = pid
        e = p.get("entrada") if isinstance(p.get("entrada"), dict) else {"tipo": "corte"}
        if e.get("tipo") not in ENTRADAS:
            e = {"tipo": "corte"}
        p["entrada"] = e
        if p["tipo"] == "estudio":
            p["modo"] = p.get("modo") if p.get("modo") in MODOS else "claro"
            cam = p.get("camera") if isinstance(p.get("camera"), dict) else {}
            p["camera"] = {**cam, "tipo": cam.get("tipo") if cam.get("tipo") in CAM_ESTUDIO else "orbita"}
        if p["tipo"] == "pista":
            cam = p.get("camera") if isinstance(p.get("camera"), dict) else {}
            p["camera"] = {**cam, "tipo": cam.get("tipo") if cam.get("tipo") in CAM_PISTA else "helicoptero"}
            carros = [c for c in p.get("carros") or [] if isinstance(c, dict)][:4] or [{"u0": 0.2, "km": 260}]
            p["carros"] = [{**c, "u0": _num(c.get("u0"), 0.2, 0, 1), "km": _num(c.get("km"), 260, 60, 340)} for c in carros]
        # sub-itens presos a palavras do trecho
        def preso(item: dict, campo: str = "em") -> None:
            j = localizar(palavras[:fim], item.get(campo), i)
            item[f"{campo}_i"] = j if j is not None else i
        if isinstance(p.get("palavra"), dict) and p["palavra"].get("texto"):
            preso(p["palavra"])
            if p["palavra"].get("ate"):
                preso(p["palavra"], "ate")
                if p["palavra"]["ate_i"] <= p["palavra"]["em_i"] + 2:  # sair logo depois de entrar não dá tempo de ler
                    p["palavra"].pop("ate"), p["palavra"].pop("ate_i")
        else:
            p.pop("palavra", None)
        p["anotacoes"] = [a for a in p.get("anotacoes") or [] if isinstance(a, dict) and a.get("tipo") in ANOTACOES][:4]
        for a in p["anotacoes"]:
            preso(a)
            for c in ("de", "para", "centro"):
                if c in a:
                    a[c] = _ponto(a[c], [960, 540])
        if not p["anotacoes"]:
            p.pop("anotacoes")
        if isinstance(p.get("contador"), dict) and _num(p["contador"].get("valor"), 0, -1e9, 1e9) > 0:
            preso(p["contador"])
        else:
            p.pop("contador", None)
        p["rotulos"] = [r for r in p.get("rotulos") or [] if isinstance(r, dict) and r.get("texto")][:3]
        for r in p["rotulos"]:
            preso(r)
            r["de"], r["para"] = _ponto(r.get("de"), [960, 600]), _ponto(r.get("para"), [1200, 450])
        if not p["rotulos"]:
            p.pop("rotulos")
        if p["tipo"] == "pessoa":
            preso(p)
            cit = p.get("citacao")
            k = localizar(palavras[:fim], cit, i) if cit else None
            p["citacao_i"] = k  # citação falada: cada palavra aparece junto da voz
        if isinstance(p.get("som"), dict) and p["som"].get("o_que"):
            j = localizar(palavras[:fim], p["som"].get("em"), i)
            p["som"]["i"] = j if j is not None else i
        else:
            p.pop("som", None)
        planos.append(p)
    return planos, avisos


# ------------------------------------------------------------------------------------------------ editor de variedade
# O diretor tende a repetir (mesma câmera 3/4, mesma entrada de palavra, nota no mesmo canto): aqui a variedade é imposta,
# como o Variador do Runeterra. Sorteio pelo id da cena (mexer numa cena não muda as outras); escolha explícita do
# diretor fica, a não ser que repita as cenas anteriores.
CAM_POOL = ["orbita", "aproximar", "deslizar", "frente", "traseira", "perfil", "cima", "baixo", "detalhe", "atravessar"]
PECA_CAM = {"detalhe", "frente", "traseira", "perfil"}  # câmeras que mostram uma parte do carro
ANGULOS = [-145, -60, -38, -18, 18, 38, 60, 145, 200]
DETALHES = ["asa_dianteira", "roda_dianteira", "cockpit", "asa_traseira", "roda_traseira"]
# de onde a câmera olha cada peça (graus; o sinal escolhe o lado): fora disso outra peça fica na frente
ANGULO_DETALHE = {"asa_dianteira": (12, 45), "roda_dianteira": (55, 85), "cockpit": (60, 100), "asa_traseira": (140, 165),
                  "roda_traseira": (100, 130)}
ENTRADAS_PALAVRA = {"decodificar": 3, "subir": 2, "impacto": 2, "deslizar": 2, "letras": 1, "digitar": 1, "seco": 1}
# cantos livres para a nota, conforme o lado em que o carro está na tela
ZONAS = {"centro": [(1330, 200), (120, 830), (1330, 830), (120, 210)],
         "esquerda": [(1280, 330), (1300, 780), (1330, 200)],
         "direita": [(120, 330), (120, 780), (120, 200)]}
FONTES = ["ink", "print", "script"]


def _sorteio_pesado(r, opcoes: dict[str, int], fora: set[str]) -> str:
    itens = [(k, v) for k, v in opcoes.items() if k not in fora] or list(opcoes.items())
    return r.choices([k for k, _ in itens], [v for _, v in itens])[0]


def variar(planos: list[dict]) -> list[dict]:
    import random

    cams: list[tuple[str, float]] = []  # (tipo e peça, ângulo)
    entradas: list[str] = []
    zona_ant, nota_ant, chegada_ant = None, -9, -99
    for n, p in enumerate(planos):
        r = random.Random(p["id"])
        if p["tipo"] == "estudio":
            cam = p["camera"]
            # o carro entrando andando cansa: no máximo uma a cada ~8 cenas, e só abrindo bloco
            if cam["tipo"] == "chegada":
                abre = n == 0 or planos[n - 1].get("bloco") != p.get("bloco")
                if not abre or n - chegada_ant < 8:
                    cam["tipo"] = r.choice([t for t in CAM_POOL if t not in {x for x, _ in cams[-2:]} and t != "detalhe"])
                else:
                    chegada_ant = n
            chave = lambda cm: cm["tipo"] + (":" + cm.get("alvo", "") if cm["tipo"] == "detalhe" else "")  # noqa: E731
            if cam["tipo"] not in ("chegada", "passagem"):
                recentes = {t for t, _ in cams[-2:]}
                # close de outra peça não é repetição; câmera escolhida pelo diretor só troca se repetir
                if chave(cam) in recentes or (cam["tipo"] == "orbita" and r.random() < 0.5):
                    cam["tipo"] = r.choice([t for t in CAM_POOL if t not in recentes and t != "detalhe"])
                perto = lambda a: any(abs(a - b) < 25 for _, b in cams[-2:])  # noqa: E731
                if "de" not in cam or perto(_num(cam["de"], 39, -360, 360)):
                    cam["de"] = r.choice([a for a in ANGULOS if not perto(a)] or ANGULOS)
                cam.setdefault("sentido", r.choice([1, -1]))
                cam.setdefault("enquadre", r.choices(["centro", "esquerda", "direita"], [2, 1, 1])[0])
                if cam["tipo"] == "detalhe":
                    if cam.get("alvo") not in DETALHES:
                        cam["alvo"] = r.choice(DETALHES)
                    lo, hi = ANGULO_DETALHE[cam["alvo"]]
                    if not lo <= abs(_num(cam.get("de"), 0, -360, 360)) <= hi:
                        cam["de"] = r.choice([1, -1]) * r.randint(lo, hi)
                else:
                    cam.pop("alvo", None)
            cams.append((chave(cam), _num(cam.get("de"), 39, -360, 360)))
            # falando de uma parte e depois de outra: o carro não troca de plano, a câmera gira até a parte citada
            ant = planos[n - 1] if n else None
            if (ant and ant["tipo"] == "estudio" and ant.get("modo") == p.get("modo") and cam["tipo"] in PECA_CAM
                    and ant["camera"]["tipo"] in PECA_CAM | {"orbita", "aproximar"}):
                p["continuar"] = True
                p["entrada"] = {"tipo": "corte"}
            else:
                p.pop("continuar", None)
        w = p.get("palavra")
        if w:
            fora = set(entradas[-1:])
            if entradas[-3:].count("decodificar") >= 1:  # a assinatura aparece, mas não em sequência
                fora.add("decodificar")
            if w.get("entrada") not in ENTRADAS_PALAVRA or w["entrada"] in fora:
                w["entrada"] = _sorteio_pesado(r, ENTRADAS_PALAVRA, fora)
            w.setdefault("contorno", r.random() < 0.15)
            entradas.append(w["entrada"])
        notas = [a for a in p.get("anotacoes") or [] if a["tipo"] in ("nota", "corrigido")]
        if notas and n - nota_ant < 2 and r.random() < 0.6:  # nota em cenas seguidas cansa: uma sai
            p["anotacoes"] = [a for a in p["anotacoes"] if a not in notas]
            notas = []
        if notas:
            enq = (p.get("camera") or {}).get("enquadre", "centro")
            opcoes = [z for z in ZONAS.get(enq, ZONAS["centro"]) if z != zona_ant] or ZONAS["centro"]
            zona = r.choice(opcoes)
            estilo = {"fonte": r.choice(FONTES), "traco": r.choice([5, 7, 9]), "marca": r.random() < 0.2}
            for k, a in enumerate(notas):
                a["x"], a["y"] = zona[0] + r.randint(-50, 50), zona[1] + r.randint(-40, 40) + k * 90
                a["giro"] = round(r.uniform(-8, 5), 1)
                a["tam"] = r.choice([46, 54, 62])
                a["estilo"] = estilo
            for a in p["anotacoes"]:
                if a["tipo"] == "seta":  # a seta sai da nota
                    a["de"] = [notas[0]["x"] + (60 if zona[0] < 960 else -10), notas[0]["y"] + 70]
                    a.setdefault("estilo", estilo)
            zona_ant, nota_ant = zona, n
        if not p.get("anotacoes"):
            p.pop("anotacoes", None)
    return planos


# ------------------------------------------------------------------------------------------------ direção
FORMATO = ("Responda SOMENTE com JSON {\"cenas\": [{\"em\": \"trecho exato onde a cena começa\", \"tipo\", \"entrada\"?, "
           "parâmetros do tipo, \"palavra\"?, \"anotacoes\"?, \"contador\"?, \"rotulos\"?, \"som\"?}]}.")


def _pedir_bloco(texto: str, palavras: list[dict], ini: int, fim: int, briefing: str, contexto: str, etiqueta: str) -> dict:
    trecho = palavras[ini:fim]
    prompt = (_docs() + _briefing(briefing) + contexto
              + f"TRECHO A DIRIGIR (com o tempo de cada frase na voz; {trecho[-1]['f'] - trecho[0]['i']:.0f} s):\n{frases(trecho)}\n\n"
              + "Monte este trecho cena por cena (a 1ª cena começa na 1ª palavra do trecho). " + FORMATO)
    r = chamar_json(prompt, sistema(), modelo=MODELO, etiqueta=etiqueta)
    return r if isinstance(r, dict) else {"cenas": r}


def dirigir(roteiro: str, palavras: list[dict], briefing: str = "", trabalho: Path | None = None, aviso=lambda m: None,
            anterior: dict | None = None) -> dict:
    """Roteiro inteiro, bloco a bloco. Bloco com o mesmo texto (e mesma folha/API/briefing) reaproveita o cache."""
    palavras = marcar_paragrafos(roteiro, palavras)
    pasta = (trabalho.parent / "direcao" / "horizontal_blocos") if trabalho else None
    if pasta:
        pasta.mkdir(parents=True, exist_ok=True)
    versao = hashlib.sha1((_docs() + sistema() + briefing + MODELO).encode()).hexdigest()[:8]
    lista = blocos_do_roteiro(palavras)
    planos, avisos, ids = [], [], set()
    for k, (ini, fim) in enumerate(lista):
        texto = " ".join(w["t"] for w in palavras[ini:fim])
        chave = hashlib.sha1(f"{versao}|{texto}".encode()).hexdigest()[:16]
        arq = pasta / f"{chave}.json" if pasta else None
        if arq and arq.exists():
            r = json.loads(arq.read_text(encoding="utf-8"))
        else:
            aviso(f"o diretor monta o bloco {k + 1} de {len(lista)}")
            ctx = ""
            if planos:
                ult = [{c: q.get(c) for c in ("tipo", "modo", "camera") if q.get(c)} for q in planos[-4:]]
                ctx = f"CENAS QUE VÊM ANTES (varie a partir delas):\n{json.dumps(ult, ensure_ascii=False)}\n\n"
            if k == 0:
                ctx += "Este é o COMEÇO do vídeo: abre direto no gancho, com movimento desde o primeiro quadro.\n\n"
            r = _pedir_bloco(texto, palavras, ini, fim, briefing, ctx, f"horizontal-bloco{k + 1}")
            if arq:
                arq.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        novos, av = resolver(r.get("cenas") or [], palavras, ini, fim, ids, primeiro=True)
        for p in novos:
            p["bloco"] = k
        planos += novos
        avisos += [f"bloco {k + 1}: {a}" for a in av]
    if not planos:
        raise RuntimeError("o diretor não devolveu nenhuma cena válida")
    planos[0]["i"] = 0
    variar(planos)
    pendentes = _fotos(planos, trabalho, roteiro)
    return {"formato": "horizontal", "planos": planos, "fotos_pendentes": pendentes, "avisos": avisos, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _fotos(planos: list[dict], trabalho: Path | None, contexto: str) -> list[str]:
    """Pessoas dos cartões: candidatas de foto livre (Commons) para o Felipe aprovar; sem aprovação = silhueta."""
    if trabalho is None:
        return []
    import fotos

    nomes = [p["nome"] for p in planos if p["tipo"] == "pessoa" and p.get("nome") and not p.get("foto")]
    return fotos.preparar(trabalho.parent, nomes, f"{CANAL['nome']} {contexto[:400]}") if nomes else []


def para_o_claude(p: dict) -> dict:
    """Cena como o Claude escreve (trechos, sem índices)."""
    def limpo(x):
        if isinstance(x, dict):
            return {k: limpo(v) for k, v in x.items() if not k.endswith("_i") and k not in ("i", "bloco")}
        if isinstance(x, list):
            return [limpo(v) for v in x]
        return x
    return {**limpo(p), "id": p["id"]}


def revisar(direcao: dict, pedidos: list[dict], palavras: list[dict], briefing: str = "", trabalho: Path | None = None,
            aviso=lambda m: None) -> dict:
    """Pedidos do Felipe: só as cenas pedidas (e as vizinhas, como contexto) vão ao Claude; só as que mudam voltam."""
    planos = direcao["planos"]
    ids = [p["id"] for p in planos]
    numero = {pid: n + 1 for n, pid in enumerate(ids)}
    alvo = {p["plano"] for p in pedidos if p.get("plano") in numero}
    geral = any(p.get("plano") not in numero for p in pedidos)
    perto = set()
    for pid in alvo:
        n = numero[pid] - 1
        perto |= set(ids[max(0, n - 2):n + 3])
    mostrar = [para_o_claude(p) if geral or p["id"] in perto else {"id": p["id"], "em": p["em"], "tipo": p["tipo"]} for p in planos]
    linhas = [f"- cena {numero[p['plano']]} (id {p['plano']}): {p['texto']}" if p.get("plano") in numero else f"- geral: {p['texto']}"
              for p in pedidos]
    prompt = (_docs() + _briefing(briefing) + f"ROTEIRO:\n{frases(palavras)}\n\nDIREÇÃO ATUAL (na ordem):\n"
              + json.dumps(mostrar, ensure_ascii=False) + f"\n\nPEDIDOS DO FELIPE:\n{chr(10).join(linhas)}\n\n"
              "Aplique os pedidos. Devolva SÓ as cenas que mudam, completas, com o mesmo id. Cena nova (dividir uma cena) vem "
              "sem id, com \"depois_de\": id da cena antes dela. Cena que sai: id em \"remover\". Pedido que não se resolve "
              "com cena (voz, texto falado) não muda nada: explique em \"nao_da\". Responda SOMENTE JSON "
              "{\"cenas\": [...], \"remover\": [ids], \"nao_da\": []}.")
    aviso("o diretor aplica os seus pedidos")
    r = chamar_json(prompt, sistema(), modelo=MODELO, etiqueta="horizontal-revisao")
    r = r if isinstance(r, dict) else {"cenas": r}
    novos = [c for c in r.get("cenas") or [] if isinstance(c, dict)]
    remover = set(r.get("remover") or [])
    por_id = {c["id"]: c for c in novos if c.get("id") in numero}
    depois: dict[str, list[dict]] = {}
    for c in novos:
        if c.get("id") not in numero:
            depois.setdefault(c.get("depois_de") if c.get("depois_de") in numero else ids[-1], []).append(
                {k: v for k, v in c.items() if k not in ("id", "depois_de")})
    brutos = []
    for p in planos:
        if p["id"] in remover:
            continue
        c = por_id.get(p["id"])
        brutos.append({**c, "id": p["id"], "em": c.get("em") or p["em"], "tipo": c.get("tipo") or p["tipo"]} if c else para_o_claude(p))
        brutos += depois.get(p["id"], [])
    novos_planos, avisos = resolver(brutos, palavras, primeiro=True)
    variar(novos_planos)
    direcao = {**direcao, "fotos_pendentes": _fotos(novos_planos, trabalho, "")}
    blocos_antes = {p["id"]: p.get("bloco", 0) for p in planos}
    b = 0
    for p in novos_planos:
        b = blocos_antes.get(p["id"], b)
        p["bloco"] = b
    antes = {p["id"]: json.dumps(p, sort_keys=True, ensure_ascii=False) for p in planos}
    mudou = {p["id"] for p in novos_planos if antes.get(p["id"]) != json.dumps(p, sort_keys=True, ensure_ascii=False)}
    mudou |= set(antes) - {p["id"] for p in novos_planos}
    if trabalho is not None:
        pasta = trabalho.parent / "direcao" / "revisoes"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps({"pedidos": pedidos, "resposta": r, "mudou": sorted(mudou)}, ensure_ascii=False, indent=1), encoding="utf-8")
    if not mudou:
        motivo = "; ".join(str(x) for x in r.get("nao_da") or [] if x)
        return {**direcao, "sem_mudanca": motivo or "o diretor não mudou nenhuma cena"}
    aviso(f"o diretor mudou {len(mudou)} cena(s)")
    return {**direcao, "planos": novos_planos, "avisos": avisos, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}


# ------------------------------------------------------------------------------------------------ render
def _total(palavras: list[dict]) -> float:
    return math.ceil((palavras[-1]["f"] + 0.35) * FPS) / FPS


def props(direcao: dict, palavras: list[dict]) -> dict:
    """Plano (índices de palavra) → props da composição Horizontal (segundos; cada tempo relativo ao começo da cena)."""
    planos = direcao["planos"]
    inicio = [0.0] + [palavras[p["i"]]["i"] for p in planos[1:]]
    total = _total(palavras)
    cenas = []
    for n, p in enumerate(planos):
        t0 = inicio[n]
        dur = (inicio[n + 1] if n + 1 < len(planos) else total) - t0
        rel = lambda j, atraso=0.0: round(max(0.0, palavras[min(j, len(palavras) - 1)]["i"] - t0 + atraso), 3)  # noqa: E731
        c = {k: v for k, v in p.items() if k not in ("id", "i", "em", "bloco", "som", "palavra", "anotacoes", "contador", "rotulos", "citacao_i", "em_i")}
        c["dur"] = round(max(0.2, dur), 3)
        if p.get("palavra"):
            w = {k: v for k, v in p["palavra"].items() if not k.endswith("_i") and k not in ("em", "ate")}
            # a palavra precisa de tempo na tela: entra até ~35% da cena (decodifica em ~0,5 s) mesmo se dita depois
            w["em"] = min(rel(p["palavra"]["em_i"], ATRASO_PALAVRA), round(max(0.1, c["dur"] * 0.35), 3))
            if "ate_i" in p["palavra"] and rel(p["palavra"]["ate_i"]) - w["em"] >= 1.5:
                w["ate"] = rel(p["palavra"]["ate_i"])
            c["palavra"] = w
        if p.get("anotacoes"):
            c["anotacoes"] = [{**{k: v for k, v in a.items() if k != "em_i"}, "em": rel(a["em_i"], 0.4)} for a in p["anotacoes"]]
        if p.get("contador"):
            c["contador"] = {**{k: v for k, v in p["contador"].items() if k != "em_i"}, "em": rel(p["contador"]["em_i"])}
            c["contador"].setdefault("x", 140)
            c["contador"].setdefault("y", 760 if p.get("palavra") else 120)  # com palavra gigante, o número vai para baixo
        if p.get("rotulos"):
            c["rotulos"] = [{**{k: v for k, v in r.items() if k != "em_i"}, "em": rel(r["em_i"], 0.2)} for r in p["rotulos"]]
        if p["tipo"] == "pessoa":
            c["em"] = rel(p.get("em_i", p["i"]))
            if p.get("citacao_i") is not None and p.get("citacao"):
                k0 = p["citacao_i"]
                c["palavras"] = [rel(k0 + j) for j in range(len(p["citacao"].split()))]
        cenas.append(c)
    paleta = direcao.get("paleta") or CFG.get("paleta") or {}
    return {"paleta": paleta, "carro": direcao.get("carro") or CFG.get("carro", "ferrari_sf26.glb"), "cenas": cenas}


def _modelos_na_pasta(trabalho: Path) -> None:
    """Os .glb do acervo 3D entram na pasta pública do render como links (nada é copiado nem alterado)."""
    origem = RAIZ / CFG.get("modelos", "F1/dados/modelos3d")
    for arq in origem.glob("*"):
        if arq.suffix.lower() in (".glb", ".json"):
            destino = trabalho / arq.name
            if not destino.exists():
                try:
                    os.link(arq, destino)
                except OSError:
                    shutil.copy2(arq, destino)


def renderizar(trabalho: Path, direcao: dict, palavras: list[dict], saida: Path, progresso=None) -> float:
    import fotos

    _modelos_na_pasta(trabalho)
    aprovadas = fotos.na_pasta(trabalho.parent, trabalho)  # só foto aprovada pelo Felipe entra no vídeo
    # a foto vai no plano (e não só nas props): assim ela entra na impressão e o bloco do cartão é refeito
    direcao = {**direcao, "planos": [{**p, **aprovadas[p["nome"]]} if p["tipo"] == "pessoa" and not p.get("foto")
                                     and p.get("nome") in aprovadas else p for p in direcao["planos"]]}
    pr = props(direcao, palavras)
    return vertical.renderizar(trabalho, direcao, palavras, saida, progresso, composicao=CFG.get("composicao", "Horizontal"),
                               props=pr, cache_nome="blocos_horizontal", concorrencia=2, fps=FPS)


gerar_musica = vertical.gerar_musica


def remixar(trabalho: Path, direcao: dict, palavras: list[dict], base: Path, saida: Path) -> None:
    vertical.remixar(trabalho, direcao, palavras, base, saida, FPS)
