// Cena genérica do montador (F1/horizontal/montador): UMA cena da SPEC no Remotion, com as camadas que a receita
// (montador/receitas.py) montou a partir dos kits. Nada é decidido aqui: dados, textos, caixas e tempos vêm nas props.
// Relógio: tau = (quadro - pre) / 60; os `pre` quadros da transição de entrada seguram o quadro 0.
// Render (feito por montador/segmentos.py):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx CenaDoc <pasta> --sequence --props=<json>
//   Lote (várias cenas numa invocação, segmentos.renderizar_lote): composição LoteDoc com props {cenas: Props[]}.
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, Freeze, Sequence, registerRoot, useCurrentFrame } from "remotion";
// @ts-ignore módulo JS puro, compartilhado com a cena HyperFrames (montador/hyperframes/gps.html)
import { movimento, transformCss } from "../../montador/movimento.js";
import { montar as montarGraficos, TEMAS, type Dados, type Larguras, type Spec } from "../../kit/graficos/graficos.ts";
import { montar as montarAnotacao, type Cena as CenaAnotacao, type Fonte } from "../../kit/anotacao/anotacao.ts";
import { montarCartoes, type CenaCartoes } from "../../kit/cartoes/cartoes.ts";
import { montarFoco, type CenaFoco } from "../../kit/foco/foco.ts";
import { CamadaGrafico } from "../graficos/CamadaGrafico";
import { CamadaAnotacao } from "../anotacao/CamadaAnotacao";
import { CamadaCartoes } from "../cartoes/CamadaCartoes";
import { CamadaFoco } from "../foco/CamadaFoco";

type Linha = { texto: string; fonte: string; peso: number; tamanho: number; x: number; y: number };
type Camada =
  | { kit: "graficos"; specs: Spec[]; dados: Dados; larguras: Larguras }
  | { kit: "anotacao"; cena: CenaAnotacao; linhas: Linha[]; fonte: Fonte }
  | { kit: "cartoes"; cena: CenaCartoes }
  | { kit: "foco"; cena: CenaFoco };
type Movimento = { tipo: string; intensidade?: number; foco?: [number, number] };
// movimento/L: câmera da cena inteira (ação direta do storyboard) ao longo dos L quadros puros da cena
type Props = { quadros: number; pre: number; largura: number; altura: number; camadas: Camada[]; movimento?: Movimento | null; L?: number };
type PropsLote = { largura: number; altura: number; cenas: Props[] };

const TINTA = "#141414";
const FUNDO = TEMAS.claro.fundo;   // fundo claro = assinatura do canal

const Graficos: React.FC<{ c: Extract<Camada, { kit: "graficos" }> }> = ({ c }) => {
  const m = useMemo(() => montarGraficos(c.specs.map((s) => ({ tema: "claro" as const, ...s })), c.dados, c.larguras), [c]);
  return <CamadaGrafico montado={m} largura={1920} altura={1080} />;
};

// textos da cena (o que o foco desfoca) e, à parte, os traços à mão (ficam nítidos por cima do foco)
const Textos: React.FC<{ c: Extract<Camada, { kit: "anotacao" }> }> = ({ c }) => (
  <AbsoluteFill>
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
      {c.linhas.map((l, i) => (
        <text key={i} x={l.x} y={l.y} fontFamily={`"${l.fonte}"`} fontWeight={l.peso} fontSize={l.tamanho} fill={TINTA}>{l.texto}</text>
      ))}
    </svg>
  </AbsoluteFill>
);

const Tracos: React.FC<{ c: Extract<Camada, { kit: "anotacao" }> }> = ({ c }) => {
  const m = useMemo(() => montarAnotacao(c.cena, c.fonte), [c]);
  return c.cena.anotacoes.length ? <CamadaAnotacao montada={m} /> : null;
};

const Cartoes: React.FC<{ c: Extract<Camada, { kit: "cartoes" }> }> = ({ c }) => {
  const m = useMemo(() => montarCartoes(c.cena), [c]);
  return <CamadaCartoes montada={m} />;
};

const Foco: React.FC<{ c: Extract<Camada, { kit: "foco" }> }> = ({ c }) => {
  const m = useMemo(() => montarFoco(c.cena), [c]);
  return <CamadaFoco montada={m} />;
};

const CenaDoc: React.FC<Props> = ({ quadros, pre, camadas, movimento: mov, L }) => {
  const frame = useCurrentFrame();
  const tau = Math.max(0, frame - pre);
  // ordem fixa: gráfico/cartão → textos → foco → traços à mão (a anotação fica nítida sobre o desfoque)
  const de = <K extends Camada["kit"]>(k: K) => camadas.filter((c): c is Extract<Camada, { kit: K }> => c.kit === k);
  const conteudo = (
    <Freeze frame={tau}>
      {de("graficos").map((c, i) => <Graficos key={`g${i}`} c={c} />)}
      {de("cartoes").map((c, i) => <Cartoes key={`c${i}`} c={c} />)}
      {de("anotacao").map((c, i) => <Textos key={`t${i}`} c={c} />)}
      {de("foco").map((c, i) => <Foco key={`f${i}`} c={c} />)}
      {de("anotacao").map((c, i) => <Tracos key={`a${i}`} c={c} />)}
    </Freeze>
  );
  return (
    <AbsoluteFill style={{ background: FUNDO, overflow: "hidden" }}>
      {mov && mov.tipo !== "parado"
        ? <AbsoluteFill style={transformCss(movimento(mov, tau / Math.max(1, (L ?? quadros) - 1)))}>{conteudo}</AbsoluteFill>
        : conteudo}
    </AbsoluteFill>
  );
};

const LoteDoc: React.FC<PropsLote> = ({ cenas }) => {
  let ini = 0;
  return (
    <AbsoluteFill style={{ background: FUNDO }}>
      {cenas.map((c, i) => {
        const de = ini;
        ini += c.quadros;
        return <Sequence key={i} from={de} durationInFrames={c.quadros}><CenaDoc {...c} /></Sequence>;
      })}
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <>
    <Composition id="CenaDoc" component={CenaDoc} fps={60} width={1920} height={1080} durationInFrames={60}
      defaultProps={{ quadros: 60, pre: 0, largura: 1920, altura: 1080, camadas: [] } as Props}
      calculateMetadata={({ props }) => ({ durationInFrames: props.quadros, width: props.largura, height: props.altura })} />
    <Composition id="LoteDoc" component={LoteDoc} fps={60} width={1920} height={1080} durationInFrames={60}
      defaultProps={{ largura: 1920, altura: 1080, cenas: [] } as PropsLote}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.cenas.reduce((s, c) => s + c.quadros, 0)),
                                           width: props.largura, height: props.altura })} />
  </>
));
