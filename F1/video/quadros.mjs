// Quadros soltos de uma composição (conferência da direção: um quadro por plano), com o projeto empacotado UMA vez.
// Uso: node quadros.mjs pedido.json
//   pedido.json = {"composicao": "Vertical", "props": "<props.json>"|null, "publicDir": "<pasta>"|null, "escala": 0.4,
//                  "quadros": [{"q": 120, "saida": "<x.jpg>"}]}
// Erros do navegador (cena que quebrou) saem como linhas "ERRO <q> <texto>".
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const pedido = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const inputProps = pedido.props ? JSON.parse(readFileSync(pedido.props, "utf-8")) : {};
const serveUrl = await bundle({ entryPoint: path.join(aqui, "src", "index.ts"), publicDir: pedido.publicDir ?? path.join(aqui, "public") });
const navegador = await openBrowser("chrome", { chromiumOptions: { gl: "angle" } });
const composition = await selectComposition({ serveUrl, id: pedido.composicao, inputProps, puppeteerInstance: navegador, chromiumOptions: { gl: "angle" } });
try {
  for (const { q, saida } of pedido.quadros) {
    await renderStill({
      serveUrl, composition, inputProps, puppeteerInstance: navegador, frame: Math.min(q, composition.durationInFrames - 1),
      output: saida, imageFormat: "jpeg", jpegQuality: 82, scale: pedido.escala ?? 0.4, overwrite: true, chromiumOptions: { gl: "angle" },
      onBrowserLog: (l) => {
        if (l.type === "error") console.log(`ERRO ${q} ${l.text.replace(/\s+/g, " ").slice(0, 400)}`);
      },
    });
    console.log(`QUADRO ${q}`);
  }
} finally {
  await navegador.close({ silent: true });
}
