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
  // o nome do personagem fica EMBAIXO do círculo: a câmera mira um pouco abaixo do centro e o zoom é limitado
  // para círculo + nome caberem na tela (antes o nome era cortado pela borda de baixo)
  const raio = alvo.r * Math.min(w, h) * k;
  const ax = ox + alvo.cx * w * k;
  const ay = oy + alvo.cy * h * k + raio * 0.55;
  const zoomMax = (ALTURA * 0.82) / (raio * 3.1);
  const zoom = Math.max(1, Math.min(cena.zoom, zoomMax));
  // continuidade (transição de seção): começa onde a transição anterior parou — fechado no ícone da seção
  // anterior —, afasta até a capa inteira e fecha no próximo. O layout da capa nunca muda.
  const origem = cena.origem !== undefined && cena.origem !== cena.destaque ? cena.circulos[cena.origem] : null;
  if (origem) {
    const ro = origem.r * Math.min(w, h) * k;
    const bx = ox + origem.cx * w * k;
    const by = oy + origem.cy * h * k + ro * 0.55;
    const zo = Math.max(1, Math.min(cena.zoom, (ALTURA * 0.82) / (ro * 3.1)));
    const meio = Math.max(2, duracao * 0.4);
    const saindo = interpolate(frame, [0, meio], [1, 0], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
    const entrando = interpolate(frame, [meio, Math.max(meio + 1, duracao)], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });
    const [px, py, z] = frame < meio ? [bx, by, 1 + (zo - 1) * saindo] : [ax, ay, 1 + (zoom - 1) * entrando];
    const t = frame < meio ? saindo : entrando;
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
            transformOrigin: `${px - ox}px ${py - oy}px`,
            transform: `translate(${(LARGURA / 2 - px) * t}px, ${(ALTURA / 2 - py) * t}px) scale(${z})`,
          }}
        />
      </AbsoluteFill>
    );
  }
  const p = interpolate(frame, [0, Math.max(1, duracao)], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const escala = 1 + (zoom - 1) * p;
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
