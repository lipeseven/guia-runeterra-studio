// Render por bloco (um trecho do plano = um mp4 em oficina/video/_blocos), com cache pelo hash do trecho.
// Uso: node render.mjs [--so id,id] [--forcar id,id|todos] [--quadros id:seg,id:seg  (só quadros pequenos de conferência)]
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const OF = "C:/Users/Felipe/Downloads/exclusive Claude/dados/comum/oficina_craft/biblioteca/catalogo_horizontal/video";
const VERSAO = "c1";
const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : undefined; };
const so = arg("--so")?.split(",");
const forcar = arg("--forcar")?.split(",") ?? [];
const quadros = arg("--quadros")?.split(",");
const plano = JSON.parse(fs.readFileSync(path.join(AQUI, "plano.json"), "utf8"));
const fps = plano.fps;
fs.mkdirSync(`${OF}/_blocos`, { recursive: true });

const serveUrl = await bundle({ entryPoint: path.join(AQUI, "index.tsx"), publicDir: `${OF}/_public` });
const composition = await selectComposition({ serveUrl, id: "catalogo" });
let ini = 0;
const lista = [];
for (const [i, t] of plano.trechos.entries()) {
  const q = Math.round(t.dur * fps);
  const h = createHash("sha1").update(VERSAO + JSON.stringify(t)).digest("hex").slice(0, 8);
  lista.push({ i, t, a: ini, b: ini + q - 1, arq: `${OF}/_blocos/${String(i + 1).padStart(2, "0")}_${t.id}_${h}.mp4` });
  ini += q;
}
if (quadros) {
  for (const s of quadros) {
    const [id, seg] = s.split(":");
    const L = lista.find((x) => x.t.id === id);
    const out = `${OF}/_tmp/q_${id}_${seg}.jpg`;
    await renderStill({ composition, serveUrl, frame: L.a + Math.round(Number(seg) * fps), output: out, imageFormat: "jpeg", jpegQuality: 80, scale: 0.25 });
    console.log("quadro", out);
  }
  process.exit(0);
}
for (const L of lista) {
  if (so && !so.includes(L.t.id)) continue;
  const prefixo = path.basename(L.arq).split("_").slice(0, 2).join("_");
  for (const f of fs.readdirSync(`${OF}/_blocos`)) if (f.startsWith(prefixo + "_") && `${OF}/_blocos/${f}` !== L.arq) fs.unlinkSync(`${OF}/_blocos/${f}`);
  if (fs.existsSync(L.arq) && !forcar.includes(L.t.id) && !forcar.includes("todos")) continue;
  const t0 = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 16, x264Preset: "medium", muted: true, imageFormat: "jpeg", jpegQuality: 92,
    frameRange: [L.a, L.b], outputLocation: L.arq, concurrency: 6, overwrite: true, logLevel: "error" });
  console.log(`${L.i + 1} ${L.t.id} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
fs.writeFileSync(`${OF}/_blocos/lista.json`, JSON.stringify(lista.map((L) => ({ id: L.t.id, arq: L.arq, a: L.a, b: L.b })), null, 1));
console.log("fim", lista.length, "trechos", ini, "quadros");
