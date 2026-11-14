"""Pós do teste Blender (Python da .venv + FFmpeg): correção de cor/grão, vídeo, folhas de comparação e de sequência.

  python folhas.py comparar <pasta_png> 1,150,300 --ref <imagem_referencia> --saida folha.jpg
  python folhas.py sequencia <pasta_png> <quadro_inicial> --saida folha.jpg      (12 quadros seguidos, 60 q/s)
  python folhas.py video <pasta_png> <saida.mp4> [--aviso]                       (aviso discreto "traçado lateral inferido")
  python folhas.py still <pasta_png> <quadro> <saida.png>
A correção (GRADE) é a mesma no vídeo e nos stills: contraste/saturação leves, vinheta e grão de filme.
"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

GRADE = "eq=contrast=1.12:saturation=1.08:gamma=0.97,vignette=angle=PI/5.5,noise=alls=4:allf=t"
FONTE = "C:/Windows/Fonts/arial.ttf"
AVISO = "traçado lateral inferido (linha ideal do mod) · ritmo: OpenF1, HAM Q 2026 v12"


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def corrigido(png, destino):
    ffmpeg("-i", png, "-vf", GRADE, destino)
    return destino


def fonte(px):
    try:
        return ImageFont.truetype(FONTE, px)
    except OSError:
        return ImageFont.load_default()


def comparar(pasta, quadros, ref, saida, larg=640):
    tmp = tempfile.mkdtemp()
    imgs = []
    if ref:
        imgs.append(("referência (Formula Addict)", Image.open(ref).convert("RGB")))
    for q in quadros:
        p = corrigido(os.path.join(pasta, f"{q:04d}.png"), os.path.join(tmp, f"{q}.png"))
        imgs.append((f"Blender q{q}", Image.open(p).convert("RGB")))
    alt = int(larg * 9 / 16)
    col = 3 if len(imgs) > 4 else 2
    lin = (len(imgs) + col - 1) // col
    folha = Image.new("RGB", (col * larg, lin * (alt + 26)), (20, 20, 20))
    d = ImageDraw.Draw(folha)
    for i, (nome, im) in enumerate(imgs):
        im = im.resize((larg, alt))
        x, y = (i % col) * larg, (i // col) * (alt + 26)
        folha.paste(im, (x, y + 26))
        d.text((x + 6, y + 4), nome, fill=(235, 235, 235), font=fonte(16))
    folha.save(saida, quality=88)


def sequencia(pasta, q0, saida, larg=480):
    tmp = tempfile.mkdtemp()
    alt = int(larg * 9 / 16)
    folha = Image.new("RGB", (4 * larg, 3 * (alt + 22)), (20, 20, 20))
    d = ImageDraw.Draw(folha)
    for i in range(12):
        q = q0 + i
        im = Image.open(corrigido(os.path.join(pasta, f"{q:04d}.png"), os.path.join(tmp, f"{q}.png"))).convert("RGB").resize((larg, alt))
        x, y = (i % 4) * larg, (i // 4) * (alt + 22)
        folha.paste(im, (x, y + 22))
        d.text((x + 6, y + 3), f"q{q}  t={(q - 1) / 60:.3f} s", fill=(235, 235, 235), font=fonte(14))
    folha.save(saida, quality=88)


def video(pasta, saida, aviso):
    vf = GRADE
    if aviso:
        f = FONTE.replace(":", "\\:")
        txt = os.path.join(tempfile.mkdtemp(), "aviso.txt")   # textfile: vírgula/dois-pontos não quebram o filtro
        open(txt, "w", encoding="utf-8").write(AVISO)
        txt = txt.replace("\\", "/").replace(":", "\\:")
        vf += (f",drawtext=fontfile='{f}':textfile='{txt}':fontsize=20:fontcolor=white@0.72:"
               "x=28:y=h-46:shadowcolor=black@0.5:shadowx=1:shadowy=1")
    ffmpeg("-framerate", "60", "-i", os.path.join(pasta, "%04d.png"), "-vf", vf, "-c:v", "h264_nvenc", "-preset", "p7",
           "-rc", "vbr", "-cq", "17", "-b:v", "30M", "-pix_fmt", "yuv420p", "-r", "60", saida)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=("comparar", "sequencia", "video", "still"))
    ap.add_argument("pasta")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("arg2", nargs="?")
    ap.add_argument("--ref")
    ap.add_argument("--saida")
    ap.add_argument("--aviso", action="store_true")
    a = ap.parse_args()
    if a.acao == "comparar":
        comparar(a.pasta, [int(x) for x in a.arg.split(",")], a.ref, a.saida)
    elif a.acao == "sequencia":
        sequencia(a.pasta, int(a.arg), a.saida)
    elif a.acao == "video":
        video(a.pasta, a.arg, a.aviso)
    else:
        corrigido(os.path.join(a.pasta, f"{int(a.arg):04d}.png"), a.arg2)
