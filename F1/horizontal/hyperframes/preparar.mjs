// Monta assets/ (fora do Git): o HyperFrames só serve arquivos de dentro do projeto, então
//  - modelos 3D: link físico (hard link) a partir de F1/dados/modelos3d (sem copiar 140 MB);
//  - kit/gps: cópia de src/, exemplo/, voltas/ e pista/ (pistas planas; mesma estrutura, para os imports relativos funcionarem).
// Rode antes de qualquer preview/render (os scripts do package.json já rodam).
import { cpSync, existsSync, linkSync, copyFileSync, mkdirSync, rmSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
  const de = path.join(modelos, f), para = path.join(assets, f);
  if (existsSync(para) && statSync(para).size === statSync(de).size) continue;
  try { linkSync(de, para); } catch { copyFileSync(de, para); }
  console.log("assets/" + f);
}
const kit = path.join(aqui, "..", "kit", "gps");
rmSync(path.join(assets, "kit"), { recursive: true, force: true });
for (const d of ["src", "exemplo", "voltas", "pista"]) cpSync(path.join(kit, d), path.join(assets, "kit", "gps", d), { recursive: true });
console.log("assets/kit/gps (src, exemplo, voltas, pista)");
