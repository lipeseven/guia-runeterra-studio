// Render por blocos do vertical: empacota UMA vez, abre o navegador UMA vez e renderiza só os intervalos de quadros
// pedidos (cada bloco vira um .mp4 sem áudio, guardado em cache pelo Python; a voz entra depois, no FFmpeg).
// Uso: node render_blocos.mjs pedido.json
//   pedido.json = {"composicao": "Vertical", "props": "<props.json>", "publicDir": "<pasta>",
//                  "blocos": [{"inicio": 0, "fim": 299, "saida": "<x.mp4>"}]}
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const pedido = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const inputProps = JSON.parse(readFileSync(pedido.props, "utf-8"));
const gl = { gl: "angle" };
const serveUrl = await bundle({ entryPoint: path.join(aqui, "src", "index.ts"), publicDir: pedido.publicDir ?? path.join(aqui, "public") });
const navegador = await openBrowser("chrome", { chromiumOptions: gl });
const composition = await selectComposition({ serveUrl, id: pedido.composicao, inputProps, puppeteerInstance: navegador, chromiumOptions: gl });
try {
  for (const [i, b] of pedido.blocos.entries()) {
    let ultimo = -1;
    await renderMedia({
      serveUrl, composition, inputProps, puppeteerInstance: navegador, chromiumOptions: gl, concurrency: 3,
      codec: "h264", muted: true, imageFormat: "jpeg", jpegQuality: 90, overwrite: true, logLevel: "error",
      frameRange: [b.inicio, b.fim], outputLocation: b.saida,
      // progresso para a barra do painel (o Python soma os quadros de todos os blocos)
      onProgress: ({ renderedFrames }) => {
        if (renderedFrames - ultimo >= 15 || renderedFrames === b.fim - b.inicio + 1) {
          ultimo = renderedFrames;
          console.log(`PROG ${i} ${renderedFrames}`);
        }
      },
    });
    console.log(`BLOCO ${i + 1}/${pedido.blocos.length}`);
  }
} finally {
  await navegador.close({ silent: true });
  try {
    rmSync(serveUrl, { recursive: true, force: true });
  } catch {}
}
