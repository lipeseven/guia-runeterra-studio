"""Teste automático da API do card documental (fase 4), com dados fictícios e sem modelo (~10 s).

Sobe o app FastAPI em processo (TestClient, sem porta e sem tocar os painéis 8765/8766), com o canal f1 apontado
para `testes/painel/dados/api/` (ver ambiente.py). Faz o caminho inteiro do card: criar → roteiro aprovado →
narração medida → prompt da História → resposta do "orquestrador" (respostas fixas de `testes/diretor/exemplo/`) →
aprovar ★ → SPEC → pedido por cena (retirar, refazer só a cena) → aprovar ★ → Ativos → Verificação → Rascunho
("sem montador ainda"). Confere o estado.json, as etapas do card, as pendências e que vertical/horizontal não mudaram.

    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\painel\\testar_api.py [-v] [--manter]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ambiente  # noqa: E402

BASE = ambiente.preparar("api")

from fastapi.testclient import TestClient  # noqa: E402

from app.servidor import etapas as ET  # noqa: E402
from app.servidor import motor  # noqa: E402
motor.iniciar = lambda: None   # sem o trabalhador em thread: o teste roda a fila tarefa a tarefa (motor.executar)
from app.servidor.banco import conectar  # noqa: E402
from app.servidor.main import app  # noqa: E402

VERBOSO = "-v" in sys.argv
motor.pedir_acervo = lambda: None   # card novo pede atualização do acervo (tarefa global): fora do teste
cli = TestClient(app)
falhas: list[str] = []
n_ok = 0


def checa(cond, nome, detalhe=""):
    global n_ok
    if cond:
        n_ok += 1
        if VERBOSO:
            print("  ok ", nome)
    else:
        falhas.append(f"{nome} {detalhe}")
        print("  FALHOU", nome, detalhe)


def doc(vid):
    r = cli.get(f"/api/videos/{vid}/doc")
    assert r.status_code == 200, r.text
    return r.json()


def card(vid):
    v = cli.get(f"/api/videos/{vid}").json()
    return v, {e["chave"]: e for e in v["etapas"]}, {p["chave"] for p in v["pendencias"]}


def orquestrador(pasta: Path, etapa: str, resposta: dict, cena: str | None = None) -> subprocess.CompletedProcess:
    """O que o chat/orquestrador faz: grava a resposta do modelo e roda o comando da pendência."""
    arq = pasta / f"resposta_{etapa}{'_' + cena if cena else ''}.json"
    arq.write_text(json.dumps(resposta, ensure_ascii=False), encoding="utf-8")
    cmd = [sys.executable, str(ambiente.DIRETOR / "painel.py"), "aplicar", str(pasta), etapa, str(arq)] + (["--cena", cena] if cena else [])
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def principal() -> int:
    print("canal:", cli.get("/api/canal").json()["nome"], "| dados:", BASE)
    c = cli.get("/api/canal").json()
    checa("horizontal_doc" in c["formatos"] and c["rotulos"]["horizontal_doc"] == "documentário", "canal oferece o formato documentário")

    # ---- cards existentes não mudam
    ids = {f: cli.post("/api/videos", json={"titulo": f"Teste {f}", "formato": f}).json()["id"]
           for f in ("vertical", "horizontal", "horizontal_doc")}
    _, et_v, _ = card(ids["vertical"])
    _, et_h, _ = card(ids["horizontal"])
    checa(list(et_v) == [e["chave"] for e in ET.ETAPAS_VERTICAL], "vertical com as etapas de sempre")
    checa(list(et_h) == [e["chave"] for e in ET.ETAPAS_HORIZONTAL_ANIMADO], "horizontal animado com as etapas de sempre")
    checa(cli.get(f"/api/videos/{ids['vertical']}/doc").status_code == 404, "card vertical não tem /doc")
    checa(cli.get(f"/api/videos/{ids['horizontal']}/doc").status_code == 404, "card horizontal não tem /doc")
    with conectar() as con:
        checa(con.execute("SELECT formato FROM videos WHERE id=?", (ids["horizontal"],)).fetchone()[0] == "horizontal", "formato horizontal gravado")

    # ---- card documental
    vid = ids["horizontal_doc"]
    v, et, pend = card(vid)
    checa(v["formato"] == "horizontal_doc", "formato horizontal_doc gravado")
    checa(list(et) == [e["chave"] for e in ET.ETAPAS_HORIZONTAL_DOC], "etapas do documentário", str(list(et)))
    d = doc(vid)
    checa(d["estado"]["etapa_atual"] == "historia", "estado novo começa na história")
    checa(d["rascunho"] is None and d["montador"] and d["rascunho_video"] is None, "rascunho: montador disponível, sem vídeo ainda")
    _, et, _ = card(vid)
    checa(et["rascunho_doc"]["status"] == "pendente", "card Rascunho aguardando (montador existe)", str(et["rascunho_doc"]))
    r = cli.post(f"/api/videos/{vid}/doc/passo/historia")
    checa(r.status_code == 409 and "roteiro" in r.json()["detail"], "história recusada sem roteiro aprovado", r.text)

    # roteiro aprovado e narração medida (fixture: o fluxo do roteiro/voz já tem os próprios caminhos no painel)
    slug = v["slug"]
    proj = motor.PASTA_PROJETOS / slug
    pasta = proj / "horizontal"
    (proj / "direcao").mkdir(parents=True, exist_ok=True)
    roteiro = (ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8")
    (proj / "direcao" / "roteiro.txt").write_text(roteiro, encoding="utf-8")
    (proj / "direcao" / "tempos_voz.json").write_text('[{"t": "só", "i": 0, "f": 0.3}]', encoding="utf-8")
    with conectar() as con:
        con.execute("UPDATE etapas SET status='concluido' WHERE video_id=? AND chave='roteiro'", (vid,))
        con.commit()
    d = doc(vid)
    checa(d["avisos_entrada"] and "estimados" in d["avisos_entrada"][0], "narração de outro roteiro não entra (tempos estimados)")
    checa((pasta / "roteiro.txt").read_text(encoding="utf-8") == roteiro, "roteiro do card copiado para a pasta horizontal")
    medidas = json.loads(subprocess.run(
        [sys.executable, "-c", "import json,sys; sys.path.insert(0, sys.argv[1]); from comum import estimar_tempos;"
         "print(json.dumps(estimar_tempos(open(sys.argv[2], encoding='utf-8').read(), 2.4)))", str(ambiente.DIRETOR),
         str(proj / "direcao" / "roteiro.txt")], capture_output=True, text=True, encoding="utf-8").stdout)
    (proj / "direcao" / "tempos_voz.json").write_text(json.dumps(medidas, ensure_ascii=False), encoding="utf-8")
    d = doc(vid)
    checa(d["entradas"]["tempos"] == "medidos" and d["entradas"]["palavras"] == len(medidas), "narração medida copiada (palavras.json)")
    _, _, pend = card(vid)
    checa("doc_historia" in pend, "pendência: gere a história")

    # ---- História: prompt → orquestrador → aprovar ★
    r = cli.post(f"/api/videos/{vid}/doc/passo/historia")
    checa(r.status_code == 200 and r.json()["passo"]["precisa_modelo"], "passo História gera prompt (sem chamar modelo)", r.text)
    checa((pasta / "prompts" / "historia.prompt.txt").exists(), "prompts/historia.prompt.txt gravado")
    d = r.json()
    checa(d["estado"]["etapas"]["historia"]["status"] == "prompt_pronto", "estado: historia prompt_pronto")
    checa(len(d["orquestrador"]) == 1 and d["orquestrador"][0]["etapa"] == "historia", "lista do orquestrador com a história")
    v, et, pend = card(vid)
    checa(et["historia"]["status"] == "andamento" and "doc_orq_historia" in pend and "doc_historia" not in pend,
          "card História em andamento + pendência do orquestrador")
    texto_orq = next(p["texto"] for p in v["pendencias"] if p["chave"] == "doc_orq_historia")
    checa("painel.py" in texto_orq and "historia.prompt.txt" in texto_orq, "pendência traz prompt e comando")
    checa(cli.post(f"/api/videos/{vid}/doc/passo/spec").status_code == 409, "SPEC recusada antes da história aprovada")
    checa(cli.post(f"/api/videos/{vid}/doc/aprovar/historia").status_code == 409, "aprovar recusa história só com prompt")

    resp_h = json.loads((ambiente.EXEMPLO / "resposta_historia.json").read_text(encoding="utf-8"))
    p = orquestrador(pasta, "historia", resp_h)
    checa(p.returncode == 0, "orquestrador aplica a história", p.stderr[-400:])
    d = doc(vid)
    checa(d["estado"]["etapas"]["historia"]["status"] == "gerado" and d["historia"]["capitulos"], "historia.json gerado")
    v, et, pend = card(vid)
    checa(et["historia"]["status"] == "atencao" and "doc_aprovar_historia" in pend and "doc_orq_historia" not in pend,
          "card pede aprovação ★ da história")
    r = cli.post(f"/api/videos/{vid}/doc/passo/historia")
    checa(r.status_code == 409, "história gerada não refaz sem pedido")
    # pedido na história + retirar
    r = cli.post(f"/api/videos/{vid}/doc/pedido", json={"etapa": "historia", "texto": "gancho mais forte"})
    checa(r.status_code == 200 and r.json()["estado"]["etapas"]["historia"]["status"] == "mudanca_pedida", "pedido na história")
    pid = r.json()["estado"]["pedidos"][-1]["id"]
    _, et, _ = card(vid)
    checa(et["historia"]["status"] == "atencao" and "mudança pedida" in (et["historia"]["detalhe"] or ""), "card mostra mudança pedida")
    r = cli.delete(f"/api/videos/{vid}/doc/pedido/{pid}")
    checa(r.status_code == 200 and r.json()["estado"]["pedidos"][-1]["status"] == "recusado"
          and r.json()["estado"]["etapas"]["historia"]["status"] == "gerado", "pedido retirado (história volta a gerado)")
    r = cli.post(f"/api/videos/{vid}/doc/aprovar/historia")
    checa(r.status_code == 200, "aprovar história ★", r.text)
    d = doc(vid)
    checa(d["estado"]["etapas"]["historia"]["status"] == "aprovado", "estado: historia aprovado")
    _, et, pend = card(vid)
    checa(et["historia"]["status"] == "concluido" and "doc_aprovar_historia" not in pend, "card História concluído")

    # ---- SPEC: prompt → orquestrador → arquivo mexido barra aprovação → pedido por cena → aprovar ★
    r = cli.post(f"/api/videos/{vid}/doc/passo/spec")
    checa(r.status_code == 200 and r.json()["estado"]["etapas"]["spec"]["status"] == "prompt_pronto", "passo SPEC gera prompt", r.text)
    resp_s = json.loads((ambiente.EXEMPLO / "resposta_spec.json").read_text(encoding="utf-8"))
    p = orquestrador(pasta, "spec", resp_s)
    checa(p.returncode == 0, "orquestrador aplica a SPEC", p.stderr[-400:])
    d = doc(vid)
    cenas = d["spec"]["cenas"]
    checa(d["estado"]["etapas"]["spec"]["status"] == "gerado" and len(cenas) >= 3, "spec.json gerado", str(len(cenas)))
    bruto = (pasta / "spec.json").read_text(encoding="utf-8")
    (pasta / "spec.json").write_text(bruto.replace('"objetivo": "', '"objetivo": "MEXIDO ', 1), encoding="utf-8")
    r = cli.post(f"/api/videos/{vid}/doc/aprovar/spec")
    checa(r.status_code == 409 and "mudou" in r.json()["detail"], "aprovação recusa spec.json mexido à mão", r.text)
    (pasta / "spec.json").write_text(bruto, encoding="utf-8")
    alvo = cenas[1]["id"]
    r = cli.post(f"/api/videos/{vid}/doc/pedido", json={"etapa": "spec", "texto": "x", "cena": "naoexiste"})
    checa(r.status_code == 409, "pedido em cena inexistente recusado")
    r = cli.post(f"/api/videos/{vid}/doc/pedido", json={"etapa": "spec", "texto": "câmera mais baixa, na altura do carro", "cena": alvo})
    est = r.json()["estado"]
    checa(r.status_code == 200 and est["pedidos"][-1]["cena"] == alvo and est["etapas"]["spec"]["status"] == "mudanca_pedida",
          "pedido por cena gravado no estado.json")
    pid = est["pedidos"][-1]["id"]
    r = cli.delete(f"/api/videos/{vid}/doc/pedido/{pid}")
    checa(r.json()["estado"]["etapas"]["spec"]["status"] == "gerado", "retirar o único pedido devolve a SPEC a gerado")
    cli.post(f"/api/videos/{vid}/doc/pedido", json={"etapa": "spec", "texto": "câmera mais baixa, na altura do carro", "cena": alvo})
    r = cli.post(f"/api/videos/{vid}/doc/passo/spec")
    checa(r.status_code == 200 and (pasta / "prompts" / f"pedido_{alvo}.prompt.txt").exists(), "pedido de cena gera prompt só da cena", r.text)
    orq = r.json()["orquestrador"]
    checa(len(orq) == 1 and orq[0]["cena"] == alvo and "--cena" in orq[0]["comando"], "orquestrador recebe a cena", str(orq))
    _, et, pend = card(vid)
    checa("doc_orq_spec" in pend and et["spec"]["status"] == "andamento", "pendência do orquestrador para a cena")
    nova = {k: v for k, v in cenas[1].items() if k not in ("id", "i0", "i1", "t0", "t1")}
    nova["camera"] = "baixa, na altura do carro"
    p = orquestrador(pasta, "spec", nova, alvo)
    checa(p.returncode == 0, "orquestrador aplica a cena refeita", p.stderr[-400:])
    d = doc(vid)
    c2 = next(c for c in d["spec"]["cenas"] if c["id"] == alvo)
    checa(c2.get("camera") == "baixa, na altura do carro" and [c["id"] for c in d["spec"]["cenas"]] == [c["id"] for c in cenas],
          "só a cena pedida mudou (ids iguais)")
    checa(all(p["status"] != "aberto" for p in d["estado"]["pedidos"]), "pedido atendido")
    r = cli.post(f"/api/videos/{vid}/doc/aprovar/spec")
    checa(r.status_code == 200 and r.json()["estado"]["etapas"]["spec"]["status"] == "aprovado", "aprovar SPEC ★", r.text)

    # ---- Ativos e Verificação (rodam no painel: offline, sem modelo)
    r = cli.post(f"/api/videos/{vid}/doc/passo/ativos")
    checa(r.status_code == 200 and "resumo" in r.json()["passo"], "passo Ativos", r.text[-300:])
    d = r.json()
    checa(d["ativos"] and d["ativos"]["itens"] and d["estado"]["etapas"]["ativos"]["status"] == "gerado", "ativos.json gerado")
    nao_prontos = [i for i in d["ativos"]["itens"] if i["status"] != "pronto"]
    checa(bool(nao_prontos), "há ativos faltando/não validados para mostrar", str(d["ativos"]["resumo"]))
    r = cli.post(f"/api/videos/{vid}/doc/passo/verificacao")
    checa(r.status_code == 200 and r.json()["verificacao"]["status"] in ("pendente", "reprovado", "aprovado"), "passo Verificação", r.text[-300:])
    d = r.json()
    checa(isinstance(d["verificacao"]["avisos"], list) and "contagem" in d["verificacao"], "verificacao.json com avisos")
    _, et, pend = card(vid)
    checa(et["ativos"]["status"] == "concluido" and et["verificacao"]["status"] in ("concluido", "atencao"), "cards Ativos/Verificação")
    if d["verificacao"]["status"] != "aprovado":
        checa("doc_verificacao" in pend, "pendência da verificação")

    # ---- Rascunho: o montador confere tudo antes de renderizar e recusa com o motivo (aqui a SPEC de exemplo tem
    # cenas com kits sem receita/ativo no montador: nada é renderizado no teste)
    r = cli.post(f"/api/videos/{vid}/doc/passo/rascunho")
    det = r.json().get("detail", "")
    checa(r.status_code == 409 and det.startswith("não dá para montar") and "cena " in det and "sem receita" in det,
          "passo Rascunho: recusa clara do montador (o que falta, por cena)", det[:300])
    r = cli.post(f"/api/videos/{vid}/doc/aprovar/rascunho")
    checa(r.status_code == 409 and "só se aprova o que foi gerado" in r.json()["detail"], "aprovar Rascunho sem rascunho gerado: recusado", r.text[:200])
    checa(cli.post(f"/api/videos/{vid}/doc/aprovar/ativos").status_code == 400, "Ativos não tem aprovação ★")

    # ---- Storyboard do Rascunho (fase 7b): cenas, ações diretas na SPEC sem modelo, ★ por cena, pedido por cena (voz)
    r = cli.get(f"/api/videos/{vid}/doc/storyboard")
    sb = r.json()
    checa(r.status_code == 200 and len(sb["cenas"]) == len(cenas), "storyboard lista as cenas da SPEC", r.text[:200])
    checa(all(c["frases"] and c["momentos"] and c["estado"] in ("sem_previa", "sem_receita") for c in sb["cenas"]),
          "cada cena com frases faladas, momentos-chave e estado", str([c["estado"] for c in sb["cenas"]]))
    checa(any(c["estado"] == "sem_receita" and "sem receita" in (c["problema"] or "") for c in sb["cenas"]),
          "cena sem receita no montador aparece com o motivo (não barra as outras)")
    c0, c1 = sb["cenas"][0], sb["cenas"][1]
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c0['id']}/ajuste", json={"acao": {"acao": "movimento", "tipo": "pan_esq"}, "previa": False})
    checa(r.status_code == 200 and r.json()["storyboard"]["cenas"][0]["movimento"] == {"tipo": "pan_esq"}, "ação direta: movimento entra na SPEC na hora", r.text[:300])
    d = doc(vid)
    checa(d["estado"]["etapas"]["spec"]["status"] == "aprovado" and d["spec"]["cenas"][0]["movimento"]["tipo"] == "pan_esq",
          "SPEC continua aprovada depois da ação direta")
    checa(any("ajuste direto" in h["evento"] for h in d["estado"]["historico"]), "histórico registra o ajuste direto")
    checa(json.loads((pasta / "ajustes_diretos.json").read_text(encoding="utf-8"))[-1]["acao"]["tipo"] == "pan_esq",
          "ajustes_diretos.json guarda a ação (aprendizado)")
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c0['id']}/ajuste", json={"acao": {"acao": "movimento", "tipo": "girar"}, "previa": False})
    checa(r.status_code == 409 and "movimento inválido" in r.json()["detail"], "movimento inválido recusado com motivo", r.text[:200])
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c0['id']}/ajuste", json={"acao": {"acao": "trocar o gráfico"}, "previa": False})
    checa(r.status_code == 409 and "orquestrador" in r.json()["detail"], "ação desconhecida: manda pedir ao orquestrador", r.text[:200])
    novo_i0 = c1["i0"] + 1
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c1['id']}/ajuste", json={"acao": {"acao": "corte", "indice": novo_i0}, "previa": False})
    sb2 = r.json().get("storyboard", {"cenas": [{}, {}]})
    checa(r.status_code == 200 and sb2["cenas"][1]["i0"] == novo_i0 and sb2["cenas"][0]["i1"] == novo_i0
          and sb2["cenas"][1]["t0"] > c1["t0"], "corte movido: a cena começa uma palavra depois e a anterior cresce", r.text[:300])
    c1 = sb2["cenas"][1]
    for c in sb2["cenas"]:   # ★ da cena: sem prévia (ou sem receita) é recusado com o motivo certo
        r = cli.post(f"/api/videos/{vid}/doc/cena/{c['id']}/aprovar")
        esperado = c["problema"] if c["estado"] == "sem_receita" else "prévia"
        checa(r.status_code == 409 and esperado in r.json()["detail"], f"★ da cena {c['estado']}: recusado com o motivo", r.text[:200])
    r = cli.post(f"/api/videos/{vid}/doc/previa", json={"cenas": ["naoexiste"]})
    checa(r.status_code == 409, "prévia de cena inexistente recusada", r.text[:200])
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c1['id']}/pedido", json={"texto": "  ", "origem": "voz"})
    checa(r.status_code == 409, "pedido vazio recusado")
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c1['id']}/pedido", json={"texto": "mostra o carro de frente", "origem": "voz"})
    dd = r.json()
    checa(r.status_code == 200 and dd["pedido"]["prompt"] and dd["pedido"]["prompt"][0].endswith(f"pedido_{c1['id']}.prompt.txt"),
          "pedido por voz vira prompt só da cena", r.text[:300])
    checa(any(t["etapa"] == "spec" and t["cena"] == c1["id"] for t in dd["orquestrador"]), "orquestrador recebe o pedido da cena")
    checa(dd["estado"]["pedidos"][-1]["cena"] == c1["id"] and "ditado por voz" in dd["estado"]["pedidos"][-1]["texto"],
          "pedido gravado na cena, marcado como ditado")
    _, et, pend = card(vid)
    checa("doc_orq_spec" in pend and et["spec"]["status"] == "andamento", "card: pendência do orquestrador para a cena")
    checa(any("Pedido na cena" in a["texto"] and "(voz)" in a["texto"] for a in cli.get(f"/api/videos/{vid}").json()["atividade"]),
          "atividade do card registra o pedido por voz")

    # ---- quadro e gancho do motor
    q = cli.get("/api/quadro").json()
    vq = next(x for x in q["videos"] if x["id"] == vid)
    checa(vq["formato"] == "horizontal_doc" and vq["total_etapas"] == len(ET.ETAPAS_HORIZONTAL_DOC), "quadro mostra o card documental")
    with conectar() as con:
        antes = motor.FILA.qsize()
        motor.verificar_direcao(con, vid)
        con.commit()
        checa(motor.FILA.qsize() == antes, "motor não põe direção do animado na fila do card documental")
    hist = json.loads((pasta / "estado.json").read_text(encoding="utf-8"))["historico"]
    checa(any("aprovado" in h["evento"] for h in hist), "histórico do estado.json registra as aprovações")

    vid7, proj7 = fase_7a()
    fase_7c(vid7, proj7)
    print(f"\n{n_ok} checagens, {len(falhas)} falhas")
    return 1 if falhas else 0


# ================================================================ fase 7a: Roteiro, Voz guia, Gravação, Ressincronização
# Tudo do Runeterra (roteirista + pesquisa, conferência, voz guia, limpeza, alinhamento) rodando no card documental,
# com o motor chamado tarefa a tarefa (sem thread) e os serviços externos trocados por fictícios: o Claude vira
# "orquestrador" (respostas gravadas aqui), Wikipedia/OpenF1/Fish/Whisper respondem dados fixos. O alinhamento por
# palavra (tools/audio/alinhar.py) e a retemporização da SPEC (diretor) são os reais.
OF1_S = {"Q": {"session_key": 9908, "session_name": "Qualifying", "year": 2025, "circuit_short_name": "Monza", "location": "Monza",
               "country_name": "Italy"},
         "R": {"session_key": 9912, "session_name": "Race", "year": 2025, "circuit_short_name": "Monza", "location": "Monza",
               "country_name": "Italy"},
         "IMOLA": {"session_key": 9990, "session_name": "Qualifying", "year": 2025, "circuit_short_name": "Imola", "location": "Imola",
                   "country_name": "Italy"}}
OF1 = {   # números reais da classificação de Monza 2025 (os do exemplo do diretor), em formato OpenF1
    ("sessions", (("year", 2025),)): list(OF1_S.values()),
    ("sessions", (("session_key", 9908),)): [OF1_S["Q"]],
    ("drivers", (("session_key", 9908),)): [{"driver_number": 16, "name_acronym": "LEC", "last_name": "Leclerc", "full_name": "Charles LECLERC"},
                                            {"driver_number": 44, "name_acronym": "HAM", "last_name": "Hamilton", "full_name": "Lewis HAMILTON"},
                                            {"driver_number": 1, "name_acronym": "VER", "last_name": "Verstappen", "full_name": "Max VERSTAPPEN"}],
    ("laps", (("driver_number", 16), ("session_key", 9908))): [{"lap_number": 10, "lap_duration": 79.31}, {"lap_number": 16, "lap_duration": 79.007},
                                                                {"lap_number": 17, "lap_duration": None}],
    ("laps", (("driver_number", 44), ("session_key", 9908))): [{"lap_number": 16, "lap_duration": 79.124}],
    ("session_result", (("session_key", 9908),)): [{"position": 1, "driver_number": 1, "number_of_laps": 18},
                                                   {"position": 4, "driver_number": 16, "number_of_laps": 20},
                                                   {"position": 6, "driver_number": 44, "number_of_laps": 19}],
    ("session_result", (("driver_number", 16), ("session_key", 9908))): [{"position": 4, "driver_number": 16, "number_of_laps": 20}],
}
CHAMADAS_OF1: list[str] = []


def _of1(endpoint, **params):
    CHAMADAS_OF1.append(endpoint)
    return OF1.get((endpoint, tuple(sorted(params.items()))), [])


def _embed(textos):
    """Embedding fictício (saco de palavras com hash): sem baixar/rodar o modelo de frases na GPU."""
    import hashlib

    import numpy as np

    m = np.zeros((len(textos), 64))
    for k, t in enumerate(textos):
        for w in str(t).lower().split():
            m[k, int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)


def _drenar(vid: int) -> list[str]:
    """Roda as tarefas da fila deste card, uma a uma, como o trabalhador do motor (mesma função `motor.executar`)."""
    feitas = []
    while not motor.FILA.empty():
        v, nome = motor.FILA.get()
        if v == vid:
            motor.executar(v, nome)
            feitas.append(nome)
    return feitas


def _responder(proj: Path, tarefa: str, texto: str) -> Path:
    """O que o chat/orquestrador faz: lê o prompt pendente e grava a resposta no caminho pedido."""
    t = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))[tarefa]
    Path(t["resposta"]).write_text(texto, encoding="utf-8")
    return Path(t["prompt"])


def fase_7a() -> None:
    import contextlib
    import wave

    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "audio"))
    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "direcao"))
    import claude_cli
    import limpar_gravacao
    import tempos
    import voz_guia

    from app.servidor import conferencia as CF
    from app.servidor import openf1 as OFM
    from app.servidor import pesquisa as PQ

    print("— fase 7a")
    motor._TravaGlobal = contextlib.nullcontext   # sem a trava de máquina real (dados/comum/motor.lock)
    claude_cli.EXE = Path("NAO_EXISTE/claude.exe")   # qualquer `claude -p` falharia: o card documental não pode chamar
    OFM._obter = _of1
    CF._embed = PQ._embed = _embed
    wiki = [("wiki: 2025 Italian Grand Prix", "Charles Leclerc qualified fourth for Ferrari at Monza in 2025; Lewis Hamilton "
             "was sixth. Max Verstappen took pole position with a lap record.")]
    CF._wiki = PQ._wiki = lambda busca: list(wiki)
    CF._pagina_do_personagem = lambda nome: []
    roteiro = (ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8")
    toks = roteiro.split()

    vid = cli.post("/api/videos", json={"titulo": "Monza 2025: Leclerc × Hamilton", "formato": "horizontal_doc"}).json()["id"]
    v, et, _ = card(vid)
    proj = motor.PASTA_PROJETOS / v["slug"]
    pasta = proj / "horizontal"
    checa(list(et) == [e["chave"] for e in ET.ETAPAS_HORIZONTAL_DOC] and {"voz_guia", "gravacao", "ressincronizacao"} <= set(et),
          "7a: card documental com Voz guia, Gravação e Ressincronização", str(list(et)))
    checa(ET.etapas_do_formato("horizontal_doc", {"roteiro", "voz_ia", "historia"}) == ET.ETAPAS_HORIZONTAL_DOC_V1,
          "7a: card documental antigo (com Narração voz_ia) continua no fluxo antigo")
    cli.patch(f"/api/videos/{vid}/mover", json={"coluna": "roteiro"})

    # ---- Roteirista + pesquisa (Wikipedia + OpenF1) pelo orquestrador, sem `claude -p`
    r = cli.post(f"/api/videos/{vid}/roteiro/gerar", json={"minutos": 1, "notas": "comparar LEC × HAM na classificação"})
    checa(r.status_code == 200, "7a: pedir roteiro ao roteirista", r.text)
    feitas = _drenar(vid)
    checa(feitas == ["roteiro"], "7a: tarefa do roteirista rodou", str(feitas) + str(card(vid)[0]["atividade"][:3]))
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    _, et, pend = card(vid)
    checa("roteiro" in agu and "pesquisa-assuntos" in agu["roteiro"]["prompt"] and "orq_roteiro" in pend
          and et["roteiro"]["detalhe"] == "aguardando o orquestrador", "7a: pesquisa pausa no prompt dos assuntos (pendência do orquestrador)", str(agu))
    pr = Path(agu["roteiro"]["prompt"]).read_text(encoding="utf-8")
    checa("SESSÕES de F1" in pr and "OpenF1" in pr and "## SISTEMA" in pr, "7a: prompt dos assuntos pede as sessões do OpenF1")
    r = cli.post(f"/api/videos/{vid}/doc/orquestrador/continuar")
    checa(r.status_code == 409 and "ainda não" in r.json()["detail"], "7a: continuar sem resposta gravada é recusado", r.text)
    _responder(proj, "roteiro", json.dumps({"assuntos": [{"nome": "Charles Leclerc", "busca": "Charles Leclerc"}], "afirmacoes": [],
                                            "sessoes": [{"ano": 2025, "local": "Monza", "sessao": "Qualifying", "pilotos": ["LEC", "HAM"]}]}))
    r = cli.post(f"/api/videos/{vid}/doc/orquestrador/continuar")
    checa(r.status_code == 200 and r.json()["retomadas"] == ["roteiro"], "7a: resposta gravada → roteirista continua", r.text)
    _drenar(vid)
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    checa("pesquisa-fatos" in agu["roteiro"]["prompt"], "7a: pausa seguinte = dossiê de fatos", agu["roteiro"]["prompt"])
    _responder(proj, "roteiro", json.dumps({"fatos": [{"assunto": "Charles Leclerc", "fato": "Leclerc largou em 4º em Monza 2025.",
                                                       "fonte": 0, "canon": "atual"}]}))
    doc(vid)   # a página aberta (GET /doc) também retoma sozinha
    _drenar(vid)
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    pr = Path(agu["roteiro"]["prompt"]).read_text(encoding="utf-8")
    checa("roteiro-gerar" in agu["roteiro"]["prompt"] and "melhor volta 1:19,007" in pr and "OpenF1" in pr,
          "7a: o roteirista recebe os números do OpenF1 no dossiê", pr[:300])
    dossie = json.loads((proj / "direcao" / "dossie.json").read_text(encoding="utf-8")) if (proj / "direcao" / "dossie.json").exists() else None
    _responder(proj, "roteiro", roteiro)
    doc(vid)
    feitas = _drenar(vid)
    dossie = json.loads((proj / "direcao" / "dossie.json").read_text(encoding="utf-8"))
    of_fatos = [f["fato"] for f in dossie["fatos"] if f["assunto"] == "OpenF1"]
    checa(any("4º LEC" in f for f in of_fatos) and any("HAM (carro 44): melhor volta 1:19,124" in f for f in of_fatos),
          "7a: dossiê com resultado e melhores voltas do OpenF1", str(of_fatos))
    checa((proj / "direcao" / "roteiro.txt").read_text(encoding="utf-8").strip() == roteiro.strip() and "conferencia" in feitas,
          "7a: roteiro gerado vira versão nova e a conferência roda em seguida", str(feitas))

    # ---- Conferência: afirmações (orquestrador) → Wikipedia + OpenF1 (local) → vereditos (orquestrador)
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    checa(list(agu) == ["conferencia"] and "conferencia-afirmacoes" in agu["conferencia"]["prompt"], "7a: conferência pausa nas afirmações", str(agu))
    checa("`openf1`" in Path(agu["conferencia"]["prompt"]).read_text(encoding="utf-8"), "7a: prompt da conferência pede o `openf1` dos números")
    conf = cli.get(f"/api/videos/{vid}/roteiro/conferencia").json()
    checa("conferencia" in conf["orquestrador"], "7a: painel do Roteiro mostra a conferência aguardando o orquestrador")
    afirm = [
        {"p": 0, "trecho": "Leclerc marcou 1:19,007 na volta 16", "afirmacao": "Leclerc fez 1:19,007 na volta 16", "busca": "Charles Leclerc",
         "openf1": {"tipo": "tempo_volta", "ano": 2025, "local": "Monza", "sessao": "Qualifying", "piloto": "LEC", "volta": 16, "valor": 79.007, "casas": 3}},
        {"p": 0, "trecho": "A diferença foi de só 0,117 segundo", "afirmacao": "LEC foi 0,117 s mais rápido que HAM", "busca": "Lewis Hamilton",
         "openf1": {"tipo": "diferenca", "ano": 2025, "local": "Monza", "sessao": "Qualifying", "piloto": 16, "piloto2": "HAM", "volta": 16, "valor": 0.117, "casas": 3}},
        {"p": 0, "trecho": "Leclerc marcou", "afirmacao": "Leclerc terminou a classificação em 3º", "busca": "Leclerc",
         "openf1": {"tipo": "posicao_final", "ano": 2025, "local": "Monza", "sessao": "Qualifying", "piloto": "LEC", "valor": 3}},
        {"p": 0, "trecho": "Monza", "afirmacao": "Monza recebeu a F1 em 2019", "busca": "Monza",
         "openf1": {"tipo": "voltas_total", "ano": 2019, "local": "Monza", "sessao": "Race", "valor": 53}},
        {"p": 0, "trecho": "os dois correram com o mesmo carro", "afirmacao": "Leclerc e Hamilton correram pela Ferrari", "busca": "Ferrari"},
    ]
    _responder(proj, "conferencia", json.dumps({"afirmacoes": afirm}, ensure_ascii=False))
    doc(vid)
    checa(vid in motor.CONFERINDO, "7a: conferência retomada (roteiro não aprova enquanto confere)")
    _drenar(vid)
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    checa("conferencia-fatos" in agu["conferencia"]["prompt"], "7a: pausa seguinte = vereditos")
    vered = [{"i": k, "veredito": "sem_fonte", "explicacao": "a wiki não traz o tempo", "trecho": -1, "fontes": 0} for k in range(4)]
    vered.append({"i": 4, "veredito": "confere", "explicacao": "a wiki cita os dois na Ferrari", "trecho": 0, "fontes": 1})
    _responder(proj, "conferencia", json.dumps({"vereditos": vered}, ensure_ascii=False))
    doc(vid)
    _drenar(vid)
    conf = cli.get(f"/api/videos/{vid}/roteiro/conferencia").json()
    fatos = {f["afirmacao"]: f for f in (conf["conferencia"] or {}).get("fatos", [])}
    checa(conf["atual"] and not conf["orquestrador"] and "erro_fatos" not in conf["conferencia"], "7a: conferência terminou sem `claude -p`",
          str(conf["conferencia"])[:300])
    f1 = fatos.get("Leclerc fez 1:19,007 na volta 16", {})
    checa(f1.get("veredito") == "confere" and f1.get("openf1", {}).get("status") == "confere" and "session_key 9908" in (f1.get("fonte") or {}).get("fonte", ""),
          "7a: tempo de volta confere com o OpenF1 (fonte = sessão)", str(f1))
    checa(fatos.get("LEC foi 0,117 s mais rápido que HAM", {}).get("veredito") == "confere", "7a: diferença 0,117 s confere com o OpenF1")
    f3 = fatos.get("Leclerc terminou a classificação em 3º", {})
    checa(f3.get("veredito") == "diverge" and "4º" in f3.get("explicacao", "") and "3º" in f3.get("explicacao", ""),
          "7a: posição errada diverge com o valor do OpenF1", str(f3))
    f4 = fatos.get("Monza recebeu a F1 em 2019", {})
    checa(f4.get("openf1", {}).get("status") == "sem_dados" and f4.get("veredito") == "sem_fonte", "7a: antes de 2023 = sem dados no OpenF1 (fica a Wikipedia)", str(f4))
    checa(fatos.get("Leclerc e Hamilton correram pela Ferrari", {}).get("veredito") == "confere" and "openf1" not in fatos.get("Leclerc e Hamilton correram pela Ferrari", {}),
          "7a: afirmação sem número segue só a Wikipedia")
    _, et, pend = card(vid)
    checa("orq_conferencia" not in pend and "orq_roteiro" not in pend, "7a: pendências do orquestrador fechadas")
    checa(OFM.conferir({"tipo": "tempo_volta", "ano": 2025, "local": "Italy", "sessao": "Qualifying", "piloto": "LEC", "valor": 79.0})["status"] == "sem_dados",
          "7a: local ambíguo (2 circuitos na Itália) não decide nada")
    checa(OFM.conferir({"tipo": "tempo_volta", "session_key": 9908, "piloto": "LEC", "volta": "melhor", "valor": 79.0, "casas": 1})["status"] == "confere"
          and OFM.conferir({"tipo": "tempo_volta", "session_key": 9908, "piloto": "LEC", "volta": "melhor", "valor": 79.1, "casas": 1})["status"] == "diverge",
          "7a: tolerância = meia unidade da casa dita (1:19,0 confere; 1:19,1 não)")

    # ---- aprovar → Voz guia (Fish fictício) → tempos por palavra → História/SPEC nos tempos da voz guia
    def gerar_fish(texto, saida, fator=None, **_):
        saida.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(saida), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(8000), w.writeframes(b"\0\0" * 8000)
        return {"duracao": 41.0, "motores": ["fish (fictício)"], "ppm_original": 150, "fator_exato": 1.0}

    guia = [{"t": t, "i": round(k * 0.45, 3), "f": round(k * 0.45 + 0.4, 3)} for k, t in enumerate(toks)]

    def medir(audio, rot, cache):
        cache.write_text(json.dumps(guia, ensure_ascii=False), encoding="utf-8")
        return guia

    voz_guia.gerar, tempos.tempos_da_narracao = gerar_fish, medir
    r = cli.post(f"/api/videos/{vid}/roteiro/aprovar")
    checa(r.status_code == 200, "7a: aprovar roteiro", r.text)
    checa(_drenar(vid) == ["voz_guia"], "7a: roteiro aprovado → voz guia na fila (como no Runeterra)")
    _, et, _ = card(vid)
    checa(et["voz_guia"]["status"] == "concluido" and "fish" in et["voz_guia"]["resumo"], "7a: card Voz guia concluído", str(et["voz_guia"]))
    d = doc(vid)
    checa(d["narracao"] == "guia" and d["entradas"]["tempos"] == "medidos" and json.loads((pasta / "palavras.json").read_text(encoding="utf-8"))[5]["i"] == guia[5]["i"],
          "7a: tempos da voz guia viram palavras.json do diretor", str(d.get("narracao")))
    cli.post(f"/api/videos/{vid}/doc/passo/historia")
    orquestrador(pasta, "historia", json.loads((ambiente.EXEMPLO / "resposta_historia.json").read_text(encoding="utf-8")))
    cli.post(f"/api/videos/{vid}/doc/aprovar/historia")
    cli.post(f"/api/videos/{vid}/doc/passo/spec")
    orquestrador(pasta, "spec", json.loads((ambiente.EXEMPLO / "resposta_spec.json").read_text(encoding="utf-8")))
    r = cli.post(f"/api/videos/{vid}/doc/aprovar/spec")
    checa(r.status_code == 200, "7a: SPEC aprovada nos tempos da voz guia", r.text[:200])
    cli.post(f"/api/videos/{vid}/doc/passo/ativos")
    cli.post(f"/api/videos/{vid}/doc/passo/verificacao")
    spec_guia = json.loads((pasta / "spec.json").read_text(encoding="utf-8"))
    checa(spec_guia["cenas"][2]["t0"] == guia[spec_guia["cenas"][2]["i0"]]["i"], "7a: SPEC nos tempos da voz guia")

    # ---- Gravação (upload, limpeza fictícia) → ponto de controle → aprovar → Ressincronização (alinhar real + retemporizar)
    meio = len(toks) // 2
    narradas = [{"t": t, "i": round(k * 0.45 + (1.5 if k >= meio else 0), 3), "f": round(k * 0.45 + 0.4 + (1.5 if k >= meio else 0), 3)}
                for k, t in enumerate(toks)]   # sua voz: igual à guia até o meio, depois 1,5 s mais lenta

    def limpar_fake(original, pasta_g, rot, **_):
        pasta_g.mkdir(parents=True, exist_ok=True)
        (pasta_g / "palavras.json").write_text(json.dumps(narradas, ensure_ascii=False), encoding="utf-8")
        with wave.open(str(pasta_g / "limpa.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(8000), w.writeframes(b"\0\0" * 8000)
        return {"duracao_original": 50.0, "duracao_limpa": narradas[-1]["f"], "removidos": [], "pausas_encurtadas": [],
                "divergencias_do_roteiro": []}

    limpar_gravacao.limpar = limpar_fake
    r = cli.post(f"/api/videos/{vid}/gravacao", files={"arquivo": ("minha_voz.wav", b"RIFF0000WAVEfmt ", "audio/wav")})
    checa(r.status_code == 200, "7a: upload da gravação (como no Runeterra)", r.text)
    checa(_drenar(vid) == ["gravacao"], "7a: gravação limpa na fila")
    _, et, pend = card(vid)
    checa(et["gravacao"]["status"] == "atencao" and "aprovar_gravacao" in pend and "vídeo final 1920×1080" in next(
        p["texto"] for p in card(vid)[0]["pendencias"] if p["chave"] == "aprovar_gravacao"), "7a: ponto de controle: confira a gravação limpa")
    checa(doc(vid)["narracao"] == "guia" and not (proj / "direcao" / "tempos_gravacao.json").exists(),
          "7a: nada é ressincronizado antes de aprovar a gravação")
    r = cli.post(f"/api/videos/{vid}/gravacao/aprovar")
    checa(r.status_code == 200 and _drenar(vid) == ["final"], "7a: aprovar gravação → ressincronização", r.text)
    v, et, pend = card(vid)
    spec_voz = json.loads((pasta / "spec.json").read_text(encoding="utf-8"))
    d = doc(vid)
    cg, cv = spec_guia["cenas"], spec_voz["cenas"]
    mudou = [b["id"] for a, b in zip(cg, cv) if (a["t0"], a["t1"]) != (b["t0"], b["t1"])]
    iguais = [b["id"] for a, b in zip(cg, cv) if b["i1"] <= meio and (a["t0"], a["t1"]) == (b["t0"], b["t1"])]
    checa([c["id"] for c in cg] == [c["id"] for c in cv] and [c["i0"] for c in cg] == [c["i0"] for c in cv],
          "7a: ressinc mantém cenas, ids e índices (âncora por palavra)")
    checa(bool(mudou) and len(mudou) < len(cv) and all(c["i1"] > meio for c in cv if c["id"] in mudou) and iguais,
          "7a: só as cenas depois do trecho mais lento mudaram de tempo", f"mudou={mudou} iguais={iguais}")
    checa(all(abs(b["t0"] - (a["t0"] + 1.5)) < 0.002 for a, b in zip(cg, cv) if b["i0"] >= meio and b["i0"] > 0),
          "7a: cena afetada anda exatamente o atraso da sua voz (1,5 s)")
    checa(et["ressincronizacao"]["status"] == "concluido" and et["ressincronizacao"]["resumo"] == f"{len(mudou)} de {len(cv)} cenas retemporizadas",
          "7a: card Ressincronização com as cenas afetadas", str(et["ressincronizacao"]))
    checa(d["narracao"] == "gravacao" and d["ressinc"]["afetadas"] == mudou and d["ressinc"]["narracao"] == "gravacao", "7a: painel mostra a ressincronização")
    est = d["estado"]["etapas"]
    checa(est["spec"]["status"] == "aprovado" and est["ativos"]["status"] == "desatualizado" and est["verificacao"]["status"] == "desatualizado",
          "7a: SPEC continua aprovada ★; ativos e verificação ficam desatualizados", str({k: x["status"] for k, x in est.items()}))
    r = cli.post(f"/api/videos/{vid}/doc/passo/verificacao")
    codigos = {e["codigo"] for e in r.json()["verificacao"]["erros"]}
    checa(r.status_code == 200 and "TEMPO" not in codigos, "7a: verificação nos tempos novos sem erro de TEMPO", str(codigos))
    checa(et["gravacao"]["status"] == "concluido" and v["coluna"] != "revisao", "7a: sem render do Runeterra no documentário (fase 7c)")
    checa(claude_cli.EXE.name == "claude.exe" and not claude_cli.EXE.exists(), "7a: nenhuma etapa dependeu do Claude Code local")
    return vid, proj


# ================================================================ fase 7c: Render final + Publicação
# O render final de verdade (1080p60, NVENC/x264, mixagem com a gravação) é testado em testes/montador/testar.py com o
# mini-spec; aqui a SPEC de exemplo tem cenas sem receita no montador, então o motor roda um MONTADOR FICTÍCIO (mesmo
# protocolo: linhas PROG + final/final.json + final.mp4 1080p60 real de 2 s) para exercitar o card: progresso por
# bloco, versões final_vN, "Assista o vídeo final", desatualizado depois de mexer na SPEC, falha visível e a Publicação
# pelo orquestrador (capítulos da SPEC, miniatura de um quadro do final, concorrentes só com chave).
MONTADOR_FICTICIO = r"""
import json, subprocess, sys
from pathlib import Path
pasta, modo, spec_hash = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
(pasta / "final").mkdir(parents=True, exist_ok=True)
if modo == "falha":
    (pasta / "final" / "falhou.json").write_text(json.dumps({"erro": "cena c9 sem receita (fictício)"}), encoding="utf-8")
    print("FALHOU: cena c9"); sys.exit(1)
print("PROG 0.0000 renderizando 2 cena(s) em 1920×1080", flush=True)
print("PROG 0.2750 cena 1 de 2 (remotion)", flush=True)
print("PROG 0.5500 cena 2 de 2 (hyperframes, cache)", flush=True)
mp4 = pasta / "final" / "final.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=60:d=2", "-f", "lavfi", "-i",
                "sine=f=440:d=2", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(mp4)], check=True)
print("PROG 0.7600 bloco 1 de 2", flush=True)
print("PROG 0.9200 bloco 2 de 2 (cache)", flush=True)
print("PROG 1.0000 pronto: verificação aprovado", flush=True)
lf = {"lufs": -14.0, "pico_dbtp": -2.1}
(pasta / "final" / "final.json").write_text(json.dumps({"arquivo": str(mp4), "duracao": 2.0, "largura": 1920, "altura": 1080,
    "fps": 60, "codificador": "h264_nvenc", "spec_hash": spec_hash, "loudness": lf, "loudness_mp4": lf, "segundos": 1.0,
    "verificacao": {"status": "aprovado", "erros": [], "avisos": []}, "blocos": {"teto_s": 45, "codificados": 1, "do_cache": 1},
    "avisos": [], "creditos_sfx": ['"whoosh 3" de Fulano (https://freesound.org/x), CC BY 4.0'], "resumo": "2 cenas"}), encoding="utf-8")
"""


def fase_7c(vid: int, proj: Path) -> None:
    from PIL import Image

    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "direcao"))
    import claude_cli

    from app.servidor import horizontal_doc as HD
    from app.servidor import publicacao as PB

    print("— fase 7c")
    pasta = proj / "horizontal"
    v, et, pend = card(vid)
    checa(list(et)[-3:] == ["ressincronizacao", "render", "publicacao"], "7c: card com Render final entre Ressincronização e Publicação", str(list(et)))
    checa(et["render"]["status"] == "atencao" and "aprove ★ no storyboard" in (et["render"]["detalhe"] or "") and "final_doc" in pend,
          "7c: gravação ressincronizada sem todas as cenas ★: Render diz o que falta (sem erro, sem render)", str(et["render"]))
    r = cli.post(f"/api/videos/{vid}/doc/final")
    checa(r.status_code == 409 and "aprove ★ no storyboard" in r.json()["detail"] and "cena" in r.json()["detail"],
          "7c: “Renderizar o vídeo final” recusado com as cenas sem ★", r.text[:300])
    outro = cli.post("/api/videos", json={"titulo": "Card sem gravação", "formato": "horizontal_doc"}).json()["id"]
    po = motor.PASTA_PROJETOS / card(outro)[0]["slug"]
    (po / "direcao").mkdir(parents=True, exist_ok=True)
    (po / "direcao" / "roteiro.txt").write_text((ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8"), encoding="utf-8")
    r = cli.post(f"/api/videos/{outro}/doc/final")
    checa(r.status_code == 409 and "sua gravação" in r.json()["detail"], "7c: sem a sua gravação, nada de vídeo final", r.text[:300])
    with conectar() as con:   # card da 7a/7b (antes da etapa Render): ganha a linha na 1ª leitura
        con.execute("DELETE FROM etapas WHERE video_id=? AND chave='render'", (outro,))
        con.commit()
    doc(outro)
    with conectar() as con:
        linha = con.execute("SELECT status FROM etapas WHERE video_id=? AND chave='render'", (outro,)).fetchone()
    checa(linha is not None and linha[0] == "pendente", "7c: card documental antigo ganha a linha Render na 1ª leitura")

    # ---- render pelo motor (montador fictício, mesmo protocolo), barra por bloco, versões, Assista o vídeo final
    progresso: list[tuple] = []
    original = motor.definir_progresso
    motor.definir_progresso = lambda t, x, f=None, i=None: (progresso.append((x, f)), original(t, x, f, i))
    modo = {"m": "ok"}
    motor._plano_final = lambda slug: ({"cenas": 2, "avisos": [], "pasta_montador": str(pasta),
                                        "comando": [str(pasta), modo["m"], doc(vid)["spec_hash"]]}, None)
    motor._comando_final = lambda args: [sys.executable, "-c", MONTADOR_FICTICIO, *args]
    motor.executar(vid, "render_doc")
    v, et, pend = card(vid)
    ren = et["render"]
    arq = ambiente.RAIZ / ren["dados"].get("video", "x")
    checa(ren["status"] == "atencao" and arq.name == "final_v1.mp4" and arq.exists() and not (pasta / "final" / "final.mp4").exists(),
          "7c: final em saida/final_v1.mp4 (movido do montador)", str(ren))
    checa("1920×1080 60 q/s" in ren["detalhe"] and "-14.0 LUFS" in ren["detalhe"] and "NVENC" in ren["detalhe"]
          and "1 bloco(s) refeito(s), 1 do cache" in ren["detalhe"], "7c: card mostra resolução, loudness, codificador e blocos", ren["detalhe"])
    fr = [f for _, f in progresso if f is not None]
    checa(any(x == "bloco 2 de 2 (cache)" for x, _ in progresso) and fr == sorted(fr) and fr[-1] == 1.0,
          "7c: barra de progresso bloco a bloco, crescente", str(progresso)[:300])
    checa("ver_final" in pend and "final_doc" not in pend and v["coluna"] == "revisao", "7c: pendência “Assista o vídeo final” e card em Revisão")
    motor.executar(vid, "render_doc")
    v, et, _ = card(vid)
    checa(et["render"]["dados"]["video"].endswith("final_v2.mp4") and arq.exists(), "7c: render de novo = final_v2 (o v1 fica intacto)")

    # ---- mexeu na SPEC depois do final → desatualizado; render de novo → em dia
    c0 = doc(vid)["spec"]["cenas"][0]["id"]
    r = cli.post(f"/api/videos/{vid}/doc/cena/{c0}/ajuste", json={"acao": {"acao": "movimento", "tipo": "pan_dir"}, "previa": False})
    checa(r.status_code == 200, "7c: correção pós-final no storyboard (ação direta)", r.text[:200])
    doc(vid)
    _, et, pend = card(vid)
    checa(et["render"]["status"] == "atencao" and "SPEC mudou" in (et["render"]["detalhe"] or "") and "ver_final" not in pend
          and "doc_final" in pend, "7c: final desatualizado: “Assista” sai e o card pede outro render", str(et["render"]["detalhe"]))
    motor.executar(vid, "render_doc")
    doc(vid)
    _, et, pend = card(vid)
    checa(et["render"]["dados"]["video"].endswith("final_v3.mp4") and "ver_final" in pend and "doc_final" not in pend
          and not et["render"]["dados"].get("desatualizado"), "7c: render depois da correção volta a pedir “Assista”")
    modo["m"] = "falha"
    motor.executar(vid, "render_doc")
    _, et, pend = card(vid)
    erro = next((p["texto"] for p in card(vid)[0]["pendencias"] if p["chave"] == "erro_render_doc"), "")
    checa("cena c9 sem receita" in erro and et["render"]["status"] == "atencao", "7c: render que falha vira pendência com o motivo", erro)
    with conectar() as con:
        con.execute("UPDATE pendencias SET resolvida=1 WHERE video_id=? AND chave='erro_render_doc'", (vid,))
        con.commit()
    modo["m"] = "ok"
    motor.executar(vid, "render_doc")
    motor.definir_progresso = original

    # ---- “Vídeo aprovado” → Publicação pelo orquestrador (sem `claude -p`), sem chave do YouTube
    PB._chave_youtube = lambda: None
    chamadas_yt: list[str] = []
    pid = next(p["id"] for p in card(vid)[0]["pendencias"] if p["chave"] == "ver_final")
    checa(cli.post(f"/api/pendencias/{pid}/resolver").status_code == 200, "7c: “Vídeo aprovado”")
    _, et, _ = card(vid)
    checa(et["render"]["status"] == "concluido" and et["publicacao"]["status"] == "andamento", "7c: render concluído, publicação na fila")
    checa(_drenar(vid) == ["publicacao"], "7c: tarefa da publicação rodou")
    agu = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))
    _, et, pend = card(vid)
    pr = Path(agu.get("publicacao", {}).get("prompt", "x"))
    texto = pr.read_text(encoding="utf-8") if pr.exists() else ""
    checa("publicacao-doc" in pr.name and "orq_publicacao" in pend and "CENAS (id, início" in texto and '"miniatura"' in texto
          and "VÍDEOS QUE JÁ EXISTEM" not in texto, "7c: prompt da publicação para o orquestrador (cenas, miniatura; sem concorrentes sem chave)",
          pr.name)
    cenas = doc(vid)["spec"]["cenas"]
    alvo = cenas[1]
    _responder(proj, "publicacao", json.dumps({"titulos": [f"Título {k}" for k in range(6)], "gancho": "Leclerc e Hamilton em Monza.",
                                               "tags": ["F1", "Monza", "Leclerc", "Hamilton", "Ferrari", "classificação", "telemetria",
                                                        "OpenF1", "Fórmula 1", "2025"], "comentario_fixado": "Quem foi melhor?",
                                               "miniatura": {"texto": "0,117 s", "enquadramento": "gráfico à direita", "cena": alvo["id"]}},
                                              ensure_ascii=False))
    doc(vid)
    checa(_drenar(vid) == ["publicacao"], "7c: resposta gravada → publicação continua")
    pub = cli.get(f"/api/videos/{vid}/publicacao").json()
    t = pub["textos"] or {}
    _, et, pend = card(vid)
    checa(len(t.get("titulos", [])) == 6 and t["titulo"] == "Título 0" and len(t["tags"]) == 10 and t["comentario_fixado"],
          "7c: títulos (6 opções), tags e comentário fixado", str(t)[:200])
    checa("OpenF1" in t["descricao"] and "Formula One Licensing" in t["descricao"] and '"whoosh 3" de Fulano' in t["descricao"],
          "7c: descrição com créditos (OpenF1, SFX CC BY) e aviso legal do F1", t["descricao"][-300:])
    caps = t["capitulos"]
    fim = cenas[-1]["t1"]
    checa((not caps) or (caps[0]["tempo"] == "0:00" and len(caps) >= 3 and all(
        (b["inicio"] if b else fim) - a["inicio"] >= 10 for a, b in zip(caps, caps[1:] + [None]))),
        "7c: capítulos da SPEC seguem as regras do YouTube (0:00, ≥ 3, ≥ 10 s)", str(caps))
    m = t.get("miniatura") or {}
    quadro = ambiente.RAIZ / (t.get("thumbnail") or "x")
    checa(m.get("cena") == alvo["id"] and m.get("texto") == "0,117 s" and quadro.exists() and Image.open(quadro).size == (1280, 720),
          "7c: miniatura = texto/enquadramento sugeridos + quadro 1280×720 do final na cena escolhida", str(m))
    checa(t["concorrentes"]["status"] == "sem_chave" and t["video_publicar"].endswith("final_v4.mp4"),
          "7c: sem YOUTUBE_API_KEY a pesquisa de concorrentes é pulada (sem erro); vídeo para subir = último final", str(t.get("video_publicar")))
    checa(et["publicacao"]["status"] == "atencao" and "publicar" in pend and "orq_publicacao" not in pend, "7c: “Revise os textos e publique”")

    # ---- capítulos (regra), concorrentes com chave (YouTube Data API fictícia), erro da API não quebra
    tmp = BASE / "caps" / "horizontal"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "historia.json").write_text(json.dumps({"capitulos": [{"id": f"c{k}", "titulo": f"Parte {k}"} for k in range(1, 5)]}), encoding="utf-8")
    (tmp / "spec.json").write_text(json.dumps({"cenas": [{"id": "a", "capitulo": "c1", "t0": 0.4, "t1": 12}, {"id": "b", "capitulo": "c2", "t0": 12, "t1": 15},
                                                         {"id": "c", "capitulo": "c3", "t0": 15, "t1": 30}, {"id": "d", "capitulo": "c4", "t0": 30, "t1": 50}]}),
                                   encoding="utf-8")
    caps = PB.capitulos_doc(tmp.parent)
    checa([(c["titulo"], c["tempo"]) for c in caps] == [("Parte 1", "0:00"), ("Parte 3", "0:15"), ("Parte 4", "0:30")],
          "7c: capítulo de 3 s junta com o anterior; 1º em 0:00", str(caps))

    def yt(recurso, params):
        chamadas_yt.append(recurso)
        assert params["key"] == "CHAVE_FICTICIA"
        if recurso == "search":
            return {"items": [{"id": {"videoId": "a1"}, "snippet": {"title": "Monza 2025 explicado", "channelTitle": "Canal A", "publishedAt": "2025-09-07"}},
                              {"id": {"videoId": "b2"}, "snippet": {"title": "Leclerc x Hamilton", "channelTitle": "Canal B", "publishedAt": "2025-09-08"}}]}
        return {"items": [{"id": "a1", "statistics": {"viewCount": "1200"}}, {"id": "b2", "statistics": {"viewCount": "56000"}}]}

    PB._chave_youtube, PB._youtube = (lambda: "CHAVE_FICTICIA"), yt
    c = PB.concorrentes(proj, "Monza 2025: Leclerc × Hamilton")
    c2 = PB.concorrentes(proj, "Monza 2025: Leclerc × Hamilton")
    checa(c["status"] == "ok" and [i["views"] for i in c["itens"]] == [56000, 1200] and chamadas_yt == ["search", "videos"] and c2 == c,
          "7c: com chave: concorrentes (título, canal, views) pela YouTube Data API, com cache", str(c)[:200])
    try:
        with claude_cli.pelo_orquestrador(BASE / "orq_teste"):
            PB.gerar_textos_doc(proj, "Monza 2025: Leclerc × Hamilton", 40.0, None)
        prompt_c = ""
    except claude_cli.PrecisaOrquestrador as e:
        prompt_c = e.prompt.read_text(encoding="utf-8")
    checa("VÍDEOS QUE JÁ EXISTEM" in prompt_c and "Leclerc x Hamilton · Canal B · 56.000 views" in prompt_c,
          "7c: os concorrentes entram no prompt da publicação", prompt_c[-400:])

    def yt_erro(recurso, params):
        raise OSError("HTTP 403 quotaExceeded")

    PB._youtube = yt_erro
    e = PB.concorrentes(proj, "outro tema")
    checa(e["status"] == "erro" and "quotaExceeded" in e["aviso"] and not e["itens"], "7c: erro da API (cota) não quebra a publicação", str(e))
    checa(not claude_cli.EXE.exists(), "7c: nada dependeu do Claude Code local")
    checa(HD.FORMATO == "horizontal_doc", "7c: formato do card documental")


if __name__ == "__main__":
    try:
        codigo = principal()
    finally:
        if "--manter" not in sys.argv:
            shutil.rmtree(BASE, ignore_errors=True)
    sys.exit(codigo)
