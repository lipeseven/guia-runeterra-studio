import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Icone } from "../componentes/Icone";
import { cor, fonte } from "../estilo";
import type { CenaGrade } from "../tipos";
import { variar } from "../tempo";

const POR_LINHA = 5;
const TAMANHO = 300;

/** Grade de retratos da abertura; a câmera fecha no personagem em destaque. */
export const Grade: React.FC<{ cena: CenaGrade; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const linhas = Math.ceil(cena.icones.length / POR_LINHA);
  const pos = (k: number) => ({
    x: 1920 / (POR_LINHA * 2) * (2 * (k % POR_LINHA) + 1),
    y: linhas === 1 ? 470 : 300 + Math.floor(k / POR_LINHA) * 420,
  });

  // Zoom até o destaque, depois que os ícones já entraram.
  const alvo = pos(cena.destaque);
  const zoomFinal = variar(cena.semente ?? "grade", 2.3, 2.7);
  const p = interpolate(frame, [8, Math.max(9, duracao - 2)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const escala = 1 + (zoomFinal - 1) * p;
  const dx = (960 - alvo.x) * p;
  const dy = (540 - (alvo.y + 60)) * p;

  return (
    <AbsoluteFill style={{ background: cor.fundo }}>
      <AbsoluteFill
        style={{
          transformOrigin: `${alvo.x}px ${alvo.y + 60}px`,
          transform: `translate(${dx}px, ${dy}px) scale(${escala})`,
        }}
      >
        {cena.icones.map((icone, k) => {
          const { x, y } = pos(k);
          const entrada = spring({ frame: frame - k * 2, fps, config: { damping: 12, stiffness: 180 } });
          return (
            <div
              key={icone.nome}
              style={{
                position: "absolute",
                left: x - TAMANHO / 2,
                top: y - TAMANHO / 2,
                width: TAMANHO,
                transform: `scale(${entrada})`,
                textAlign: "center",
              }}
            >
              <Icone icone={icone} tamanho={TAMANHO} />
              <div style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: 50, color: cor.texto, marginTop: 14 }}>
                {icone.nome}
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
