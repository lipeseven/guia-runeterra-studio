# Mods de pista do Assetto Corsa (AC) -> kit/gps, SEM o Blender aberto (só numpy + Pillow).
#  - ler_kn5: lê um .kn5 (texturas DDS, materiais, árvore de nós com malhas) em coordenadas de mundo do AC.
#  - exportar_glb: grava .glb (glTF 2.0 binário) — "superficies" (malhas de física: 1ROAD, 1KERB, 1GRASS..., para o
#    alinhamento e a altura) ou "visual" (malhas visíveis com textura reduzida, agrupadas por material, para o render).
#  - ler_ai: lê fast_lane.ai / ideal_line.ai (traçado ideal do mod + distância às bordas em cada ponto).
#
# Coordenadas: o .glb sai com x, y, z do AC sem troca de eixos (Y para cima, metros) — é o mesmo sistema das linhas
# .ai e o mesmo que o add-on KN5 Tools + exportador glTF do Blender produziram (conferido: a linha ideal cai a 0,67 m
# mediano dos vértices da malha 1road exportada pelo Blender). O AC é "mão esquerda": visto de cima pelo three.js o
# mapa sai espelhado em relação ao mundo real, o que o alinhador (py/alinhar.py) resolve testando a reflexão.
#
# Uso (pasta do mod = a que tem models_*.ini e os .kn5):
#   python assetto.py superficies <pasta_mod> <saida.glb>                 # física: 1ROAD/1KERB/1GRASS/... por nó
#   python assetto.py visual <pasta_mod> <saida.glb> [--textura 512] [--kn5 a.kn5 b.kn5] [--sem-fisica]
#   python assetto.py ai <arquivo.ai>                                    # resumo da linha
import argparse
import io
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np

# superfícies físicas do AC: nome do objeto começa com dígitos + chave de surfaces.ini (1ROAD, 1KERB, 2GRASS...)
RE_FISICA = re.compile(r"^\d+(ROAD|KERB|CURB|GRASS|SAND|OUTER|PITLANE|CARPET|GRAVEL|DIRT|WALL)", re.I)


# ------------------------------------------------------------------------------------------------ .ai
def ler_ai(caminho):
    """fast_lane.ai / ideal_line.ai (versão 7). Devolve dict com pontos (n, 3) em coordenadas do AC, s (m, distância
    acumulada), velocidade (m/s), lado_esq / lado_dir (m do traçado até a borda esquerda/direita da pista), normal e
    frente. A esquerda é (fz, 0, -fx) para a frente (fx, fy, fz) (conferido contra a malha 1road do mod)."""
    b = Path(caminho).read_bytes()
    versao, n, _, _ = struct.unpack("<4i", b[:16])
    if versao != 7:
        raise ValueError(f"{caminho}: versão .ai {versao} não suportada (só 7)")
    p = np.frombuffer(b, np.float32, count=n * 5, offset=16).reshape(n, 5)
    o = 16 + 20 * n
    ne, = struct.unpack("<i", b[o:o + 4])
    ex = np.frombuffer(b, np.float32, count=ne * 18, offset=o + 4).reshape(ne, 18).astype(float)
    return dict(pontos=p[:, :3].astype(float), s=p[:, 3].astype(float), velocidade=ex[:, 0], acelerador=ex[:, 1],
                freio=ex[:, 2], raio=ex[:, 4], lado_esq=ex[:, 5], lado_dir=ex[:, 6], normal=ex[:, 9:12],
                frente=ex[:, 13:16], comprimento=float(p[-1, 3]))


# ------------------------------------------------------------------------------------------------ .kn5
class _Leitor:
    def __init__(self, b):
        self.b, self.o = b, 0

    def i32(self):
        v, = struct.unpack_from("<i", self.b, self.o); self.o += 4; return v

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v

    def f32(self, n=1):
        v = np.frombuffer(self.b, np.float32, count=n, offset=self.o); self.o += 4 * n; return v

    def txt(self):
        n = self.i32(); s = bytes(self.b[self.o:self.o + n]).decode("utf-8", "replace"); self.o += n; return s

    def bruto(self, n):
        v = self.b[self.o:self.o + n]; self.o += n; return v


def ler_kn5(caminho, texturas=True):
    """Lê um .kn5. Devolve dict(texturas={nome: bytes DDS}, materiais=[{nome, shader, alfa, textura}],
    malhas=[{nome, material, pos (n,3) mundo, normal, uv, idx (m,3), visivel}])."""
    b = memoryview(Path(caminho).read_bytes())
    r = _Leitor(b)
    if bytes(r.bruto(6)) != b"sc6969":
        raise ValueError(f"{caminho}: não é .kn5")
    versao = r.i32()
    if versao > 5:
        r.i32()
    tex = {}
    for _ in range(r.i32()):
        r.i32()
        nome = r.txt()
        n = r.i32()
        dados = r.bruto(n)
        if texturas:
            tex[nome] = bytes(dados)
    mats = []
    for _ in range(r.i32()):
        nome, shader = r.txt(), r.txt()
        alfa_mistura, alfa_teste = r.u8(), r.u8()
        r.i32()  # depth mode
        props = {}
        for _ in range(r.i32()):
            pn = r.txt()
            props[pn] = float(r.f32()[0])
            r.bruto(36)
        mapas = {}
        for _ in range(r.i32()):
            mn = r.txt(); r.i32(); mapas[mn] = r.txt()
        mats.append(dict(nome=nome, shader=shader, alfa=bool(alfa_mistura or alfa_teste), props=props, mapas=mapas,
                         textura=mapas.get("txDiffuse")))
    malhas = []

    def no(pai):
        classe = r.i32()
        nome = r.txt()
        nfilhos = r.i32()
        r.u8()
        m = pai
        if classe == 1:
            m = r.f32(16).astype(float).reshape(4, 4) @ pai  # DirectX: vetor-linha, translação na 4ª linha
        elif classe in (2, 3):
            r.u8(); visivel = r.u8(); r.u8()
            if classe == 3:
                for _ in range(r.i32()):
                    r.txt(); r.f32(16)
            nv = r.i32()
            passo = 11 if classe == 2 else 19
            v = r.f32(nv * passo).reshape(nv, passo).astype(float)
            ni = r.i32()
            idx = np.frombuffer(b, np.uint16, count=ni, offset=r.o).astype(np.int64); r.o += 2 * ni
            mat = r.i32()
            r.i32()  # layer
            r.f32(2)  # lod in/out
            if classe == 2:
                r.f32(4); r.u8()  # esfera envolvente, renderizável
            pos = np.c_[v[:, :3], np.ones(nv)] @ pai
            nrm = v[:, 3:6] @ pai[:3, :3]
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
            malhas.append(dict(nome=nome, material=mat, pos=pos[:, :3], normal=nrm, uv=v[:, 6:8],
                               idx=idx.reshape(-1, 3), visivel=bool(visivel)))
        for _ in range(nfilhos):
            no(m)

    no(np.eye(4))
    return dict(versao=versao, texturas=tex, materiais=mats, malhas=malhas)


# ------------------------------------------------------------------------------------------------ .glb
def _abrir(dds):
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(dds))
        im.load()
        return im
    except Exception:
        return None


def _imagem(dds, lado_max, com_alfa=True):
    """DDS -> (bytes, mime, tem_alfa) reduzido a lado_max px; JPEG se opaco (ou com_alfa=False), PNG se tem alfa.
    None se o Pillow não ler."""
    im = _abrir(dds)
    if im is None:
        return None
    im.thumbnail((lado_max, lado_max))
    alfa = com_alfa and im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 250
    buf = io.BytesIO()
    if alfa:
        im.convert("RGBA").save(buf, "PNG", optimize=True)
        return buf.getvalue(), "image/png", True
    im.convert("RGB").save(buf, "JPEG", quality=82)
    return buf.getvalue(), "image/jpeg", False


def exportar_glb(grupos, destino, texturas=None, lado_textura=512, cor_padrao=(0.6, 0.6, 0.6)):
    """grupos = [{nome, pos (n,3), normal (n,3)|None, uv (n,2)|None, idx (m,3), textura (nome)|None, alfa, cor}]:
    um nó + uma malha por grupo. texturas = {nome: bytes DDS}. Grava glTF 2.0 binário (sem dependências)."""
    texturas = texturas or {}
    bin_ = bytearray()
    g = dict(asset=dict(version="2.0", generator="kit/gps py/assetto.py"), scene=0, scenes=[dict(nodes=[])], nodes=[],
             meshes=[], materials=[], accessors=[], bufferViews=[], buffers=[])
    imgs, tex_idx = [], {}

    def vista(dados, alvo=None):
        while len(bin_) % 4:
            bin_.append(0)
        ini = len(bin_)
        bin_.extend(dados)
        v = dict(buffer=0, byteOffset=ini, byteLength=len(dados))
        if alvo:
            v["target"] = alvo
        g["bufferViews"].append(v)
        return len(g["bufferViews"]) - 1

    def acessor(arr, tipo, alvo, minmax=False):
        arr = np.ascontiguousarray(arr)
        ct = 5126 if arr.dtype == np.float32 else 5125
        a = dict(bufferView=vista(arr.tobytes(), alvo), componentType=ct, count=int(arr.shape[0]), type=tipo)
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        g["accessors"].append(a)
        return len(g["accessors"]) - 1

    def textura(nome, com_alfa):
        k = (nome, com_alfa)
        if k in tex_idx:
            return tex_idx[k]
        tex_idx[k] = None
        if nome in texturas:
            im = _imagem(texturas[nome], lado_textura, com_alfa)
            if im:
                g.setdefault("images", []).append(dict(bufferView=vista(im[0]), mimeType=im[1], name=nome))
                g.setdefault("textures", []).append(dict(source=len(g["images"]) - 1, sampler=0))
                g.setdefault("samplers", [dict(magFilter=9729, minFilter=9987, wrapS=10497, wrapT=10497)])
                tex_idx[k] = (len(g["textures"]) - 1, im[2])
        return tex_idx[k]

    for gr in grupos:
        pos = np.asarray(gr["pos"], np.float32)
        at = dict(POSITION=acessor(pos, "VEC3", 34962, True))
        if gr.get("normal") is not None:
            at["NORMAL"] = acessor(np.asarray(gr["normal"], np.float32), "VEC3", 34962)
        pbr = dict(baseColorFactor=list(gr.get("cor", cor_padrao)) + [1.0], metallicFactor=0.0, roughnessFactor=0.92)
        mat = dict(name=gr.get("material", gr["nome"]), pbrMetallicRoughness=pbr, doubleSided=True)
        t = textura(gr["textura"], bool(gr.get("alfa"))) if gr.get("textura") else None
        if t is not None and gr.get("uv") is not None:
            at["TEXCOORD_0"] = acessor(np.asarray(gr["uv"], np.float32), "VEC2", 34962)
            pbr["baseColorTexture"] = dict(index=t[0])
            pbr["baseColorFactor"] = [float(np.clip(c, 0, 1)) for c in gr.get("tinta", (1.0, 1.0, 1.0))] + [1.0]
            # recorte de alfa só quando o MATERIAL pede (no AC o canal alfa de muitas texturas guarda outra coisa:
            # máscara de brilho/detalhe; usá-lo como transparência apagava grama e asfalto)
            if gr.get("alfa") and t[1]:
                mat["alphaMode"], mat["alphaCutoff"] = "MASK", 0.5
        g["materials"].append(mat)
        ind = acessor(np.asarray(gr["idx"], np.uint32).ravel(), "SCALAR", 34963)
        g["meshes"].append(dict(name=gr["nome"], primitives=[dict(attributes=at, indices=ind, material=len(g["materials"]) - 1)]))
        g["nodes"].append(dict(name=gr["nome"], mesh=len(g["meshes"]) - 1))
        g["scenes"][0]["nodes"].append(len(g["nodes"]) - 1)
    while len(bin_) % 4:
        bin_.append(0)
    g["buffers"].append(dict(byteLength=len(bin_)))
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(bin_), 0x004E4942)); f.write(bin_)
    return destino


def _kn5_do_mod(pasta, nomes=None):
    """Lista de .kn5 do layout: models_*.ini (o 1º achado) ou todos os .kn5 da pasta."""
    pasta = Path(pasta)
    if nomes:
        return [pasta / n for n in nomes]
    for ini in sorted(pasta.glob("models*.ini")):
        arqs = re.findall(r"^FILE\s*=\s*(.+?)\s*$", ini.read_text(errors="replace"), re.M)
        if arqs:
            return [pasta / a for a in arqs if (pasta / a).exists()]
    return sorted(pasta.glob("*.kn5"))


def superficies(pasta, destino, nomes=None):
    """Malhas de física (1ROAD, 1KERB...) de todos os .kn5 do layout, um nó por objeto (nome em minúsculas, como o
    Blender exporta: '1road_001'), sem textura. É o que pista/<circuito>.json usa com "agrupar": "no"."""
    grupos, vistos = [], {}
    for k in _kn5_do_mod(pasta, nomes):
        for m in ler_kn5(k, texturas=False)["malhas"]:
            if RE_FISICA.match(m["nome"]) and len(m["idx"]):
                base = m["nome"].lower()
                vistos[base] = vistos.get(base, 0) + 1
                nome = base if vistos[base] == 1 else f"{base}_{vistos[base]}"
                grupos.append(dict(nome=nome, pos=m["pos"], normal=m["normal"], uv=None, idx=m["idx"]))
    return exportar_glb(grupos, destino), len(grupos), sum(len(gr["idx"]) for gr in grupos)


def visual(pasta, destino, nomes=None, lado_textura=512, sem_fisica=True, excluir=None):
    """Malhas visíveis com textura reduzida, agrupadas por (arquivo, material) para poucas chamadas de desenho."""
    grupos, tex = [], {}
    rx = re.compile(excluir, re.I) if excluir else None
    for k in _kn5_do_mod(pasta, nomes):
        d = ler_kn5(k)
        tex.update(d["texturas"])
        por_mat = {}
        for m in d["malhas"]:
            if not m["visivel"] or not len(m["idx"]):
                continue
            if sem_fisica and RE_FISICA.match(m["nome"]) and not d["materiais"][m["material"]].get("textura"):
                continue
            if rx and rx.search(m["nome"]):
                continue
            por_mat.setdefault(m["material"], []).append(m)
        medias = {}

        def media(nome):  # cor média (0..1) de uma textura de detalhe
            if nome not in medias:
                im = _abrir(d["texturas"].get(nome, b"")) if nome else None
                medias[nome] = None if im is None else np.asarray(im.convert("RGB").resize((64, 64)), float).reshape(-1, 3).mean(0) / 255
            return medias[nome]

        for mi, ms in por_mat.items():
            mat = d["materiais"][mi]
            # ksMultilayer: a cor final do AC = txDiffuse x detalhes (txDetailR/G/B, pela máscara) x ~2. Aproximação:
            # tinta = 2 x cor média dos detalhes (grama sai verde, asfalto cinza-escuro, zebra mais clara)
            tinta = (1.0, 1.0, 1.0)
            if "multilayer" in mat["shader"].lower():
                ds = [m for m in (media(mat["mapas"].get(c)) for c in ("txDetailR", "txDetailG", "txDetailB")) if m is not None]
                if ds:
                    tinta = tuple(np.clip(2.0 * np.mean(ds, 0), 0, 1))
            off, P, N, U, I = 0, [], [], [], []
            for m in ms:
                usados, novo = np.unique(m["idx"], return_inverse=True)  # só os vértices referenciados
                P.append(m["pos"][usados]); N.append(m["normal"][usados]); U.append(m["uv"][usados])
                I.append(novo.reshape(-1, 3) + off); off += len(usados)
            grupos.append(dict(nome=f"{k.stem}:{mat['nome']}", material=mat["nome"], pos=np.concatenate(P),
                               normal=np.concatenate(N), uv=np.concatenate(U), idx=np.concatenate(I),
                               textura=mat.get("textura"), alfa=mat["alfa"], tinta=tinta))
    return exportar_glb(grupos, destino, tex, lado_textura), len(grupos), sum(len(gr["idx"]) for gr in grupos)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="mods de pista do Assetto Corsa (.kn5/.ai) -> .glb / resumo")
    ap.add_argument("acao", choices=("superficies", "visual", "ai", "listar"))
    ap.add_argument("origem", help="pasta do mod (superficies/visual), arquivo .ai (ai) ou .kn5 (listar)")
    ap.add_argument("saida", nargs="?")
    ap.add_argument("--kn5", nargs="*", help="só estes .kn5 (padrão: os do models_*.ini)")
    ap.add_argument("--textura", type=int, default=512, help="lado máximo das texturas (px)")
    ap.add_argument("--excluir", default=None, help="regex de nomes de objeto a deixar de fora (visual)")
    a = ap.parse_args()
    if a.acao == "ai":
        d = ler_ai(a.origem)
        print(dict(pontos=len(d["s"]), comprimento_m=round(d["comprimento"], 1),
                   largura_mediana_m=round(float(np.median(d["lado_esq"] + d["lado_dir"])), 2),
                   vel_max_kmh=round(float(d["velocidade"].max() * 3.6), 1)))
    elif a.acao == "listar":
        d = ler_kn5(a.origem, texturas=False)
        for m in d["malhas"]:
            print(m["nome"], len(m["idx"]), d["materiais"][m["material"]]["nome"], "vis" if m["visivel"] else "oculto")
    else:
        if not a.saida:
            ap.error("falta <saida.glb>")
        f = superficies if a.acao == "superficies" else visual
        kw = dict(nomes=a.kn5)
        if a.acao == "visual":
            kw.update(lado_textura=a.textura, excluir=a.excluir)
        arq, n, nf = f(a.origem, a.saida, **kw)
        print(arq, f"{Path(arq).stat().st_size / 1e6:.1f} MB", n, "grupos", nf, "faces")
