# Testes automáticos do kit de SFX (sem pytest: roda direto e sai com código 1 se algo falhar).
#   .venv\Scripts\python.exe F1\horizontal\kit\sfx\testes.py
# Confere: catálogo (18 categorias: >= 15 variações nas 8 originais, >= 8 nas 10 de F1; campos, arquivos), sons da
# API do Freesound (licença CC0/CC BY conferida pela url, nunca NC; crédito; freesound.json = catálogo), cada WAV (48 kHz, estéreo, 16 bits, loudness
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
import gerar  # noqa: E402
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


ORIGINAIS = {"impacto", "riser", "clique", "tecla", "sino", "whoosh", "pop", "alerta"}
NOVAS = {"motor", "pneu", "radio", "cronometro", "grafico", "obturador", "whoosh_grave", "boom", "box", "multidao"}
MIN_ORIGINAIS, MIN_NOVAS = 15, 8


def teste_catalogo(cat: dict) -> None:
    cats = cat["categorias"]
    checar(set(cats) == ORIGINAIS | NOVAS, f"categorias erradas: {sorted(set(cats) ^ (ORIGINAIS | NOVAS))}")
    for c in cats:
        n = sum(1 for i in cat["itens"] if i["categoria"] == c)
        minimo = MIN_ORIGINAIS if c in ORIGINAIS else MIN_NOVAS
        checar(n >= minimo, f"{c}: só {n} variações (mínimo {minimo})")
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
    # os 12 pico_s corrigidos no uso real (PR #113) têm de sair iguais da geração (±2 ms)
    pico113 = {"impacto_fs748752": 0.182, "impacto_fs804681": 0.722, "impacto_remotion_14s": 0.199,
               "sino_carrilhao_duplo": 0.128, "sino_hf_brilho": 0.021, "alerta_dois_tons": 0.307, "alerta_fs634089": 0.097,
               "alerta_hf_erro": 0.141, "alerta_radio_duplo": 0.07, "pop_fs849841": 0.057, "clique_hf_suave": 0.013,
               "tecla_hf_digitando_3": 0.012}
    por_id = {i["id"]: i for i in cat["itens"]}
    for k, v in pico113.items():
        checar(k in por_id and abs(por_id[k]["pico_s"] - v) <= 0.002,
               f"{k}: pico_s {por_id.get(k, {}).get('pico_s')} ≠ {v} corrigido no uso real")


def teste_freesound(cat: dict) -> None:
    """Sons da API do Freesound: licença permitida (CC0/CC BY, nunca NC), crédito completo, lista de regeneração
    (freesound.json) igual ao catálogo, sem id repetido, e a licença conferida pela URL que a API deu."""
    import freesound as fsapi
    lista = json.loads((AQUI / "freesound.json").read_text(encoding="utf-8"))["itens"]
    por_id = {i["id"]: i for i in cat["itens"]}
    checar(len(lista) >= 1, "freesound.json vazio")
    for it in lista:
        checar(it["id"] in por_id, f"{it['id']}: está em freesound.json mas não no catálogo (rode gerar.py)")
        checar(it.get("previa", "").startswith("https://cdn.freesound.org/previews/"), f"{it['id']}: sem url de prévia")
        checar(fsapi.licenca(it["licenca_url"]) == it["licenca"], f"{it['id']}: licença {it['licenca']} × url {it['licenca_url']}")
    ids_fs = []
    for i in cat["itens"]:
        if i["origem"] != "freesound":
            continue
        lic = i["licenca"]
        checar(lic == "CC0" or re.fullmatch(r"CC BY \d\.\d", lic) is not None, f"{i['id']}: licença não permitida {lic!r}")
        checar("NC" not in lic and "nc" not in i.get("licenca_url", ""), f"{i['id']}: licença NC")
        checar(i.get("credito_obrigatorio") == lic.startswith("CC BY"), f"{i['id']}: credito_obrigatorio errado para {lic}")
        checar(bool(i.get("autor")) and str(i.get("url", "")).startswith("https://freesound.org/people/"), f"{i['id']}: sem autor/url")
        if "freesound_id" in i:
            ids_fs.append(i["freesound_id"])
            checar(str(i["freesound_id"]) in i["url"], f"{i['id']}: url não é do som {i['freesound_id']}")
    checar(len(ids_fs) == len(set(ids_fs)), "o mesmo som do Freesound aparece duas vezes no banco")
    checar(len(ids_fs) == len(lista), f"catálogo tem {len(ids_fs)} sons da API, freesound.json tem {len(lista)}")
    # créditos: todo CC BY usado gera linha com autor, url e licença; CC0 não gera
    b = sfx.Banco()
    evs = [b.para(i["categoria"], 5.0, variacao=i["id"]) for i in cat["itens"] if i["origem"] == "freesound"]
    linhas = b.creditos(evs)
    cc_by = {i["url"] for i in cat["itens"] if i["origem"] == "freesound" and i["licenca"].startswith("CC BY")}
    checar(len(linhas) == len(cc_by) and all(any(u in l for l in linhas) for u in cc_by), "créditos CC BY incompletos")


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
            t_pico = float(np.argmax(gerar.envelope_deslizante(x.mean(1)))) / medir.SR
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


def teste_api_novas() -> None:
    """Categorias novas: âncora no pico (ou no início para ambiente), todas as variações alcançáveis e paridade
    Python × TS (escolha, início, duração, ganho e créditos) em todas as 18 categorias."""
    b = sfx.Banco()
    tol = {"cronometro": 0.02, "obturador": 0.02, "boom": 0.03, "radio": 0.05, "grafico": 0.05, "pneu": 0.15,
           "box": 0.15, "motor": 0.25, "whoosh_grave": 0.15}
    for catg, t in tol.items():
        for _ in range(3):
            e = b.para(catg, 4.0, 1.0)
            x = sfx.mixar([e], 9.0, limitar=False)
            t_pico = float(np.argmax(gerar.envelope_deslizante(x.mean(1)))) / medir.SR
            checar(abs(t_pico - 4.0) <= t, f"âncora {catg}/{e.id}: pico em {t_pico:.3f} s, esperado 4,000 (±{t})")
    for _ in range(3):
        e = b.para("multidao", 2.0, 1.0)
        checar(e.inicio == 2.0 and e.corte_ini == 0.0, f"multidao/{e.id}: ambiente deveria começar na âncora")
    vistos = {c: {b.escolher(c) for _ in range(200)} for c in sfx.Banco().por_cat}
    for c, ids in sfx.Banco().por_cat.items():
        checar(vistos[c] == set(ids), f"{c}: variações nunca escolhidas: {sorted(set(ids) - vistos[c])}")
    import tempfile
    cats = sorted(sfx.Banco().categorias)
    pedidos = [{"categoria": c, "t": 1.0 + 0.37 * k + 0.05 * j, "intensidade": (k % 5) / 4}
               for j in range(4) for k, c in enumerate(cats)] + [{"categoria": "capitulo", "t": 9.0}]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(pedidos, fh)
    for sem in (0, 5):
        bp = sfx.Banco(semente=sem)
        evs = bp.de_pedidos(pedidos)
        py = sfx.para_json(evs)
        r = subprocess.run(["node", str(AQUI / "exemplo" / "eventos.ts"), str(sem), fh.name], capture_output=True,
                           text=True, encoding="utf-8")
        checar(r.returncode == 0, f"eventos.ts falhou: {r.stderr[-300:]}")
        if r.returncode:
            continue
        ts = json.loads(r.stdout)
        igual = len(py) == len(ts["eventos"]) and all(
            a["id"] == c["id"] and abs(a["inicio"] - c["inicio"]) < 1e-3 and abs(a["dur"] - c["dur"]) < 1e-3
            and abs(a["ganho_db"] - c["ganho_db"]) < 1e-2 for a, c in zip(py, ts["eventos"]))
        checar(igual, f"Python × TS diferentes (18 categorias) na semente {sem}")
        checar(bp.creditos(evs) == ts["creditos"], f"créditos Python × TS diferentes na semente {sem}")
    Path(fh.name).unlink(missing_ok=True)


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
    for f in (teste_catalogo, teste_freesound, teste_arquivos, teste_medida):
        f(cat)
    teste_api()
    teste_api_novas()
    teste_mixagem()
    print(f"{OK} checagens ok, {len(FALHAS)} falhas")
    for m in FALHAS:
        print("  FALHA:", m)
    sys.exit(1 if FALHAS else 0)
