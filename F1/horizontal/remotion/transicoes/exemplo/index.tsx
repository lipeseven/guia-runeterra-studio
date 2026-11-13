// Exemplo mínimo Remotion do kit/transicoes: 5 cenas paradas ligadas por corte (impacto), fade, wipe (whoosh) e
// zoom-through (whoosh), com os SFX do kit/sfx no quadro de pico. Render (feito por F1/horizontal/testes/transicoes/rodar.py,
// que monta o public dir só com os WAVs usados):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploTransicoes <pasta> --sequence --public-dir=<pasta>
import React, { useMemo } from "react";
import { AbsoluteFill, Composition, registerRoot } from "remotion";
import { montarTransicoes, pedidosSfx, type Transicao } from "../../../kit/transicoes/transicoes.ts";
import { Banco, type Catalogo } from "../../../kit/sfx/sfx.ts";
import catalogoJson from "../../../kit/sfx/catalogo.json";
import cenaJson from "../../../kit/transicoes/exemplo/cena.json";
import { TrilhaSfx } from "../../../kit/sfx/exemplo/remotion/TrilhaSfx";
import { SequenciaTransicoes } from "../SequenciaTransicoes";

const cena = cenaJson as unknown as { largura: number; altura: number; fps: number; duracao: number; cenas: string[]; transicoes: Transicao[] };

const Exemplo: React.FC<{ semSom?: boolean }> = ({ semSom }) => {
  const ts = useMemo(() => montarTransicoes(cena.transicoes, cena.fps), []);
  const eventos = useMemo(() => new Banco(catalogoJson as unknown as Catalogo, 0).dePedidos(pedidosSfx(ts)), [ts]);
  const cenas = cena.cenas.map((svg, i) => (
    <svg key={i} width={cena.largura} height={cena.altura} style={{ position: "absolute", inset: 0 }} dangerouslySetInnerHTML={{ __html: svg }} />
  ));
  return (
    <AbsoluteFill style={{ background: "#f3f1ec" }}>
      <SequenciaTransicoes ts={ts} cenas={cenas} />
      {semSom ? null : <TrilhaSfx eventos={eventos} />}
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploTransicoes" component={Exemplo} durationInFrames={Math.round(cena.duracao * cena.fps) + 1} fps={cena.fps} width={cena.largura} height={cena.altura} defaultProps={{ semSom: false }} />
));
