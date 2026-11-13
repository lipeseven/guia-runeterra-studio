// Adaptador Remotion do kit/graficos: desenha o estado(t) do kit numa camada SVG. Nada é medido nem calculado aqui:
// escala, rótulos, cores e desenho progressivo vêm do kit. Uso:
//   const m = useMemo(() => montar(specs, dados, larguras), []);
//   <CamadaGrafico montado={m} />            (o fundo do tema é do quadro: TEMAS[tema].fundo)
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { estado, type Montado } from "../../kit/graficos/graficos.ts";

export const CamadaGrafico: React.FC<{ montado: Montado; largura?: number; altura?: number }> = ({ montado, largura, altura }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const des = estado(montado, frame / fps);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={width} height={height} viewBox={`0 0 ${largura ?? width} ${altura ?? height}`} style={{ position: "absolute", inset: 0 }}>
        {des.map((d) =>
          d.tipo === "path" ? (
            <path key={d.id} d={d.d} fill={d.fill ?? "none"} stroke={d.stroke ?? "none"} strokeWidth={d.largura}
              strokeLinecap={d.tracejado ? "butt" : "round"} strokeLinejoin="round" strokeDasharray={d.tracejado} opacity={d.opac} />
          ) : (
            <text key={d.id} x={d.x} y={d.y} fontFamily={montado.fonteCss} fontSize={d.tam} fontWeight={d.peso} fill={d.cor}
              textAnchor={d.ancora} opacity={d.opac}>{d.texto}</text>
          ),
        )}
      </svg>
    </AbsoluteFill>
  );
};
