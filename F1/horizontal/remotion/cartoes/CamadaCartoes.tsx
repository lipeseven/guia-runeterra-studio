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
      {/* 100%: a cena é desenhada em 1920×1080 e a composição pode ser menor (rascunho 1280×720; uso real 2026-11-14:
          com width={largura} o cartão saía 1,5× maior e cortado) */}
      <svg width="100%" height="100%" viewBox={`0 0 ${largura} ${altura}`} style={{ position: "absolute", inset: 0 }}
        dangerouslySetInnerHTML={{ __html: svgCartoes(montada, frame / fps) }} />
    </AbsoluteFill>
  );
};
