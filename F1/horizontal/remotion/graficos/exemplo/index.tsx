// Exemplo mínimo Remotion do kit/graficos: a cena de teste (kit/graficos/exemplo/cena.json), 5 gráficos em sequência.
// Render (feito por F1/horizontal/testes/graficos/rodar.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploGraficos <pasta> --sequence
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot } from "remotion";
import { montar, TEMAS, type Dados, type Larguras, type Spec } from "../../../kit/graficos/graficos.ts";
import cenaJson from "../../../kit/graficos/exemplo/cena.json";
import dadosJson from "../../../kit/graficos/comparacoes/11408_16-17_12-22.json";
import largJson from "../../../kit/graficos/fonte/segoe_larguras.json";
import { CamadaGrafico } from "../CamadaGrafico";

type Cena = { largura: number; altura: number; fps: number; duracao: number; tema?: "claro" | "escuro"; graficos: Spec[] };
const cena = cenaJson as unknown as Cena;

const Exemplo: React.FC = () => {
  const m = useMemo(() => montar(cena.graficos.map((g) => ({ tema: cena.tema, ...g })), dadosJson as unknown as Dados, largJson as unknown as Larguras), []);
  return (
    <AbsoluteFill style={{ background: TEMAS[cena.tema ?? "claro"].fundo }}>
      <CamadaGrafico montado={m} largura={cena.largura} altura={cena.altura} />
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploGraficos" component={Exemplo} durationInFrames={Math.round(cena.duracao * cena.fps) + 1} fps={cena.fps} width={cena.largura} height={cena.altura} />
));
