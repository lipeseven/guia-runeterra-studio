# Exemplo do critério de pronto do kit/imagens (GP de São Paulo 2026, corrida, session_key 11412):
#   1. Leclerc (16), volta 55: o pedido do teste HyperFrames. Nenhum vídeo oficial mostra essa volta -> nao_encontrado
#      (e nunca a volta 1 nem a 64, que é o que os highlights têm por perto).
#   2. O trecho que o HyperFrames usou (rh_20.mp4 = highlights 00:20–00:26, volta 1) validado contra a volta 55 -> reprovado.
#   3. Hamilton (44), volta 62, incidente com bandeira amarela -> validado, com arquivo, quadro e crédito.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import imagens  # noqa: E402

HL = "https://www.youtube.com/watch?v=lkb5kqDJYXk"


def mostra(titulo, r):
    print(f"\n== {titulo}\nstatus: {r['status']}  validado: {r['validado']}  arquivo: {r.get('arquivo')}")
    for e in r["evidencia"]:
        print("  -", e)


r1 = imagens.achar({"sessao": 11412, "piloto": 16, "volta": 55})
mostra("Leclerc, volta 55", r1)
hf = Path(r"C:\Users\Felipe\teste-motores\hyperframes\externo\rh_20.mp4")
if hf.exists():
    r2 = imagens.validar_arquivo(hf, {"sessao": 11412, "piloto": 16, "volta": 55}, HL, ini_na_fonte=20)
    mostra("rh_20.mp4 do teste HyperFrames contra a volta 55 do Leclerc", r2)
r3 = imagens.achar({"sessao": 11412, "piloto": 44, "volta": 62, "evento": "bandeira_amarela"})
mostra("Hamilton, volta 62, bandeira amarela", r3)
print("\ncrédito:", r3.get("credito"))
