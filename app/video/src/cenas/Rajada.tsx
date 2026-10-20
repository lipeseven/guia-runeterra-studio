// Rajada: 3 a 6 imagens-relâmpago (≈0,1–0,15 s cada, com flash branco entre elas) e a última fica na tela até o
// fim da cena, com movimento. Pontuação rítmica dos canais rápidos (evolução, golpes, "olha quantos são").
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Figura } from "../componentes/Figura";
import { transformMovimento, type Movimento } from "../efeitos";
import type { Midia } from "../tipos";

export type CenaRajada = { tipo: "rajada"; de: number; ate: number; itens: { midia: Midia; foco?: [number, number] }[]; movimento?: Movimento };

const QUADROS_POR_IMAGEM = 8; // 60 fps → 0,13 s

export const Rajada: React.FC<{ cena: CenaRajada; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const n = cena.itens.length;
  if (!n) return <AbsoluteFill style={{ background: "#fff" }} />;
  const k = Math.min(n - 1, Math.floor(frame / QUADROS_POR_IMAGEM));
  const fimRajada = (n - 1) * QUADROS_POR_IMAGEM;
  const naRajada = frame < fimRajada;
  // flash branco nos 2 primeiros quadros de cada troca
  const flash = naRajada && frame % QUADROS_POR_IMAGEM < 2 ? 0.75 : 0;
  const p = interpolate(frame, [fimRajada, Math.max(fimRajada + 1, duracao)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const item = cena.itens[k];
  // arte recortada (PNG transparente) entra inteira no branco do canal; foto/screenshot preenche a tela
  const recorte = item.midia.arquivo.toLowerCase().endsWith(".png");
  return (
    <AbsoluteFill style={{ background: recorte ? "#fff" : "#000", overflow: "hidden" }}>
      <Figura
        midia={item.midia}
        largura={1920}
        altura={1080}
        ajuste={recorte ? "contain" : "cover"}
        foco={item.foco}
        style={{ transform: naRajada ? `scale(${1.04 + 0.02 * (k % 2)})` : transformMovimento(cena.movimento, p) }}
      />
      {flash > 0 && <AbsoluteFill style={{ background: "#fff", opacity: flash }} />}
    </AbsoluteFill>
  );
};
