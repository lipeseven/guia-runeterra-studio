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
  | { kit: "foco"; cena: CenaFoco }
  | { kit: "duelo"; titulo: string; unidade: string; rodape: string; destaque?: number | null; destaqueEm: number;
      forma?: "cartoes" | "barras"; escala?: [number, number] | null;
      lados: { sigla: string; nome: string; equipe: string; cor: string; valor: string; em: number }[] };
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

// Duelo: dois cartões lado a lado (piloto, equipe, número grande) na cor da equipe; os cartões entram no início e cada
// NÚMERO entra seco na própria palavra
// (opacidade em 0,15 s, sem animação de texto); o lado `destaque` ganha contorno na cor dele depois que os dois entram.
const Duelo: React.FC<{ c: Extract<Camada, { kit: "duelo" }> }> = ({ c }) => {
  const t = useCurrentFrame() / 60;
  const ent = (em: number) => Math.min(1, Math.max(0, (t - em) / 0.15));
  if (c.forma === "barras") {
    // rodada 2: forma "barras" (variar os duelos): eixo e nomes desde o início, cada barra cresce em 0,5 s na palavra
    const [v0, v1] = c.escala ?? [0, Math.max(...c.lados.map((l) => parseFloat(l.valor) || 0)) * 1.05];
    const X0 = 520, X1 = 1680, cres = (em: number) => { const u = Math.min(1, Math.max(0, (t - em) / 0.5)); return 1 - (1 - u) ** 3; };
    const px = (v: number) => X0 + ((v - v0) / (v1 - v0)) * (X1 - X0);
    const ticks = Array.from({ length: 5 }, (_, i) => v0 + ((v1 - v0) * i) / 4);
    return (
      <AbsoluteFill>
        <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
          <text x={960} y={190} textAnchor="middle" fontFamily='"Arial Black"' fontWeight={900} fontSize={76} fill={TINTA}>{c.titulo}</text>
          {ticks.map((v, i) => (
            <g key={i}>
              <line x1={px(v)} x2={px(v)} y1={300} y2={780} stroke="#d9d7d0" strokeWidth={2} />
              <text x={px(v)} y={830} textAnchor="middle" fontFamily='"Arial"' fontSize={34} fill="#777">{Math.round(v)}</text>
            </g>
          ))}
          {c.lados.map((l, k) => {
            const y = 340 + k * 230, v = parseFloat(l.valor) || 0, w = (px(v) - X0) * cres(l.em);
            const marcado = c.destaque === k && t >= c.destaqueEm;
            return (
              <g key={k}>
                <rect x={240} y={y + 20} width={14} height={110} fill={l.cor} />
                <text x={274} y={y + 80} fontFamily='"Arial"' fontWeight={700} fontSize={60} fill={TINTA}>{l.sigla}</text>
                <text x={274} y={y + 122} fontFamily='"Arial"' fontSize={30} fill="#555">{l.equipe}</text>
                <rect x={X0} y={y} width={Math.max(0, w)} height={150} rx={10} fill={l.cor} stroke={marcado ? TINTA : "none"} strokeWidth={6} />
                <text x={X0 + w - 24} y={y + 104} textAnchor="end" fontFamily='"Arial Black"' fontWeight={900} fontSize={84} fill="#fff"
                  opacity={ent(l.em + 0.35)}>{`${l.valor} ${c.unidade}`}</text>
              </g>
            );
          })}
          <text x={1680} y={880} textAnchor="end" fontFamily='"Arial"' fontSize={30} fill="#777">{`eixo de ${Math.round(v0)} a ${Math.round(v1)} ${c.unidade}`}</text>
          {c.rodape ? <text x={1872} y={1036} textAnchor="end" fontFamily='"Segoe UI"' fontSize={28} fill="#666">{c.rodape}</text> : null}
        </svg>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        <text x={960} y={190} textAnchor="middle" fontFamily='"Arial Black"' fontWeight={900} fontSize={76} fill={TINTA}>{c.titulo}</text>
        {c.lados.map((l, k) => {
          const x = k === 0 ? 260 : 1020, y = 300, w = 640, h = 520;
          const marcado = c.destaque === k && t >= c.destaqueEm;
          return (
            <g key={k} opacity={ent(l.em)}>
              <rect x={x} y={y} width={w} height={h} rx={18} fill="#ffffff" stroke={marcado ? l.cor : "#d9d7d0"} strokeWidth={marcado ? 10 : 2} />
              <rect x={x} y={y} width={w} height={22} rx={10} fill={l.cor} />
              <text x={x + 48} y={y + 120} fontFamily='"Arial"' fontWeight={700} fontSize={64} fill={TINTA}>{l.sigla}</text>
              <text x={x + 48} y={y + 172} fontFamily='"Arial"' fontWeight={400} fontSize={38} fill="#555">{`${l.nome} · ${l.equipe}`}</text>
              <text x={x + w / 2} y={y + 380} textAnchor="middle" fontFamily='"Arial Black"' fontWeight={900} fill={TINTA} opacity={ent(l.em)}
                fontSize={Math.min(150, 560 / [...l.valor].reduce((s, ch) => s + (/[0-9]/.test(ch) ? 0.667 : 0.34), 0))}>{l.valor}</text>
              {c.unidade ? <text x={x + w / 2} y={y + 450} textAnchor="middle" fontFamily='"Arial"' fontWeight={700} fontSize={40} fill="#555" opacity={ent(l.em)}>{c.unidade}</text> : null}
            </g>
          );
        })}
        {c.rodape ? <text x={1872} y={1036} textAnchor="end" fontFamily='"Segoe UI"' fontSize={28} fill="#666">{c.rodape}</text> : null}
      </svg>
    </AbsoluteFill>
  );
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
      {de("duelo").map((c, i) => <Duelo key={`d${i}`} c={c} />)}
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
