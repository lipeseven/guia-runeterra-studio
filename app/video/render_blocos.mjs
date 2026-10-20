// Render por blocos: empacota o projeto UMA vez, abre o navegador UMA vez e renderiza só os intervalos de quadros
// pedidos (cada bloco do vídeo vira um .mp4 sem áudio, guardado em cache pelo Python). O áudio sai num .wav à parte.
// Uso: node render_blocos.mjs pedido.json
//   pedido.json = {"props": "<props.json>", "blocos": [{"inicio": 0, "fim": 899, "saida": "<x.mp4>"}], "audio": "<a.wav>"|null}
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const pedido = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const inputProps = JSON.parse(readFileSync(pedido.props, "utf-8"));

// cada bundle é uma cópia do projeto + public/ (~1,2 GB) na pasta temporária: apaga as que sobraram de renders
// antigos (> 6 h) e, no fim, a deste render — antes elas se acumulavam (54 GB em 6 dias)
for (const nome of readdirSync(os.tmpdir()).filter((n) => n.startsWith("remotion-webpack-bundle-"))) {
  const pasta = path.join(os.tmpdir(), nome);
  try {
    if (Date.now() - statSync(pasta).mtimeMs > 6 * 3600 * 1000) rmSync(pasta, { recursive: true, force: true });
  } catch {}
}

const serveUrl = await bundle({ entryPoint: path.join(aqui, "src", "index.ts"), publicDir: path.join(aqui, "public") });
const navegador = await openBrowser("chrome");
const composition = await selectComposition({ serveUrl, id: "Video", inputProps, puppeteerInstance: navegador });
const comum = {
  serveUrl,
  composition,
  inputProps,
  puppeteerInstance: navegador,
  imageFormat: "jpeg",
  jpegQuality: 90,
  hardwareAcceleration: "if-possible",
  overwrite: true,
  logLevel: "error",
};
try {
  console.log("PRONTO bundle");
  for (const [i, b] of pedido.blocos.entries()) {
    const t0 = Date.now();
    let ultimo = -1;
    await renderMedia({
      ...comum,
      codec: "h264",
      muted: true,
      frameRange: [b.inicio, b.fim],
      outputLocation: b.saida,
      // progresso para a barra do painel (o Python soma os quadros de todos os blocos)
      onProgress: ({ renderedFrames }) => {
        if (renderedFrames - ultimo >= 30 || renderedFrames === b.fim - b.inicio + 1) {
          ultimo = renderedFrames;
          console.log(`PROG ${i} ${renderedFrames}`);
        }
      },
    });
    console.log(`BLOCO ${i + 1}/${pedido.blocos.length} ${b.fim - b.inicio + 1} quadros em ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  if (pedido.audio) {
    await renderMedia({ ...comum, codec: "wav", outputLocation: pedido.audio });
    console.log("AUDIO ok");
  }
} finally {
  await navegador.close({ silent: true });
  try {
    rmSync(serveUrl, { recursive: true, force: true });
  } catch {}
}
