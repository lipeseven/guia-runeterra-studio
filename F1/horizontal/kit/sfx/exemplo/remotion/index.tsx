// Exemplo mínimo Remotion: o trilho de 20 s do exemplo (pedidos.json + palavras.json) calculado pela API TS.
// Render só do áudio (feito por exemplo_20s.py --motores):
//   node <F1/video/node_modules>/@remotion/cli/remotion-cli.js render index.tsx ExemploSfx saida.wav --public-dir=../saida/remotion_public
import React from "react";
import { AbsoluteFill, Composition, registerRoot } from "remotion";
import { Banco, type Catalogo, type Palavra, type Pedido } from "../../sfx.ts";
import catalogo from "../../catalogo.json";
import pedidos from "../pedidos.json";
import palavras from "../palavras.json";
import { TrilhaSfx } from "./TrilhaSfx";

const Exemplo: React.FC = () => {
  const eventos = new Banco(catalogo as unknown as Catalogo, 0).dePedidos(pedidos as Pedido[], palavras as Palavra[]);
  return (
    <AbsoluteFill style={{ background: "#ecebe7" }}>
      <TrilhaSfx eventos={eventos} />
    </AbsoluteFill>
  );
};

registerRoot(() => (
  <Composition id="ExemploSfx" component={Exemplo} durationInFrames={20 * 60} fps={60} width={320} height={180} />
));
