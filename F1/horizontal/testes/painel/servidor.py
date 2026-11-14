r"""Painel do F1 numa porta TEMPORÁRIA com dados fictícios, para ver as telas do documentário de verdade no navegador.

Não toca os painéis 8765/8766 nem os dados reais (ver ambiente.py). Semeia um card documental com o roteiro de
exemplo do diretor (Monza 2025), roteiro aprovado e a História já respondida pelo "orquestrador" (aguardando ★),
mais um card vertical e um horizontal para conferir que continuam iguais.

Fase 7a: um 2º card documental ("Fluxo 7a") com o roteiro de exemplo ENVIADO (não aprovado), para seguir no navegador
Roteiro (conferência pelo orquestrador + Wikipedia/OpenF1 reais) → Voz guia → Gravação → Ressincronização. O Claude não
roda (o card documental não chama `claude -p`): quem responde os prompts é o chat (arquivo `.resposta.txt`).
Fish Audio sem chave no worktree: com `--voz-windows`, a voz guia sai da voz pt-BR do Windows (SAPI) — fala de verdade,
medida pelo Whisper real; `gravacao_exemplo.wav` (mais lenta, com uma frase repetida) fica na pasta do projeto para
copiar em entrada/ e usar "Já coloquei na pasta". Opção: `--voz-windows`.

    .venv\Scripts\python.exe F1\horizontal\testes\painel\servidor.py [--porta 8799] [--manter] [--voz-windows] [--storyboard]
(--storyboard: mais um card no Rascunho com o mini-spec e os trechos do teste do montador, para ver o storyboard;
 --final (fase 7c, junto com --storyboard): esse card já com a "gravação" (narração sintética do teste) aprovada e
 ressincronizada, para renderizar o vídeo final 1080p60 de verdade pelo painel e seguir para a Publicação)
(precisa de app/painel/dist compilado: npm run build em app/painel)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ambiente  # noqa: E402

PORTA = int(sys.argv[sys.argv.index("--porta") + 1]) if "--porta" in sys.argv else 8799
assert PORTA not in (8765, 8766), "use uma porta temporária: 8765/8766 são os painéis de verdade"
BASE = ambiente.preparar("tela", limpar="--manter" not in sys.argv)

import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.servidor import motor  # noqa: E402
from app.servidor.banco import conectar  # noqa: E402
from app.servidor.main import app  # noqa: E402

from app.servidor import storyboard  # noqa: E402

motor.pedir_acervo = lambda: None   # sem varrer acervo no teste
storyboard.preaquecer_busca = lambda: None   # sem carregar o CLIP na GPU (acervo fictício vazio)


def sapi(texto: str, saida: Path, ritmo: int = 0) -> None:
    """Fala pt-BR do Windows (System.Speech, voz "Maria") num .wav: áudio de exemplo, nunca vai para vídeo nenhum."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    txt = saida.with_suffix(".txt")
    txt.write_text(texto, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$v = $s.GetInstalledVoices() | ? { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | select -First 1; "
          "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
          f"$s.Rate = {ritmo}; $s.SetOutputToWaveFile('{saida}'); $s.Speak([IO.File]::ReadAllText('{txt}')); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def voz_windows() -> None:
    """Voz guia pela voz do Windows no lugar do Fish Audio (sem FISH_API_KEY no worktree). O resto é o código real."""
    sys.path.insert(0, str(ambiente.RAIZ / "tools" / "audio"))
    import voz_guia

    def gerar(roteiro, saida, fator=None, **_):
        sapi(roteiro, saida)
        return {"duracao": voz_guia.duracao(saida), "motores": ["voz do Windows (no lugar do Fish)"], "ppm_original": 0,
                "fator_exato": 1.0}

    voz_guia.gerar = gerar


def semear_7a(cli) -> None:
    vid = cli.post("/api/videos", json={"titulo": "Fluxo 7a: Monza 2025", "formato": "horizontal_doc"}).json()["id"]
    cli.patch(f"/api/videos/{vid}/mover", json={"coluna": "roteiro"})
    roteiro = (ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8")
    cli.post(f"/api/videos/{vid}/roteiro", json={"texto": roteiro, "nome": "roteiro_exemplo.txt"})
    if "--voz-windows" in sys.argv:   # gravação de exemplo: mais lenta e com a 2ª frase repetida (regravação)
        frases = roteiro.split(". ")
        proj = motor.PASTA_PROJETOS / cli.get(f"/api/videos/{vid}").json()["slug"]
        sapi(". ".join(frases[:2] + frases[1:]), proj / "gravacao_exemplo.wav", ritmo=-2)
    print(json.dumps({"fluxo_7a": vid, "url": f"http://127.0.0.1:{PORTA}/#/video/{vid}"}, ensure_ascii=False))


def semear() -> None:
    cli = TestClient(app)
    if cli.get("/api/quadro").json()["videos"]:
        return
    for f in ("vertical", "horizontal"):
        cli.post("/api/videos", json={"titulo": f"Exemplo {f}", "formato": f})
    vid = cli.post("/api/videos", json={"titulo": "Por que Leclerc foi mais rápido em Monza", "formato": "horizontal_doc"}).json()["id"]
    slug = cli.get(f"/api/videos/{vid}").json()["slug"]
    proj = motor.PASTA_PROJETOS / slug
    (proj / "direcao").mkdir(parents=True, exist_ok=True)
    (proj / "direcao" / "roteiro.txt").write_text((ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8"), encoding="utf-8")
    with conectar() as con:
        con.execute("UPDATE etapas SET status='concluido', resumo='roteiro de exemplo' WHERE video_id=? AND chave='roteiro'", (vid,))
        con.execute("UPDATE videos SET coluna='montagem' WHERE id=?", (vid,))
        con.commit()
    cli.post(f"/api/videos/{vid}/doc/passo/historia")
    pasta = proj / "horizontal"
    resp = pasta / "resposta_historia.json"
    resp.write_text((ambiente.EXEMPLO / "resposta_historia.json").read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run([sys.executable, str(ambiente.DIRETOR / "painel.py"), "aplicar", str(pasta), "historia", str(resp)], check=True)
    cli.get(f"/api/videos/{vid}/doc")
    semear_7a(cli)
    print(json.dumps({"video": vid, "pasta": str(pasta), "url": f"http://127.0.0.1:{PORTA}/#/video/{vid}"}, ensure_ascii=False))
    if "--storyboard" in sys.argv:
        semear_storyboard(cli)


def semear_storyboard(cli) -> None:
    """Card documental já no Rascunho, com o mini-spec do teste do montador (Monza 2025, 3 cenas, kits reais) e os
    trechos/prévias que o `testes/montador/testar.py` deixou em `saida/` (rode-o antes): storyboard com quadros de verdade."""
    import shutil

    origem = ambiente.RAIZ / "F1" / "horizontal" / "testes" / "montador" / "saida" / "projeto" / "horizontal"
    if not (origem / "spec.json").exists():
        print("sem testes/montador/saida: rode testes/montador/testar.py antes de --storyboard")
        return
    vid = cli.post("/api/videos", json={"titulo": "Storyboard: Leclerc × Hamilton em Monza (mini)", "formato": "horizontal_doc"}).json()["id"]
    slug = cli.get(f"/api/videos/{vid}").json()["slug"]
    proj = motor.PASTA_PROJETOS / slug
    pasta = proj / "horizontal"
    shutil.copytree(origem, pasta, ignore=shutil.ignore_patterns("rascunho", "blocos", "prompts", "resposta_*", "_*", "final"))
    (proj / "direcao").mkdir(parents=True, exist_ok=True)
    shutil.copy2(pasta / "roteiro.txt", proj / "direcao" / "roteiro.txt")
    shutil.copy2(pasta / "palavras.json", proj / "direcao" / "tempos_voz.json")
    sys.path.insert(0, str(ambiente.DIRETOR))
    import etapas as E
    from comum import gravar_json, hash_dados

    est = E.novo(slug)
    spec = json.loads((pasta / "spec.json").read_text(encoding="utf-8"))
    for n, st in (("historia", "aprovado"), ("spec", "aprovado"), ("ativos", "gerado"), ("verificacao", "gerado"), ("rascunho", "desatualizado")):
        est["etapas"][n]["status"] = st
    est["etapas"]["spec"]["hash"] = hash_dados(spec)
    est["pedidos"] = []
    if not (origem / "historia.json").exists():   # a 7c do teste do montador deixa uma história válida (presa à SPEC)
        gravar_json(pasta / "historia.json", {"titulo": "Leclerc × Hamilton em Monza", "tese": "mini-spec do teste do montador",
                                              "tempos": "medidos", "capitulos": [], "afirmacoes": []})
    gravar_json(pasta / "verificacao" / "verificacao.json", {"status": "aprovado", "contagem": {"erros": 0, "pendencias": 0, "avisos": 0},
                                                            "erros": [], "pendencias": [], "avisos": []})
    E.gravar(pasta, est)
    with conectar() as con:
        con.execute("UPDATE etapas SET status='concluido', resumo='roteiro do teste do montador' WHERE video_id=? AND chave='roteiro'", (vid,))
        con.execute("UPDATE videos SET coluna='montagem' WHERE id=?", (vid,))
        con.commit()
    if "--final" in sys.argv:   # fase 7c: a narração sintética do teste no papel da sua gravação limpa (já aprovada)
        (proj / "trabalho" / "gravacao").mkdir(parents=True, exist_ok=True)
        shutil.copy2(pasta / "narracao.wav", proj / "trabalho" / "gravacao" / "limpa.wav")
        shutil.copy2(pasta / "palavras.json", proj / "direcao" / "tempos_gravacao.json")
        with conectar() as con:
            for ch in ("voz_guia", "gravacao", "ressincronizacao"):
                con.execute("UPDATE etapas SET status='concluido', resumo='fictício (teste do montador)' WHERE video_id=? AND chave=?", (vid, ch))
            con.commit()
    cli.get(f"/api/videos/{vid}/doc")
    print(json.dumps({"storyboard": vid, "url": f"http://127.0.0.1:{PORTA}/#/video/{vid}"}, ensure_ascii=False))


if __name__ == "__main__":
    if "--voz-windows" in sys.argv:
        voz_windows()
    semear()
    uvicorn.run(app, host="127.0.0.1", port=PORTA, log_level="warning")
