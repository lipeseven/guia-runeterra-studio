# Testes automáticos do kit de SFX (sem pytest: roda direto e sai com código 1 se algo falhar).
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\testes.py
# Confere: catálogo (8 categorias, >= 5 variações, campos, arquivos), cada WAV (48 kHz, estéreo, 16 bits, loudness
# dentro da faixa da categoria, pico verdadeiro <= -1 dBTP, sem clipping, os dois canais com som e equilibrados,
# duração), medida própria BS.1770 × ebur128 do ffmpeg, som excluído (asa do Remotion), API (âncora no pico, riser
# terminando na palavra, sem repetir, determinismo, paridade Python × TS) e a mixagem de exemplo (numpy × ffmpeg).
from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "exemplo"))
import medir  # noqa: E402
import sfx  # noqa: E402

FALHAS: list[str] = []
OK = 0


def checar(cond: bool, msg: str) -> None:
    global OK
    if cond:
        OK += 1
    else:
        FALHAS.append(msg)


def ebur128_ffmpeg(caminho: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def teste_catalogo(cat: dict) -> None:
    cats = cat["categorias"]
    checar(set(cats) == {"impacto", "riser", "clique", "tecla", "sino", "whoosh", "pop", "alerta"}, "categorias erradas")
    for c in cats:
        n = sum(1 for i in cat["itens"] if i["categoria"] == c)
        checar(n >= 5, f"{c}: só {n} variações (mínimo 5)")
    ids = [i["id"] for i in cat["itens"]]
    checar(len(ids) == len(set(ids)), "ids repetidos no catálogo")
    for i in cat["itens"]:
        for campo in ("arquivo", "categoria", "duracao_s", "pico_s", "lufs_m_max", "lufs_integrado", "pico_verdadeiro_dbtp", "origem", "licenca"):
            checar(campo in i, f"{i['id']}: falta {campo}")
        checar((AQUI / i["arquivo"]).is_file(), f"{i['id']}: arquivo não existe (rode gerar.py)")
        checar("fs669142" not in json.dumps(i), f"{i['id']}: usa o som da asa do Remotion (excluído)")
        if i.get("credito_obrigatorio"):
            checar(bool(i.get("autor")) and bool(i.get("url")), f"{i['id']}: CC BY sem autor/url para crédito")
    checar(not cat.get("faltando"), f"fontes faltando na geração: {cat.get('faltando')}")


def teste_arquivos(cat: dict) -> None:
    cats = cat["categorias"]
    for i in cat["itens"]:
        p = AQUI / i["arquivo"]
        if not p.is_file():
            continue
        with wave.open(str(p)) as w:
            checar((w.getframerate(), w.getnchannels(), w.getsampwidth()) == (48000, 2, 2), f"{i['id']}: formato {w.getparams()}")
            bruto = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2)
        x = bruto.astype(np.float64) / 32768.0
        c = cats[i["categoria"]]
        m = medir.lufs_m_max(x)
        lo, hi = c["faixa_lufs_m"]
        checar(lo <= m <= hi, f"{i['id']}: LUFS-M máx {m:.2f} fora da faixa [{lo}, {hi}] de {i['categoria']}")
        checar(abs(m - i["lufs_m_max"]) < 0.1, f"{i['id']}: catálogo diz {i['lufs_m_max']}, medido {m:.2f}")
        tp = medir.pico_verdadeiro_db(x)
        checar(tp <= -1.0, f"{i['id']}: pico verdadeiro {tp:.2f} dBTP > -1")
        cheio = (np.abs(bruto) >= 32700).any(1)
        checar(not cheio.any(), f"{i['id']}: {int(cheio.sum())} amostras em fundo de escala (clipping)")
        l, r = medir.lufs_canais(x)
        checar(l > -60 and r > -60, f"{i['id']}: canal quase mudo (L {l:.1f}, R {r:.1f})")
        checar(abs(l - r) <= 6.0, f"{i['id']}: estéreo desequilibrado (L {l:.1f}, R {r:.1f})")
        checar(i["duracao_s"] <= c["dur_max"] + 0.01, f"{i['id']}: {i['duracao_s']} s > dur_max {c['dur_max']}")
        checar(0 <= i["pico_s"] <= i["duracao_s"], f"{i['id']}: pico_s fora do arquivo")
        if i["categoria"] == "riser":  # crescendo: 1 s antes do pico (ou no começo) o som está >= 4 dB mais baixo
            env = 20 * np.log10(medir.envelope(x) + 1e-12)
            k = int(round(i["pico_s"] / 0.01))
            checar(k >= 30 and env[max(0, k - 100)] <= env[max(0, k - 2):k + 3].max() - 4,
                   f"{i['id']}: riser sem crescendo até o pico ({i['pico_s']} de {i['duracao_s']} s)")


def teste_medida(cat: dict) -> None:
    longos = sorted((i for i in cat["itens"] if i["duracao_s"] >= 2.0), key=lambda i: -i["duracao_s"])[:3]
    for i in longos:
        meu = medir.lufs_integrado(medir.ler(str(AQUI / i["arquivo"])))
        ff = ebur128_ffmpeg(AQUI / i["arquivo"])
        checar(abs(meu - ff) <= 0.3, f"{i['id']}: BS.1770 próprio {meu:.2f} × ffmpeg ebur128 {ff:.2f}")


def teste_api() -> None:
    b = sfx.Banco()
    # âncora: o pico do envelope do som mixado cai em t (impacto/clique) e o riser termina em t
    for catg, tol in (("impacto", 0.02), ("clique", 0.02), ("whoosh", 0.03), ("sino", 0.02)):
        for _ in range(3):
            e = b.para(catg, 3.0, 1.0)
            x = sfx.mixar([e], 7.0, limitar=False)
            t_pico = float(np.argmax(medir.envelope(x))) * 0.01
            checar(abs(t_pico - 3.0) <= tol, f"âncora {catg}/{e.id}: pico em {t_pico:.3f} s, esperado 3,000")
    for _ in range(5):
        e = b.para("riser", 6.0, 1.0)
        pico = b.itens[e.id]["pico_s"]
        checar(abs(e.inicio + pico - 6.0) < 1e-3 and e.inicio + e.dur >= 6.0, f"riser {e.id} não chega ao pico na âncora")
    # sem repetir as 2 últimas, determinístico, intensidade
    b1, b2 = sfx.Banco(semente=3), sfx.Banco(semente=3)
    s1 = [b1.para("pop", k).id for k in range(12)]
    s2 = [b2.para("pop", k).id for k in range(12)]
    checar(s1 == s2, "escolha não determinística")
    checar(all(s1[k] not in s1[max(0, k - 2):k] for k in range(len(s1))), f"repetiu variação recente: {s1}")
    checar(sfx.Banco().para("impacto", 1, 0.0).ganho_db == -9.0 and sfx.Banco().para("impacto", 1, 1.0).ganho_db == 0.0,
           "intensidade 0..1 deveria virar -9..0 dB no impacto")
    e = sfx.Banco().para("whoosh", 0.1, 1.0)
    checar(e.inicio == 0.0 and e.corte_ini > 0, "âncora antes do pico deveria cortar o começo do arquivo")
    # paridade Python × TS (3 sementes)
    import exemplo_20s as ex
    for sem in (0, 1, 7):
        py = sfx.para_json(ex.eventos_py(sem))
        ts = ex.eventos_ts(sem)
        igual = len(py) == len(ts) and all(a["id"] == c["id"] and abs(a["inicio"] - c["inicio"]) < 1e-3
                                           and abs(a["dur"] - c["dur"]) < 1e-3 and abs(a["ganho_db"] - c["ganho_db"]) < 1e-2
                                           for a, c in zip(py, ts))
        checar(igual, f"Python × TS diferentes na semente {sem}")


def teste_mixagem() -> None:
    import exemplo_20s as ex
    ex.SAIDA.mkdir(exist_ok=True)
    evs = ex.eventos_py()
    checar(len(evs) >= 10, "exemplo deveria ter >= 10 SFX")
    final = sfx.mixar(evs, ex.DUR, ex.SAIDA / "trilho_numpy.wav")
    cru = sfx.mixar(evs, ex.DUR, limitar=False)
    sfx.mixar_ffmpeg(evs, ex.DUR, ex.SAIDA / "trilho_ffmpeg.wav")
    ff = medir.ler(str(ex.SAIDA / "trilho_ffmpeg.wav"))
    comp = ex.comparar(cru, ff)
    checar(comp["residuo_onda_db"] < -60, f"numpy × ffmpeg diferem: {comp}")
    y = medir.ler(str(ex.SAIDA / "trilho_numpy.wav"))
    checar(medir.pico_verdadeiro_db(y) <= -1.0, "trilho de exemplo passa de -1 dBTP")
    checar(not (np.abs(y) >= 0.998).any(), "trilho de exemplo com clipping")
    checar(abs(medir.lufs_integrado(y) - ebur128_ffmpeg(ex.SAIDA / "trilho_numpy.wav")) <= 0.3, "LUFS do trilho difere do ffmpeg")
    checar(abs(len(final) / medir.SR - 20.0) < 1e-6, "trilho não tem 20 s")


if __name__ == "__main__":
    cat = json.loads((AQUI / "catalogo.json").read_text(encoding="utf-8"))
    for f in (teste_catalogo, teste_arquivos, teste_medida):
        f(cat)
    teste_api()
    teste_mixagem()
    print(f"{OK} checagens ok, {len(FALHAS)} falhas")
    for m in FALHAS:
        print("  FALHA:", m)
    sys.exit(1 if FALHAS else 0)
