// Cena genérica do montador (F1/horizontal/montador): UMA cena da SPEC no Remotion, com as camadas que a receita
// (montador/receitas.py) montou a partir dos kits. Nada é decidido aqui: dados, textos, caixas e tempos vêm nas props.
// Relógio: tau = (quadro - pre) / 60; os `pre` quadros da transição de entrada seguram o quadro 0.
// Render (feito por montador/segmentos.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx CenaDoc <pasta> --sequence --props=<json>
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, Freeze, registerRoot, useCurrentFrame } from "remotion";
import { montar as montarGraficos, TEMAS, type Dados, type Larguras, type Spec } from "../../kit/graficos/graficos.ts";
import { montar as montarAnotacao, type Cena as CenaAnotacao, type Fonte } from "../../kit/anotacao/anotacao.ts";
import { CamadaGrafico } from "../graficos/CamadaGrafico";
import { CamadaAnotacao } from "../anotacao/CamadaAnotacao";

type Linha = { texto: string; fonte: string; peso: number; tamanho: number; x: number; y: number };
type Camada =
  | { kit: "graficos"; specs: Spec[]; dados: Dados; larguras: Larguras }
  | { kit: "anotacao"; cena: CenaAnotacao; linhas: Linha[]; fonte: Fonte };
type Props = { quadros: number; pre: number; largura: number; altura: number; camadas: Camada[] };

const TINTA = "#141414";
const FUNDO = TEMAS.claro.fundo;   // fundo claro = assinatura do canal

const Graficos: React.FC<{ c: Extract<Camada, { kit: "graficos" }> }> = ({ c }) => {
  const m = useMemo(() => montarGraficos(c.specs.map((s) => ({ tema: "claro" as const, ...s })), c.dados, c.larguras), [c]);
  return <CamadaGrafico montado={m} largura={1920} altura={1080} />;
};

const Anotacao: React.FC<{ c: Extract<Camada, { kit: "anotacao" }> }> = ({ c }) => {
  const m = useMemo(() => montarAnotacao(c.cena, c.fonte), [c]);
  return (
    <>
      <AbsoluteFill>
        <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
          {c.linhas.map((l, i) => (
            <text key={i} x={l.x} y={l.y} fontFamily={`"${l.fonte}"`} fontWeight={l.peso} fontSize={l.tamanho} fill={TINTA}>{l.texto}</text>
          ))}
        </svg>
      </AbsoluteFill>
      <CamadaAnotacao montada={m} />
    </>
  );
};

const CenaDoc: React.FC<Props> = ({ pre, camadas }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: FUNDO }}>
      <Freeze frame={Math.max(0, frame - pre)}>
        {camadas.map((c, i) => (c.kit === "graficos" ? <Graficos key={i} c={c} /> : <Anotacao key={i} c={c} />))}
      </Freeze>
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="CenaDoc" component={CenaDoc} fps={60} width={1920} height={1080} durationInFrames={60}
    defaultProps={{ quadros: 60, pre: 0, largura: 1920, altura: 1080, camadas: [] } as Props}
    calculateMetadata={({ props }) => ({ durationInFrames: props.quadros, width: props.largura, height: props.altura })} />
));
