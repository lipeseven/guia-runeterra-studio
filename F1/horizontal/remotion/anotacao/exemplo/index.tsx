// Exemplo mínimo Remotion do kit/anotacao: a cena de teste (kit/anotacao/exemplo/cena.json) com a peça que anda e gira,
// os textos e as 7 anotações. Render (feito por F1/horizontal/testes/anotacao/rodar.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploAnotacao <pasta> --sequence
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot, useCurrentFrame, useVideoConfig } from "remotion";
import { ancoraEm, montar, type Cena, type Fonte } from "../../../kit/anotacao/anotacao.ts";
import cenaJson from "../../../kit/anotacao/exemplo/cena.json";
import fonteJson from "../../../kit/anotacao/fonte/caveat_traco.json";
import { CamadaAnotacao } from "../CamadaAnotacao";

type Render = { texto: string; fonte: string; peso: number; tamanho: number; x: number; y: number };
type CenaEx = Cena & { fundo: string; tinta: string; alvos: Record<string, Cena["alvos"][string] & { render?: Render; peca?: { w: number; h: number; giroAmp: number; giroPeriodo: number; cx: number; cy: number } }> };
const cena = cenaJson as unknown as CenaEx;

const Exemplo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const m = useMemo(() => montar(cena, fonteJson as unknown as Fonte), []);
  const asa = cena.alvos.asa, pc = asa.peca!;
  const an = ancoraEm(asa, t);
  const giro = pc.giroAmp * Math.sin((2 * Math.PI * t) / pc.giroPeriodo);
  return (
    <AbsoluteFill style={{ background: cena.fundo }}>
      <svg width={cena.largura} height={cena.altura} style={{ position: "absolute", inset: 0 }}>
        {Object.entries(cena.alvos).filter(([, a]) => a.render).map(([id, a]) => (
          <text key={id} x={a.render!.x} y={a.render!.y} fontFamily={`"${a.render!.fonte}"`} fontWeight={a.render!.peso} fontSize={a.render!.tamanho} fill={cena.tinta}>
            {a.render!.texto}
          </text>
        ))}
        <g transform={`translate(${pc.cx + an.dx} ${pc.cy + an.dy}) rotate(${giro})`}>
          <rect x={-pc.w / 2} y={-pc.h / 2} width={pc.w} height={pc.h} rx={14} fill="#1d1d1f" />
          <rect x={-pc.w / 2 + 14} y={-pc.h / 2 + 12} width={pc.w - 28} height={30} rx={8} fill="#55565a" />
          <rect x={-pc.w / 2 + 14} y={pc.h / 2 - 34} width={pc.w - 28} height={18} rx={6} fill="#3a3b3f" />
        </g>
      </svg>
      <CamadaAnotacao montada={m} />
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploAnotacao" component={Exemplo} durationInFrames={Math.round(cena.duracao * cena.fps) + 1} fps={cena.fps} width={cena.largura} height={cena.altura} />
));
