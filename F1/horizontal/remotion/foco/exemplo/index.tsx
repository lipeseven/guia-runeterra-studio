// Exemplo mínimo Remotion do kit/foco: carro estilizado andando sobre fundo claro, foco na asa traseira (caixa) e depois
// na roda dianteira (elipse). Prop `semFoco` = mesma cena sem a camada (referência do teste de pixels).
// Render (feito por F1/horizontal/testes/foco/rodar.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploFoco <pasta> --sequence
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot, useCurrentFrame, useVideoConfig } from "remotion";
import { ancoraEm } from "../../../kit/anotacao/anotacao.ts";
import { montarFoco, type CenaFoco } from "../../../kit/foco/foco.ts";
import cenaJson from "../../../kit/foco/exemplo/cena.json";
import { CamadaFoco } from "../CamadaFoco";

type CenaEx = CenaFoco & { fundo_svg: string; carro_svg: string; movimento: { t: number; dx: number; dy: number }[] };
const cena = cenaJson as unknown as CenaEx;

const Exemplo: React.FC<{ semFoco?: boolean }> = ({ semFoco }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const m = useMemo(() => montarFoco(cena), []);
  const a = ancoraEm({ caixa: { x: 0, y: 0, w: 0, h: 0 }, movimento: cena.movimento }, frame / fps);
  return (
    <AbsoluteFill style={{ background: "#f3f1ec" }}>
      <svg width={cena.largura} height={cena.altura} style={{ position: "absolute", inset: 0 }}>
        <g dangerouslySetInnerHTML={{ __html: cena.fundo_svg }} />
        <g transform={`translate(${a.dx} ${a.dy})`} dangerouslySetInnerHTML={{ __html: cena.carro_svg }} />
      </svg>
      {semFoco ? null : <CamadaFoco montada={m} />}
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploFoco" component={Exemplo} durationInFrames={Math.round(cena.duracao * cena.fps) + 1} fps={cena.fps} width={cena.largura} height={cena.altura} defaultProps={{ semFoco: false }} />
));
