"""Diretor do vídeo vertical (curto animado). Genérico: o canal entrega o projeto Remotion, a composição e o catálogo
de planos (`[vertical]` no canal.toml); aqui só se escolhe, valida e renderiza.

O Claude escolhe os planos citando TRECHOS do roteiro; a validação converte cada trecho no índice da palavra
(direção presa à palavra, não ao segundo). Resultado em direcao/vertical.json do vídeo.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

from canal import CANAL, RAIZ, caminho
from claude_cli import chamar_json

CFG = CANAL.get("vertical", {})


def _limpa(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def catalogo() -> str:
    return (caminho("docs") / CFG.get("catalogo", "catalogo_vertical.md")).read_text(encoding="utf-8")


def tipos() -> set[str]:
    """Os tipos válidos são a 1ª coluna da tabela do catálogo (fonte única)."""
    return set(re.findall(r"^\| ([a-z_]+) \|", catalogo(), re.M)) - {"tipo"}


def _doc(nome: str) -> str:
    p = caminho("docs") / nome
    return p.read_text(encoding="utf-8") if p.exists() else ""


def sistema() -> str:
    return (f"Você é o diretor de animação dos vídeos verticais do canal \"{CANAL['nome']}\" ({CANAL['assunto']}).\n"
            "Escolha a cena de cada trecho da fala seguindo a folha de estilos e usando SÓ os tipos do catálogo.\n"
            "A câmera segue o sentimento da fala. Varie: nunca o mesmo tipo duas vezes seguidas, e cada mundo/luz "
            "dura poucos planos. Placas e números só com o que a fala diz.\n\n"
            f"# Folha de estilos\n{_doc('folha_de_estilos.md')}\n\n# Regras do diretor\n{_doc('regras_de_direcao.md')}\n\n"
            f"{catalogo()}")


def frases(palavras: list[dict]) -> str:
    """Roteiro em frases, cada uma com o tempo, para o Claude dosar a duração dos planos."""
    linhas, atual, ini = [], [], 0.0
    for p in palavras:
        if not atual:
            ini = p["i"]
        atual.append(p["t"])
        if re.search(r"[.!?:]$|\.\.\.$", p["t"]):
            linhas.append(f"[{ini:5.1f}s → {p['f']:5.1f}s] {' '.join(atual)}")
            atual = []
    if atual:
        linhas.append(f"[{ini:5.1f}s] {' '.join(atual)}")
    return "\n".join(linhas)


def localizar(palavras: list[dict], trecho: str | None, apos: int = 0) -> int | None:
    if not trecho:
        return None
    alvo = [_limpa(x) for x in str(trecho).split() if _limpa(x)]
    lim = [_limpa(p["t"]) for p in palavras]
    for k in range(apos, len(lim) - len(alvo) + 1):
        if alvo and lim[k:k + len(alvo)] == alvo:
            return k
    return None


def resolver(brutos: list[dict], palavras: list[dict]) -> tuple[list[dict], list[str]]:
    """Trechos → índices; tipos e parâmetros conferidos. Plano que não se acha no roteiro sai (vira aviso)."""
    validos, planos, avisos, ult = tipos(), [], [], 0
    for n, b in enumerate(brutos):
        if b.get("tipo") not in validos:
            avisos.append(f"plano {n + 1}: tipo desconhecido ({b.get('tipo')}), ignorado")
            continue
        i = 0 if not planos else localizar(palavras, b.get("em"), ult + 1)
        if i is None:
            avisos.append(f"plano {n + 1} ({b['tipo']}): trecho não encontrado no roteiro: \"{b.get('em')}\"")
            continue
        ult = i
        p = {k: v for k, v in b.items() if k not in ("em", "marcas")}
        p["em"] = " ".join(w["t"] for w in palavras[i:i + 4]) if not b.get("em") else b["em"]
        p["i"] = i
        p["id"] = hashlib.sha1(f"{b['tipo']}|{p['em']}".encode()).hexdigest()[:8]
        if "equipe" in p:
            p["equipe"] = max(0, min(10, int(p["equipe"])))
        if "n" in p:
            p["n"] = max(1, min(22, int(p["n"])))
        marcas = {}
        for nome, trecho in (b.get("marcas") or {}).items():
            j = localizar(palavras, trecho, i)
            if j is not None:
                marcas[nome] = j
        if marcas:
            p["marcas"] = marcas
            p["marcas_texto"] = b["marcas"]
        for pl in p.get("placas") or []:
            j = localizar(palavras, pl.pop("em", None), i)
            if j is not None:
                pl["i"] = j
        for campo, chaves in (("contador", (("em", "i0"), ("ate_em", "i1"))), ("chips", (("em", "i"),)), ("selo", (("em", "i"),)),
                              ("medidor", (("em", "i"),)), ("riscado", (("em", "i"),))):
            if isinstance(p.get(campo), dict):
                for de, para in chaves:
                    j = localizar(palavras, p[campo].pop(de, None), i)
                    if j is not None:
                        p[campo][para] = j
        if isinstance(p.get("riscado"), dict) and "i" not in p["riscado"]:
            p["riscado"]["i"] = i
        planos.append(p)
    if not planos:
        raise RuntimeError("o diretor não devolveu nenhum plano válido")
    planos[0]["i"] = 0
    return planos, avisos


def _pedir(prompt: str, palavras: list[dict], etiqueta: str) -> dict:
    r = chamar_json(prompt, sistema(), modelo="opus", etiqueta=etiqueta)
    brutos = r["planos"] if isinstance(r, dict) else r
    planos, avisos = resolver(brutos, palavras)
    chaves = [c for c in (r.get("chaves") if isinstance(r, dict) else None) or [] if isinstance(c, str)][:20]
    return {"planos": planos, "avisos": avisos, "chaves": chaves, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _briefing(texto: str) -> str:
    if not texto:
        return ""
    return ("BRIEFING DO VÍDEO (pedidos de quem fez o roteiro: siga sempre que couber no catálogo; trecho que não existe "
            "mais no roteiro = ignore; cena marcada MODELO A CRIAR = use a alternativa indicada; nunca contrarie o EVITAR):\n"
            f"{texto}\n\n")


def dirigir(roteiro: str, palavras: list[dict], briefing: str = "") -> dict:
    prompt = (f"ROTEIRO (com o tempo de cada frase na voz pronta; duração total {palavras[-1]['f']:.0f} s):\n{frases(palavras)}\n\n"
              f"{_briefing(briefing)}Monte o vídeo inteiro. Responda SOMENTE com JSON {\"chaves\": [um termo-chave por frase, como aparece na fala], "
              "\"planos\": [...]} com os campos do catálogo.")
    return _pedir(prompt, palavras, "vertical-direcao")


def para_o_claude(planos: list[dict]) -> list[dict]:
    """Planos como o Claude os escreve (trechos no lugar de índices), para revisar."""
    fora = {"i", "id", "marcas", "marcas_texto"}
    saida = []
    for p in planos:
        q = {k: v for k, v in p.items() if k not in fora}
        if p.get("marcas_texto"):
            q["marcas"] = p["marcas_texto"]
        q["id"] = p["id"]
        saida.append(q)
    return saida


def revisar(direcao: dict, pedidos: list[dict], palavras: list[dict], briefing: str = "") -> dict:
    """Pedidos do Felipe (gerais ou por plano) → planos novos. Planos sem pedido devem voltar iguais."""
    linhas = [f"- plano {p['plano']}: {p['texto']}" if p.get("plano") else f"- geral: {p['texto']}" for p in pedidos]
    prompt = (f"ROTEIRO:\n{frases(palavras)}\n\n{_briefing(briefing)}DIREÇÃO ATUAL (cada plano com id):\n"
              f"{json.dumps(para_o_claude(direcao['planos']), ensure_ascii=False)}\n\n"
              f"PEDIDOS DO FELIPE:\n{chr(10).join(linhas)}\n\n"
              "Aplique os pedidos. Planos sem pedido voltam iguais. Responda SOMENTE com JSON {\"chaves\": [...], "
              "\"planos\": [lista completa]}.")
    nova = _pedir(prompt, palavras, "vertical-revisao")
    if not nova["chaves"]:
        nova["chaves"] = direcao.get("chaves", [])
    return nova


def renderizar(trabalho: Path, direcao: dict, palavras: list[dict], saida: Path, progresso=None) -> float:
    """Render da composição do canal. A pasta trabalho/ do vídeo (com voz.wav) vira a pasta pública do Remotion."""
    projeto = RAIZ / CFG.get("projeto", "")
    props = trabalho / "vertical_props.json"
    props.write_text(json.dumps({"palavras": [{"t": p["t"], "i": p["i"], "f": p["f"]} for p in palavras],
                                 "planos": direcao["planos"], "audio": "voz.wav", "chaves": direcao.get("chaves", [])},
                                ensure_ascii=False), encoding="utf-8")
    saida.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["npx.cmd", "remotion", "render", "src/index.ts", CFG.get("composicao", "Vertical"), str(saida),
           f"--props={props}", f"--public-dir={trabalho}", "--gl=angle", "--concurrency=3"]
    inicio = time.time()
    proc = subprocess.Popen(cmd, cwd=projeto, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    cauda: list[str] = []
    for linha in proc.stdout:
        cauda = (cauda + [linha.rstrip()])[-30:]
        m = re.search(r"Rendered (\d+)/(\d+)", linha)
        if m and progresso:
            progresso(int(m.group(1)) / int(m.group(2)), inicio)
    if proc.wait() != 0 or not saida.exists():
        raise RuntimeError("render falhou: " + " | ".join(l for l in cauda if l.strip())[-600:])
    return time.time() - inicio
