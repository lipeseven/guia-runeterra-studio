// Adaptador Remotion do kit/cartoes: desenha o SVG que o kit monta para o tempo do quadro (layout e animação no kit).
//   const m = useMemo(() => montarCartoes(cena), []);   // `foto` de cada pessoa já como URL (staticFile/import)
//   <CamadaCartoes montada={m} />
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { svgCartoes, type MontadaCartoes } from "../../kit/cartoes/cartoes.ts";

export const CamadaCartoes: React.FC<{ montada: MontadaCartoes }> = ({ montada }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { largura, altura } = montada.cena;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={largura} height={altura} viewBox={`0 0 ${largura} ${altura}`} style={{ position: "absolute", inset: 0 }}
        dangerouslySetInnerHTML={{ __html: svgCartoes(montada, frame / fps) }} />
    </AbsoluteFill>
  );
};
