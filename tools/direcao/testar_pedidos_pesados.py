r"""Testes automáticos dos PEDIDOS PESADOS (pedido de cena que vai para o orquestrador no lugar do diretor), com dados
fictícios e sem modelo (o `claude -p` é trocado por respostas fixas). Sem pytest: sai com código 1 se algo falhar.

    .venv\Scripts\python.exe tools\direcao\testar_pedidos_pesados.py            (F1/vertical e, em outro processo, Runeterra)
    .venv\Scripts\python.exe tools\direcao\testar_pedidos_pesados.py --canal runeterra

Os dados do canal (banco, projetos...) apontam para `dados/testes/pedidos_pesados_<canal>/` da pasta do código (fora do
Git); nada toca os painéis 8765/8766 nem os projetos reais. O render nunca roda: a fila do motor só é conferida.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
CANAL_TESTE = sys.argv[sys.argv.index("--canal") + 1] if "--canal" in sys.argv else "f1"
os.environ["GRS_CANAL"] = CANAL_TESTE
os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(AQUI))

import canal  # noqa: E402

BASE = RAIZ / "dados" / "testes" / f"pedidos_pesados_{CANAL_TESTE}"
if BASE.exists():
    shutil.rmtree(BASE)   # pasta de teste nossa (nunca junção)
BASE.mkdir(parents=True)
for chave in list(canal.CANAL["pastas"]):
    if chave != "docs":
        destino = BASE / chave
        canal.CANAL["pastas"][chave] = str(destino.with_suffix(".db") if chave in ("studio", "banco_acervo") else destino)
(BASE / "projetos").mkdir()

from fastapi.testclient import TestClient  # noqa: E402

from app.servidor import motor, storyboard  # noqa: E402

motor.iniciar = lambda: None
motor.pedir_acervo = lambda: None
storyboard.preaquecer_busca = lambda: None
from app.servidor.banco import conectar  # noqa: E402
from app.servidor.main import app  # noqa: E402

import pedidos_pesados as PP  # noqa: E402

cli = TestClient(app)
FALHAS: list[str] = []
OK = 0


def checa(cond, msg: str) -> None:
    global OK
    if cond:
        OK += 1
    else:
        FALHAS.append(msg)
        print("FALHOU:", msg)


def esvaziar_fila() -> list:
    itens = []
    while not motor.FILA.empty():
        itens.append(motor.FILA.get_nowait())
    return itens


def pendencias(vid: int) -> dict:
    return {p["chave"]: p for p in cli.get(f"/api/videos/{vid}").json()["pendencias"]}


def cli_pp(*args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cod = PP.main(list(args))
    return cod, buf.getvalue()


# ======================================================================================== F1 / vertical
def testar_vertical() -> None:
    import vertical as V

    print("1. vertical: pedido pesado manual (por cena e geral)")
    vid = cli.post("/api/videos", json={"titulo": "Teste pedido pesado", "formato": "vertical"}).json()["id"]
    slug = cli.get(f"/api/videos/{vid}").json()["slug"]
    proj = motor.PASTA_PROJETOS / slug
    dirc = proj / "direcao"
    for s in ("direcao", "trabalho/conferencia_cenas", "saida"):
        (proj / s).mkdir(parents=True, exist_ok=True)
    roteiro = "Abre a cena aqui. A asa traseira abre na reta. O carro some no fim."
    pal = [{"t": w, "i": k * 0.4, "f": k * 0.4 + 0.35} for k, w in enumerate(roteiro.split())]
    planos, _ = V.resolver([
        {"em": "Abre a cena aqui.", "set": "estudio", "clima": "vazio", "codigo": "const w=c.w;"},
        {"em": "A asa traseira abre na reta.", "set": "pista", "clima": "sol", "codigo": "const a=c.carro;\na.asa(1);"},
        {"em": "O carro some no fim.", "set": "pista", "clima": "sol", "codigo": "c.carro.sumir();"},
    ], pal)
    (dirc / "vertical.json").write_text(json.dumps({"planos": planos, "avisos": []}, ensure_ascii=False), encoding="utf-8")
    (dirc / "tempos_voz.json").write_text(json.dumps(pal), encoding="utf-8")
    (dirc / "roteiro.txt").write_text(roteiro, encoding="utf-8")
    (proj / "saida" / "final_v1.mp4").write_bytes(b"x")
    (proj / "trabalho" / "conferencia_cenas" / "001.jpg").write_bytes(b"\xff\xd8quadro")
    a, b, c = (p["id"] for p in planos)

    r = cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": a, "texto": "câmera mais perto"})
    checa(r.status_code == 200, "pedido normal anotado")
    r = cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": b, "texto": "a asa deve abrir com DRS animado", "pesado": True})
    checa(r.status_code == 200 and r.json().get("pedido_pesado"), f"pedido com pesado=true vira pedido pesado: {r.text[:200]}")
    item = r.json()["pedido_pesado"]
    md = Path(item["arquivo"])
    checa(md.exists() and md.name == f"pedido_pesado_{item['id']}.md" and md.parent == proj / "orquestrador", "arquivo orquestrador/pedido_pesado_<id>.md")
    txt = md.read_text(encoding="utf-8")
    checa("a asa deve abrir com DRS animado" in txt and "cena 2" in txt and "A asa traseira abre na reta." in txt, "md tem texto, cena e fala")
    checa("a.asa(1);" in txt and str(dirc / "vertical.json") in txt, "md tem o código da cena e o caminho do vertical.json")
    checa(item["quadro"] and Path(item["quadro"]).exists() and "quadro" in txt, "quadro de conferência copiado e citado no md")
    pend = pendencias(vid)
    checa("orq_pedido_pesado" in pend and "1 pedido" in pend["orq_pedido_pesado"]["titulo"], "pendência orq_pedido_pesado no card")
    quadro = cli.get("/api/quadro").json()
    checa(any(v["id"] == vid and "orquestrador" in (v["aguardando"] or "") for v in quadro["videos"]), "card mostra 'aguardando o orquestrador'")
    g = cli.get("/api/pedidos-pesados").json()
    checa(g["abertos"] == 1 and g["pedidos"][0]["id"] == item["id"] and g["pedidos"][0]["titulo"] == "Teste pedido pesado",
          "GET /api/pedidos-pesados lista o pedido do card")
    an = cli.get(f"/api/videos/{vid}/animacao").json()
    checa(len(an["pedidos"]) == 2 and an["pedidos"][1].get("pesado") == item["id"] and len(an["pesados"]) == 1,
          "animação mostra o pedido marcado (pesado) e a lista de pesados")
    checa(motor.pedidos_do_diretor(dirc) == [an["pedidos"][0]], "o diretor só recebe o pedido normal")

    r = cli.post(f"/api/videos/{vid}/animacao/refazer", json={"so_render": True})
    checa(r.status_code == 400, "só renderizar recusa com pedido normal na fila")
    cli.delete(f"/api/videos/{vid}/animacao/pedido/0")
    r = cli.post(f"/api/videos/{vid}/animacao/refazer", json={})
    checa(r.status_code == 400 and "orquestrador" in r.text, "refazer com os pedidos recusa quando só há pedido pesado")
    r = cli.post(f"/api/videos/{vid}/animacao/refazer", json={"so_render": True})
    checa(r.status_code == 200 and esvaziar_fila() == [(vid, "rascunho")], "pedido pesado não trava o 'Só renderizar de novo'")

    # pedido geral já anotado → enviar ao orquestrador
    cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": None, "texto": "luz de pôr do sol no vídeo todo"})
    n = len(motor.pedidos_animacao(dirc)) - 1
    r = cli.post(f"/api/videos/{vid}/animacao/pedido/{n}/orquestrador")
    checa(r.status_code == 200 and motor.pedidos_animacao(dirc)[n].get("pesado"), "pedido geral da fila enviado ao orquestrador")
    checa(cli.post(f"/api/videos/{vid}/animacao/pedido/{n}/orquestrador").status_code == 400, "enviar de novo o mesmo pedido = 400")
    geral = r.json()["pedido_pesado"]
    checa("pedido geral" in Path(geral["arquivo"]).read_text(encoding="utf-8"), "md do pedido geral diz 'pedido geral'")
    checa("2 pedido" in pendencias(vid)["orq_pedido_pesado"]["titulo"], "pendência conta 2 pedidos pesados")

    print("2. vertical: promoção automática (nao_feitos com capacidade: true)")
    cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": c, "texto": "o carro deve deixar rastro de faíscas"})
    cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": a, "texto": "logo da equipe no canto"})
    resposta = {"planos": [], "remover": [], "nao_feitos": [
        {"id": c, "motivo": "a API não tem partículas de faísca", "capacidade": True},
        {"id": a, "motivo": "falta o arquivo F1/dados/logos/equipe.png", "capacidade": False}]}
    orig = V.chamar_json
    try:
        V.chamar_json = lambda *x, **k: resposta
        motor.tarefa_animacao(vid, revisar=True)
    finally:
        V.chamar_json = orig
    fila = motor.pedidos_animacao(dirc)
    faisca = next((p for p in fila if "faíscas" in p["texto"]), {})
    logo = next((p for p in fila if "logo" in p["texto"]), {})
    checa(bool(faisca.get("pesado")), "capacidade: true → o pedido vira pesado sozinho")
    checa(logo and not logo.get("pesado"), "capacidade: false (falta arquivo) continua com o diretor / aviso")
    abertos = PP.abertos(proj)
    auto = next((p for p in abertos if p["id"] == faisca.get("pesado")), {})
    checa(auto.get("origem") == "diretor" and "partículas" in auto.get("motivo", ""), "pedido pesado automático guarda o motivo do diretor")
    checa("partículas" in Path(auto["arquivo"]).read_text(encoding="utf-8") if auto else False, "md do automático tem o motivo")
    pend = pendencias(vid)
    checa("3 pedido" in pend["orq_pedido_pesado"]["titulo"], "pendência conta 3 pedidos pesados")
    checa("sem_mudanca" in pend, "o pedido que sobrou (logo) gera o aviso de 'não aplicou'")
    esvaziar_fila()

    # só pedidos de capacidade: sem pendência "não aplicou"
    cli.post(f"/api/pendencias/{pend['sem_mudanca']['id']}/resolver")
    cli.delete(f"/api/videos/{vid}/animacao/pedido/{fila.index(logo)}")
    cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": a, "texto": "zoom em espiral"})
    resposta2 = {"planos": [], "nao_feitos": [{"id": a, "motivo": "não existe câmera em espiral", "capacidade": True}]}
    try:
        V.chamar_json = lambda *x, **k: resposta2
        motor.tarefa_animacao(vid, revisar=True)
    finally:
        V.chamar_json = orig
    pend = pendencias(vid)
    checa("sem_mudanca" not in pend and "4 pedido" in pend["orq_pedido_pesado"]["titulo"],
          "todos os pedidos da rodada foram ao orquestrador: sem pendência 'não aplicou'")
    checa(not motor.pedidos_do_diretor(dirc), "fila do diretor vazia (só pesados)")

    # unidade: o diretor muda uma cena e devolve outra por capacidade (caminho normal, sem render)
    try:
        V.chamar_json = lambda *x, **k: {"planos": [{"id": a, "em": "Abre a cena aqui.", "set": "estudio", "clima": "vazio",
                                                    "codigo": "const w=c.w;w.chao.color.set('#222');"}],
                                         "nao_feitos": [{"id": c, "motivo": "sem partículas", "capacidade": True}]}
        r = V.revisar({"planos": planos, "avisos": []}, [{"plano": a, "texto": "chão escuro", "quando": "t1"},
                                                        {"plano": c, "texto": "faíscas", "quando": "t2"}], pal, "", None)
    finally:
        V.chamar_json = orig
    checa([x["pedido"]["texto"] for x in r.get("pesados", [])] == ["faíscas"], "revisar devolve 'pesados' casado com o pedido certo")
    checa(not any("pedido não feito" in x for x in r.get("avisos", [])), "pedido de capacidade não vira aviso 'pedido não feito'")
    import inspect
    checa('\\"capacidade\\": true' in inspect.getsource(V.revisar), "prompt do diretor pede o campo capacidade")

    print("3. CLI do orquestrador e resolver")
    cod, out = cli_pp("listar")
    checa(cod == 0 and "4 pedido(s) pesado(s) aberto(s)" in out and item["id"] in out and "partículas" in out, f"listar: {out[:300]}")
    checa(all(len(linha) < 260 for linha in out.splitlines()), "listar em linhas curtas")
    cod, out = cli_pp("mostrar", item["id"])
    checa(cod == 0 and "a asa deve abrir com DRS animado" in out, "mostrar imprime o md")
    cod, out = cli_pp("resolver", item["id"], "--nota", "asa com DRS na biblioteca", "--renderizar", "--porta", "8799")
    checa(cod == 0 and "abertos no card: 3" in out and "não renderizei" in out, f"resolver com outros abertos não renderiza: {out}")
    checa(not any(p.get("pesado") == item["id"] for p in motor.pedidos_animacao(dirc)), "resolvido sai da fila de pedidos")
    hist = json.loads((dirc / "historico_pedidos_vertical.json").read_text(encoding="utf-8"))
    checa(any(h.get("via") == "orquestrador" and h["texto"] == "a asa deve abrir com DRS animado" and h.get("nota") for h in hist),
          "resolvido vai para o histórico com via: orquestrador")
    checa("RESOLVIDO" in md.read_text(encoding="utf-8"), "md marcado como resolvido")
    checa(cli_pp("resolver", item["id"])[0] == 1, "resolver de novo = erro")
    checa(cli_pp("mostrar", "naoexiste")[0] == 1, "id desconhecido = erro")

    # descartar no painel um pedido pesado
    fila = motor.pedidos_animacao(dirc)
    k = next(i for i, p in enumerate(fila) if p.get("pesado") == geral["id"])
    cli.delete(f"/api/videos/{vid}/animacao/pedido/{k}")
    checa(next(p for p in PP.ler(proj) if p["id"] == geral["id"])["status"] == "descartado", "descartar no painel fecha o pedido pesado")

    # API: resolver o penúltimo; o último com renderizar → só renderizar na fila
    resto = PP.abertos(proj)
    checa(len(resto) == 2, "sobram 2 abertos")
    r = cli.post(f"/api/pedidos-pesados/{resto[0]['id']}/resolver", json={"nota": "feito", "renderizar": True})
    checa(r.status_code == 200 and r.json()["render"] is None and r.json()["pedido"]["restantes"] == 1, "API resolve sem renderizar com outro aberto")
    r = cli.post(f"/api/pedidos-pesados/{resto[1]['id']}/resolver", json={"nota": "feito", "renderizar": True})
    checa(r.status_code == 200 and r.json()["render"] == {"ok": True}, f"último resolvido dispara 'só renderizar': {r.text[:200]}")
    checa([i for i in esvaziar_fila() if i[1] != "orquestrador"] == [(vid, "rascunho")], "render do card na fila do motor")  # o orquestrador automático também entra na fila
    checa("orq_pedido_pesado" not in pendencias(vid), "sem pedido aberto: pendência fechada")
    checa(cli.get("/api/pedidos-pesados").json()["abertos"] == 0, "GET /api/pedidos-pesados zerado")
    checa(cli.post(f"/api/pedidos-pesados/{resto[1]['id']}/resolver", json={}).status_code == 409, "resolver resolvido pela API = 409")
    checa(cli.post("/api/pedidos-pesados/zzzzzzzz/resolver", json={}).status_code == 404, "id desconhecido pela API = 404")

    # resolver a pendência à mão no painel fecha todos
    cli.post(f"/api/videos/{vid}/animacao/pedido", json={"plano": b, "texto": "pneu derretendo", "pesado": True})
    pid = pendencias(vid)["orq_pedido_pesado"]["id"]
    cli.post(f"/api/pendencias/{pid}/resolver")
    checa(not PP.abertos(proj) and not any(p.get("pesado") for p in motor.pedidos_animacao(dirc)),
          "resolver a pendência no painel fecha os pedidos pesados do card")

    # vertical.json intacto (nenhum render, nenhuma direção nova além das rodadas sem mudança)
    checa(json.loads((dirc / "vertical.json").read_text(encoding="utf-8"))["planos"] == planos, "direção do card não mudou")


# ======================================================================================== Runeterra / storyboard
def testar_storyboard() -> None:
    print("4. Runeterra: storyboard → orquestrador")
    vid = cli.post("/api/videos", json={"titulo": "Teste storyboard pesado"}).json()["id"]
    slug = cli.get(f"/api/videos/{vid}").json()["slug"]
    proj = motor.PASTA_PROJETOS / slug
    (proj / "direcao").mkdir(parents=True, exist_ok=True)
    cenas = [{"id": "c1", "numero": "3", "frase": "Noxus avança sobre Ionia", "tipo": "cartao", "legenda": "NOXUS"}]
    orig = storyboard.cenas
    storyboard.cenas = lambda pasta: cenas   # o storyboard real precisa do plano/acervo completos
    try:
        r = cli.post(f"/api/videos/{vid}/storyboard/c1/orquestrador", json={"texto": ""})
        checa(r.status_code == 400, "sem texto e sem pedido na cena = 400")
        storyboard.salvar_ajustes(proj, {"c1": {"comentario": "mapa animado com as tropas", "comentario_aplicado": False}})
        checa(storyboard.pendentes_para_o_diretor(storyboard.carregar(proj)["ajustes"]) == ["c1"], "antes: pedido vai ao diretor")
        r = cli.post(f"/api/videos/{vid}/storyboard/c1/orquestrador", json={"texto": ""})
        checa(r.status_code == 200, f"pedido da cena enviado ao orquestrador: {r.text[:200]}")
        item = r.json()["pedido_pesado"]
        aj = storyboard.carregar(proj)["ajustes"]
        checa(aj["c1"].get("comentario_pesado") == item["id"], "ajuste marcado com comentario_pesado")
        checa(storyboard.pendentes_para_o_diretor(aj) == [], "o diretor não recebe o pedido pesado")
        txt = Path(item["arquivo"]).read_text(encoding="utf-8")
        checa("mapa animado com as tropas" in txt and "Noxus avança sobre Ionia" in txt and "storyboard" in txt, "md do storyboard")
        checa("orq_pedido_pesado" in pendencias(vid), "pendência no card do Runeterra")
        checa(cli.post(f"/api/videos/{vid}/storyboard/c1/orquestrador", json={}).status_code == 400, "enviar de novo = 400")
        cod, out = cli_pp("listar")
        checa(cod == 0 and item["id"] in out and "cena 3" in out, f"listar no Runeterra: {out[:200]}")
        with conectar() as con:
            con.execute("UPDATE etapas SET status='concluido' WHERE video_id=? AND chave='direcao'", (vid,))
            con.commit()
        r = cli.post(f"/api/pedidos-pesados/{item['id']}/resolver", json={"nota": "mapa feito no kit", "renderizar": True})
        checa(r.status_code == 200 and r.json()["render"] == {"ok": True}, f"resolver + novo rascunho: {r.text[:200]}")
        checa(esvaziar_fila() == [(vid, "rascunho")], "novo rascunho na fila")
        aj = storyboard.carregar(proj)["ajustes"]["c1"]
        checa(aj.get("comentario_aplicado") and "comentario_pesado" not in aj, "resolvido: pedido da cena marcado como atendido")
        checa("orq_pedido_pesado" not in pendencias(vid), "pendência fechada")
    finally:
        storyboard.cenas = orig


if CANAL_TESTE == "f1":
    testar_vertical()
else:
    testar_storyboard()

print(f"\n[{CANAL_TESTE}] {OK} ok, {len(FALHAS)} falha(s)")
codigo = 1 if FALHAS else 0
if CANAL_TESTE == "f1" and "--canal" not in sys.argv:   # o Runeterra roda em outro processo (o canal é fixo por processo)
    codigo |= subprocess.run([sys.executable, str(Path(__file__)), "--canal", "runeterra"]).returncode
sys.exit(codigo)
