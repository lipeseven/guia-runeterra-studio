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

    print(f"\n{n_ok} checagens, {len(falhas)} falhas")
    return 1 if falhas else 0


if __name__ == "__main__":
    try:
        codigo = principal()
    finally:
        if "--manter" not in sys.argv:
            shutil.rmtree(BASE, ignore_errors=True)
    sys.exit(codigo)
