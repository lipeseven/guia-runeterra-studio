import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { EntradaTexto } from "../efeitos";
import { fonte } from "../estilo";
import { CORES } from "../tema";
import type { CenaTexto } from "../tipos";

/** Texto sozinho (guia de estilo §10.2): uma frase/conceito no branco ou no preto, sem imagem ("A Clareza"). */
export const Texto: React.FC<{ cena: CenaTexto; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const c = CORES[cena.fundo];
  const zoom = interpolate(frame, [0, Math.max(1, duracao)], [1, 1.05], { extrapolateRight: "clamp" });
  const tam = cena.texto.length > 50 ? 90 : cena.texto.length > 25 ? 112 : 140;
  return (
    <AbsoluteFill style={{ background: c.fundo, alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${zoom})`, maxWidth: 1500 }}>
        <EntradaTexto
          texto={cena.texto}
          desde={0}
          entrada={cena.entrada_texto}
          style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: tam, lineHeight: 1.2, color: c.texto, textAlign: "center" }}
        />
      </div>
    </AbsoluteFill>
  );
};
