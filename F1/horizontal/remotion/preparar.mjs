// Põe em public/ (fora do Git) os modelos 3D usados pelas cenas: link físico (hard link) a partir de F1/dados/modelos3d,
// sem copiar 140 MB. Procura F1/dados/modelos3d subindo as pastas (funciona também a partir de uma worktree).
import { existsSync, linkSync, copyFileSync, mkdirSync, readdirSync, statSync } from "node:fs";
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
const pub = path.join(aqui, "public");
mkdirSync(pub, { recursive: true });
for (const f of ["interlagos_sao_paulo.glb", "ferrari_sf26.glb", "2026_mercedes_w17.glb"]) {
  const de = achar(modelos, f), para = path.join(pub, f);
  if (existsSync(para) && statSync(para).size === statSync(de).size) continue;
  try { linkSync(de, para); } catch { copyFileSync(de, para); }
  console.log("public/" + f);
}
