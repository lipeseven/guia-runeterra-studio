"""Painel do F1 numa porta TEMPORÁRIA com dados fictícios, para ver as telas do documentário de verdade no navegador.

Não toca os painéis 8765/8766 nem os dados reais (ver ambiente.py). Semeia um card documental com o roteiro de
exemplo do diretor (Monza 2025), roteiro aprovado e a História já respondida pelo "orquestrador" (aguardando ★),
mais um card vertical e um horizontal para conferir que continuam iguais.

    .venv\\Scripts\\python.exe F1\\horizontal\\testes\\painel\\servidor.py [--porta 8799] [--manter]
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
    print(json.dumps({"video": vid, "pasta": str(pasta), "url": f"http://127.0.0.1:{PORTA}/#/video/{vid}"}, ensure_ascii=False))


if __name__ == "__main__":
    semear()
    uvicorn.run(app, host="127.0.0.1", port=PORTA, log_level="warning")
