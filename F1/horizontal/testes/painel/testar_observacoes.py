"""Teste automático das OBSERVAÇÕES GERAIS do card (voz ou texto), com dados fictícios (ver ambiente.py).

TestClient em processo (sem porta, sem tocar 8765/8766). Caminho inteiro:
- ditado: um WAV FALADO gerado aqui pela voz do Windows (SAPI, "Microsoft Maria" pt-BR) → POST .../transcrever →
  faster-whisper local (tools/audio/ditado.py, processo à parte) → texto com as palavras ditas;
- salvar / editar / apagar (banco + espelho <projeto>/observacoes.json), recusas (vazio, formato, tarefa inexistente);
- card documentário: as observações viram horizontal/observacoes.txt e entram no prompt da História e da SPEC;
- vertical e horizontal animado: gravam e listam; card excluído leva as observações junto.

    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\painel\\testar_observacoes.py [-v] [--manter]
Demora ~20-60 s (o modelo do Whisper carrega uma vez por ditado). Sem a voz pt-BR do Windows, o ditado é pulado (avisa).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ambiente  # noqa: E402

BASE = ambiente.preparar("observacoes")

from fastapi.testclient import TestClient  # noqa: E402

from app.servidor import motor  # noqa: E402
from app.servidor.banco import conectar  # noqa: E402
from app.servidor.main import app  # noqa: E402

VERBOSO = "-v" in sys.argv
motor.pedir_acervo = lambda: None
cli = TestClient(app)
falhas: list[str] = []
n_ok = 0
FRASE = "Quero mais gráficos de telemetria e menos texto na tela."


def checa(cond, nome, detalhe=""):
    global n_ok
    if cond:
        n_ok += 1
        if VERBOSO:
            print("  ok ", nome)
    else:
        falhas.append(f"{nome} {detalhe}")
        print("  FALHOU", nome, detalhe)


def sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def falar(frase: str, destino: Path) -> bool:
    """WAV falado pela voz pt-BR do Windows (local, sem rede). False se não houver a voz."""
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$v = $s.GetInstalledVoices() | ? { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | select -First 1; "
          "if (-not $v) { exit 3 }; $s.SelectVoice($v.VoiceInfo.Name); "
          f"$s.SetOutputToWaveFile('{destino}'); $s.Speak('{frase}'); $s.Dispose()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    return r.returncode == 0 and destino.exists() and destino.stat().st_size > 1000


def ditar(vid: int, arquivo: Path, nome: str | None = None) -> dict:
    with arquivo.open("rb") as f:
        r = cli.post(f"/api/videos/{vid}/observacoes/transcrever", files={"arquivo": (nome or arquivo.name, f, "audio/wav")})
    assert r.status_code == 200, r.text
    tid = r.json()["tarefa"]
    fim = time.time() + 600
    while time.time() < fim:
        t = cli.get(f"/api/transcricoes/{tid}").json()
        if t["status"] in ("pronto", "falhou"):
            return t
        time.sleep(0.5)
    return {"status": "tempo esgotado"}


def obs(vid: int) -> list[dict]:
    r = cli.get(f"/api/videos/{vid}/observacoes")
    assert r.status_code == 200, r.text
    return r.json()["observacoes"]


def principal() -> int:
    ids = {f: cli.post("/api/videos", json={"titulo": f"Obs {f}", "formato": f}).json()["id"]
           for f in ("vertical", "horizontal", "horizontal_doc")}
    vid = ids["horizontal_doc"]
    v = cli.get(f"/api/videos/{vid}").json()
    proj = motor.PASTA_PROJETOS / v["slug"]
    espelho = proj / "observacoes.json"

    # ---- ditado (áudio falado → texto)
    wav = BASE / "ditado_teste.wav"
    if falar(FRASE, wav):
        t = ditar(vid, wav)
        texto = sem_acento(t.get("texto") or "")
        checa(t["status"] == "pronto", "ditado transcrito", str(t)[:300])
        checa(all(p in texto for p in ("telemetria", "texto", "tela")), "texto ditado reconhecido (PT-BR)", repr(t.get("texto")))
        print(f"  ditado: {t.get('texto')!r} ({t.get('dispositivo')})")
        checa(not list((proj / "observacoes_audio").glob("*")), "áudio do ditado apagado depois de transcrever")
        webm = BASE / "ditado_teste.webm"   # o que o navegador (MediaRecorder do Chrome/Edge) envia: webm/opus
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libopus", str(webm)], check=True)
        t = ditar(vid, webm)
        checa(t["status"] == "pronto" and "telemetria" in sem_acento(t.get("texto") or ""), "ditado em webm/opus (navegador)", str(t)[:200])
    else:
        print("  AVISO: sem voz pt-BR do Windows: ditado real não testado")
    r = cli.post(f"/api/videos/{vid}/observacoes/transcrever", files={"arquivo": ("x.txt", b"oi", "text/plain")})
    checa(r.status_code == 400, "formato que não é áudio recusado", r.text)
    r = cli.post(f"/api/videos/{vid}/observacoes/transcrever", files={"arquivo": ("vazio.webm", b"", "audio/webm")})
    checa(r.status_code == 400, "áudio vazio recusado", r.text)
    lixo = BASE / "lixo.webm"
    lixo.write_bytes(b"isto nao e audio" * 100)
    t = ditar(vid, lixo)
    checa(t["status"] == "falhou" and t.get("erro"), "áudio corrompido: falha com motivo (servidor continua de pé)", str(t)[:200])
    checa(cli.get("/api/transcricoes/naoexiste").status_code == 404, "tarefa inexistente: 404")
    checa(cli.post("/api/videos/9999/observacoes", json={"texto": "x"}).status_code == 404, "vídeo inexistente: 404")

    # ---- salvar / editar / apagar
    checa(obs(vid) == [], "card começa sem observações")
    checa(cli.post(f"/api/videos/{vid}/observacoes", json={"texto": "   "}).status_code == 400, "observação vazia recusada")
    r = cli.post(f"/api/videos/{vid}/observacoes", json={"texto": FRASE, "origem": "voz"})
    checa(r.status_code == 200 and len(r.json()["observacoes"]) == 1, "observação ditada salva", r.text)
    o1 = r.json()["observacoes"][0]
    checa(o1["origem"] == "voz" and o1["criada_em"] and o1["editada_em"] is None, "origem voz + data")
    checa(espelho.exists() and json.loads(espelho.read_text(encoding="utf-8"))[0]["texto"] == FRASE, "espelho observacoes.json na pasta do card")
    r = cli.post(f"/api/videos/{vid}/observacoes", json={"texto": "Ritmo mais calmo no fim.", "origem": "qualquer"})
    o2 = r.json()["observacoes"][1]
    checa(o2["origem"] == "texto", "origem desconhecida vira texto")
    r = cli.put(f"/api/videos/{vid}/observacoes/{o1['id']}", json={"texto": "Quero gráficos de telemetria, pouco texto."})
    e1 = next(x for x in r.json()["observacoes"] if x["id"] == o1["id"])
    checa(r.status_code == 200 and e1["texto"].startswith("Quero gráficos") and e1["editada_em"], "editar: texto novo + editada_em")
    checa("pouco texto" in espelho.read_text(encoding="utf-8"), "espelho atualizado na edição")
    checa(cli.put(f"/api/videos/{vid}/observacoes/9999", json={"texto": "x"}).status_code == 404, "editar inexistente: 404")
    checa(cli.put(f"/api/videos/{ids['vertical']}/observacoes/{o1['id']}", json={"texto": "x"}).status_code == 404,
          "não edita observação de outro card")

    # ---- card documentário: observações entram nos prompts do diretor
    pasta = proj / "horizontal"
    (proj / "direcao").mkdir(parents=True, exist_ok=True)
    (proj / "direcao" / "roteiro.txt").write_text((ambiente.EXEMPLO / "roteiro.txt").read_text(encoding="utf-8"), encoding="utf-8")
    with conectar() as con:
        con.execute("UPDATE etapas SET status='concluido' WHERE video_id=? AND chave='roteiro'", (vid,))
        con.commit()
    d = cli.get(f"/api/videos/{vid}/doc").json()
    txt = (pasta / "observacoes.txt").read_text(encoding="utf-8") if (pasta / "observacoes.txt").exists() else ""
    checa("pouco texto" in txt and "Ritmo mais calmo" in txt and d["entradas"]["observacoes"], "horizontal/observacoes.txt sincronizado", txt)
    r = cli.post(f"/api/videos/{vid}/doc/passo/historia")
    ph = (pasta / "prompts" / "historia.prompt.txt").read_text(encoding="utf-8") if r.status_code == 200 else ""
    checa("Observações gerais do Felipe" in ph and "pouco texto" in ph and "Ritmo mais calmo" in ph, "prompt da História traz as observações", r.text[:200])
    resp = pasta / "resposta_historia.json"
    resp.write_text((ambiente.EXEMPLO / "resposta_historia.json").read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run([sys.executable, str(ambiente.DIRETOR / "painel.py"), "aplicar", str(pasta), "historia", str(resp)],
                       capture_output=True, text=True, encoding="utf-8")
    checa(p.returncode == 0, "orquestrador aplica a história", p.stderr[-300:])
    checa(cli.post(f"/api/videos/{vid}/doc/aprovar/historia").status_code == 200, "história aprovada ★")
    r = cli.post(f"/api/videos/{vid}/doc/passo/spec")
    ps = (pasta / "prompts" / "spec.prompt.txt").read_text(encoding="utf-8") if r.status_code == 200 else ""
    checa("Observações gerais do Felipe" in ps and "pouco texto" in ps, "prompt da SPEC traz as observações", r.text[:200])

    r = cli.delete(f"/api/videos/{vid}/observacoes/{o1['id']}")
    checa(r.status_code == 200 and [x["id"] for x in r.json()["observacoes"]] == [o2["id"]], "apagar uma observação")
    checa(cli.delete(f"/api/videos/{vid}/observacoes/{o1['id']}").status_code == 404, "apagar de novo: 404")
    cli.get(f"/api/videos/{vid}/doc")
    txt = (pasta / "observacoes.txt").read_text(encoding="utf-8")
    checa("pouco texto" not in txt and "Ritmo mais calmo" in txt, "apagada sai do observacoes.txt do diretor")
    cli.delete(f"/api/videos/{vid}/observacoes/{o2['id']}")
    cli.get(f"/api/videos/{vid}/doc")
    checa(not espelho.exists() and not (pasta / "observacoes.txt").exists(), "sem observações: espelho e observacoes.txt somem")

    # ---- vertical e horizontal animado: só gravar e mostrar (nada mais muda)
    for f in ("vertical", "horizontal"):
        i = ids[f]
        antes = [(e["chave"], e["status"]) for e in cli.get(f"/api/videos/{i}").json()["etapas"]]
        r = cli.post(f"/api/videos/{i}/observacoes", json={"texto": f"nota do {f}"})
        checa(r.status_code == 200 and obs(i)[0]["texto"] == f"nota do {f}", f"{f}: observação salva e listada")
        depois = [(e["chave"], e["status"]) for e in cli.get(f"/api/videos/{i}").json()["etapas"]]
        checa(antes == depois, f"{f}: etapas do card não mudam")
    i = ids["vertical"]
    checa(cli.delete(f"/api/videos/{i}").status_code == 200, "excluir card vertical")
    with conectar() as con:
        checa(con.execute("SELECT COUNT(*) FROM observacoes WHERE video_id=?", (i,)).fetchone()[0] == 0, "card excluído leva as observações")

    print(f"\n{n_ok} checagens, {len(falhas)} falhas")
    return 1 if falhas else 0


if __name__ == "__main__":
    try:
        codigo = principal()
    finally:
        if "--manter" not in sys.argv:
            shutil.rmtree(BASE, ignore_errors=True)
    sys.exit(codigo)
