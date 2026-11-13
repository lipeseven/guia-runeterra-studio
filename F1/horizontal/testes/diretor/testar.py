"""Teste automático do diretor documental (offline, sem modelo, sem render, ~1 s).

Roteiro curto de exemplo (Monza 2025, classificação, LEC v16 × HAM v16; os tempos são os do OpenF1 já guardados em
`kit/graficos/comparacoes/9908_16-16_44-16.json`). As "respostas do modelo" são arquivos fixos em `exemplo/`
(o que o Claude devolveria aos prompts de `diretor/prompts/`). O teste roda história → SPEC → ativos → verificação
num projeto temporário e depois estraga a SPEC/história de vários jeitos, conferindo que a verificação barra cada um.

    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\diretor\\testar.py [-v]
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EX = AQUI / "exemplo"
sys.path.insert(0, str(AQUI.parents[1] / "diretor"))

import ativos as A          # noqa: E402
import etapas as E          # noqa: E402
import historia as H        # noqa: E402
import spec as S            # noqa: E402
import verificar as V       # noqa: E402
from comum import estimar_tempos, gravar_json, hash_dados, ler_json  # noqa: E402
from esquema import validar  # noqa: E402

VERBOSO = "-v" in sys.argv
falhas: list[str] = []
n_ok = 0


def checa(cond, nome, detalhe=""):
    global n_ok
    if cond:
        n_ok += 1
        if VERBOSO:
            print("  ok  ", nome)
    else:
        falhas.append(f"{nome} {detalhe}")
        print("  FALHA", nome, detalhe)


def projeto(raiz: Path, nome: str = "exemplo-monza", roteiro: str | None = None) -> Path:
    pasta = raiz / "projetos" / nome / "horizontal"
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    (pasta / "roteiro.txt").write_text(roteiro or (EX / "roteiro.txt").read_text(encoding="utf-8"), encoding="utf-8")
    (pasta / "ativos" / "imagens").mkdir(parents=True)
    shutil.copy(EX / "imagens" / "s9908_c16_v16.json", pasta / "ativos" / "imagens")
    return pasta


def resp(nome):
    return json.loads((EX / nome).read_text(encoding="utf-8"))


def verif(spec, hist, pal, rot, pasta, ativos=None):
    """Verifica com ativos RE-resolvidos para a SPEC dada (isola o defeito); `ativos` força um ativos.json."""
    at = ativos if ativos is not None else A.resolver(spec, hist, pasta)
    return V.verificar(spec, hist, pal, rot, at)


def barra(nome, v, codigo):
    cods = {x["codigo"] for x in v["erros"]}
    checa(v["status"] == "reprovado" and codigo in cods, f"barra: {nome} -> {codigo}", f"(veio {v['status']} {sorted(cods)})")


def main() -> int:
    raiz = Path(tempfile.mkdtemp(prefix="diretor_"))
    try:
        return _testes(raiz)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)


def _testes(raiz: Path) -> int:
    print("1. esquemas e prompts")
    for nome in ("historia", "spec", "ativos", "estado"):
        esq = json.loads((AQUI.parents[1] / "diretor" / "esquemas" / f"{nome}.schema.json").read_text(encoding="utf-8"))
        checa(esq.get("$schema", "").startswith("https://json-schema.org/"), f"esquema {nome} é JSON Schema")
    checa(validar({"a": 1}, {"type": "object", "required": ["b"]}) != [], "validador acusa campo faltando")
    checa(validar(5, {"enum": [1, 2]}) != [], "validador acusa enum")
    checa(validar({"x": "z"}, {"type": "object", "additionalProperties": False}) != [], "validador acusa campo extra")

    pasta = projeto(raiz)
    roteiro, pal, tempos, brief = S.entradas(pasta)
    checa(tempos == "estimados" and len(pal) > 50, "sem palavras.json: tempos estimados", f"({tempos}, {len(pal)})")
    ph = H.prompt(roteiro, pal, brief)
    checa("{{" not in ph and "Leclerc marcou 1:19,007" in ph and "Regras de direção" in ph, "prompt da história preenchido")

    print("2. história")
    hist = H.aplicar(pasta, resp("resposta_historia.json"))
    checa(not validar(hist, "historia"), "historia.json válido no esquema")
    checa(len(hist["capitulos"]) == 4 and [c["i"] for c in hist["capitulos"]][0] == 0, "4 capítulos, 1º na palavra 0")
    checa(len(hist["afirmacoes"]) == 7, "afirmação com trecho inventado saiu", f"({len(hist['afirmacoes'])})")
    checa(any("Verstappen" in a for a in hist["avisos"]), "aviso da afirmação inventada")
    checa([a["id"] for a in hist["afirmacoes"]] == [f"a{k}" for k in range(1, 8)], "ids a1..a7 em ordem de fala")
    checa(sum(a["verificavel"] for a in hist["afirmacoes"]) == 6, "6 afirmações verificáveis")
    checa(all(pal[a["i"]]["t"].startswith(a["em"].split()[0]) for a in hist["afirmacoes"]), "afirmações presas à palavra")
    h2 = H.normalizar({"titulo": "teste", "tese": "tese x", "capitulos": [{"titulo": "parte", "funcao": "gancho", "em": "Por que"}],
                       "afirmacoes": [{"texto": "sem sessão", "em": "Leclerc marcou", "tipo": "tempo_volta", "verificavel": True}]},
                      pal, roteiro)
    checa(not h2["afirmacoes"][0]["verificavel"] and h2["avisos"], "verificável sem sessão vira não verificável (com aviso)")
    E.aprovar(pasta, "historia")

    print("3. SPEC")
    psp = S.prompt(roteiro, pal, hist, brief)
    checa("{{" not in psp and "`graficos`" in psp and '"a5"' in psp, "prompt da SPEC preenchido (kits e história)")
    spec = S.aplicar(pasta, resp("resposta_spec.json"))
    checa(not validar(spec, "spec"), "spec.json válido no esquema")
    checa(len(spec["cenas"]) == 8 and any("Schumacher" in a for a in spec["avisos"]), "cena com trecho inventado saiu (aviso)")
    cs = spec["cenas"]
    checa(cs[0]["i0"] == 0 and all(a["i1"] == b["i0"] for a, b in zip(cs, cs[1:])) and cs[-1]["i1"] == len(pal),
          "cenas contíguas cobrindo o roteiro")
    checa(all(a["t1"] == b["t0"] for a, b in zip(cs, cs[1:])), "tempos contíguos")
    dlt = cs[3]["kits"][0]["params"]["ritmo"]
    checa(all(isinstance(r["i"], int) and cs[3]["i0"] <= r["i"] < cs[3]["i1"] for r in dlt), "âncoras do ritmo do gráfico resolvidas")
    checa(cs[1]["transicao"] == {"tipo": "wipe", "quadros": 24}, "transição com quadros do kit")
    checa(len({c["id"] for c in cs}) == len(cs), "ids de cena únicos")
    est = E.ler(pasta)
    checa(est["etapas"]["spec"]["base_hash"] == hash_dados(hist), "spec.base_hash = hash da história")

    print("4. ativos")
    at = A.aplicar(pasta)
    checa(not validar(at, "ativos"), "ativos.json válido no esquema")
    por = {i["id"]: i for i in at["itens"]}
    comp = por.get("comparacao:9908:16-16:44-16")
    checa(comp and comp["status"] == "pronto" and comp["dados"]["pilotos"]["16"]["tempo"] == 79.007, "comparação Monza pronta (kit/graficos)")
    checa(por.get("volta_gps:9908:16:16", {}).get("status") == "falta" and "preparar_volta.py 9908 16 16" in por["volta_gps:9908:16:16"]["comando"],
          "GPS de Monza falta, com o comando")
    img = por.get("imagem:s9908_c16_v16")
    checa(img and img["status"] == "nao_validado", "imagem da classificação = nao_validado (kit/imagens)")
    checa(all(i["status"] in ("pronto", "falta") for i in at["itens"] if i["tipo"] == "sfx"), "SFX resolvidos no banco/catálogo")
    checa(len(comp["cenas"]) >= 4, "mesmo ativo em várias cenas = um item só", f"({comp['cenas']})")

    print("5. verificação do exemplo bom")
    v = V.aplicar(pasta)
    if VERBOSO or v["erros"]:
        V.imprimir(v)
    checa(not v["erros"], "exemplo bom sem erros", f"({[x['codigo'] for x in v['erros']]})")
    checa(v["status"] == "pendente" and {p["codigo"] for p in v["pendencias"]} <= {"ATIVO_FALTA"}, "status pendente (só ativos a produzir)")
    checa(any("9908" in p["msg"] and "GPS" in p["msg"] for p in v["pendencias"]), "pendência lista o GPS que falta")
    checa(any(a["codigo"] == "IMAGEM_NAO_VALIDADA_ACEITA" for a in v["avisos"]), "imagem não validada aceita aparece como aviso")
    checa(not any(a["codigo"] == "VALOR_NAO_CONFERIDO" for a in v["avisos"]), "os 6 valores conferidos com o OpenF1 (comparação)")
    checa(E.ler(pasta)["etapas"]["verificacao"]["status"] == "gerado", "estado: verificação gerada")

    print("6. casos errados (a verificação barra)")

    def mut(f, nome, codigo, hist_=None, ativos=None, rot=None, pal_=None):
        s = copy.deepcopy(spec)
        h = copy.deepcopy(hist_ or hist)
        f(s, h)
        barra(nome, verif(s, h, pal_ or pal, rot or roteiro, pasta, ativos), codigo)

    def cena(s, k):
        return s["cenas"][k]

    mut(lambda s, h: cena(s, 3).update(em="A distância foi de"), "âncora de cena inexistente", "ANCORA_CENA")
    mut(lambda s, h: cena(s, 2).update(motor="blender"), "motor inválido", "MOTOR")
    mut(lambda s, h: cena(s, 2).update(motor="blender"), "motor inválido (esquema)", "ESQUEMA_SPEC")
    mut(lambda s, h: cena(s, 3)["kits"][0]["params"].update(sessao=11408), "gráfico de outra sessão", "AFIRMACAO_DADOS")
    mut(lambda s, h: cena(s, 3)["kits"][0]["params"]["a"].update(volta=17), "gráfico de outra volta", "AFIRMACAO_DADOS")
    mut(lambda s, h: cena(s, 2)["kits"][0]["params"]["a"].update(piloto=1), "gráfico de outro carro", "AFIRMACAO_DADOS")
    mut(lambda s, h: cena(s, 3)["afirmacoes"].append("a5"), "afirmação dita em outra cena", "AFIRMACAO_FORA_DA_CENA")
    mut(lambda s, h: cena(s, 3)["afirmacoes"].append("a99"), "afirmação inexistente", "AFIRMACAO_INEXISTENTE")
    mut(lambda s, h: cena(s, 3).update(kits=[]), "diferença sem dado real", "AFIRMACAO_SEM_ATIVO")
    mut(lambda s, h: cena(s, 5).pop("aceitar_nao_validado"), "imagem não validada silenciosa", "IMAGEM_NAO_VALIDADA")
    mut(lambda s, h: cena(s, 5).update(texto=["Setor 2: LEC −0,104 s"]), "não validada aceita sem aviso na tela", "IMAGEM_NAO_VALIDADA")
    mut(lambda s, h: cena(s, 5)["kits"][0]["params"].update(afirmacao="a7"), "imagem sem afirmação verificável", "IMAGEM_SEM_AFIRMACAO")
    mut(lambda s, h: cena(s, 3).update(texto=["0,3 s"]), "número na tela que a fala não diz", "NUMERO_NA_TELA")
    mut(lambda s, h: cena(s, 3)["kits"][0]["params"].update(tipo="pizza"), "tipo de gráfico inexistente", "KIT_PARAMETRO")
    mut(lambda s, h: cena(s, 1)["kits"][0]["params"].pop("carros"), "GPS sem carros", "KIT_PARAMETRO")
    mut(lambda s, h: cena(s, 3)["kits"][0]["params"]["ritmo"][1].update(i=cena(s, 6)["i0"], em=cena(s, 6)["em"]),
        "âncora do gráfico fora da cena", "ANCORA_PARAMETRO")
    mut(lambda s, h: cena(s, 3)["kits"][0]["params"]["ritmo"][0].update(em="no fim da reta"), "âncora do gráfico inexistente", "ANCORA_PARAMETRO")
    mut(lambda s, h: cena(s, 2)["sfx"].append({**cena(s, 2)["sfx"][0], "categoria": "pop"}),
        "dois SFX colados", "SFX_PERTO")
    mut(lambda s, h: cena(s, 2)["sfx"][0].update(i=cena(s, 3)["sfx"][0]["i"], em=cena(s, 3)["sfx"][0]["em"]),
        "SFX ancorado fora da cena", "ANCORA_SFX")
    mut(lambda s, h: cena(s, 2)["sfx"][0].update(categoria="buzina"), "SFX de categoria inexistente", "SFX_CATEGORIA")
    mut(lambda s, h: cena(s, 0).update(transicao={"tipo": "wipe", "quadros": 24}), "1ª cena com wipe", "TRANSICAO")
    mut(lambda s, h: cena(s, 4).update(transicao={"tipo": "corte", "quadros": 12}), "corte com quadros", "TRANSICAO")
    mut(lambda s, h: cena(s, 2).update(t0=cena(s, 2)["t0"] + 0.5), "tempo editado à mão", "TEMPO")
    mut(lambda s, h: cena(s, 2).update(i1=cena(s, 2)["i1"] - 2), "buraco entre cenas", "ORDEM")
    mut(lambda s, h: cena(s, 2).update(capitulo="c9"), "capítulo inexistente", "CAPITULO")
    mut(lambda s, h: cena(s, 2).pop("objetivo"), "cena sem objetivo", "ESQUEMA_SPEC")

    # duração curta: SPEC com uma cena começando 2 palavras depois da anterior
    r2 = resp("resposta_spec.json")
    r2["cenas"].insert(4, {**r2["cenas"][4], "em": "segundo.", "afirmacoes": [], "sfx": [], "kits": [], "texto": []})
    s2 = S.normalizar(r2, pal, hist, roteiro, tempos)
    barra("cena curta demais", verif(s2, hist, pal, roteiro, pasta), "DURACAO")

    # história mudou depois da SPEC / ativos velhos
    h3 = copy.deepcopy(hist)
    h3["tese"] += " (editada)"
    barra("história mudou depois da SPEC", verif(spec, h3, pal, roteiro, pasta), "HISTORIA_MUDOU")
    s3 = copy.deepcopy(spec)
    cena(s3, 2)["texto"].append("Ferrari")
    barra("ativos de outra SPEC", verif(s3, hist, pal, roteiro, pasta, ativos=at), "ATIVOS_DESATUALIZADOS")

    # roteiro mudou (narração regravada com frase nova no meio): âncoras velhas não batem
    rot4 = roteiro.replace("A diferença foi de", "Foi por muito pouco. A diferença foi de")
    pal4 = estimar_tempos(rot4)
    v4 = verif(spec, hist, pal4, rot4, pasta)
    barra("roteiro mudou", v4, "ROTEIRO_MUDOU")
    barra("roteiro mudou: âncora velha", v4, "ANCORA_CENA")

    # valor errado na história (pipeline inteiro de novo, só o valor muda)
    rh = resp("resposta_historia.json")
    rh["afirmacoes"][2]["valor"] = 0.217
    pasta5 = projeto(raiz, "valor-errado")
    h5 = H.aplicar(pasta5, rh)
    E.aprovar(pasta5, "historia")
    S.aplicar(pasta5, resp("resposta_spec.json"))
    A.aplicar(pasta5)
    v5 = V.aplicar(pasta5)
    barra("valor que o OpenF1 não confirma", v5, "VALOR_NAO_BATE")
    checa(E.ler(pasta5)["etapas"]["verificacao"]["status"] == "falhou", "estado: verificação falhou")
    rh["afirmacoes"][3]["valor"] = 0.146
    barra("setor com valor errado", verif(*_pipeline(raiz, rh)), "VALOR_NAO_BATE")

    # imagem reprovada pelo kit/imagens
    reprov = copy.deepcopy(at)
    for it in reprov["itens"]:
        if it["tipo"] == "imagem":
            it["status"] = "reprovado"
            it["evidencia"] = ["contador 1 fora da volta 16"]
    barra("imagem reprovada", V.verificar(spec, hist, pal, roteiro, reprov), "ATIVO_REPROVADO")

    print("7. estado.json e retemporização")
    try:
        E.aprovar(pasta, "spec")
        checa(True, "aprovar SPEC (história aprovada)")
    except ValueError as e:
        checa(False, "aprovar SPEC", str(e))
    s_disco = ler_json(pasta / "spec.json")
    s_disco["cenas"][0]["objetivo"] = "editado à mão"
    gravar_json(pasta / "spec.json", s_disco)
    E.marcar(pasta, "spec", "gerado")
    try:
        E.aprovar(pasta, "spec")
        checa(False, "aprovar recusa arquivo mudado depois de gerado")
    except ValueError:
        checa(True, "aprovar recusa arquivo mudado depois de gerado")
    H.aplicar(pasta, {**resp("resposta_historia.json"), "tese": "outra tese"})
    st = E.ler(pasta)
    checa(st["etapas"]["spec"]["status"] == "desatualizado" and st["etapa_atual"] == "historia",
          "história nova desatualiza SPEC e volta a etapa", f"({st['etapas']['spec']['status']}, {st['etapa_atual']})")
    E.pedir(pasta, "spec", "trocar o gráfico de setores por telemetria", cena=cs[2]["id"])
    st = E.ler(pasta)
    checa(E.pedidos_abertos(st, "spec") and st["pedidos"][-1]["cena"] == cs[2]["id"], "pedido por cena registrado")
    checa(not validar(st, "estado"), "estado.json válido no esquema")
    pp = S.prompt_pedido(pasta, cs[2]["id"])
    checa("{{" not in pp and "telemetria" in pp and "Leclerc marcou" in pp, "prompt de pedido de cena")
    nova = {**{k: v for k, v in cs[2].items() if k not in ("id", "i0", "i1", "t0", "t1")}}
    nova["kits"] = [{"kit": "graficos", "params": {"tipo": "telemetria", "sessao": 9908, "a": {"piloto": 16, "volta": 16},
                                                   "b": {"piloto": 44, "volta": 16}, "trecho": [1903, 2600]}}]
    s6 = S.trocar_cena(spec, cs[2]["id"], nova, pal, hist, roteiro)
    checa([c["id"] for c in s6["cenas"]] == [c["id"] for c in cs] and s6["cenas"][2]["kits"][0]["params"]["tipo"] == "telemetria",
          "troca de UMA cena mantém os ids das outras")
    pal7 = [{"t": p["t"], "i": round(p["i"] * 1.1, 3), "f": round(p["f"] * 1.1, 3)} for p in pal]
    s7 = S.retemporizar(spec, pal7)
    checa([c["i0"] for c in s7["cenas"]] == [c["i0"] for c in cs] and abs(s7["cenas"][-1]["t1"] - (pal7[-1]["f"] + S.CAUDA)) < 1e-6,
          "narração nova: mesmos índices, tempos novos")
    v7 = verif(s7, hist, pal7, roteiro, pasta)
    checa(not v7["erros"], "SPEC retemporizada passa", f"({[x['codigo'] for x in v7['erros']]})")

    print(f"\n{n_ok} checagens ok, {len(falhas)} falhas")
    return 1 if falhas else 0


def _pipeline(raiz: Path, rh: dict):
    pasta = projeto(raiz, "pipeline")
    roteiro, pal, tempos, _ = S.entradas(pasta)
    h = H.normalizar(rh, pal, roteiro, tempos)
    s = S.normalizar(resp("resposta_spec.json"), pal, h, roteiro, tempos)
    return s, h, pal, roteiro, pasta


if __name__ == "__main__":
    sys.exit(main())
