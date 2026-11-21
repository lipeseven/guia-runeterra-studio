// Monta assets/ (fora do Git): o HyperFrames só serve arquivos de dentro do projeto, então
//  - modelos 3D: link físico (hard link) a partir de F1/dados/modelos3d (sem copiar 140 MB);
//  - kit/gps: cópia de src/, exemplo/, voltas/ e pista/ (pistas planas; mesma estrutura, para os imports relativos funcionarem).
// Rode antes de qualquer preview/render (os scripts do package.json já rodam).
import { cpSync, existsSync, linkSync, copyFileSync, mkdirSync, readdirSync, rmSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// acha o arquivo na pasta ou em qualquer subpasta (o Felipe organiza modelos3d em carros/, pistas/, pneus/...)
function achar(pasta, nome) {
  const direto = path.join(pasta, nome);
  if (existsSync(direto)) return direto;
  const fila = [pasta];
  while (fila.length) {
    const d = fila.shift();
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (e.isDirectory()) fila.push(path.join(d, e.name));
      else if (e.name === nome) return path.join(d, e.name);
    }
  }
  return direto;
}

const aqui = path.dirname(fileURLToPath(import.meta.url));
let base = aqui, modelos = null;
while (!modelos) {
  const c = path.join(base, "F1", "dados", "modelos3d");
  if (existsSync(c)) modelos = c;
  else if (path.dirname(base) === base) throw new Error("não achei F1/dados/modelos3d");
  else base = path.dirname(base);
}
const assets = path.join(aqui, "assets");
mkdirSync(assets, { recursive: true });
for (const f of ["interlagos_sao_paulo.glb", "ferrari_sf26.glb", "2026_mercedes_w17.glb"]) {
  const de = achar(modelos, f), para = path.join(assets, f);
  if (existsSync(para) && statSync(para).size === statSync(de).size) continue;
  try { linkSync(de, para); } catch { copyFileSync(de, para); }
  console.log("assets/" + f);
}
const kit = path.join(aqui, "..", "kit", "gps");
rmSync(path.join(assets, "kit"), { recursive: true, force: true });
for (const d of ["src", "exemplo", "voltas", "pista"]) cpSync(path.join(kit, d), path.join(assets, "kit", "gps", d), { recursive: true });
console.log("assets/kit/gps (src, exemplo, voltas, pista)");
