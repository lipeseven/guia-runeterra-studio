"""Peças comuns do diretor documental: caminhos, palavras (âncoras), JSON, hash e o registro dos kits.

Sem dependências fora da biblioteca padrão. Os caminhos de dados seguem a convenção dos kits: `F1/dados` é achado
subindo as pastas (funciona numa worktree dentro do repositório).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent            # F1/horizontal/diretor
HORIZONTAL = AQUI.parent                           # F1/horizontal
KIT = HORIZONTAL / "kit"
F1 = HORIZONTAL.parent
PROMPTS = AQUI / "prompts"
ESQUEMAS = AQUI / "esquemas"

FPS = 60
LARGURA, ALTURA = 1920, 1080
MOTORES = ("remotion", "hyperframes")
VERSAO = 1


def dados_f1() -> Path:
    """`F1/dados` (fora do Git). DIRETOR_F1_DADOS muda a pasta (testes)."""
    if os.environ.get("DIRETOR_F1_DADOS"):
        return Path(os.environ["DIRETOR_F1_DADOS"])
    for base in [F1, *F1.parents]:
        cand = base / "dados" if base.name == "F1" else base / "F1" / "dados"
        if cand.is_dir():
            return cand
    return F1 / "dados"


def pasta_projeto(slug: str) -> Path:
    """Pasta do vídeo horizontal: F1/dados/projetos/<slug>/horizontal/."""
    return dados_f1() / "projetos" / slug / "horizontal"


# ---------------------------------------------------------------- JSON e hash
def ler_json(p: Path, padrao=None):
    p = Path(p)
    if not p.exists():
        return padrao
    return json.loads(p.read_text(encoding="utf-8"))


def gravar_json(p: Path, dados) -> Path:
    """Gravação atômica (arquivo temporário + replace): o painel nunca lê meio arquivo."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


def hash_dados(dados) -> str:
    """Hash estável do conteúdo (sem os campos de carimbo), 12 hex."""
    def limpo(x):
        if isinstance(x, dict):
            return {k: limpo(v) for k, v in sorted(x.items()) if k not in ("criado_em", "hash", "avisos")}
        if isinstance(x, list):
            return [limpo(v) for v in x]
        return x
    return hashlib.sha1(json.dumps(limpo(dados), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def hash_texto(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- palavras e âncoras
def limpa(t: str) -> str:
    """Forma de comparação de uma palavra (igual ao `tools/direcao/vertical.py`): minúscula, sem acento e pontuação."""
    t = unicodedata.normalize("NFD", str(t).lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def palavras_do_roteiro(roteiro: str) -> list[str]:
    return [w for w in roteiro.split() if limpa(w)]


def estimar_tempos(roteiro: str, ritmo: float = 2.6) -> list[dict]:
    """Tempos ESTIMADOS por palavra (sem narração gravada): `ritmo` palavras/s + pausa em ponto final.
    Servem só para dosar a SPEC antes da gravação; a narração medida substitui (a SPEC é presa às palavras)."""
    out, t = [], 0.0
    for w in palavras_do_roteiro(roteiro):
        d = max(0.18, 0.06 * len(limpa(w)) + 0.12) * 2.6 / ritmo
        out.append({"t": w, "i": round(t, 3), "f": round(t + d, 3)})
        t += d + (0.35 if re.search(r"[.!?]$", w) else 0.12 if w.endswith((",", ";", ":")) else 0.04)
    return out


def localizar(palavras: list[dict], trecho, apos: int = 0) -> int | None:
    """Índice da 1ª palavra do `trecho` no roteiro a partir de `apos` (mesma regra do vertical)."""
    if not trecho or not isinstance(trecho, str):
        return None
    alvo = [limpa(x) for x in trecho.split() if limpa(x)]
    lim = [limpa(p["t"]) for p in palavras]
    for k in range(max(0, apos), len(lim) - len(alvo) + 1):
        if alvo and lim[k:k + len(alvo)] == alvo:
            return k
    return None


def tamanho_trecho(trecho: str) -> int:
    return len([x for x in str(trecho).split() if limpa(x)])


def texto_de(palavras: list[dict], i0: int, i1: int) -> str:
    return " ".join(p["t"] for p in palavras[i0:i1])


def frases(palavras: list[dict]) -> str:
    """Roteiro em frases com o tempo (para o prompt), igual ao vertical."""
    linhas, atual, ini = [], [], 0.0
    for p in palavras:
        if not atual:
            ini = p["i"]
        atual.append(p["t"])
        # fim de frase mesmo com fecho depois do ponto ("cronômetro.**", "fim.”", "(sim.)")
        if re.search(r"[.!?:…][\"'”’»)\]*_]*$", p["t"]):
            linhas.append(f"[{ini:6.1f}s → {p['f']:6.1f}s] {' '.join(atual)}")
            atual = []
    if atual:   # roteiro que termina sem ponto: a última frase também tem fim
        linhas.append(f"[{ini:6.1f}s → {palavras[-1]['f']:6.1f}s] {' '.join(atual)}")
    return "\n".join(linhas)


def extrair_json(texto: str):
    """JSON da resposta do modelo (aceita cercas ```json e texto antes/depois)."""
    if not isinstance(texto, str):
        return texto
    m = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
    if m:
        texto = m.group(1)
    ini = min([i for i in (texto.find("{"), texto.find("[")) if i >= 0], default=-1)
    if ini < 0:
        raise ValueError("resposta sem JSON")
    return json.loads(texto[ini:texto.rfind("}" if texto[ini] == "{" else "]") + 1])


# ---------------------------------------------------------------- registro dos kits
# Fonte única do que a SPEC pode pedir a cada kit. `requer` = parâmetros obrigatórios; `tipos` = valores de `tipo`.
# `motores` = adaptadores que existem; `prefere` = motor indicado pela ARQUITETURA (aviso se outro for escolhido).
KITS: dict[str, dict] = {
    "gps": {"requer": ["sessao", "carros"], "motores": MOTORES, "prefere": "hyperframes",
            "faz": "carro(s) pelo GPS real do OpenF1 na pista 3D; carros = [{piloto, volta}], fator (acelerado), pista (.glb)"},
    "graficos": {"requer": ["tipo", "sessao", "a", "b"], "tipos": ["velocidade", "setores", "delta", "telemetria", "normalizado"],
                 "motores": MOTORES, "prefere": "remotion",
                 "faz": "comparação de duas voltas (a, b = {piloto, volta}); trecho [d0,d1] m; ritmo [{em, d}] = desenho ancorado na fala"},
    "imagens": {"requer": ["afirmacao"], "motores": MOTORES,
                "faz": "trecho real da corrida VALIDADO contra a afirmação (sessão/piloto/volta/evento)"},
    "anotacao": {"requer": ["tipo"], "tipos": ["oval", "seta", "sublinhado", "chave", "riscado", "nota", "corrigido"],
                 "motores": MOTORES, "faz": "anotação à mão ancorada em caixa estável"},
    "cartoes": {"requer": ["tipo"], "tipos": ["pessoa", "capitulo", "tag", "duelo"], "motores": MOTORES, "prefere": "remotion",
                "faz": "cartão de pessoa, de capítulo, tag com perninha ou duelo (dois números lado a lado na cor de cada "
                       "equipe: {titulo, sessao, unidade, destaque: 0|1, lados: [{piloto, valor, em}, {piloto, valor, em}]})"},
    "foco": {"requer": ["alvo"], "motores": MOTORES, "faz": "desfoca o que não é destaque"},
    "modelo3d": {"requer": ["arquivo"], "motores": MOTORES, "prefere": "hyperframes",
                 "faz": "modelo .glb de F1/dados/modelos3d (carro, pista, peça)"},
}
TRANSICOES = {"corte": 0, "fade": 18, "wipe": 24, "zoom": 30}   # quadros a 60 q/s (kit/transicoes QUADROS)


def categorias_sfx() -> dict:
    cat = ler_json(KIT / "sfx" / "catalogo.json", {}) or {}
    return cat.get("categorias", {})


def resumo_kits() -> str:
    """Texto do registro para os prompts."""
    linhas = []
    for nome, k in KITS.items():
        tipos = f" tipos: {', '.join(k['tipos'])}." if k.get("tipos") else ""
        pref = f" Motor indicado: {k['prefere']}." if k.get("prefere") else ""
        linhas.append(f"- `{nome}` (obrigatório: {', '.join(k['requer'])}).{tipos}{pref} {k['faz']}")
    linhas.append(f"- transição de entrada da cena: {', '.join(f'{t} ({q} q)' for t, q in TRANSICOES.items())}")
    linhas.append(f"- SFX (categoria + palavra-âncora): {', '.join(categorias_sfx()) or 'impacto, riser, whoosh, sino, alerta, pop, clique, tecla'}; "
                  "\"capitulo\" = riser + impacto")
    return "\n".join(linhas)


def preencher(modelo: str, **campos) -> str:
    """Preenche `{{campo}}` no texto do prompt (chaves simples ficam intactas: o JSON de exemplo não quebra)."""
    def troca(m):
        k = m.group(1)
        if k not in campos:
            raise KeyError(f"prompt pede {{{{{k}}}}} e não foi passado")
        return str(campos[k])
    return re.sub(r"\{\{(\w+)\}\}", troca, modelo)


def prompt_arquivo(nome: str) -> str:
    return (PROMPTS / nome).read_text(encoding="utf-8")


def cache_resposta(pasta: Path, etapa: str, prompt: str, resposta=None):
    """Cache por prompt (como o vertical): mesmo prompt = mesma resposta, sem gastar cota de novo.
    Com `resposta`, grava; sem, devolve a guardada ou None. Arquivo: <pasta>/cache/<etapa>_<hash do prompt>.json"""
    arq = Path(pasta) / "cache" / f"{etapa}_{hash_texto(prompt)}.json"
    if resposta is not None:
        gravar_json(arq, {"etapa": etapa, "prompt_hash": hash_texto(prompt), "resposta": resposta})
        return resposta
    d = ler_json(arq)
    return d["resposta"] if d else None


def entradas(pasta: Path) -> tuple[str, list[dict], str, str]:
    """(roteiro, palavras, tempos, briefing) da pasta do projeto horizontal.
    roteiro.txt = texto falado; palavras.json = [{t, i, f}] da narração medida (se faltar, tempos estimados);
    briefing.txt = instruções do roteirista (opcional, texto livre)."""
    pasta = Path(pasta)
    roteiro = (pasta / "roteiro.txt").read_text(encoding="utf-8")
    palavras = ler_json(pasta / "palavras.json")
    tempos = "medidos"
    if not palavras:
        palavras, tempos = estimar_tempos(roteiro), "estimados"
    b = pasta / "briefing.txt"
    return roteiro, palavras, tempos, b.read_text(encoding="utf-8") if b.exists() else ""


def observacoes(pasta: Path) -> str:
    """Observações gerais do Felipe sobre o vídeo (ditadas/digitadas no card do painel), já como texto de prompt.
    O painel copia para <pasta>/observacoes.txt (ver painel.sincronizar_entradas); sem arquivo = nenhuma."""
    arq = Path(pasta) / "observacoes.txt"
    texto = arq.read_text(encoding="utf-8").strip() if arq.exists() else ""
    return texto or "(nenhuma observação geral)"


def regras_de_direcao() -> str:
    p = F1 / "docs" / "regras_de_direcao.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""
