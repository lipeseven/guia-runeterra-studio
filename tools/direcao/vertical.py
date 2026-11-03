"""Diretor do vídeo vertical (curto animado). Genérico: o canal entrega o projeto Remotion, a composição, a API das
cenas e o catálogo de cenas prontas (`[vertical]` no canal.toml).

Cada vídeo é um projeto novo: o Claude escreve o CÓDIGO de cada cena (JavaScript com a API do canal) citando TRECHOS do
roteiro; a validação converte cada trecho no índice da palavra (direção presa à palavra, não ao segundo). Depois o código
passa pelo tsc (erros voltam ao Claude) e por uma rodada de revisão em que o Claude vê um quadro de cada cena.
Resultado em direcao/vertical.json do vídeo (o código fica só ali, nunca no projeto Remotion).
"""
from __future__ import annotations

import hashlib
import json
import math
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


SETS = {"pista", "circuito", "estudio", "pit", "livre"}


def sistema() -> str:
    return (f"Você é o diretor de animação dos vídeos verticais do canal \"{CANAL['nome']}\" ({CANAL['assunto']}).\n"
            "Cada vídeo é um projeto novo: escreva o CÓDIGO de cada cena para o que aquele trecho da fala diz, com a API "
            "das cenas (modelos da biblioteca + câmera). Cena pronta do catálogo só quando ela mostra exatamente a fala. "
            "A câmera segue o sentimento da fala e nunca para. Varie: nenhuma cena repetida, cada mundo/luz dura poucos "
            "planos. Placas e números só com o que a fala diz. Responda SOMENTE JSON.")


def _docs() -> str:
    """Documentos do diretor. Vão no prompt (stdin): na linha de comando do Windows não cabem."""
    return (f"# Folha de estilos\n{_doc('folha_de_estilos.md')}\n\n# Regras do diretor\n{_doc('regras_de_direcao.md')}\n\n"
            f"{_doc(CFG.get('api', 'api_cenas.md'))}\n\n# Cenas prontas (campo `tipo`) e sobreposições\n{catalogo()}\n\n")

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
    """Trechos → índices; código ou tipo e parâmetros conferidos. Plano que não se acha no roteiro sai (vira aviso)."""
    validos, planos, avisos, ult, ids = tipos(), [], [], 0, set()
    for n, b in enumerate(brutos):
        if isinstance(b.get("codigo"), str) and b["codigo"].strip():
            b = {k: v for k, v in b.items() if k != "tipo"}
            if b.get("set") not in SETS:
                b["set"] = "pista"
        elif b.get("tipo") not in validos:
            avisos.append(f"plano {n + 1}: sem código e com tipo desconhecido ({b.get('tipo')}), ignorado")
            continue
        i = 0 if not planos else localizar(palavras, b.get("em"), ult + 1)
        if i is None:
            avisos.append(f"plano {n + 1}: trecho não encontrado no roteiro: \"{b.get('em')}\"")
            continue
        ult = i
        p = {k: v for k, v in b.items() if k not in ("em", "marcas", "id")}
        p["em"] = " ".join(w["t"] for w in palavras[i:i + 4]) if not b.get("em") else b["em"]
        p["i"] = i
        pid = hashlib.sha1(f"{b.get('tipo') or 'codigo'}|{p['em']}".encode()).hexdigest()[:8]
        while pid in ids:
            pid = hashlib.sha1(pid.encode()).hexdigest()[:8]
        ids.add(pid)
        p["id"] = pid
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


FORMATO = ("Responda SOMENTE com JSON {\"chaves\": [um termo-chave por frase, como aparece na fala], \"planos\": [{\"em\", "
           "\"set\", \"clima\", \"codigo\" (ou \"tipo\" + parâmetros), \"marcas\"?, sobreposições?}]}. O código é JavaScript "
           "puro dentro de uma string JSON.")


def _pedir(prompt: str, palavras: list[dict], etiqueta: str) -> dict:
    r = chamar_json(prompt, sistema(), modelo="opus", etiqueta=etiqueta)
    brutos = r["planos"] if isinstance(r, dict) else r
    planos, avisos = resolver(brutos, palavras)
    chaves = [c for c in (r.get("chaves") if isinstance(r, dict) else None) or [] if isinstance(c, str)][:20]
    return {"planos": planos, "avisos": avisos, "chaves": chaves, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _briefing(texto: str) -> str:
    if not texto:
        return ""
    return ("BRIEFING DO VÍDEO (pedidos de quem fez o roteiro: siga; trecho que não existe mais no roteiro = ignore; cena "
            "marcada MODELO A CRIAR = use o modelo da API se já existir, senão a alternativa indicada; nunca contrarie o "
            f"EVITAR):\n{texto}\n\n")


def dirigir(roteiro: str, palavras: list[dict], briefing: str = "", trabalho: Path | None = None, aviso=lambda m: None) -> dict:
    prompt = (_docs() + f"ROTEIRO (com o tempo de cada frase na voz pronta; duração total {palavras[-1]['f']:.0f} s):\n"
              f"{frases(palavras)}\n\n" + _briefing(briefing)
              + "Monte o vídeo inteiro, cena por cena, para ESTE texto (troque de plano a cada 2 a 6 s). " + FORMATO)
    aviso("o diretor escreve as cenas")
    direcao = _pedir(prompt, palavras, "vertical-direcao")
    return conferir(direcao, palavras, briefing, trabalho, aviso)


# ------------------------------------------------------------------------------------------------ conferência
ARQ_CONFERIR = "src/_conferir_cenas.ts"  # arquivo temporário: o código das cenas passa pelo tsc antes do render


def _nomes_api(projeto: Path) -> list[str]:
    """Nomes que o código das cenas enxerga (bloco API:inicio … API:fim do Vertical.tsx)."""
    txt = (projeto / "src" / f"{CFG.get('composicao', 'Vertical')}.tsx").read_text(encoding="utf-8")
    bloco = txt.split("// API:inicio")[1].split("// API:fim")[0]
    return re.findall(r"[A-Za-z_]\w*", bloco[bloco.index("{") + 1:bloco.rindex("}")])


def checar_codigo(planos: list[dict]) -> dict[str, str]:
    """Erros do TypeScript no código de cada cena: {id do plano: erros}."""
    projeto = RAIZ / CFG.get("projeto", "")
    com = [p for p in planos if p.get("codigo")]
    if not com:
        return {}
    comp = CFG.get("composicao", "Vertical")
    linhas = [f'import {{ API, type CV }} from "./{comp}";', f"const {{ {', '.join(_nomes_api(projeto))} }} = API;",
              "export const cenas: Record<string, (c: CV) => void> = {"]
    faixas = []
    for p in com:
        ini = len(linhas) + 1
        linhas.append(f'"{p["id"]}": (c) => {{')
        linhas += p["codigo"].splitlines()
        linhas.append("},")
        faixas.append((ini, len(linhas), p["id"]))
    linhas.append("};")
    arq = projeto / ARQ_CONFERIR
    arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    try:
        r = subprocess.run(["npx.cmd", "tsc", "--noEmit", "-p", "tsconfig.cenas.json"], cwd=projeto, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300)
    finally:
        arq.unlink(missing_ok=True)
    erros: dict[str, list[str]] = {}
    for linha in r.stdout.splitlines():
        m = re.match(r"src[\\/]_conferir_cenas\.ts\((\d+),\d+\): error (TS\d+: .*)", linha)
        if not m:
            continue
        n = int(m.group(1))
        faixa = next((f for f in faixas if f[0] <= n <= f[1]), None)
        if faixa:
            erros.setdefault(faixa[2], []).append(f"linha {n - faixa[0]}: {m.group(2)}")
    return {k: "; ".join(v[:6]) for k, v in erros.items()}


def _trocar(direcao: dict, novos: list[dict], palavras: list[dict]) -> dict:
    """Planos corrigidos (por id, no formato do Claude) entram no lugar dos antigos; trechos resolvidos de novo."""
    por_id = {n["id"]: n for n in novos if isinstance(n, dict) and n.get("id")}
    brutos = []
    for p in para_o_claude(direcao["planos"]):
        n = por_id.get(p["id"])
        brutos.append({**p, **{k: v for k, v in n.items() if k != "id"}} if n else p)
    planos, avisos = resolver(brutos, palavras)
    return {**direcao, "planos": planos, "avisos": direcao.get("avisos", []) + avisos}


def _consertar_tsc(direcao: dict, palavras: list[dict], aviso) -> dict:
    """Até 2 rodadas: os erros do tsc voltam ao Claude; o que continuar quebrado vira cena pronta (aviso)."""
    for rodada in range(2):
        erros = checar_codigo(direcao["planos"])
        if not erros:
            return direcao
        aviso(f"corrigindo o código de {len(erros)} cena(s)")
        ruins = [{"id": p["id"], "em": p["em"], "codigo": p["codigo"], "erro": erros[p["id"]]}
                 for p in direcao["planos"] if p["id"] in erros]
        r = chamar_json(_docs() + "O código destas cenas não compila. Corrija mantendo a intenção de cada uma.\n"
                        f"{json.dumps(ruins, ensure_ascii=False)}\n\nResponda SOMENTE JSON {{\"planos\": [{{\"id\", \"codigo\"}}]}}.",
                        sistema(), modelo="sonnet", etiqueta="vertical-tsc")
        direcao = _trocar(direcao, r.get("planos", []) if isinstance(r, dict) else [], palavras)
    erros = checar_codigo(direcao["planos"])
    for p in direcao["planos"]:
        if p["id"] in erros:
            p.pop("codigo", None)
            p["tipo"] = "perseguicao"
            direcao["avisos"].append(f"cena \"{p['em']}\" não compilou e virou cena pronta: {erros[p['id']][:160]}")
    return direcao


def _props(direcao: dict, palavras: list[dict]) -> dict:
    return {"palavras": [{"t": p["t"], "i": p["i"], "f": p["f"]} for p in palavras], "planos": direcao["planos"],
            "audio": "voz.wav", "chaves": direcao.get("chaves", [])}


def quadros(trabalho: Path, direcao: dict, palavras: list[dict], ids: set[str] | None = None) -> tuple[list[Path], dict[str, str]]:
    """Um quadro por plano (60% do plano), em folhas de 8, numeradas. Devolve (folhas, erros de execução por id)."""
    from PIL import Image, ImageDraw, ImageFont

    projeto = RAIZ / CFG.get("projeto", "")
    pasta = trabalho / "conferencia_cenas"
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("*.jpg"):
        velho.unlink()
    planos = direcao["planos"]
    fim_fala = palavras[-1]["f"]
    alvos = []
    for n, p in enumerate(planos):
        if ids is not None and p["id"] not in ids:
            continue
        ini = 0 if n == 0 else palavras[p["i"]]["i"]
        fim = palavras[planos[n + 1]["i"]]["i"] if n + 1 < len(planos) else fim_fala
        alvos.append((n, p, int((ini + (fim - ini) * 0.6) * 30)))
    props = trabalho / "vertical_props_conferencia.json"
    props.write_text(json.dumps(_props(direcao, palavras), ensure_ascii=False), encoding="utf-8")
    pedido = trabalho / "quadros_pedido.json"
    pedido.write_text(json.dumps({"composicao": CFG.get("composicao", "Vertical"), "props": str(props), "publicDir": str(trabalho),
                                  "escala": 0.25, "quadros": [{"q": q, "saida": str(pasta / f"{n:03d}.jpg")} for n, _, q in alvos]}),
                      encoding="utf-8")
    r = subprocess.run(["node", "quadros.mjs", str(pedido)], cwd=projeto, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    por_quadro = {q: p["id"] for _, p, q in alvos}
    erros: dict[str, str] = {}
    for linha in r.stdout.splitlines():
        m = re.match(r"ERRO (\d+) (.*)", linha)
        if m and "ERRO_CENA" in m.group(2) and int(m.group(1)) in por_quadro:
            erros.setdefault(por_quadro[int(m.group(1))], m.group(2)[m.group(2).find("ERRO_CENA"):][:300])
    if r.returncode != 0:
        raise RuntimeError("quadros da conferência falharam: " + (r.stderr or r.stdout)[-500:])
    fonte = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)
    folhas = []
    for k in range(0, len(alvos), 8):
        folha = Image.new("RGB", (1080, 960), "#111")
        for j, (n, p, _) in enumerate(alvos[k:k + 8]):
            arq = pasta / f"{n:03d}.jpg"
            if arq.exists():
                folha.paste(Image.open(arq).convert("RGB").resize((270, 480)), ((j % 4) * 270, (j // 4) * 480))
            d = ImageDraw.Draw(folha)
            x, y = (j % 4) * 270, (j // 4) * 480
            d.rectangle([x, y, x + 64, y + 40], fill="#000")
            d.text((x + 8, y + 2), str(n + 1), fill="#ffd400", font=fonte)
        destino = pasta / f"folha_{k // 8 + 1}.jpg"
        folha.save(destino, quality=85)
        folhas.append(destino)
    return folhas, erros


def _revisar_imagens(direcao: dict, palavras: list[dict], briefing: str, trabalho: Path, aviso, ids: set[str] | None = None) -> dict:
    aviso("renderizando um quadro de cada cena")
    folhas, erros = quadros(trabalho, direcao, palavras, ids)
    planos = direcao["planos"]
    lista = []
    for n, p in enumerate(planos):
        if ids is not None and p["id"] not in ids:
            continue
        fala =" ".join(w["t"] for w in palavras[p["i"]:(planos[n + 1]["i"] if n + 1 < len(planos) else len(palavras))])
        item = {"numero": n + 1, **para_o_claude([p])[0], "fala": fala}
        if p["id"] in erros:
            item["erro_ao_rodar"] = erros[p["id"]]
        lista.append(item)
    aviso("o diretor confere as cenas pelas imagens")
    r = chamar_json(
        _docs() + _briefing(briefing)
        + "As imagens mostram um quadro de cada plano (número no canto, 60% do plano), na ordem. Confira cada um contra a "
          "fala: mostra o que a fala diz? O assunto está enquadrado (nada cortado, vazio, minúsculo ou atrás de outra coisa)? "
          "Peça atravessando outra, peça solta no ar, pessoa enterrada no chão ou dentro do carro, rótulo cobrindo o que "
          "nomeia, número na placa que não bate com a cena? (colisão se corrige com número na posição, nunca escondendo "
          "com a câmera.) Cena repetida demais? Plano com erro_ao_rodar quebrou e precisa de código novo. Devolva SÓ os planos que precisam "
          "mudar, completos, com o mesmo id.\n\nPLANOS:\n" + json.dumps(lista, ensure_ascii=False)
          + "\n\nResponda SOMENTE JSON {\"planos\": [...], \"observacao\": \"1 frase\"}.",
        sistema(), modelo="opus", imagens=folhas, etiqueta="vertical-imagens")
    novos = r.get("planos", []) if isinstance(r, dict) else []
    if not novos:
        return direcao
    aviso(f"o diretor refez {len(novos)} cena(s) depois de ver as imagens")
    return _consertar_tsc(_trocar(direcao, novos, palavras), palavras, aviso)


def conferir(direcao: dict, palavras: list[dict], briefing: str, trabalho: Path | None, aviso, ids: set[str] | None = None) -> dict:
    """tsc (com correção) e, havendo pasta de trabalho, uma rodada de revisão pelas imagens."""
    aviso("conferindo o código das cenas")
    direcao = _consertar_tsc(direcao, palavras, aviso)
    if trabalho is not None:
        direcao = _revisar_imagens(direcao, palavras, briefing, trabalho, aviso, ids)
    # aviso de cena que não compilou e depois foi reescrita (com código) já não vale
    com_codigo = {p["em"] for p in direcao["planos"] if p.get("codigo")}
    direcao["avisos"] = [a for a in direcao.get("avisos", [])
                         if not (a.startswith('cena "') and a.split('"')[1] in com_codigo)]
    return direcao


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


def _resumo(p: dict) -> dict:
    """Plano sem pedido, como contexto barato: só o que ele mostra (sem o código)."""
    q = {k: p[k] for k in ("id", "em", "set", "clima", "tipo") if k in p}
    if p.get("codigo"):
        q["codigo"] = f"({len(p['codigo'].splitlines())} linhas, fica igual)"
    return q


def revisar(direcao: dict, pedidos: list[dict], palavras: list[dict], briefing: str = "", trabalho: Path | None = None,
            aviso=lambda m: None) -> dict:
    """Pedidos do Felipe (gerais ou por plano) → só os planos pedidos vão completos ao Claude (os outros, resumidos) e
    só os que mudaram voltam; o resto fica intacto. Só os que mudaram passam pela conferência das imagens."""
    ids = [p["id"] for p in direcao["planos"]]
    numero = {pid: n + 1 for n, pid in enumerate(ids)}
    alvo = {p["plano"] for p in pedidos if p.get("plano") in numero}
    geral = any(not p.get("plano") or p["plano"] not in numero for p in pedidos)
    linhas = [f"- plano {numero[p['plano']]} (id {p['plano']}): {p['texto']}" if p.get("plano") in numero else f"- geral: {p['texto']}"
              for p in pedidos]
    claude = para_o_claude(direcao["planos"])
    # pedido geral pode mexer em qualquer cena: aí todas vão completas (mas só as alteradas voltam)
    atuais = [q if geral or q["id"] in alvo else _resumo(q) for q in claude]
    prompt = (_docs() + f"ROTEIRO:\n{frases(palavras)}\n\n{_briefing(briefing)}DIREÇÃO ATUAL (na ordem; "
              + ("todos os planos completos" if geral else "os planos pedidos vêm completos, os outros resumidos")
              + f"):\n{json.dumps(atuais, ensure_ascii=False)}\n\nPEDIDOS DO FELIPE:\n{chr(10).join(linhas)}\n\n"
              "Aplique os pedidos. Devolva SÓ os planos que mudam, completos, com o mesmo id (plano sem mudança NÃO volta). "
              "Plano novo (dividir uma cena) vem sem id, com \"depois_de\": id do plano que vem antes dele. Plano que sai: "
              "id em \"remover\". Responda SOMENTE JSON {\"planos\": [{\"id\", \"em\", \"set\", \"clima\", \"codigo\" (ou "
              "\"tipo\" + parâmetros), \"marcas\"?, sobreposições?}], \"remover\": [ids]}. O código é JavaScript puro dentro "
              "de uma string JSON.")
    aviso("o diretor aplica os seus pedidos")
    r = chamar_json(prompt, sistema(), modelo="opus", etiqueta="vertical-revisao")
    novos = [n for n in (r.get("planos") if isinstance(r, dict) else r) or [] if isinstance(n, dict)]
    remover = set(r.get("remover") or []) if isinstance(r, dict) else set()
    por_id = {n["id"]: n for n in novos if n.get("id") in numero}
    depois: dict[str, list[dict]] = {}
    for n in novos:
        if n.get("id") not in numero:
            depois.setdefault(n.get("depois_de") if n.get("depois_de") in numero else ids[-1], []).append(
                {k: v for k, v in n.items() if k not in ("id", "depois_de")})
    brutos = []
    for q in claude:
        if q["id"] not in remover:
            n = por_id.get(q["id"])
            if n:  # o plano volta completo; trecho e cena que faltarem ficam os de antes
                n = {k: v for k, v in n.items() if k != "depois_de"}
                n.setdefault("em", q["em"])
                if not n.get("codigo") and not n.get("tipo"):
                    n.update({k: q[k] for k in ("codigo", "tipo", "set") if k in q})
            brutos.append(n or q)
        brutos += depois.get(q["id"], [])
    planos, avisos = resolver(brutos, palavras)
    nova = {**direcao, "planos": planos, "avisos": avisos, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}
    antes = {p["id"]: json.dumps(p, sort_keys=True, ensure_ascii=False) for p in direcao["planos"]}
    mudou = {p["id"] for p in nova["planos"] if antes.get(p["id"]) != json.dumps(p, sort_keys=True, ensure_ascii=False)}
    aviso(f"o diretor mudou {len(mudou)} cena(s)")
    return conferir(nova, palavras, briefing, trabalho if mudou else None, aviso, mudou)

# ------------------------------------------------------------------------------------------------ render
FPS = 30


def _fonte_remotion(projeto: Path) -> str:
    """Impressão do código que desenha as cenas: mudou um modelo = todos os blocos são refeitos."""
    h = hashlib.sha1()
    for arq in sorted([*(projeto / "src").rglob("*"), projeto / "package.json"]):
        if arq.is_file() and arq.name != Path(ARQ_CONFERIR).name:
            h.update(arq.relative_to(projeto).as_posix().encode())
            h.update(arq.read_bytes())
    return h.hexdigest()


def blocos(direcao: dict, palavras: list[dict], fonte: str = "") -> list[dict]:
    """Planos agrupados em blocos de ~3 planos (corte decidido pelo id do plano, não pela posição: inserir ou tirar um
    plano não muda os blocos dos outros). Cada bloco = intervalo de quadros + impressão do que aparece nele."""
    planos = direcao["planos"]
    total = math.ceil((palavras[-1]["f"] + 0.35) * FPS)
    q = [0] + [min(total, math.ceil(palavras[p["i"]]["i"] * FPS - 1e-6)) for p in planos[1:]] + [total]
    comum = hashlib.sha1(json.dumps([[w["t"], w["i"], w["f"]] for w in palavras] + [direcao.get("chaves", []), fonte],
                                    ensure_ascii=False).encode()).hexdigest()
    saida, atual = [], []
    for n, p in enumerate(planos):
        atual.append(n)
        if int(p["id"][:6], 16) % 3 == 0 or len(atual) >= 5 or n == len(planos) - 1:
            ini, fim = q[atual[0]], q[n + 1] - 1
            if fim >= ini:
                chave = json.dumps({"planos": [planos[k] for k in atual], "q": [ini, fim], "comum": comum}, sort_keys=True,
                                   ensure_ascii=False)
                saida.append({"inicio": ini, "fim": fim, "planos": [planos[k]["id"] for k in atual],
                              "impressao": hashlib.sha1(chave.encode()).hexdigest()[:16]})
            atual = []
    return saida


def renderizar(trabalho: Path, direcao: dict, palavras: list[dict], saida: Path, progresso=None) -> float:
    """Render por blocos com cache (como no Runeterra): só os blocos com plano alterado são renderizados de novo; a
    voz entra no FFmpeg, sem recomprimir o vídeo. A pasta trabalho/ do vídeo (com voz.wav) é a pasta pública do Remotion."""
    projeto = RAIZ / CFG.get("projeto", "")
    cache = trabalho.parent / "blocos_vertical"  # fora de trabalho/: a pasta pública é copiada a cada render
    cache.mkdir(parents=True, exist_ok=True)
    props = trabalho / "vertical_props.json"
    props.write_text(json.dumps(_props(direcao, palavras), ensure_ascii=False), encoding="utf-8")
    lista = blocos(direcao, palavras, _fonte_remotion(projeto))
    faltam = [b for b in lista if not (cache / f"{b['impressao']}.mp4").exists()]
    inicio = time.time()
    if faltam:
        pedido = trabalho / "render_blocos_pedido.json"
        pedido.write_text(json.dumps({"composicao": CFG.get("composicao", "Vertical"), "props": str(props), "publicDir": str(trabalho),
                                      "blocos": [{"inicio": b["inicio"], "fim": b["fim"], "saida": str(cache / f"{b['impressao']}.mp4")}
                                                 for b in faltam]}), encoding="utf-8")
        a_fazer = sum(b["fim"] - b["inicio"] + 1 for b in faltam)
        feitos = [0] * len(faltam)
        proc = subprocess.Popen(["node", "render_blocos.mjs", str(pedido)], cwd=projeto, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        cauda: list[str] = []
        for linha in proc.stdout:
            cauda = (cauda + [linha.rstrip()])[-30:]
            m = re.match(r"PROG (\d+) (\d+)", linha)
            if m and progresso:
                feitos[int(m.group(1))] = int(m.group(2))
                progresso(sum(feitos) / a_fazer, inicio)
        if proc.wait() != 0 or any(not (cache / f"{b['impressao']}.mp4").exists() for b in faltam):
            raise RuntimeError("render falhou: " + " | ".join(l for l in cauda if l.strip())[-600:])
    saida.parent.mkdir(parents=True, exist_ok=True)
    juntar = trabalho / "render_blocos.txt"
    juntar.write_text("".join(f"file '{(cache / (b['impressao'] + '.mp4')).as_posix()}'\n" for b in lista), encoding="utf-8")
    total = math.ceil((palavras[-1]["f"] + 0.35) * FPS) / FPS
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(juntar), "-i", str(trabalho / "voz.wav"),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
                        "-movflags", "+faststart", str(saida)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not saida.exists():
        raise RuntimeError("junção dos blocos falhou: " + r.stderr[-600:])
    # o cache guarda os blocos desta versão e os da anterior (para voltar atrás sem renderizar)
    usados = {b["impressao"] for b in lista}
    anterior = trabalho.parent / "blocos_vertical.json"
    if anterior.exists():
        usados |= set(json.loads(anterior.read_text(encoding="utf-8")))
    for velho in cache.glob("*.mp4"):
        if velho.stem not in usados:
            velho.unlink(missing_ok=True)
    anterior.write_text(json.dumps(sorted(b["impressao"] for b in lista)), encoding="utf-8")
    return time.time() - inicio
