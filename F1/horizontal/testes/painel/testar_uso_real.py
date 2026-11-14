"""Teste das correções do 1º uso real do fluxo documental (card "Nove milésimos", 2026-11-14), com dados fictícios.

TestClient em processo (sem porta, sem tocar 8765/8766, sem rede: OpenF1 fictício com os números reais da classificação
do México 2026, session_key 11400). Cada bloco falhava antes da correção:
1. Markdown no roteiro (`**negrito**`, `# título`, `_itálico_`): sai da narração (roteiro.txt do card e da pasta
   horizontal, palavras, âncoras); o roteiro_fonte.txt guarda como veio; roteiro sem Markdown (Runeterra) não muda.
4. Conferência F1: a sessão vem do TEXTO ("classificação do GP do México de 2026") e completa o pedido do modelo
   (que pode vir sem ano/local, ou com "México"/"Classificação"); tipo setor; prompt diz a sessão lida ou pede o
   session_key ao orquestrador; "sem fonte" nunca aparece como conferido no card.
5. Card documental novo = etapas da fase 7a e roteiro aprovado → voz guia (Fish fictício); código velho rodando
   (pasta atrás do origin/main, ou código mudado sem reiniciar) vira aviso no /api/canal (app/servidor/versao.py).

    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\painel\\testar_uso_real.py [-v] [--manter]
"""
from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ambiente  # noqa: E402

BASE = ambiente.preparar("uso_real")

from fastapi.testclient import TestClient  # noqa: E402

from app.servidor import etapas as ET  # noqa: E402
from app.servidor import motor  # noqa: E402
motor.iniciar = lambda: None
from app.servidor import versao  # noqa: E402
from app.servidor.banco import conectar  # noqa: E402
from app.servidor.main import app  # noqa: E402

VERBOSO = "-v" in sys.argv
sys.stdout.reconfigure(errors="replace")   # console cp1252: emoji no detalhe nao derruba o teste
motor.pedir_acervo = lambda: None
cli = TestClient(app)
falhas: list[str] = []
n_ok = 0

ROTEIRO = """# Nove milésimos

Nove milésimos de segundo.

Foi essa a diferença entre Lewis Hamilton e George Russell na classificação do GP do México de 2026. [Texto na tela: pole]

Hamilton colocou sua Ferrari na pole com **1 minuto, 16 segundos e 514 milésimos**. Russell, com a Mercedes, ficou apenas 9 milésimos atrás.

No primeiro setor, Hamilton foi 25 milésimos mais rápido. Já no segundo setor, Russell fez _30.008_ contra 30.030.

**Nove milésimos. Uma pole. E uma diferença praticamente invisível no cronômetro.**
"""

S11400 = {"session_key": 11400, "session_name": "Qualifying", "year": 2026, "circuit_short_name": "Mexico City",
          "location": "Mexico City", "country_name": "Mexico"}
OF1 = {   # números reais (OpenF1, sessão 11400), copiados em 2026-11-14
    ("sessions", (("year", 2026),)): [S11400, {**S11400, "session_key": 11404, "session_name": "Race"},
                                      {**S11400, "session_key": 11408, "circuit_short_name": "Interlagos", "location": "São Paulo",
                                       "country_name": "Brazil"}],
    ("sessions", (("session_key", 11400),)): [S11400],
    ("drivers", (("session_key", 11400),)): [{"driver_number": 44, "name_acronym": "HAM", "last_name": "Hamilton", "full_name": "Lewis HAMILTON"},
                                             {"driver_number": 63, "name_acronym": "RUS", "last_name": "Russell", "full_name": "George RUSSELL"}],
    ("laps", (("driver_number", 44), ("session_key", 11400))): [
        {"lap_number": 19, "lap_duration": 76.514, "duration_sector_1": 26.852, "duration_sector_2": 30.03, "duration_sector_3": 19.632, "st_speed": 347}],
    ("laps", (("driver_number", 63), ("session_key", 11400))): [
        {"lap_number": 21, "lap_duration": 76.523, "duration_sector_1": 26.877, "duration_sector_2": 30.008, "duration_sector_3": 19.638, "st_speed": 350}],
    ("session_result", (("driver_number", 44), ("session_key", 11400))): [{"position": 1, "driver_number": 44, "number_of_laps": 20}],
}


def _of1(endpoint, **params):
    return OF1.get((endpoint, tuple(sorted(params.items()))), [])


def checa(cond, nome, detalhe=""):
    global n_ok
    if cond:
        n_ok += 1
        if VERBOSO:
            print("  ok ", nome)
    else:
        falhas.append(f"{nome} {detalhe}")
        print("  FALHOU", nome, detalhe)


def card(vid):
    v = cli.get(f"/api/videos/{vid}").json()
    return v, {e["chave"]: e for e in v["etapas"]}, {p["chave"] for p in v["pendencias"]}


def _drenar(vid: int) -> list[str]:
    feitas = []
    while not motor.FILA.empty():
        v, nome = motor.FILA.get()
        if v == vid:
            motor.executar(v, nome)
            feitas.append(nome)
    return feitas


def _responder(proj: Path, tarefa: str, texto: str) -> str:
    t = json.loads((proj / "orquestrador" / "aguardando.json").read_text(encoding="utf-8"))[tarefa]
    Path(t["resposta"]).write_text(texto, encoding="utf-8")
    return Path(t["prompt"]).read_text(encoding="utf-8")


def _conferir(vid: int, proj: Path, afirm: list[dict], vereditos: list[dict]) -> tuple[str, dict]:
    """Conferência pelo orquestrador: afirmações → (OpenF1/Wikipedia locais) → vereditos. Devolve o prompt e os fatos."""
    _drenar(vid)
    prompt = _responder(proj, "conferencia", json.dumps({"afirmacoes": afirm}, ensure_ascii=False))
    cli.get(f"/api/videos/{vid}/doc")
    _drenar(vid)
    _responder(proj, "conferencia", json.dumps({"vereditos": vereditos}, ensure_ascii=False))
    cli.get(f"/api/videos/{vid}/doc")
    _drenar(vid)
    conf = cli.get(f"/api/videos/{vid}/roteiro/conferencia").json()["conferencia"] or {}
    return prompt, {f["afirmacao"]: f for f in conf.get("fatos", [])}


def principal() -> int:
    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "audio"))
    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "direcao"))
    import claude_cli
    import notas
    import tempos
    import voz_guia

    from app.servidor import conferencia as CF
    from app.servidor import openf1 as OFM

    motor._TravaGlobal = contextlib.nullcontext
    claude_cli.EXE = Path("NAO_EXISTE/claude.exe")
    OFM._obter = _of1
    CF._wiki = lambda busca: []
    CF._pagina_do_personagem = lambda nome: []
    CF._embed = lambda textos: __import__("numpy").ones((len(textos), 4)) / 2

    # rodada 1 (placar): o "347" do roteiro é o speed trap (st_speed do /laps), não a máxima da telemetria
    ped = {"ano": 2026, "local": "Mexico City", "sessao": "Qualifying", "volta": "melhor"}
    checa(OFM.calcular({**ped, "tipo": "speed_trap", "piloto": "HAM"})[0] == 347.0
          and OFM.calcular({**ped, "tipo": "speed_trap", "piloto": "RUS"})[0] == 350.0
          and "speed_trap" in OFM.TIPOS, "OpenF1: tipo speed_trap (st_speed) HAM 347 × RUS 350")

    print("5. card documental novo: etapas da 7a")
    vid = cli.post("/api/videos", json={"titulo": "Nove milésimos (teste)", "formato": "horizontal_doc"}).json()["id"]
    v, et, _ = card(vid)
    proj = motor.PASTA_PROJETOS / v["slug"]
    checa(list(et) == [e["chave"] for e in ET.ETAPAS_HORIZONTAL_DOC] and "voz_ia" not in et and "voz_guia" in et,
          "card novo pela API: Roteiro → Voz guia → … → Render final → Publicação (sem 'Narração' voz_ia)", str(list(et)))
    checa([e["titulo"] for e in v["etapas"]][:2] == ["Roteiro", "Voz guia"], "títulos das duas primeiras etapas")
    cli.patch(f"/api/videos/{vid}/mover", json={"coluna": "roteiro"})

    print("1. Markdown fora da narração")
    r = cli.post(f"/api/videos/{vid}/roteiro", json={"texto": ROTEIRO, "nome": "nove.txt"})
    checa(r.status_code == 200, "roteiro recebido", r.text)
    narr = (proj / "direcao" / "roteiro.txt").read_text(encoding="utf-8")
    fonte = (proj / "direcao" / "roteiro_fonte.txt").read_text(encoding="utf-8")
    checa("*" not in narr and "#" not in narr and "_30.008_" not in narr and "30.008 contra" in narr, "roteiro.txt: marcas fora, texto dentro", narr)
    checa("**1 minuto" in fonte and "# Nove" in fonte, "roteiro_fonte.txt guarda como veio (com Markdown)")
    nts = json.loads((proj / "direcao" / "notas.json").read_text(encoding="utf-8"))
    toks = narr.split()
    checa(nts and toks[nts[0]["palavra"] - 1].endswith("2026."), "nota de direção continua na palavra certa", str(nts))
    rot_runeterra = (ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8")
    checa(notas.separar(rot_runeterra)[0].strip() == rot_runeterra.strip(), "roteiro sem Markdown (Runeterra/vertical) sai idêntico")
    checa(notas.separar("Nome_de_arquivo e 2*3 é [nota] isso.")[0].strip() == "Nome_de_arquivo e 2*3 é isso.", "sublinhado dentro de palavra e 2*3 ficam")

    print("4. conferência F1: sessão lida do roteiro (OpenF1)")
    afirm = [  # o que o modelo costuma mandar: sem ano/local no trecho de setor, local e sessão em português
        {"p": 3, "trecho": "1 minuto, 16 segundos e 514 milésimos", "afirmacao": "Pole de Hamilton em 1:16.514", "busca": "Lewis Hamilton",
         "openf1": {"tipo": "tempo_volta", "ano": 2026, "local": "México", "sessao": "Classificação", "piloto": "HAM", "volta": "melhor",
                    "valor": 76.514, "casas": 3}},
        {"p": 3, "trecho": "ficou apenas 9 milésimos atrás", "afirmacao": "Russell 9 milésimos atrás", "busca": "George Russell",
         "openf1": {"tipo": "diferenca", "piloto": "RUS", "piloto2": "HAM", "volta": "melhor", "valor": 0.009, "casas": 3}},
        {"p": 4, "trecho": "Hamilton foi 25 milésimos mais rápido", "afirmacao": "Hamilton 25 ms mais rápido no setor 1", "busca": "Lewis Hamilton",
         "openf1": {"tipo": "setor", "setor": 1, "piloto": "HAM", "piloto2": "RUS", "volta": "melhor", "valor": 0.025, "casas": 3}},
        {"p": 4, "trecho": "Russell fez 30.008", "afirmacao": "Russell 30.008 no setor 2", "busca": "George Russell",
         "openf1": {"tipo": "setor", "setor": 2, "piloto": "RUS", "local": "Hermanos Rodriguez", "volta": "melhor", "valor": 30.008, "casas": 3}},
        {"p": 3, "trecho": "colocou sua Ferrari na pole", "afirmacao": "Hamilton na pole", "busca": "Lewis Hamilton",
         "openf1": {"tipo": "posicao_final", "piloto": "Hamilton", "valor": 1}},
        {"p": 3, "trecho": "Russell, com a Mercedes,", "afirmacao": "Russell corre pela Mercedes", "busca": "George Russell"},
    ]
    vered = [{"i": k, "veredito": "sem_fonte", "explicacao": "a wiki não traz", "trecho": -1, "fontes": 0} for k in range(len(afirm))]
    prompt, fatos = _conferir(vid, proj, afirm, vered)
    checa('ano 2026, local "Mexico City", sessão "Qualifying"' in prompt, "prompt da conferência diz a sessão lida do roteiro", prompt[-900:])
    for a in afirm[:5]:
        f = fatos.get(a["afirmacao"], {})
        checa(f.get("veredito") == "confere" and "session_key 11400" in ((f.get("fonte") or {}).get("fonte") or ""),
              f"OpenF1 confere na sessão 11400: {a['afirmacao']}", str(f.get("openf1")))
    checa(fatos.get("Russell corre pela Mercedes", {}).get("veredito") == "sem_fonte", "sem número e sem fonte segue sem_fonte")
    _, et, _ = card(vid)
    det = et["roteiro"]["detalhe"] or ""
    checa("conferido: 0 ⚠️ fato(s) · 1 não conferido(s)" in det, "card: '1 não conferido(s)' junto do conferido", det)
    ativ = [a["texto"] for a in card(vid)[0]["atividade"] if a["texto"].startswith("Roteiro conferido")]
    checa(ativ and "5 de 6 fato(s) com fonte" in ativ[0] and "1 NÃO conferido(s)" in ativ[0], "atividade: quantos têm fonte e quantos não", str(ativ[:1]))

    # tudo sem fonte (o caso real: 16/16) nunca vira "conferido: 0 ⚠️"
    vid2 = cli.post("/api/videos", json={"titulo": "Sem sessão (teste)", "formato": "horizontal_doc"}).json()["id"]
    v2, _, _ = card(vid2)
    proj2 = motor.PASTA_PROJETOS / v2["slug"]
    cli.post(f"/api/videos/{vid2}/roteiro", json={"texto": "Hamilton foi muito rápido naquela volta, a mais rápida que já vimos. "
                                                         "Ele marcou 1:16.514 e ninguém chegou perto.", "nome": "x.txt"})
    prompt2, fatos2 = _conferir(vid2, proj2, [{"p": 0, "trecho": "marcou 1:16.514", "afirmacao": "Volta em 1:16.514", "busca": "Hamilton",
                                               "openf1": {"tipo": "tempo_volta", "piloto": "HAM", "valor": 76.514, "casas": 3}}],
                                [{"i": 0, "veredito": "sem_fonte", "explicacao": "nada", "trecho": -1, "fontes": 0}])
    checa("session_key" in prompt2 and "não deixa clara a sessão" in prompt2, "sessão não lida do texto: prompt pede o session_key ao orquestrador", prompt2[-700:])
    f = fatos2.get("Volta em 1:16.514", {})
    checa(f.get("veredito") == "sem_fonte" and (f.get("openf1") or {}).get("status") == "sem_dados", "sem sessão: OpenF1 sem dados (não inventa)", str(f))
    _, et2, _ = card(vid2)
    det2 = et2["roteiro"]["detalhe"] or ""
    checa("não conferido: 1 fato(s) sem fonte" in det2 and "conferido: 0" not in det2, "card: tudo sem fonte = 'não conferido'", det2)
    ativ2 = next(a for a in card(vid2)[0]["atividade"] if a["texto"].startswith("Roteiro conferido"))
    checa(ativ2["tipo"] == "alerta" and "0 de 1" in ativ2["texto"], "atividade: alerta quando nenhum fato tem fonte", str(ativ2))
    # roteirista/pesquisa: o tema completa a sessão do pedido
    checa(OFM.sessao_do_texto("A pole da classificação do GP do México de 2026") == {"local": "Mexico City", "ano": 2026, "sessao": "Qualifying"}
          and OFM.sessao_do_texto("Na corrida de Interlagos em 2025, Norris venceu.") == {"local": "Interlagos", "ano": 2025, "sessao": "Race"}
          and OFM.sessao_do_texto("o TL2 do GP da Grã-Bretanha de 2024")["sessao"] == "Practice 2"
          and OFM.sessao_do_texto("classificação da sprint em Miami 2025")["sessao"] == "Sprint Qualifying",
          "sessao_do_texto: GP/país/circuito em PT, ano e sessão")
    checa(OFM.fatos_da_sessao({"local": "México", "sessao": "Classificação", "pilotos": ["HAM"]}, {"ano": 2026}) != [],
          "pesquisa: pedido sem ano completado pelo tema (fatos_da_sessao com contexto)")

    print("1b. a ponte copia a narração limpa para o diretor; última frase com tempo final")
    # ---- aprovar → voz guia (Fish fictício), tempos por palavra → palavras.json e frases do diretor
    def gerar_fish(texto, saida, fator=None, **_):
        checa("*" not in texto and "#" not in texto, "voz guia recebe o texto sem Markdown")
        saida.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(saida), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(8000), w.writeframes(b"\0\0" * 8000)
        return {"duracao": 30.0, "motores": ["fish (fictício)"], "ppm_original": 150, "fator_exato": 1.0}

    def medir(audio, rot, cache):
        ws = (proj / "direcao" / "roteiro.txt").read_text(encoding="utf-8").split()
        g = [{"t": t, "i": round(k * 0.4, 3), "f": round(k * 0.4 + 0.35, 3)} for k, t in enumerate(ws)]
        cache.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        return g

    voz_guia.gerar, tempos.tempos_da_narracao = gerar_fish, medir
    r = cli.post(f"/api/videos/{vid}/roteiro/aprovar")
    checa(r.status_code == 200, "aprovar roteiro", r.text)
    checa(_drenar(vid) == ["voz_guia"], "5. roteiro aprovado → voz guia na fila (não pede a gravação)")
    _, et, pend = card(vid)
    checa(et["voz_guia"]["status"] == "concluido" and "enviar_voz" not in pend, "voz guia concluída; sem 'Suba a sua gravação'", str(et["voz_guia"]))
    d = cli.get(f"/api/videos/{vid}/doc").json()
    hrot = (proj / "horizontal" / "roteiro.txt").read_text(encoding="utf-8")
    pal = json.loads((proj / "horizontal" / "palavras.json").read_text(encoding="utf-8"))
    checa("*" not in hrot and "#" not in hrot and all("*" not in p["t"] for p in pal) and d["entradas"]["tempos"] == "medidos",
          "horizontal/roteiro.txt e palavras.json sem Markdown", hrot[:120])
    fr = subprocess.run([sys.executable, "-c", "import json,sys; sys.path.insert(0, sys.argv[1]); from comum import frases;"
                         "print(frases(json.load(open(sys.argv[2], encoding='utf-8'))))", str(ambiente.DIRETOR),
                         str(proj / "horizontal" / "palavras.json")], capture_output=True, text=True, encoding="utf-8",
                        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}).stdout
    linhas = fr.strip().splitlines()
    checa(linhas and all("→" in x for x in linhas) and linhas[-1].endswith("cronômetro."), "frases do prompt: última com tempo final", linhas[-1:])

    print("5b. código velho rodando vira aviso (versao.py)")
    tmp = Path(tempfile.mkdtemp(prefix="versao_"))
    try:
        def git(*a, cwd=tmp / "pasta"):
            return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
        (tmp / "pasta").mkdir()
        git("init", "-q", "-b", "main")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "PR #108")
        velho = git("rev-parse", "HEAD")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "PR #111 fase 7c")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        git("reset", "-q", "--hard", velho)
        e = versao.estado(tmp / "pasta", carregado=velho)
        checa(e["atras"] == 1 and "atrás do GitHub" in (e["aviso"] or "") and "PR #111" in e["aviso"] and not e["reiniciar"],
              "pasta principal atrás do origin/main = aviso", str(e))
        git("merge", "-q", "--ff-only", "origin/main")
        e = versao.estado(tmp / "pasta", carregado=velho)
        checa(e["atras"] == 0 and e["reiniciar"] and "reinicie" in e["aviso"], "pasta atualizada mas servidor com o código velho = reinicie", str(e))
        checa(versao.estado(tmp / "pasta", carregado=git("rev-parse", "HEAD"))["aviso"] is None, "em dia: sem aviso")
        checa(versao.estado(tmp / "nada")["aviso"] is None, "fora de um repositório git: sem aviso (não quebra)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    c = cli.get("/api/canal").json()
    checa("codigo" in c and "aviso" in c["codigo"], "/api/canal devolve o estado do código", str(c.get("codigo")))
    return 0


if __name__ == "__main__":
    try:
        principal()
    finally:
        if "--manter" not in sys.argv:
            shutil.rmtree(BASE, ignore_errors=True)
    print(f"\n{n_ok} checagens ok, {len(falhas)} falha(s)")
    for f in falhas:
        print("  -", f)
    sys.exit(1 if falhas else 0)
