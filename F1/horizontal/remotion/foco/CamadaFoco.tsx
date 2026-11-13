// Adaptador Remotion do kit/foco: uma camada por cima da cena que desfoca (backdrop-filter) e escurece de leve tudo
// que está fora da janela nítida da peça. Toda a conta (janela, máscara, força) vem do kit; aqui só vira <div>.
// Coloque DEPOIS (por cima) do que deve ser desfocado e ANTES de legendas/anotações que devem ficar nítidas:
//   const m = useMemo(() => montarFoco(cena), []);
//   <Cena3D /> <CamadaFoco montada={m} /> <CamadaAnotacao ... />
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { estadoFoco, estilos, type MontadaFoco } from "../../kit/foco/foco.ts";

export const CamadaFoco: React.FC<{ montada: MontadaFoco }> = ({ montada }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const est = estadoFoco(montada, frame / fps);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {est.map((e) => {
        const s = estilos(e);
        return (
          <React.Fragment key={e.id}>
            <div style={s.camada as React.CSSProperties} />
            <div style={s.veu as React.CSSProperties} />
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};
