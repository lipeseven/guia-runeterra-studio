# Folhas de sequência (12 quadros SEGUIDOS a 60 q/s, 4x3) do vídeo renderizado, nos momentos-chave da decupagem:
# S do Senna (entrada, ápice da 1, perseguição), Bico de Pato, Mergulho, panorâmica. Uso: python folhas.py <video.mp4>
# Saída: F1/horizontal/testes/vhe/folha_<nome>.jpg
import subprocess
import sys
from pathlib import Path

SAIDA = Path(__file__).resolve().parents[2] / "testes" / "vhe"
MOMENTOS = {  # segundo de cena do 1º quadro
    "panorama": 9.0, "senna_entrada": 15.9, "senna_apice1": 16.75, "senna_2": 20.5, "senna_perseguicao": 22.65,
    "curva_do_sol": 27.3, "laranja": 38.4, "bico_de_pato": 43.35, "mergulho": 46.6, "juncao": 49.1,
}


def folha(video, nome, t0, n=12, fps=60):
    SAIDA.mkdir(parents=True, exist_ok=True)
    q0 = round(t0 * fps)
    filtro = (f"select='between(n\\,{q0}\\,{q0 + n - 1})',scale=640:-1,"
              f"drawtext=text='%{{n}}':x=10:y=10:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.6:"
              f"fontfile=C\\\\:/Windows/Fonts/arial.ttf,tile=4x3")
    arq = SAIDA / f"folha_{nome}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", filtro, "-frames:v", "1", "-q:v", "3", str(arq)],
                   check=True)
    return arq


if __name__ == "__main__":
    for nome, t in MOMENTOS.items():
        print(folha(sys.argv[1], nome, t))
