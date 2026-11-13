// Componente Remotion que toca os eventos do kit de SFX (sfx.ts): cada som numa <Sequence> começando no quadro do
// evento, pulando corte_ini, com o ganho do evento e saída suave de 30 ms (igual a sfx.py/mixar).
// Os WAVs são servidos com staticFile(e.arquivo): o public dir do render precisa ter banco/<categoria>/<id>.wav (o exemplo copia só os usados).
import React from "react";
import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { volume, type Evento } from "../../sfx.ts";

export const TrilhaSfx: React.FC<{ eventos: Evento[] }> = ({ eventos }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {eventos.map((e, k) => {
        const n = Math.max(1, Math.round(e.dur * fps));
        const saida = Math.max(1, Math.round(0.03 * fps));
        return (
          <Sequence key={k} from={Math.round(e.inicio * fps)} durationInFrames={n} layout="none">
            <Audio src={staticFile(e.arquivo)} trimBefore={Math.round(e.corte_ini * fps)}
              volume={(f) => volume(e) * Math.min(1, (n - f) / saida)} />
          </Sequence>
        );
      })}
    </>
  );
};
