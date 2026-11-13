// Adaptador Remotion do kit/anotacao: desenha o estado(t) do kit numa camada SVG (sem medir nada no motor).
// Toda a geometria vem do kit; aqui só vira <path>. Uso:
//   const m = useMemo(() => montar(cena, fonte), []);
//   <CamadaAnotacao montada={m} />
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { estado, type Montada, type TracoEstado } from "../../kit/anotacao/anotacao.ts";

const Traco: React.FC<{ tr: TracoEstado; cor: string }> = ({ tr, cor }) => (
  <path
    d={tr.d}
    fill="none"
    stroke={cor}
    strokeWidth={tr.largura}
    strokeLinecap="round"
    strokeLinejoin="round"
    pathLength={1}
    strokeDasharray="1 2"
    strokeDashoffset={1 - tr.k}
    opacity={tr.k > 0 ? 1 : 0}
  />
);

export const CamadaAnotacao: React.FC<{ montada: Montada }> = ({ montada }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const itens = estado(montada, frame / fps);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={width} height={height} viewBox={`0 0 ${montada.cena.largura} ${montada.cena.altura}`} style={{ position: "absolute", inset: 0 }}>
        {itens.map((it) => (
          <g key={it.id} transform={it.transform}>
            {it.tracos.map((tr, i) => <Traco key={i} tr={tr} cor={it.cor} />)}
            {it.glifos.map((g, gi) => {
              const id = `anot-${it.id}-${gi}`;
              return (
                <g key={gi} transform={g.transform}>
                  {g.outline ? (
                    <>
                      <mask id={id} maskUnits="userSpaceOnUse" x={-600} y={-1400} width={2400} height={2200}>
                        {g.tracos.filter((tr) => !tr.tinta).map((tr, i) => <Traco key={i} tr={tr} cor="#fff" />)}
                      </mask>
                      <path d={g.outline} fill={it.cor} mask={`url(#${id})`} />
                    </>
                  ) : null}
                  {g.tracos.filter((tr) => tr.tinta).map((tr, i) => <Traco key={`t${i}`} tr={tr} cor={it.cor} />)}
                </g>
              );
            })}
          </g>
        ))}
      </svg>
    </AbsoluteFill>
  );
};
