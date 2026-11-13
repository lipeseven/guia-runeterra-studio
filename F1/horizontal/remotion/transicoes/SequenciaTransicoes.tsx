// Adaptador Remotion do kit/transicoes: desenha as cenas ligadas pelas transições, aplicando em cada quadro o estilo
// que o kit calcula (opacidade, escala, recorte, desfoque) e a barra do wipe. O SFX vem de pedidosSfx(ts) → kit/sfx
// (Banco.dePedidos) → <TrilhaSfx> (kit/sfx/exemplo/remotion/TrilhaSfx.tsx).
//   const ts = montarTransicoes([{ tipo: "corte", em: 1, sfx: "impacto" }, { tipo: "wipe", em: 3 }], fps);
//   <SequenciaTransicoes ts={ts} cenas={[<CenaA/>, <CenaB/>, <CenaC/>]} />
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { estadoSequencia, type TransicaoM } from "../../kit/transicoes/transicoes.ts";

export const SequenciaTransicoes: React.FC<{ ts: TransicaoM[]; cenas: React.ReactNode[] }> = ({ ts, cenas }) => {
  const frame = useCurrentFrame();
  const s = estadoSequencia(ts, frame);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {s.itens.map((it) => (
        <div key={it.cena} style={it.estilo as React.CSSProperties}>{cenas[it.cena]}</div>
      ))}
      {s.barra ? <div style={{ position: "absolute", left: s.barra.x, top: s.barra.y, width: s.barra.w, height: s.barra.h, background: s.barra.cor }} /> : null}
    </AbsoluteFill>
  );
};
