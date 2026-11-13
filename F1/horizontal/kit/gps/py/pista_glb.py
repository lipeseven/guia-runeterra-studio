# Leitura mínima de .glb (sem dependências além de numpy) e consulta de altura do asfalto por "raycast" vertical.
# Coordenadas = as do glTF já com as matrizes dos nós aplicadas (Y para cima), iguais às que o three.js usa ao carregar
# o arquivo sem transformações. É o sistema de coordenadas de todo o kit/gps.
import json
import struct
from pathlib import Path

import numpy as np

_TIPOS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _ler_glb(caminho):
    b = Path(caminho).read_bytes()
    cl, = struct.unpack("<I", b[12:16])
    g = json.loads(b[20:20 + cl])
    o = 20 + cl
    bl, = struct.unpack("<I", b[o:o + 4])
    binario = memoryview(b)[o + 8:o + 8 + bl]
    return g, binario


def _acessor(g, binario, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    tipo = np.dtype(_TIPOS[a["componentType"]])
    nc = _NCOMP[a["type"]]
    ini = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    passo = bv.get("byteStride") or tipo.itemsize * nc
    n = a["count"]
    bruto = np.frombuffer(binario, dtype=np.uint8, count=passo * (n - 1) + tipo.itemsize * nc, offset=ini)
    if passo == tipo.itemsize * nc:
        return np.frombuffer(bruto.tobytes(), dtype=tipo).reshape(n, nc)
    linhas = np.lib.stride_tricks.as_strided(bruto, shape=(n, tipo.itemsize * nc), strides=(passo, 1))
    return np.frombuffer(linhas.copy().tobytes(), dtype=tipo).reshape(n, nc)


def _matriz(no):
    if "matrix" in no:
        return np.array(no["matrix"], float).reshape(4, 4).T  # glTF guarda por coluna
    m = np.eye(4)
    if "scale" in no:
        m = np.diag(list(no["scale"]) + [1.0]) @ m
    if "rotation" in no:
        x, y, z, w = no["rotation"]
        r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        r4 = np.eye(4); r4[:3, :3] = r
        m = r4 @ m
    if "translation" in no:
        t = np.eye(4); t[:3, 3] = no["translation"]
        m = t @ m
    return m


def triangulos(caminho, filtro_no=None):
    """Triângulos do .glb em coordenadas de mundo. Devolve dict material -> array (n, 3, 3).
    filtro_no: nome de nó; só a sub-árvore dele entra (ex.: 'tracksplit_0')."""
    g, binario = _ler_glb(caminho)
    saida = {}

    def visitar(i, pai, dentro):
        no = g["nodes"][i]
        m = pai @ _matriz(no)
        dentro = dentro or (filtro_no is None) or no.get("name") == filtro_no
        if dentro and "mesh" in no:
            for p in g["meshes"][no["mesh"]]["primitives"]:
                if p.get("mode", 4) != 4:
                    continue
                pos = _acessor(g, binario, p["attributes"]["POSITION"]).astype(float)
                pos = (np.c_[pos, np.ones(len(pos))] @ m.T)[:, :3]
                idx = _acessor(g, binario, p["indices"]).ravel() if "indices" in p else np.arange(len(pos))
                tri = pos[idx.reshape(-1, 3)]
                nome = g["materials"][p["material"]].get("name") if "material" in p else None
                saida.setdefault(nome, []).append(tri)
        for c in no.get("children", []):
            visitar(c, m, dentro)

    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        visitar(r, np.eye(4), False)
    return {k: np.concatenate(v) for k, v in saida.items()}


class Superficie:
    """Altura (Y) de uma malha por raio vertical: grade de baldes no plano XZ + baricêntrica."""

    def __init__(self, tri, celula=4.0):
        tri = tri[np.abs(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])[:, 1]) > 1e-9]  # descarta paredes verticais
        self.tri = tri
        self.c = celula
        xz = tri[:, :, [0, 2]]
        lo = np.floor(xz.min(1) / celula).astype(int)
        hi = np.floor(xz.max(1) / celula).astype(int)
        self.baldes = {}
        for k in range(len(tri)):
            for a in range(lo[k, 0], hi[k, 0] + 1):
                for b in range(lo[k, 1], hi[k, 1] + 1):
                    self.baldes.setdefault((a, b), []).append(k)
        self.baldes = {k: np.array(v) for k, v in self.baldes.items()}

    def alturas(self, x, z):
        """Todas as alturas da malha sob (x, z) (lista, pode ser vazia)."""
        ks = self.baldes.get((int(np.floor(x / self.c)), int(np.floor(z / self.c))))
        if ks is None:
            return []
        t = self.tri[ks]
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        v0x, v0z = b[:, 0] - a[:, 0], b[:, 2] - a[:, 2]
        v1x, v1z = c[:, 0] - a[:, 0], c[:, 2] - a[:, 2]
        px, pz = x - a[:, 0], z - a[:, 2]
        den = v0x * v1z - v1x * v0z
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (px * v1z - v1x * pz) / den
            v = (v0x * pz - px * v0z) / den
        ok = (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
        if not ok.any():
            return []
        y = a[ok, 1] + u[ok] * (b[ok, 1] - a[ok, 1]) + v[ok] * (c[ok, 1] - a[ok, 1])
        return y.tolist()

    def altura(self, x, z, perto=None, janela=1.5):
        """Altura do topo da superfície sob (x, z). Com 'perto', ignora acertos a mais de 'janela' m dela
        (evita pegar passarela/viaduto)."""
        hs = self.alturas(x, z)
        if perto is not None:
            hs = [h for h in hs if abs(h - perto) <= janela]
        return max(hs) if hs else None
