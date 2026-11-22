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
import tempfile
import time
import unicodedata
from pathlib import Path

from canal import CANAL, DADOS_COMUM, RAIZ, caminho
import anexos
from claude_cli import chamar_json

CFG = CANAL.get("vertical", {})


def _limpa(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def catalogo() -> str:
    return _doc(CFG.get("catalogo", "catalogo_vertical.md"))


def tipos() -> set[str]:
    """Os tipos válidos são a 1ª coluna da tabela do catálogo (fonte única)."""
    return set(re.findall(r"^\| ([a-z_]+) \|", catalogo(), re.M)) - {"tipo"}


def _doc(nome: str) -> str:
    """Documento do diretor: primeiro na pasta de docs do vertical ([vertical].docs), depois na do canal ([pastas].docs)."""
    for pasta in ([RAIZ / CFG["docs"]] if CFG.get("docs") else []) + [caminho("docs")]:
        p = pasta / nome
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


SETS = {"pista", "circuito", "estudio", "pit", "livre", "real"}


def sistema() -> str:
    return (f"Você é o diretor de animação dos vídeos verticais do canal \"{CANAL['nome']}\" ({CANAL['assunto']}).\n"
            "Cada vídeo é um projeto novo: escreva o CÓDIGO de cada cena para o que aquele trecho da fala diz, com a API "
            "das cenas (modelos da biblioteca + câmera). Cena pronta do catálogo só quando ela mostra exatamente a fala. "
            "A câmera segue o sentimento da fala e nunca para. Varie: nenhuma cena repetida, cada mundo/luz dura poucos "
            "planos. Placas e números só com o que a fala diz, EXCETO os liberados pelo Felipe (seção NÚMEROS NA TELA do "
            "briefing ou pedido dele: esses vão para a tela exatamente como escritos). Pedido explícito do Felipe SEMPRE é cumprido: vale mais que qualquer regra destes "
            "documentos; só deixe de fazer por falta real de capacidade da API, dizendo exatamente o que falta (ex.: o arquivo "
            "que ele precisa pôr). Responda SOMENTE JSON.")


def _docs() -> str:
    """Documentos do diretor. Vão no prompt (stdin): na linha de comando do Windows não cabem."""
    return (f"# Folha de estilos\n{_doc('folha_de_estilos.md')}\n\n# Regras do diretor\n{_doc('regras_de_direcao.md')}\n\n"
            f"{_doc(CFG.get('api', 'api_cenas.md'))}\n\n# Cenas prontas (campo `tipo`) e sobreposições\n{catalogo()}\n\n"
            f"{_lista_logos()}\n\n")


# ------------------------------------------------------------------------------------------------ logos de arquivo
EXT_LOGO = (".png", ".jpg", ".jpeg", ".webp", ".svg")
PASTA_LOGOS = RAIZ / CFG.get("logos", "F1/comum/arte/logos")  # nome do arquivo = chave (fia.png → "logo:fia")
_REF_LOGO = re.compile(r"logo:([a-z0-9_\-]+)", re.I)


def logos_disponiveis(pasta: Path | None = None) -> dict[str, Path]:
    """{chave: arquivo} dos logos que o Felipe pôs na pasta (só leitura)."""
    pasta = pasta or PASTA_LOGOS
    if not pasta.is_dir():
        return {}
    return {a.stem.lower(): a for a in sorted(pasta.iterdir()) if a.is_file() and a.suffix.lower() in EXT_LOGO}


def _lista_logos() -> str:
    rel = PASTA_LOGOS.relative_to(RAIZ).as_posix() if PASTA_LOGOS.is_relative_to(RAIZ) else str(PASTA_LOGOS)
    tem = ", ".join(f"logo:{k}" for k in logos_disponiveis()) or "nenhum"
    return (f"LOGOS DISPONÍVEIS (arquivos em {rel}/; use a chave em logo(), criarPainelLogo, criarLivro, aplicarLogo): {tem}. "
            f"Logo que não está nesta lista NÃO existe: não invente nem desenhe à mão; ponha em \"nao_feitos\" o arquivo exato "
            f"que o Felipe precisa colocar (ex.: \"falta o arquivo {rel}/fia.png\").")


def logos_usados(planos: list[dict]) -> set[str]:
    return {m.lower() for m in _REF_LOGO.findall(json.dumps(planos, ensure_ascii=False))}


def avisos_logos(planos: list[dict], pasta: Path | None = None) -> list[str]:
    """Logo citado no código que não tem arquivo: diz exatamente qual arquivo o Felipe precisa colocar."""
    pasta = pasta or PASTA_LOGOS
    rel = pasta.relative_to(RAIZ).as_posix() if pasta.is_relative_to(RAIZ) else str(pasta)
    falta = sorted(logos_usados(planos) - set(logos_disponiveis(pasta)))
    return [f"falta o logo \"{k}\": coloque o arquivo {rel}/{k}.png (PNG, de preferência com fundo transparente; nome do "
            f"arquivo = chave)" for k in falta]


def copiar_logos(trabalho: Path, planos: list[dict], pasta: Path | None = None) -> dict[str, str]:
    """Copia os logos citados para <trabalho>/logos (a pasta pública do render). Devolve {chave: caminho público}."""
    import shutil

    disp = logos_disponiveis(pasta)
    saida = {}
    for k in sorted(logos_usados(planos) & set(disp)):
        dados = disp[k].read_bytes()
        nome = disp[k].name
        if dados.lstrip(b"\xef\xbb\xbf \t\r\n")[:5].lower() in (b"<svg ", b"<svg\n", b"<?xml") or b"<svg" in dados[:400].lower():
            # SVG salvo com extensão .png (aconteceu com o fia.png): o servidor do render o serviria como image/png e o
            # navegador não decodifica. Grava como .svg e, se faltar largura/altura, deriva do viewBox.
            nome = disp[k].stem + ".svg"
            txt = dados.decode("utf-8", errors="replace")
            m = re.search(r"<svg\b[^>]*>", txt, re.I)
            if m and not re.search(r"\swidth\s*=", m.group(0), re.I):
                vb = re.search(r'viewBox\s*=\s*"([-\d.\s,]+)"', m.group(0))
                if vb:
                    p = [float(x) for x in re.split(r"[\s,]+", vb.group(1).strip())]
                    if len(p) == 4 and p[2] > 0 and p[3] > 0:
                        esc = 1024 / max(p[2], p[3])
                        nova = m.group(0)[:-1] + f' width="{p[2] * esc:.0f}" height="{p[3] * esc:.0f}">'
                        txt = txt.replace(m.group(0), nova, 1)
            dados = txt.encode("utf-8")
        destino = trabalho / "logos" / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists() or destino.read_bytes() != dados:
            destino.write_bytes(dados)
        saida[k] = f"logos/{nome}"
    return saida


def _assinatura_logos(planos: list[dict]) -> str:
    """Trocar o arquivo de um logo refaz os blocos que o usam (entra na impressão)."""
    disp = logos_disponiveis()
    usados = sorted(logos_usados(planos) & set(disp))
    if not usados:
        return ""
    return "|logos:" + hashlib.sha1(b"".join(k.encode() + disp[k].read_bytes() for k in usados)).hexdigest()


# ------------------------------------------------------------------------------------------------ números na tela
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_UNID = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
         "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14, "quinze": 15,
         "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40,
         "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
         "duzentos": 200, "duzentas": 200, "trezentos": 300, "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400,
         "quinhentos": 500, "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700, "setecentas": 700,
         "oitocentos": 800, "oitocentas": 800, "novecentos": 900, "novecentas": 900}
_MULT = {"mil": 1000, "milhao": 10 ** 6, "milhoes": 10 ** 6}


def _chave_num(bruto: str) -> str:
    """Número comparável: só os dígitos ("6,201" = "6.201" = "6201"; "311.0" de JSON = "311")."""
    return re.sub(r"\D", "", bruto).lstrip("0") or "0"


def _por_extenso(texto: str) -> set[str]:
    """Números falados por extenso ("seis vírgula duzentos e um" → 6201; "dezessete" → 17)."""
    tok = [_limpa(x) for x in re.split(r"[\s\-]+", texto) if _limpa(x)]
    achados, i = set(), 0
    while i < len(tok):
        if tok[i] not in _UNID and tok[i] not in _MULT:
            i += 1
            continue
        total = atual = 0
        inteiro, j = None, i
        while j < len(tok):
            w = tok[j]
            if w in _UNID:
                atual += _UNID[w]
            elif w in _MULT:
                total += (atual or 1) * _MULT[w]
                atual = 0
            elif w == "e" and j + 1 < len(tok) and (tok[j + 1] in _UNID or tok[j + 1] in _MULT):
                pass
            elif w == "virgula" and inteiro is None and j + 1 < len(tok) and tok[j + 1] in _UNID:
                inteiro, total, atual = total + atual, 0, 0
            else:
                break
            j += 1
        n = total + atual
        achados.add(_chave_num(f"{inteiro}{n}") if inteiro is not None else str(n))
        i = j
    return achados


def numeros_do_texto(texto: str) -> set[str]:
    """Chaves de todos os números de um texto (em algarismos e por extenso)."""
    return {_chave_num(x) for x in _NUM.findall(texto)} | _por_extenso(texto)


def _sem_float(v) -> str:
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


_TEXTO_COD = re.compile(r"(?:\b(?:rotulo|criarAlfinete|criarLivro|criarPainelLogo)\(\s*|\b(?:texto|titulo|sub):\s*)([\"'`])(.*?)\1")


def textos_na_tela(p: dict) -> list[str]:
    """Textos que o plano escreve na tela (sobreposições, gráficos e rótulos do código)."""
    t: list[str] = []
    for pl in p.get("placas") or []:
        if isinstance(pl, dict):
            t.append(f"{pl.get('texto', '')} {pl.get('unidade', '')}")
    if isinstance(p.get("contador"), dict):
        t.append(_sem_float(p["contador"].get("ate", "")))
    for campo in ("titulo", "selo", "riscado", "medidor", "gota"):
        if isinstance(p.get(campo), dict):
            t += [str(p[campo].get(k, "")) for k in ("texto", "sub")]
    if isinstance(p.get("chips"), dict):
        t += [str(x) for x in p["chips"].get("itens") or []]
    g = p.get("grafico")
    if isinstance(g, dict):
        t += [str(g.get(k, "")) for k in ("texto", "esquerda", "direita", "unidade")]
        if g.get("tipo") in ("numero", "ano") and "valor" in g:
            t.append(_sem_float(g["valor"]))
        t += [str(x) for x in g.get("itens") or []]
        t += [str(x.get("t", "")) for x in g.get("palavras") or [] if isinstance(x, dict)]
        t += [f"{x.get('rotulo', '')} {x.get('nome', '')}" for x in g.get("marcos") or [] if isinstance(x, dict)]
        t += [str(g.get("titulo", ""))] + [str(x.get("nome", "")) for x in g.get("linhas") or [] if isinstance(x, dict)]  # classificação (posições ficam de fora)
        t += [str(x.get("texto", "")) for x in g.get("horas") or [] if isinstance(x, dict)]
    if isinstance(p.get("codigo"), str):
        t += [m.group(2) for m in _TEXTO_COD.finditer(p["codigo"])]
    return [x for x in t if x and x.strip()]


def numeros_liberados(briefing: str) -> list[str]:
    """Linhas da seção "NÚMEROS NA TELA (pedido do Felipe)" do briefing: textos/números que podem ir para a tela mesmo
    fora da fala. Aceita o briefing do diretor ("## TÍTULO") e o arquivo original (títulos entre linhas de "=")."""
    if not briefing:
        return []
    texto = briefing.replace("\r\n", "\n")
    secao = None
    for m in re.finditer(r"^##[ \t]*(.+)$", texto, re.M):
        if "NUMEROS NA TELA" in _limpa_titulo(m.group(1)):
            fim = re.search(r"^##[ \t]", texto[m.end():], re.M)
            secao = texto[m.end():m.end() + fim.start()] if fim else texto[m.end():]
            break
    if secao is None:
        partes = re.split(r"^=+[ \t]*\n[ \t]*(?:\d+\.[ \t]*)?([^\n]+?)[ \t]*\n=+[ \t]*$", texto, flags=re.M)
        for tit, corpo in zip(partes[1::2], partes[2::2]):
            if "NUMEROS NA TELA" in _limpa_titulo(tit):
                secao = corpo
                break
    if not secao:
        return []
    return [re.sub(r"^[-*•]\s*", "", x.strip()) for x in secao.splitlines() if x.strip()]


def _limpa_titulo(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()


def avisos_numeros(planos: list[dict], palavras: list[dict], liberados: list[str]) -> list[str]:
    """Número na tela que a fala não diz e o Felipe não liberou (NÚMEROS NA TELA do briefing ou pedido dele)."""
    ok = numeros_do_texto(" ".join(w["t"] for w in palavras))
    for x in liberados:
        ok |= numeros_do_texto(x)
    avisos = []
    for n, p in enumerate(planos):
        fora = sorted({b for txt in textos_na_tela(p) for b in _NUM.findall(txt) if _chave_num(b) not in ok})
        if fora:
            avisos.append(f"número fora da fala (cena {n + 1}): {', '.join(fora)}. Se foi pedido do Felipe, ponha na seção "
                          "NÚMEROS NA TELA do briefing (ou peça no card) para liberar")
    return avisos

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
                              ("medidor", (("em", "i"),)), ("riscado", (("em", "i"),)),
                              ("titulo", (("em", "i"),)), ("grafico", (("em", "i"), ("ate_em", "i1")))):
            if isinstance(p.get(campo), dict):
                for de, para in chaves:
                    j = localizar(palavras, p[campo].pop(de, None), i)
                    if j is not None:
                        p[campo][para] = j
        if isinstance(p.get("grafico"), dict) and isinstance(p["grafico"].get("itens_em"), list):  # cada etapa na sua palavra
            idx = [localizar(palavras, x, i) for x in p["grafico"].pop("itens_em")]
            if all(j is not None for j in idx):
                p["grafico"]["itens_i"] = idx
        for campo in ("palavras", "marcos", "horas"):  # itens de gráfico que entram cada um na sua palavra
            for item in (p["grafico"].get(campo) or []) if isinstance(p.get("grafico"), dict) else []:
                j = localizar(palavras, item.pop("em", None), i)
                if j is not None:
                    item["i"] = j
        if isinstance(p.get("riscado"), dict) and "i" not in p["riscado"]:
            p["riscado"]["i"] = i
        if isinstance(p.get("som"), dict) and (p["som"].get("o_que") or p["som"].get("arquivo")):  # o "em" fica: a revisão volta a localizar
            j = localizar(palavras, p["som"].get("em"), i)
            p["som"]["i"] = j if j is not None else i
        else:
            p.pop("som", None)
        for s in p.get("sons") or []:  # mais de um efeito no plano, cada um na sua palavra
            j = localizar(palavras, s.get("em"), i)
            s["i"] = j if j is not None else i
        planos.append(p)
    if not planos:
        raise RuntimeError("o diretor não devolveu nenhum plano válido")
    planos[0]["i"] = 0
    return planos, avisos


FORMATO = ("Responda SOMENTE com JSON {\"chaves\": [um termo-chave por frase, como aparece na fala], \"planos\": [{\"em\", "
           "\"set\", \"clima\", \"codigo\" (ou \"tipo\" + parâmetros), \"marcas\"?, \"som\"?, \"legenda\"?, sobreposições?}], "
           "\"legenda\"?: estilo da legenda do vídeo inteiro}. O código é JavaScript puro dentro de uma string JSON.")


def _pedir(prompt: str, palavras: list[dict], etiqueta: str) -> dict:
    r = chamar_json(prompt, sistema(), modelo="opus", etiqueta=etiqueta)
    brutos = r["planos"] if isinstance(r, dict) else r
    planos, avisos = resolver(brutos, palavras)
    chaves = [c for c in (r.get("chaves") if isinstance(r, dict) else None) or [] if isinstance(c, str)][:20]
    d = {"planos": planos, "avisos": avisos, "chaves": chaves, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if isinstance(r, dict) and isinstance(r.get("legenda"), dict):
        d["legenda"] = r["legenda"]
    return d


def _briefing(texto: str) -> str:
    if not texto:
        return ""
    return ("BRIEFING DO VÍDEO (pedidos de quem fez o roteiro: siga; trecho que não existe mais no roteiro = ignore; cena "
            "marcada MODELO A CRIAR = use o modelo da API se já existir, senão a alternativa indicada; nunca contrarie o "
            f"EVITAR):\n{texto}\n\n")  # NÚMEROS NA TELA: explicado no sistema() do vertical (o horizontal também usa este texto)


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


def _props(direcao: dict, palavras: list[dict], logos: dict[str, str] | None = None) -> dict:
    d = {"palavras": [{"t": p["t"], "i": p["i"], "f": p["f"]} for p in palavras], "planos": direcao["planos"],
         "audio": "voz.wav", "chaves": direcao.get("chaves", [])}
    if logos:
        d["logos"] = logos  # {chave: caminho na pasta pública}: o Vertical.tsx carrega antes de desenhar
    if isinstance(direcao.get("legenda"), dict):
        d["legenda"] = direcao["legenda"]  # estilo da legenda do vídeo inteiro (o plano pode trocar com o próprio "legenda")
    return d


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
        alvos.append((n, p, int((ini + (fim - ini) * 0.6) * FPS)))
    props = trabalho / "vertical_props_conferencia.json"
    props.write_text(json.dumps(_props(direcao, palavras, copiar_logos(trabalho, planos)), ensure_ascii=False), encoding="utf-8")
    pedido = trabalho / "quadros_pedido.json"
    pedido.write_text(json.dumps({"composicao": CFG.get("composicao", "Vertical"), "props": str(props), "publicDir": str(trabalho),
                                  "escala": 0.25, "quadros": [{"q": q, "saida": str(pasta / f"{n:03d}.jpg")} for n, _, q in alvos]}),
                      encoding="utf-8")
    r = subprocess.run(["node", str(BIBLIOTECA / "quadros.mjs"), str(pedido)], cwd=projeto, capture_output=True, text=True, encoding="utf-8",
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
          "nomeia, número na placa que não bate com a cena? Gráfico informativo cobrindo o assunto, tela poluída (dois "
          "gráficos ou gráfico + placa), gráfico que não reforça a fala, carro na tela quando a fala é sobre o volante? "
          "(colisão se corrige com número na posição, nunca escondendo "
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
    return checar_regras(direcao, palavras, briefing, trabalho.parent if trabalho is not None else None)


_AVISOS_REGRAS = ("número fora da fala", "falta o logo", "som não encontrado")


def checar_regras(direcao: dict, palavras: list[dict], briefing: str = "", projeto: Path | None = None) -> dict:
    """Checagens que não pedem nada ao Claude (só avisos no card): números fora da fala (menos os liberados pelo Felipe),
    logos sem arquivo e sons por arquivo que não existem. Refeitas a cada conferência (os avisos antigos saem)."""
    planos = direcao["planos"]
    liberados = numeros_liberados(briefing) + list(direcao.get("numeros_liberados") or [])
    novos = avisos_numeros(planos, palavras, liberados) + avisos_logos(planos) + avisos_sons(planos, projeto)
    direcao["avisos"] = [a for a in direcao.get("avisos", []) if not a.startswith(_AVISOS_REGRAS)] + novos
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


def liberar_dos_pedidos(antes: list[str] | None, pedidos: list[dict]) -> list[str]:
    """Os números que o Felipe escreveu nos pedidos (só eles, exatos) entram na lista de liberados do vídeo."""
    saida = list(antes or [])
    for p in pedidos:
        texto = re.sub(r"\b(?:cenas?|planos?)\s+\d+", "", str(p.get("texto", "")), flags=re.I)  # "cena 5" não é número de tela
        for n in _NUM.findall(texto):
            if n not in saida:
                saida.append(n)
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
    # links e "pesquise" nos pedidos: a ponte baixa as imagens e pesquisa antes (o diretor roda sem internet)
    falas = {p["id"]: p.get("fala") or p.get("em", "") for p in direcao["planos"]}
    pedidos_orig = pedidos
    pedidos, imagens, notas = anexos.preparar(pedidos, falas, (trabalho.parent / "direcao") if trabalho else Path(tempfile.gettempdir()),
                                              briefing, aviso)
    linhas = [f"- plano {numero[p['plano']]} (id {p['plano']}): {p['texto']}" if p.get("plano") in numero else f"- geral: {p['texto']}"
              for p in pedidos]
    claude = para_o_claude(direcao["planos"])
    # pedido geral pode mexer em qualquer cena: aí todas vão completas (mas só as alteradas voltam)
    atuais = [q if geral or q["id"] in alvo else _resumo(q) for q in claude]
    prompt = (_docs() + f"ROTEIRO:\n{frases(palavras)}\n\n{_briefing(briefing)}DIREÇÃO ATUAL (na ordem; "
              + ("todos os planos completos" if geral else "os planos pedidos vêm completos, os outros resumidos")
              + f"):\n{json.dumps(atuais, ensure_ascii=False)}\n\nPEDIDOS DO FELIPE:\n{chr(10).join(linhas)}\n\n"
              + (f"IMAGENS ANEXAS: as {len(imagens)} imagem(ns) enviada(s) junto são as que o Felipe linkou, na ordem "
                 "([imagem anexa 1], [imagem anexa 2]...). São a referência fiel: siga a forma delas, não a memória.\n\n"
                 if imagens else "")
              + "Aplique os pedidos. Devolva SÓ os planos que mudam, completos, com o mesmo id (plano sem mudança NÃO volta). "
              "Plano novo (dividir uma cena) vem sem id, com \"depois_de\": id do plano que vem antes dele. Plano que sai: "
              "id em \"remover\". Responda SOMENTE JSON {\"planos\": [{\"id\", \"em\", \"set\", \"clima\", \"codigo\" (ou "
              "\"tipo\" + parâmetros), \"marcas\"?, \"som\"?, sobreposições?}], \"remover\": [ids]}. O código é JavaScript puro dentro "
              "de uma string JSON. Pedido que não se resolve com cena (música de fundo, voz, texto falado) não muda plano: "
              "explique em \"nao_da\": [\"motivo curto\"]. Pedido do Felipe vale mais que as regras destes documentos "
              "(número fora da fala, teto de efeitos, estilo): FAÇA, nunca recuse por regra; um número/texto que ele "
              "pede na tela fica liberado na checagem. NUNCA ignore um pedido em silêncio: cada pedido que você não "
              "fizer por inteiro por falta REAL de capacidade (falta modelo na API, falta o arquivo do logo ou do som, "
              "falta informação) vai em \"nao_feitos\": [{\"id\": id do plano ou \"geral\", \"motivo\": \"curto: o que "
              "faltou; se for arquivo, o caminho exato que o Felipe precisa colocar\", \"capacidade\": true quando o que "
              "falta é CAPACIDADE NOVA no motor (função/modelo/efeito que a API não tem, ou julgamento visual que só "
              "olhando os quadros resolve) — esse pedido vai para o orquestrador, que edita a biblioteca; false quando "
              "falta só um arquivo ou uma informação do Felipe}]. Estilo da legenda do vídeo "
              "inteiro: \"legenda\": {...} na raiz da resposta. Fato marcado PESQUISADO NA INTERNET vale como confirmado.")
    aviso("o diretor aplica os seus pedidos")
    r = chamar_json(prompt, sistema(), modelo="opus", etiqueta="vertical-revisao", imagens=imagens)
    novos = [n for n in (r.get("planos") if isinstance(r, dict) else r) or [] if isinstance(n, dict)]
    remover = set(r.get("remover") or []) if isinstance(r, dict) else set()
    por_id = {n["id"]: n for n in novos if n.get("id") in numero}
    depois: dict[str, list[dict]] = {}
    for n in novos:
        if n.get("id") not in numero:
            depois.setdefault(n.get("depois_de") if n.get("depois_de") in numero else ids[-1], []).append(
                {k: v for k, v in n.items() if k not in ("id", "depois_de")})
    brutos = []
    perdidos: dict[int, list[str]] = {}  # campos que o diretor deixou de devolver e foram mantidos
    for q in claude:
        if q["id"] not in remover:
            n = por_id.get(q["id"])
            if n:  # o plano volta completo; trecho e cena que faltarem ficam os de antes
                n = {k: v for k, v in n.items() if k != "depois_de"}
                n.setdefault("em", q["em"])
                if not n.get("codigo") and not n.get("tipo"):
                    n.update({k: q[k] for k in ("codigo", "tipo", "set") if k in q})
                if q["id"] not in alvo:
                    # plano que o Felipe NÃO pediu cena a cena (só pedido geral): o que o diretor não devolveu continua como estava
                    # (placas, marcas, som, gráfico, legenda...). Antes o campo omitido sumia em silêncio (a placa "48/62" da cena 19
                    # existia nas duas versões anteriores e foi apagada pela revisão de um pedido geral, 2026-11-16).
                    for k, v in q.items():
                        if k not in n and k not in ("depois_de",):
                            n[k] = v
                            perdidos.setdefault(numero[q["id"]], []).append(k)
            brutos.append(n or q)
        brutos += depois.get(q["id"], [])
    planos, avisos = resolver(brutos, palavras)
    pesados = []   # falta REAL de capacidade (`capacidade: true`): o pedido vai para o orquestrador (pedidos_pesados.py)
    for nf in (r.get("nao_feitos") or []) if isinstance(r, dict) else []:
        if isinstance(nf, dict) and nf.get("motivo"):
            onde = f"cena {numero[nf['id']]}" if nf.get("id") in numero else "pedido geral"
            casados = [p for p in pedidos_orig if (p.get("plano") == nf.get("id") if nf.get("id") in numero
                                                   else p.get("plano") not in numero)] if nf.get("capacidade") is True else []
            if casados:
                pesados += [{"pedido": p, "motivo": str(nf["motivo"])} for p in casados
                            if not any(x["pedido"] is p for x in pesados)]
            else:
                avisos.append(f"pedido não feito ({onde}): {nf['motivo']}")
    avisos += notas
    nova = {**direcao, "planos": planos, "avisos": avisos, "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}
    # número escrito pelo Felipe num pedido (inclusive a resposta a um "pedido não feito") fica liberado na tela
    nova["numeros_liberados"] = liberar_dos_pedidos(direcao.get("numeros_liberados"), pedidos_orig)
    if isinstance(r, dict) and isinstance(r.get("legenda"), dict):
        nova["legenda"] = r["legenda"]
    antes = {p["id"]: json.dumps(p, sort_keys=True, ensure_ascii=False) for p in direcao["planos"]}
    mudou = {p["id"] for p in nova["planos"] if antes.get(p["id"]) != json.dumps(p, sort_keys=True, ensure_ascii=False)}
    mudou |= set(antes) - {p["id"] for p in nova["planos"]}  # plano removido também é mudança
    if trabalho is not None:  # cada rodada fica guardada: o que foi pedido e o que o diretor devolveu
        pasta = trabalho.parent / "direcao" / "revisoes"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps({"pedidos": pedidos_orig, "enviados": pedidos, "resposta": r, "mudou": sorted(mudou)}, ensure_ascii=False, indent=1), encoding="utf-8")
    if not mudou:
        nao_da = [str(x) for x in (r.get("nao_da") or []) if x] if isinstance(r, dict) else []
        motivo = "; ".join(nao_da + [a for a in avisos if a.startswith("pedido não feito")] + notas
                           + [f"enviado ao orquestrador: {x['motivo']}" for x in pesados])
        return {**direcao, "sem_mudanca": motivo or "o diretor não mudou nenhum plano", "pesados": pesados}
    aviso(f"o diretor mudou {len(mudou)} cena(s)")
    return {**conferir(nova, palavras, briefing, trabalho if mudou else None, aviso, mudou), "pesados": pesados}

# ------------------------------------------------------------------------------------------------ render
BIBLIOTECA = RAIZ / CFG.get("biblioteca", "F1/comum/remotion")  # modelos 3D, kit e scripts de render compartilhados pelos formatos do canal
FPS = int(CFG.get("fps", 60))  # quadros por segundo do vertical (canal.toml [vertical] fps; igual ao Root.tsx). Tempos das cenas em segundos


def _fonte_remotion(projeto: Path) -> str:
    """Impressão do código que desenha as cenas: mudou um modelo = todos os blocos são refeitos."""
    h = hashlib.sha1()
    for arq in sorted([*(projeto / "src").rglob("*"), *BIBLIOTECA.rglob("*"), RAIZ / "package.json"]):
        if arq.is_file() and arq.name != Path(ARQ_CONFERIR).name and "node_modules" not in arq.parts:
            h.update(arq.relative_to(RAIZ).as_posix().encode())
            h.update(arq.read_bytes())
    return h.hexdigest()


def _corte(pid: str) -> bool:
    """O bloco termina depois deste plano? Decidido pelo id (hexadecimal; id escrito à mão também vale)."""
    try:
        return int(pid[:6], 16) % 3 == 0
    except ValueError:
        return int(hashlib.sha1(pid.encode()).hexdigest()[:6], 16) % 3 == 0


def blocos(direcao: dict, palavras: list[dict], fonte: str = "", fps: int = FPS) -> list[dict]:
    """Planos agrupados em blocos de ~3 planos (corte decidido pelo id do plano, não pela posição: inserir ou tirar um
    plano não muda os blocos dos outros). Cada bloco = intervalo de quadros + impressão do que aparece nele."""
    planos = direcao["planos"]
    total = math.ceil((palavras[-1]["f"] + 0.35) * fps)
    q = [0] + [min(total, math.ceil(palavras[p["i"]]["i"] * fps - 1e-6)) for p in planos[1:]] + [total]
    extra = [direcao["legenda"]] if direcao.get("legenda") else []  # sem estilo de legenda, a impressão fica a de antes
    comum = hashlib.sha1(json.dumps([[w["t"], w["i"], w["f"]] for w in palavras] + [direcao.get("chaves", []), fonte] + extra,
                                    ensure_ascii=False).encode()).hexdigest()
    saida, atual = [], []
    for n, p in enumerate(planos):
        atual.append(n)
        if _corte(p["id"]) or len(atual) >= 5 or n == len(planos) - 1:
            ini, fim = q[atual[0]], q[n + 1] - 1
            if fim >= ini:
                # efeito sonoro não entra: é só áudio, não muda a imagem do bloco
                sem_som = [{c: v for c, v in planos[k].items() if c not in ("som", "sons")} for k in atual]
                if n + 1 < len(planos) and planos[n + 1].get("entrada"):  # horizontal: a transição da próxima cena começa neste bloco
                    sem_som.append({"proxima_entrada": planos[n + 1]["entrada"]})
                chave = json.dumps({"planos": sem_som, "q": [ini, fim], "fps": fps, "comum": comum}, sort_keys=True,
                                   ensure_ascii=False)
                saida.append({"inicio": ini, "fim": fim, "planos": [planos[k]["id"] for k in atual],
                              "impressao": hashlib.sha1(chave.encode()).hexdigest()[:16]})
            atual = []
    return saida


SOM_INTERVALO = 0.5  # segundos entre efeitos: só uma lista falada curta chega perto disso
SOM_POR_SEGUNDOS = 12.0  # teto: até 15 efeitos em 137 s ainda foi "goteira" (Felipe, 2026-11-04); ~1 a cada 12 s é o máximo
SOM_DURACAO = {"pop": 0.3, "clique": 0.25, "alerta": 0.8, "seletor": 0.7, "radio": 0.9, "whoosh": 1.2}  # segundos que tocam de cada efeito


def _toques(arquivo: str) -> list[float]:
    """Instantes (s) em que o som "bate": vários arquivos do catálogo repetem o toque, o que soa como goteira."""
    import numpy as np
    import soundfile as sf

    a, sr = sf.read(arquivo, always_2d=True)
    a = a.mean(1)
    h = max(1, sr // 100)
    db = 20 * np.log10(np.array([np.sqrt(np.mean(a[i:i + h] ** 2)) for i in range(0, max(1, len(a) - h), h)]) + 1e-6)
    piso = db.max() - 24
    toques: list[float] = []
    for i in range(len(db)):
        antes = db[max(0, i - 3):i].max() if i else -120.0
        if db[i] > piso and db[i] - antes > 8 and (not toques or i / 100 - toques[-1] > 0.08):
            toques.append(i / 100)
    return toques


def _na_fala(trabalho: Path) -> callable:
    """Devolve a função que cola um instante no começo real da palavra na voz (a tabela de tempos pode vir um pouco adiantada)."""
    import numpy as np
    import soundfile as sf

    v, sr = sf.read(trabalho / "voz.wav", always_2d=True)
    v = v.mean(1)
    h = sr // 100
    db = 20 * np.log10(np.array([np.sqrt(np.mean(v[i:i + h] ** 2)) for i in range(0, len(v) - h, h)]) + 1e-6)

    def colar(t: float) -> float:
        i0, i1 = max(0, int(t * 100)), min(len(db), int((t + 0.35) * 100))  # já há fala em t = fica em t; tabela adiantada = anda até a fala
        for i in range(i0, i1):
            if db[i] > -38:
                return round(i / 100, 3)
        return t

    return colar
SOM_VOLUME = {"clique": 0.22, "seletor": 0.22, "radio": 0.26, "whoosh": 0.24, "pop": 0.24, "alerta": 0.22}


EXT_SOM = (".wav", ".mp3", ".ogg", ".flac", ".m4a")
SOM_ARQ_VOLUME = 0.26  # padrão do som por arquivo (mesma faixa dos do catálogo, ~15 dB abaixo da voz)
SOM_ARQ_MAX = 6.0  # segundos: igual ao corte do catálogo (sfx.MAX_SEG)


def pastas_de_som(projeto: Path | None = None) -> list[Path]:
    """Onde um `arquivo` relativo é procurado, na ordem: dados/comum/, a pasta do projeto do vídeo, a raiz do repositório
    e as pastas liberadas (dados/comum/freesound_cache, F1/horizontal/kit/sfx/banco e o catálogo dados/comum/sfx)."""
    pastas = [DADOS_COMUM]
    if projeto is not None:
        pastas += [projeto, projeto / "trabalho"]
    return pastas + [RAIZ, DADOS_COMUM / "freesound_cache", RAIZ / "F1" / "horizontal" / "kit" / "sfx" / "banco", DADOS_COMUM / "sfx"]


def achar_som(nome: str, projeto: Path | None = None) -> Path:
    """Caminho absoluto, ou relativo a uma das pastas_de_som. Erro com a lista do que foi procurado."""
    p = Path(str(nome).strip().replace("\\", "/"))
    if p.suffix.lower() not in EXT_SOM:
        raise FileNotFoundError(f"som não encontrado: \"{nome}\" não é áudio ({', '.join(EXT_SOM)})")
    candidatos = [p] if p.is_absolute() else [d / p for d in pastas_de_som(projeto)]
    for c in candidatos:
        if c.is_file():
            return c.resolve()
    onde = str(p) if p.is_absolute() else ", ".join(str(d) for d in pastas_de_som(projeto))
    raise FileNotFoundError(f"som não encontrado: \"{nome}\" (procurado em {onde})")


def avisos_sons(planos: list[dict], projeto: Path | None = None) -> list[str]:
    avisos = []
    for n, p in enumerate(planos):
        for s in ([p["som"]] if isinstance(p.get("som"), dict) else []) + [x for x in p.get("sons") or [] if isinstance(x, dict)]:
            if s.get("arquivo"):
                try:
                    achar_som(s["arquivo"], projeto)
                except FileNotFoundError as e:
                    avisos.append(f"{e} (cena {n + 1})")
    return avisos


def _normalizar_som(origem: Path, destino: Path) -> float:
    """Como o catálogo (sfx._preparar): mono 44,1 kHz, sem silêncio no início, até 6 s com fade, pico em -3 dBFS.
    Devolve a duração (s)."""
    import numpy as np
    import soundfile as sf

    sr = 44100
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(origem), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"não consegui ler o som {origem}: {r.stderr.decode(errors='replace')[-200:]}")
    a = np.frombuffer(r.stdout, dtype=np.float32).copy()
    if not len(a) or np.abs(a).max() == 0:
        raise RuntimeError(f"som vazio ou mudo: {origem}")
    env = np.abs(a)
    limiar = env.max() * 0.03
    ini = int(np.argmax(env > limiar))
    a = a[max(0, ini - int(0.01 * sr)):]
    fim_util = len(a) - int(np.argmax(np.abs(a[::-1]) > limiar))
    a = a[:max(1, fim_util + int(0.15 * sr))]
    if len(a) > SOM_ARQ_MAX * sr:
        a = a[:int(SOM_ARQ_MAX * sr)]
        n = int(0.6 * sr)
        a[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
    a = (a / np.abs(a).max() * 10 ** (-3 / 20)).astype(np.float32)
    destino.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(destino), a, sr, subtype="PCM_16")
    return len(a) / sr


def som_de_arquivo(s: dict, trabalho: Path) -> dict:
    """Pedido {"arquivo", "volume"?, "duracao"?} → som pronto para a mixagem (cópia normalizada em trabalho/sons_arquivo)."""
    origem = achar_som(s["arquivo"], trabalho.parent)
    h = hashlib.sha1(f"{origem}|{origem.stat().st_size}|{origem.stat().st_mtime_ns}".encode()).hexdigest()[:12]
    destino = trabalho / "sons_arquivo" / f"{origem.stem[:40]}_{h}.wav"
    if destino.exists():
        import soundfile as sf

        total = sf.info(str(destino)).duration
    else:
        total = _normalizar_som(origem, destino)
    try:
        vol = float(s.get("volume", SOM_ARQ_VOLUME))
    except (TypeError, ValueError):
        vol = SOM_ARQ_VOLUME
    try:
        dur = float(s.get("duracao") or total)
    except (TypeError, ValueError):
        dur = total
    return {"o_que": s.get("o_que") or origem.name, "arquivo": str(destino), "origem": str(origem), "categoria": "arquivo",
            "volume": round(max(0.02, min(1.0, vol)), 3), "inicio": 0.0, "duracao": round(max(0.05, min(total, dur)), 3)}


def sons(direcao: dict, palavras: list[dict], trabalho: Path) -> list[dict]:
    """Efeitos pedidos pelo diretor (`som` do plano) → arquivos do catálogo do canal (busca CLAP pela descrição).
    As regras valem aqui mesmo que o diretor exagere: intervalo mínimo, teto pela duração, sem repetir o mesmo som.
    A escolha fica guardada (mesmos pedidos = mesmos sons, sem carregar o CLAP de novo)."""
    pedidos = sorted(((palavras[min(s["i"], len(palavras) - 1)]["i"], s) for p in direcao["planos"]
                      for s in ([p["som"]] if isinstance(p.get("som"), dict) else []) + (p.get("sons") or [])
                      if isinstance(s, dict) and "i" in s and (s.get("o_que") or s.get("arquivo"))), key=lambda x: x[0])
    teto = max(1, int(palavras[-1]["f"] / SOM_POR_SEGUNDOS))
    # "obrigatorio": pedido explícito do Felipe (a palavra dele vale mais que a regra): passa por fora do intervalo e do teto,
    # que continuam valendo para os outros efeitos do vídeo
    fixos = [(round(t, 3), s) for t, s in pedidos if s.get("obrigatorio")]
    aceitos, ultimo = [], -1e9
    for t, s in pedidos:
        if not s.get("obrigatorio") and t - ultimo >= SOM_INTERVALO:
            aceitos.append((round(t, 3), s))
            ultimo = t
    if len(aceitos) > teto:  # corta por igual ao longo do vídeo: cortar só o excesso do fim deixaria o final sem efeito
        aceitos = [aceitos[round(k * (len(aceitos) - 1) / max(1, teto - 1))] for k in range(teto)]
    aceitos = sorted(aceitos + fixos, key=lambda x: (x[0], str(x[1].get("o_que") or x[1].get("arquivo"))))
    if not aceitos:
        return []
    guardado = trabalho / "sons_vertical.json"
    # som do catálogo entra na chave como antes ([t, o_que]: a escolha guardada dos vídeos antigos continua valendo)
    chave = hashlib.sha1(json.dumps(["um-toque-2", [
        (t, s["o_que"]) if not s.get("arquivo") else (t, s.get("o_que"), {k: s.get(k) for k in ("arquivo", "volume", "duracao")})
        for t, s in aceitos]], ensure_ascii=False).encode()).hexdigest()
    if guardado.exists():
        g = json.loads(guardado.read_text(encoding="utf-8"))
        if g.get("chave") == chave and all(Path(s["arquivo"]).exists() for s in g["sons"]):
            return g["sons"]
    saida = []
    colar = _na_fala(trabalho)
    catalogo_pedidos = [(t, s["o_que"]) for t, s in aceitos if not s.get("arquivo")]
    faltou = False
    for t, s in aceitos:  # som por arquivo: direto do arquivo, sem busca
        if s.get("arquivo"):
            try:
                saida.append({"t": colar(t), **som_de_arquivo(s, trabalho)})
            except (FileNotFoundError, RuntimeError) as e:  # nunca quebra o render: o aviso já saiu na conferência
                print("som por arquivo ignorado:", e)
                faltou = True
    busca = None
    if catalogo_pedidos:
        try:
            import sys

            sys.path.insert(0, str(RAIZ / "tools" / "audio"))
            from sfx import PASTA as PASTA_SFX, Busca

            busca = Busca()
        except Exception as e:  # sem catálogo/CLAP: o vídeo sai só com a voz, nunca quebra o render
            print("efeitos sonoros indisponíveis:", e)
            catalogo_pedidos = []
    usados: set[int] = set()
    for t, o_que in catalogo_pedidos:
        achados = busca.buscar(o_que, 8, evitar=usados)
        if not achados:
            continue
        # o melhor que ainda não tocou neste vídeo, mas da mesma categoria: repetir um pop é melhor que trocá-lo por um rádio
        melhor = busca.info[achados[0][0]]["categoria"]
        iguais = [s for s, _ in achados if busca.info[s]["categoria"] == melhor]
        toques = {s: _toques(str(PASTA_SFX / busca.info[s]["arquivo"])) for s in iguais}
        # prefere um som de um toque só; entre eles, um que ainda não tocou no vídeo
        sid = next((s for s in iguais if len(toques[s]) == 1 and s not in usados), None) or next(
            (s for s in iguais if len(toques[s]) == 1), None) or iguais[0]
        usados.add(sid)
        cat = busca.info[sid]["categoria"]
        tq = toques[sid]
        dur = SOM_DURACAO.get(cat, 1.0)
        if len(tq) > 1:  # corta antes do segundo toque
            dur = min(dur, tq[1] - tq[0] - 0.02)
        saida.append({"t": colar(t), "o_que": o_que, "arquivo": str(PASTA_SFX / busca.info[sid]["arquivo"]), "categoria": cat,
                      "volume": SOM_VOLUME.get(cat, 0.26), "inicio": max(0.0, (tq[0] if tq else 0.0) - 0.005), "duracao": round(dur, 3)})
    if busca is not None:
        busca.liberar()
    saida.sort(key=lambda s: s["t"])
    if faltou:  # não guarda: quando o Felipe puser o arquivo, o som entra no próximo render
        guardado.unlink(missing_ok=True)
        return saida
    guardado.write_text(json.dumps({"chave": chave, "sons": saida}, ensure_ascii=False, indent=1), encoding="utf-8")
    return saida


MUSICA_DB = -14.0  # volume padrão sobre a trilha já nivelada em -20 LUFS (~11 dB abaixo da voz); o painel ajusta por vídeo (musica.json "volume")
EXT_AUDIO = (".mp3", ".wav", ".m4a", ".ogg", ".flac")


def config_musica(projeto: Path) -> dict:
    arq = projeto / "direcao" / "musica.json"
    # utf-8-sig: um musica.json salvo por outro programa com BOM não pode derrubar a página
    return json.loads(arq.read_text(encoding="utf-8-sig")) if arq.exists() else {"ligada": True, "descricao": ""}  # trilha baixa é o padrão do vertical (Felipe, 2026-11-04)


def arquivo_musica(projeto: Path) -> Path | None:
    """A música que entra no vídeo: a do Felipe (qualquer áudio em <projeto>/musica/) tem prioridade; senão a gerada."""
    cfg = config_musica(projeto)
    if not cfg.get("ligada"):
        return None
    pasta = projeto / "musica"
    propria = sorted(p for p in pasta.glob("*") if p.suffix.lower() in EXT_AUDIO and not p.name.startswith("trilha_")) if pasta.exists() else []
    if propria:
        return propria[0]
    gerada = projeto / cfg["arquivo"] if cfg.get("arquivo") else None
    return gerada if gerada and gerada.exists() else None


def _com_audio(video: list[str], trabalho: Path, direcao: dict, palavras: list[dict], saida: Path, fps: int = FPS) -> None:
    """Vídeo (sem recomprimir) + áudio: voz, efeitos (2 quadros antes da palavra, ~15 dB abaixo da voz) e, se ligada,
    a música de fundo em laço, baixa e com ducking (abaixa sozinha enquanto alguém fala), entrando e saindo em fade."""
    total = math.ceil((palavras[-1]["f"] + 0.35) * fps) / fps
    efeitos = sons(direcao, palavras, trabalho)
    musica = arquivo_musica(trabalho.parent)
    entradas = [*video, "-i", str(trabalho / "voz.wav")]
    filtros = ["[1:a]aresample=48000,aformat=channel_layouts=stereo" + (",asplit=2[voz][vsc]" if musica else "[voz]")]
    rotulos = ["[voz]"]
    for j, s in enumerate(efeitos, start=2):
        entradas += ["-i", s["arquivo"]]
        ms = max(0, round(s["t"] * 1000))  # o toque bate no começo da palavra e o som acaba logo depois
        d = s.get("duracao", 1.0)
        filtros.append(f"[{j}:a]atrim=start={s.get('inicio', 0)}:duration={d},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                       f"afade=t=out:st={max(0, d - 0.06):.3f}:d=0.06,volume={s['volume']},adelay={ms}:all=1[s{j}]")
        rotulos.append(f"[s{j}]")
    if musica:
        j = len(efeitos) + 2
        entradas += ["-stream_loop", "-1", "-i", str(musica)]
        vol = float(config_musica(trabalho.parent).get("volume", MUSICA_DB))
        # trilha gerada: corta o chiado dos pratos (agudos acima de ~6 kHz, que no fone parecem interferência);
        # todas: nível por loudness (não por pico), para o controle de volume valer igual em qualquer música
        # (e o grave que celular e fone não reproduzem: sub abaixo de ~110 Hz sai, a melodia nos médios sobe um pouco)
        eq = "highpass=f=110,equalizer=f=1200:t=q:w=1:g=3,treble=g=-6:f=5000,lowpass=f=7500," if musica.name.startswith("trilha_") else ""
        filtros.append(f"[{j}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},{eq}loudnorm=I=-20:TP=-2:LRA=11,"
                       f"aresample=48000,volume={vol}dB,"
                       f"afade=t=in:d=1.5,afade=t=out:st={max(0, total - 2.5):.3f}:d=2.5[m0]")
        # ducking suave: abaixa ~4 a 6 dB enquanto há fala (antes era forte demais e só sobravam os pratos)
        filtros.append("[m0][vsc]sidechaincompress=threshold=0.06:ratio=2.5:attack=60:release=800[mus]")
        rotulos.append("[mus]")
    filtros.append(f"{''.join(rotulos)}amix=inputs={len(rotulos)}:duration=first:normalize=0,apad,atrim=0:{total:.3f}[audio]")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
                        "-map", "0:v", "-map", "[audio]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
                        "-movflags", "+faststart", str(saida)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not saida.exists():
        raise RuntimeError("mixagem do áudio falhou: " + r.stderr[-600:])


def remixar(trabalho: Path, direcao: dict, palavras: list[dict], base: Path, saida: Path, fps: int = FPS) -> None:
    """Só o áudio de novo (ex.: música ligada/trocada): a imagem do vídeo `base` é copiada, sem renderizar."""
    _com_audio(["-i", str(base)], trabalho, direcao, palavras, saida, fps)


def gerar_musica(projeto: Path, segundos: float, aviso=lambda m: None) -> Path | None:
    """Gera a trilha descrita em musica.json se ainda não houver uma para essa descrição (ou se o Felipe pôs a dele)."""
    cfg = config_musica(projeto)
    if not cfg.get("ligada"):
        return None
    pasta = projeto / "musica"
    if pasta.exists() and any(p.suffix.lower() in EXT_AUDIO and not p.name.startswith("trilha_") for p in pasta.glob("*")):
        return arquivo_musica(projeto)  # a do Felipe vale
    chave = hashlib.sha1(f"{cfg.get('descricao', '')}|{math.ceil(segundos)}".encode()).hexdigest()[:10]
    destino = pasta / f"trilha_{chave}.wav"
    if not destino.exists():
        import sys

        sys.path.insert(0, str(RAIZ / "tools" / "audio"))
        from trilha import gerar

        aviso("gerando a música de fundo")
        gerar(cfg.get("descricao") or "calm modern electronic, soft pads, light beat", segundos + 3, destino)
    cfg["arquivo"] = destino.relative_to(projeto).as_posix()
    (projeto / "direcao" / "musica.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def renderizar(trabalho: Path, direcao: dict, palavras: list[dict], saida: Path, progresso=None, composicao: str | None = None,
               props: dict | None = None, cache_nome: str = "blocos_vertical", concorrencia: int = 3, fps: int = FPS,
               projeto_remotion: str | None = None) -> float:
    """Render por blocos com cache (como no Runeterra): só os blocos com plano alterado são renderizados de novo; a
    voz entra no FFmpeg, sem recomprimir o vídeo. A pasta trabalho/ do vídeo (com voz.wav) é a pasta pública do Remotion."""
    projeto = RAIZ / (projeto_remotion or CFG.get("projeto", ""))
    cache = trabalho.parent / cache_nome  # fora de trabalho/: a pasta pública é copiada a cada render
    cache.mkdir(parents=True, exist_ok=True)
    arq_props = trabalho / ("vertical_props.json" if props is None else f"{cache_nome}_props.json")
    arq_props.write_text(json.dumps(_props(direcao, palavras, copiar_logos(trabalho, direcao["planos"])) if props is None else props,
                                    ensure_ascii=False), encoding="utf-8")
    # props entram na impressão dos blocos: no horizontal elas trazem dados que não estão nos planos (paleta, carro)
    lista = blocos(direcao, palavras, _fonte_remotion(projeto) + (_assinatura_logos(direcao["planos"]) if props is None else json.dumps(
        {k: v for k, v in props.items() if k != "cenas"}, sort_keys=True)), fps)
    faltam = [b for b in lista if not (cache / f"{b['impressao']}.mp4").exists()]
    inicio = time.time()
    if faltam:
        pedido = trabalho / "render_blocos_pedido.json"
        pedido.write_text(json.dumps({"composicao": composicao or CFG.get("composicao", "Vertical"), "props": str(arq_props),
                                      "publicDir": str(trabalho), "concorrencia": concorrencia, "blocos": [{"inicio": b["inicio"], "fim": b["fim"], "saida": str(cache / f"{b['impressao']}.mp4")}
                                                 for b in faltam]}), encoding="utf-8")
        a_fazer = sum(b["fim"] - b["inicio"] + 1 for b in faltam)
        feitos = [0] * len(faltam)
        proc = subprocess.Popen(["node", str(BIBLIOTECA / "render_blocos.mjs"), str(pedido)], cwd=projeto, stdout=subprocess.PIPE,
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
    _com_audio(["-f", "concat", "-safe", "0", "-i", str(juntar)], trabalho, direcao, palavras, saida, fps)
    # o cache guarda os blocos desta versão e os da anterior (para voltar atrás sem renderizar)
    usados = {b["impressao"] for b in lista}
    anterior = trabalho.parent / f"{cache_nome}.json"
    if anterior.exists():
        usados |= set(json.loads(anterior.read_text(encoding="utf-8")))
    for velho in cache.glob("*.mp4"):
        if velho.stem not in usados:
            velho.unlink(missing_ok=True)
    anterior.write_text(json.dumps(sorted(b["impressao"] for b in lista)), encoding="utf-8")
    return time.time() - inicio
