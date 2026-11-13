// Põe em public/ (fora do Git) os modelos 3D usados pelas cenas: link físico (hard link) a partir de F1/dados/modelos3d,
// sem copiar 140 MB. Procura F1/dados/modelos3d subindo as pastas (funciona também a partir de uma worktree).
import { existsSync, linkSync, copyFileSync, mkdirSync, statSync } from "node:fs";
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
const pub = path.join(aqui, "public");
mkdirSync(pub, { recursive: true });
for (const f of ["interlagos_sao_paulo.glb", "ferrari_sf26.glb", "2026_mercedes_w17.glb"]) {
  const de = path.join(modelos, f), para = path.join(pub, f);
  if (existsSync(para) && statSync(para).size === statSync(de).size) continue;
  try { linkSync(de, para); } catch { copyFileSync(de, para); }
  console.log("public/" + f);
}
