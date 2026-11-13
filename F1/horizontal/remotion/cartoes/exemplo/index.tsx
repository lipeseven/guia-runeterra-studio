// Exemplo mínimo Remotion do kit/cartoes: pista estilizada, tag fixa na curva, tag presa a um carro que anda, cartão de
// pessoa e cartão de capítulo. Render (feito por F1/horizontal/testes/cartoes/rodar.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploCartoes <pasta> --sequence
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot, useCurrentFrame, useVideoConfig } from "remotion";
import { ancoraTag, montarCartoes, type CenaCartoes, type Tag } from "../../../kit/cartoes/cartoes.ts";
import cenaJson from "../../../kit/cartoes/exemplo/cena.json";
// @ts-expect-error o bundler do Remotion devolve a URL do arquivo
import fotoUrl from "../../../kit/cartoes/exemplo/foto_exemplo.jpg";
import { CamadaCartoes } from "../CamadaCartoes";

type CenaEx = CenaCartoes & { fundo_svg: string; carro: { t: number; x: number; y: number }[] };
const cena = cenaJson as unknown as CenaEx;

const Exemplo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const m = useMemo(() => montarCartoes({ ...cena, cartoes: cena.cartoes.map((c) => (c.tipo === "pessoa" ? { ...c, foto: fotoUrl as string } : c)) }), []);
  const [cx, cy] = ancoraTag({ ancora: cena.carro } as Tag, frame / fps);
  return (
    <AbsoluteFill style={{ background: "#f3f1ec" }}>
      <svg width={cena.largura} height={cena.altura} style={{ position: "absolute", inset: 0 }}>
        <g dangerouslySetInnerHTML={{ __html: cena.fundo_svg }} />
        <rect x={cx - 16} y={cy - 9} width={32} height={18} rx={5} fill="#c8102e" />
      </svg>
      <CamadaCartoes montada={m} />
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploCartoes" component={Exemplo} durationInFrames={Math.round(cena.duracao * cena.fps) + 1} fps={cena.fps} width={cena.largura} height={cena.altura} />
));
