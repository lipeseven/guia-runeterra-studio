"""Etapa VERIFICAÇÃO (automática, antes de compor): a SPEC bate com o roteiro, com a história e com os ativos?

Três níveis no resultado:
- `erros`: a SPEC está errada e não segue (âncora que não existe, motor inválido, afirmação sem prova, número que a
  fala não diz, imagem não validada sem aviso, valor que não bate com o OpenF1...).
- `pendencias`: a SPEC está certa, mas falta produzir ativo (`ativos.py --produzir`).
- `avisos`: conferir com o olho (cena longa, motor fora do indicado, afirmação verificável sem cena...).
`status` = `reprovado` (há erro) | `pendente` (só pendências) | `aprovado`.

    python verificar.py <pasta_do_projeto>          # grava verificacao/verificacao.json; sai 1 se houver erro
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import etapas
from comum import (FPS, KITS, MOTORES, TRANSICOES, categorias_sfx, entradas, hash_dados, hash_texto, limpa, ler_json,
                   localizar)
from esquema import validar

DUR_MIN = 1.0       # s: cena mais curta que isso é piscada
DUR_LONGA = 12.0    # s: aviso (documentário aceita plano longo, mas confira se algo acontece)
DUR_MAX = 30.0      # s: erro
SFX_MIN_INTERVALO = 0.5   # s entre dois efeitos (igual ao vertical)
SFX_SEGUNDOS = 8.0        # aviso se a média for mais de 1 efeito a cada 8 s
TOL_TEMPO = 0.0005        # s (tempos oficiais têm 3 casas)
TOL_DIF = 0.0015          # s (diferença de dois tempos arredondados)
TIPOS_DADO = ("tempo_volta", "diferenca", "setor", "velocidade")
DISCLAIMER = re.compile(r"^\s*(acelerado|em tempo real|dados:|fonte:)", re.I)   # texto técnico de rodapé: número livre
AVISO_TELA = re.compile(r"ilustrativ|n[aã]o validad|n[aã]o confirmad", re.I)


class Relatorio:
    def __init__(self):
        self.erros, self.pendencias, self.avisos = [], [], []

    def e(self, codigo, msg, cena=None):
        self.erros.append({"codigo": codigo, "msg": msg, **({"cena": cena} if cena else {})})

    def p(self, codigo, msg, cena=None):
        self.pendencias.append({"codigo": codigo, "msg": msg, **({"cena": cena} if cena else {})})

    def a(self, codigo, msg, cena=None):
        self.avisos.append({"codigo": codigo, "msg": msg, **({"cena": cena} if cena else {})})

    def codigos(self) -> set[str]:
        return {x["codigo"] for x in self.erros}


def _bate(palavras, i, trecho) -> bool:
    alvo = [limpa(x) for x in str(trecho).split() if limpa(x)]
    return bool(alvo) and isinstance(i, int) and 0 <= i and [limpa(p["t"]) for p in palavras[i:i + len(alvo)]] == alvo


def _ancora(r: Relatorio, codigo, palavras, i, trecho, onde, cena=None, faixa=None):
    if not _bate(palavras, i, trecho):
        existe = localizar(palavras, trecho)
        r.e(codigo, f"{onde}: \"{trecho}\" " + ("não existe no roteiro" if existe is None
                                                 else f"não está na palavra {i} (está na {existe}: SPEC velha?)"), cena)
        return False
    if faixa and not (faixa[0] <= i < faixa[1]):
        r.e(codigo, f"{onde}: \"{trecho}\" (palavra {i}) fora da cena [{faixa[0]}, {faixa[1]})", cena)
        return False
    return True


def _norm(n: str) -> str:
    n = n.replace(",", ".")
    return n.rstrip("0").rstrip(".") if "." in n else n


def _segundos(m: str, s: str, casas: int) -> str:
    return _norm(f"{int(m) * 60 + float(s.replace(',', '.')):.{casas}f}")


# tempo em formato de cronômetro na tela ("1:16.514", "1:16,514") ou por extenso na fala / na tela
# ("1 minuto, 16 segundos e 514 milésimos", "1 min 16 s 514") = o mesmo número em segundos (76.514) das afirmações
CRONOMETRO = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2}(?:[.,]\d+)?)(?![\d:])")
POR_EXTENSO = re.compile(r"(\d{1,2})\s*(?:minutos?|min)\b[\s,]*(\d{1,2})\s*(?:segundos?|seg|s)\b[\s,]*(?:e\s+)?(\d{1,3})"
                         r"(?:\s*(?:milésimos?|milesimos?|ms)\b)?", re.I)
FRACAO = re.compile(r"(\d{1,3})\s+(milésimos?|milesimos?|centésimos?|centesimos?|décimos?|decimos?)\b", re.I)
CASAS_FRACAO = {"mil": 3, "cen": 2, "dec": 1, "déc": 1}
# cartão/título de capítulo ("PARTE 02", "Capítulo 3"): o número do capítulo é livre, como o rodapé técnico
CAPITULO = re.compile(r"\b(?:parte|cap[ií]tulo|cap\.|part|chapter|ato)\s*0*\d{1,2}\b", re.I)


def _numeros(t: str, tela: bool = False) -> set[str]:
    """Números de um texto, normalizados (vírgula = ponto, sem zeros à direita). Tempo de cronômetro ("1:16.514") e
    por extenso ("1 minuto, 16 segundos e 514 milésimos") entram em segundos (76.514); "9 milésimos" entra também como
    0.009. Na fala os números soltos continuam valendo (ela os diz); na tela (`tela=True`) o tempo conta como UM número."""
    saida: set[str] = set()

    def crono(m):
        dec = re.split(r"[.,]", m.group(2))
        saida.add(_segundos(m.group(1), m.group(2), len(dec[1]) if len(dec) > 1 else 0))
        return " "

    def extenso(m):
        saida.add(_segundos(m.group(1), f"{m.group(2)}.{m.group(3).zfill(3)}", 3))
        return " " if tela else m.group(0)

    def fracao(m):
        casas = CASAS_FRACAO[m.group(2).lower()[:3]]
        saida.add(_norm(f"{int(m.group(1)) / 10 ** casas:.{casas}f}"))
        return " " if tela else m.group(0)

    t = FRACAO.sub(fracao, POR_EXTENSO.sub(extenso, CRONOMETRO.sub(crono, t)))
    return saida | {_norm(n) for n in re.findall(r"\d+(?:[.,]\d+)?", t)}


def _historia(r: Relatorio, h: dict, palavras: list[dict]) -> None:
    for e in validar(h, "historia"):
        r.e("ESQUEMA_HISTORIA", e)
    for c in h.get("capitulos", []):
        _ancora(r, "ANCORA_CAPITULO", palavras, c.get("i"), c.get("em"), f"capítulo {c.get('id')}")
    for a in h.get("afirmacoes", []):
        _ancora(r, "ANCORA_AFIRMACAO", palavras, a.get("i"), a.get("em"), f"afirmação {a.get('id')}")


def _kit(r: Relatorio, c: dict, uso: dict, palavras, afs: dict) -> None:
    k, p, cid = uso.get("kit"), uso.get("params") or {}, c["id"]
    reg = KITS.get(k)
    if reg is None:
        r.e("KIT_DESCONHECIDO", f"kit '{k}' não existe", cid)
        return
    falta = [x for x in reg["requer"] if p.get(x) in (None, "", [])]
    if falta:
        r.e("KIT_PARAMETRO", f"{k}: falta {', '.join(falta)}", cid)
    if reg.get("tipos") and p.get("tipo") not in reg["tipos"]:
        r.e("KIT_PARAMETRO", f"{k}: tipo '{p.get('tipo')}' fora de {reg['tipos']}", cid)
    if c["motor"] not in reg["motores"]:
        r.e("MOTOR_KIT", f"{k} não tem adaptador para {c['motor']}", cid)
    elif reg.get("prefere") and reg["prefere"] != c["motor"] and k in ("gps", "modelo3d"):
        r.a("MOTOR_PREFERIDO", f"{k} em {c['motor']}: a ARQUITETURA indica {reg['prefere']} para pista/3D", cid)

    def ancoras(no, onde):
        if isinstance(no, dict):
            if "em" in no:
                _ancora(r, "ANCORA_PARAMETRO", palavras, no.get("i"), no.get("em"), f"{k}{onde}", cid, (c["i0"], c["i1"]))
            for kk, v in no.items():
                ancoras(v, f"{onde}.{kk}")
        elif isinstance(no, list):
            for n, v in enumerate(no):
                ancoras(v, f"{onde}[{n}]")
    ancoras(p, "")

    # afirmação ↔ dados pedidos ao kit
    citadas = [afs[x] for x in c["afirmacoes"] if x in afs and afs[x].get("verificavel")]
    if k == "imagens":
        a = afs.get(str(p.get("afirmacao")))
        if not a or not a.get("verificavel"):
            r.e("IMAGEM_SEM_AFIRMACAO", f"imagem precisa de afirmação verificável (sessão/carro/volta); veio '{p.get('afirmacao')}'", cid)
        elif a["id"] not in c["afirmacoes"]:
            r.e("IMAGEM_SEM_AFIRMACAO", f"imagem prova {a['id']}, que a cena não cita", cid)
    if k in ("graficos", "gps"):
        carros = ([p.get("a") or {}, p.get("b") or {}] if k == "graficos" else list(p.get("carros") or []))
        pedidos = {(x.get("piloto"), x.get("volta")) for x in carros}
        for a in citadas:
            if a.get("sessao") != p.get("sessao"):
                r.e("AFIRMACAO_DADOS", f"{a['id']} é da sessão {a.get('sessao')}, o {k} mostra a sessão {p.get('sessao')}", cid)
                continue
            for car in a.get("carros", []):
                if not any(car["piloto"] == pp and (car["volta"] == vv or "melhor" in (car["volta"], vv)) for pp, vv in pedidos):
                    r.e("AFIRMACAO_DADOS", f"{a['id']} fala do carro {car['piloto']} volta {car['volta']}, "
                                           f"o {k} mostra {sorted(pedidos, key=str)}", cid)


def _valor(r: Relatorio, a: dict, comparacoes: list[dict]) -> None:
    """Valor escrito na afirmação × tempos oficiais da comparação (OpenF1 /laps) dos mesmos carros."""
    if a.get("valor") is None or a.get("tipo") not in ("tempo_volta", "diferenca", "setor"):
        return
    pils = [str(c["piloto"]) for c in a.get("carros", [])]
    for d in comparacoes:
        if d.get("sessao") != a.get("sessao") or not all(p in d["pilotos"] for p in pils):
            continue
        tp = d["pilotos"]
        if a["tipo"] == "tempo_volta" and pils:
            # com 2 carros ("1:16.514 contra 1:16.523"), o valor é o tempo do 1º carro (uso real, 2026-11-14)
            ok, certo = abs(a["valor"] - tp[pils[0]]["tempo"]) <= TOL_TEMPO, tp[pils[0]]["tempo"]
        elif a["tipo"] == "diferenca" and len(pils) == 2:
            certo = round(abs(tp[pils[0]]["tempo"] - tp[pils[1]]["tempo"]), 3)
            ok = abs(abs(a["valor"]) - certo) <= TOL_DIF
        elif a["tipo"] == "setor" and a.get("setor"):
            s = a["setor"] - 1
            if len(pils) == 1:
                certo = tp[pils[0]]["setores"][s]
                ok = abs(a["valor"] - certo) <= TOL_TEMPO
            else:
                # 2 carros: o valor é a diferença no setor OU o tempo do 1º carro no setor ("30.008 contra 30.030";
                # uso real, 2026-11-14: o tempo absoluto era cobrado como diferença e reprovava a SPEC)
                certo = round(abs(tp[pils[0]]["setores"][s] - tp[pils[1]]["setores"][s]), 3)
                ok = abs(abs(a["valor"]) - certo) <= TOL_DIF or abs(a["valor"] - tp[pils[0]]["setores"][s]) <= TOL_TEMPO
                if not ok:
                    certo = f"{certo} (diferença) ou {tp[pils[0]]['setores'][s]} (tempo do 1º carro)"
        else:
            continue
        if not ok:
            r.e("VALOR_NAO_BATE", f"{a['id']} diz {a['valor']} {a.get('unidade', '')}, o OpenF1 dá {certo} ({d.get('fonte')})")
        return
    r.a("VALOR_NAO_CONFERIDO", f"{a['id']} ({a['valor']} {a.get('unidade', '')}): nenhuma comparação pronta com esses carros")


def verificar(spec: dict, historia: dict, palavras: list[dict], roteiro: str, ativos: dict | None = None) -> dict:
    r = Relatorio()
    _historia(r, historia, palavras)
    erros_esq = validar(spec, "spec")
    for e in erros_esq:
        r.e("ESQUEMA_SPEC", e)
    if erros_esq and not isinstance(spec.get("cenas"), list):
        return _fim(r, spec)
    if spec.get("roteiro_hash") != hash_texto(roteiro):
        r.e("ROTEIRO_MUDOU", "o roteiro mudou depois da SPEC: refaça a SPEC (ou confira as âncoras abaixo)")
    if spec.get("historia_hash") != hash_dados(historia):
        r.e("HISTORIA_MUDOU", "a história mudou depois da SPEC (spec.historia_hash ≠ história atual)")
    afs = {a["id"]: a for a in historia.get("afirmacoes", [])}
    caps = {c["id"]: c for c in historia.get("capitulos", [])}
    cenas = spec["cenas"]
    n = len(palavras)
    cats = set(categorias_sfx()) | {"capitulo"}
    sfx_t = []
    for k, c in enumerate(cenas):
        cid = c.get("id")
        # âncora e continuidade
        _ancora(r, "ANCORA_CENA", palavras, c.get("i0"), c.get("em"), "início da cena", cid)
        esperado_i1 = cenas[k + 1].get("i0") if k + 1 < len(cenas) else n
        if k == 0 and c.get("i0") != 0:
            r.e("ORDEM", "a 1ª cena não começa na 1ª palavra (fala sem imagem)", cid)
        if c.get("i1") != esperado_i1:
            r.e("ORDEM", f"i1={c.get('i1')} mas a próxima cena começa em {esperado_i1} (buraco ou sobreposição)", cid)
        if not isinstance(c.get("i0"), int) or not isinstance(c.get("i1"), int) or c["i1"] <= c["i0"]:
            r.e("ORDEM", f"cena vazia ou invertida (i0={c.get('i0')}, i1={c.get('i1')})", cid)
            continue
        # tempos derivados das palavras
        t0 = 0.0 if k == 0 else palavras[min(c["i0"], n - 1)]["i"]
        if abs(c["t0"] - t0) > 0.011:
            r.e("TEMPO", f"t0={c['t0']} mas a palavra {c['i0']} começa em {t0:.3f} s (tempos velhos? spec.retemporizar)", cid)
        if k + 1 < len(cenas) and abs(c["t1"] - cenas[k + 1]["t0"]) > 0.011:
            r.e("TEMPO", f"t1={c['t1']} ≠ t0 da próxima ({cenas[k + 1]['t0']})", cid)
        if k + 1 == len(cenas) and c["t1"] < palavras[-1]["f"]:
            r.e("TEMPO", f"a última cena acaba ({c['t1']}) antes da última palavra ({palavras[-1]['f']})", cid)
        dur = c["t1"] - c["t0"]
        if dur < DUR_MIN:
            r.e("DURACAO", f"{dur:.2f} s < {DUR_MIN} s", cid)
        elif dur > DUR_MAX:
            r.e("DURACAO", f"{dur:.1f} s > {DUR_MAX} s: divida a cena", cid)
        elif dur > DUR_LONGA:
            r.a("DURACAO_LONGA", f"{dur:.1f} s: confira se algo acontece o tempo todo", cid)
        # motor, transição
        if c.get("motor") not in MOTORES:
            r.e("MOTOR", f"motor '{c.get('motor')}' inválido (use {' ou '.join(MOTORES)})", cid)
        tr = c.get("transicao") or {}
        if k == 0 and tr.get("tipo") != "corte":
            r.e("TRANSICAO", "a 1ª cena não tem cena anterior: transição tem de ser corte", cid)
        if tr.get("tipo") in TRANSICOES:
            if tr["tipo"] == "corte" and tr.get("quadros"):
                r.e("TRANSICAO", "corte tem 0 quadros", cid)
            if tr.get("quadros", 0) * 2 > dur * FPS:
                r.e("TRANSICAO", f"{tr['quadros']} quadros de transição em cena de {dur * FPS:.0f} quadros", cid)
            if k and tr.get("quadros", 0) * 2 > (cenas[k - 1]["t1"] - cenas[k - 1]["t0"]) * FPS:
                r.e("TRANSICAO", "transição maior que metade da cena anterior (sem quadros de sobreposição)", cid)
            if tr["tipo"] != "corte" and tr.get("quadros") != TRANSICOES[tr["tipo"]]:
                r.a("TRANSICAO_FORA_DO_PADRAO", f"{tr['tipo']} com {tr.get('quadros')} q (kit/transicoes mede {TRANSICOES[tr['tipo']]} q)", cid)
        # capítulo
        if c.get("capitulo") not in caps:
            r.e("CAPITULO", f"capítulo '{c.get('capitulo')}' não existe na história", cid)
        else:
            dono = next((x["id"] for x in reversed(historia["capitulos"]) if x["i"] <= c["i0"]), None)
            if dono != c["capitulo"]:
                r.a("CAPITULO_TROCADO", f"a cena começa no capítulo {dono}, marcada {c['capitulo']}", cid)
        # afirmações citadas
        for x in c.get("afirmacoes", []):
            a = afs.get(x)
            if a is None:
                r.e("AFIRMACAO_INEXISTENTE", f"cena cita {x}, que não está na história", cid)
            elif not (c["i0"] <= a["i"] < c["i1"]):
                r.e("AFIRMACAO_FORA_DA_CENA", f"{x} (\"{a['em']}\", palavra {a['i']}) é dita fora desta cena "
                                              f"[{c['i0']}, {c['i1']}): a prova apareceria na hora errada", cid)
        for uso in c.get("kits", []):
            _kit(r, c, uso, palavras, afs)
        # texto na tela: número só se a fala (ou a afirmação) disser
        falados = _numeros(" ".join(p["t"] for p in palavras[c["i0"]:c["i1"]]))
        for x in c.get("afirmacoes", []):
            a = afs.get(x, {})
            for campo in ("valor", "setor"):
                if a.get(campo) is not None:
                    falados |= _numeros(str(a[campo]))
            for car in a.get("carros", []):
                falados |= _numeros(f"{car['volta']}")
        for t in c.get("texto", []):
            if DISCLAIMER.search(t):
                continue
            for num in _numeros(CAPITULO.sub(" ", t), tela=True) - falados:
                r.e("NUMERO_NA_TELA", f"\"{t}\": o número {num} não é dito nesta cena nem está numa afirmação dela", cid)
        # SFX
        for s in c.get("sfx", []):
            if s.get("categoria") not in cats:
                r.e("SFX_CATEGORIA", f"categoria '{s.get('categoria')}' não existe no kit/sfx", cid)
            if _ancora(r, "ANCORA_SFX", palavras, s.get("i"), s.get("em"), f"SFX {s.get('categoria')}", cid, (c["i0"], c["i1"])):
                sfx_t.append((palavras[s["i"]]["f" if s.get("ponto") == "f" else "i"], cid, s["categoria"]))
    sfx_t.sort()
    for (ta, ca, xa), (tb, cb, xb) in zip(sfx_t, sfx_t[1:]):
        if tb - ta < SFX_MIN_INTERVALO:
            r.e("SFX_PERTO", f"{xa} ({ta:.2f} s) e {xb} ({tb:.2f} s) a menos de {SFX_MIN_INTERVALO} s", cb)
    total = palavras[-1]["f"] if palavras else 0
    if sfx_t and total / len(sfx_t) < SFX_SEGUNDOS:
        r.a("SFX_DENSIDADE", f"{len(sfx_t)} efeitos em {total:.0f} s (1 a cada {total / len(sfx_t):.1f} s): risco de \"goteira\"")
    # afirmações verificáveis sem prova
    for a in afs.values():
        if not a.get("verificavel"):
            continue
        cenas_a = [c for c in cenas if a["id"] in c.get("afirmacoes", [])]
        if not cenas_a:
            r.a("AFIRMACAO_SEM_CENA", f"{a['id']} (\"{a['texto']}\") é verificável e nenhuma cena a mostra")
            continue
        com_dado = any(u.get("kit") in ("gps", "graficos", "imagens") for c in cenas_a for u in c.get("kits", []))
        if not com_dado:
            (r.e if a["tipo"] in TIPOS_DADO else r.a)("AFIRMACAO_SEM_ATIVO",
                f"{a['id']} ({a['tipo']}) é citada mas nenhuma cena dela usa dado real (gps/graficos/imagens)")
    _ativos(r, spec, ativos, afs)
    return _fim(r, spec)


def _ativos(r: Relatorio, spec: dict, ativos: dict | None, afs: dict) -> None:
    if ativos is None:
        r.p("ATIVOS_NAO_RESOLVIDOS", "ativos.json ainda não existe (rode ativos.py)")
        return
    if ativos.get("spec_hash") != hash_dados(spec):
        r.e("ATIVOS_DESATUALIZADOS", "ativos.json foi gerado para outra SPEC: rode ativos.py de novo")
    cenas = {c["id"]: c for c in spec["cenas"]}
    for it in ativos.get("itens", []):
        for cid in it.get("cenas", [it.get("cena")]):
            c = cenas.get(cid, {})
            st = it["status"]
            if st == "falta":
                r.p("ATIVO_FALTA", f"{it['descricao']}: {it.get('comando', '')}", cid)
            elif st in ("reprovado", "nao_encontrado"):
                r.e("ATIVO_" + st.upper(), f"{it['descricao']}: {st}" + (f" ({'; '.join(it.get('evidencia', [])[:2])})"
                                                                          if it.get("evidencia") else "") + " — troque a cena ou a afirmação", cid)
            elif st == "nao_validado":
                if not c.get("aceitar_nao_validado"):
                    r.e("IMAGEM_NAO_VALIDADA", f"{it['descricao']}: NÃO validada e a cena não diz que aceita "
                                               "(aceitar_nao_validado + aviso na tela, só com OK do Felipe)", cid)
                elif not any(AVISO_TELA.search(t) for t in c.get("texto", [])):
                    r.e("IMAGEM_NAO_VALIDADA", f"{it['descricao']}: aceita sem validar, mas sem aviso na tela "
                                               "(\"imagem ilustrativa\" / \"não validada\")", cid)
                else:
                    r.a("IMAGEM_NAO_VALIDADA_ACEITA", f"{it['descricao']}: {c['aceitar_nao_validado']}", cid)
    comps = [it["dados"] for it in ativos.get("itens", []) if it["tipo"] == "comparacao" and it["status"] == "pronto"]
    for a in afs.values():
        if a.get("verificavel"):
            _valor(r, a, comps)


def _fim(r: Relatorio, spec: dict) -> dict:
    status = "reprovado" if r.erros else "pendente" if r.pendencias else "aprovado"
    return {"versao": 1, "spec_hash": hash_dados(spec), "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": status,
            "contagem": {"erros": len(r.erros), "pendencias": len(r.pendencias), "avisos": len(r.avisos)},
            "erros": r.erros, "pendencias": r.pendencias, "avisos": r.avisos}


def aplicar(pasta: Path) -> dict:
    pasta = Path(pasta)
    roteiro, palavras, _, _ = entradas(pasta)
    spec = ler_json(pasta / "spec.json")
    v = verificar(spec, ler_json(pasta / "historia.json"), palavras, roteiro, ler_json(pasta / "ativos.json"))
    estado = etapas.registrar(pasta, "verificacao", v, base=spec,
                              resumo=f"{v['status']}: {v['contagem']['erros']} erros, {v['contagem']['pendencias']} pendências")
    if v["status"] == "reprovado":
        etapas.marcar(pasta, "verificacao", "falhou", estado["etapas"]["verificacao"].get("resumo", ""))
    return v


def imprimir(v: dict) -> None:
    print(f"verificação: {v['status']} ({v['contagem']})")
    for nivel in ("erros", "pendencias", "avisos"):
        for x in v[nivel]:
            print(f"  {nivel[:-1] if nivel != 'pendencias' else 'pendência'}: [{x['codigo']}]{' ' + x['cena'] if x.get('cena') else ''} {x['msg']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    v = aplicar(Path(sys.argv[1]))
    imprimir(v)
    sys.exit(1 if v["erros"] else 0)
