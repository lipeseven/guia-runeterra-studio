// Render por blocos: empacota o projeto UMA vez, abre o navegador UMA vez e renderiza só os intervalos de quadros
// pedidos (cada bloco do vídeo vira um .mp4 sem áudio, guardado em cache pelo Python). O áudio sai num .wav à parte.
// Uso: node render_blocos.mjs pedido.json
//   pedido.json = {"props": "<props.json>", "blocos": [{"inicio": 0, "fim": 899, "saida": "<x.mp4>"}], "audio": "<a.wav>"|null}
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const pedido = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const inputProps = JSON.parse(readFileSync(pedido.props, "utf-8"));

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
  for (const [i, b] of pedido.blocos.entries()) {
    const t0 = Date.now();
    await renderMedia({ ...comum, codec: "h264", muted: true, frameRange: [b.inicio, b.fim], outputLocation: b.saida });
    console.log(`BLOCO ${i + 1}/${pedido.blocos.length} ${b.fim - b.inicio + 1} quadros em ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  if (pedido.audio) {
    await renderMedia({ ...comum, codec: "wav", outputLocation: pedido.audio });
    console.log("AUDIO ok");
  }
} finally {
  await navegador.close({ silent: true });
}
