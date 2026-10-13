import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ALTURA, LARGURA, cor } from "../estilo";
import type { CenaCapa } from "../tipos";

/** A própria capa do vídeo (grade de ícones) com a câmera fechando no personagem em destaque. */
export const Capa: React.FC<{ cena: CenaCapa; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const { w, h } = cena.midia;
  // "cover": a capa preenche a tela; calcula onde o círculo em destaque cai na tela.
  const k = Math.max(LARGURA / w, ALTURA / h);
  const ox = (LARGURA - w * k) / 2;
  const oy = (ALTURA - h * k) / 2;
  const alvo = cena.circulos[cena.destaque];
  const ax = ox + alvo.cx * w * k;
  const ay = oy + alvo.cy * h * k;
  const p = interpolate(frame, [0, Math.max(1, duracao)], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const escala = 1 + (cena.zoom - 1) * p;
  return (
    <AbsoluteFill style={{ background: cor.fundo, overflow: "hidden" }}>
      <Img
        src={staticFile(cena.midia.arquivo)}
        style={{
          position: "absolute",
          left: ox,
          top: oy,
          width: w * k,
          height: h * k,
          transformOrigin: `${ax - ox}px ${ay - oy}px`,
          transform: `translate(${(LARGURA / 2 - ax) * p}px, ${(ALTURA / 2 - ay) * p}px) scale(${escala})`,
        }}
      />
    </AbsoluteFill>
  );
};
