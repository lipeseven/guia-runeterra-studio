import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ALTURA, LARGURA, cor } from "../estilo";
import type { CenaCapa } from "../tipos";

const MARGEM = 8; // px entre o círculo e o topo, e entre o nome e a base da tela — Felipe, 2026-10-31

/** Vídeos sem a medida do nome: o que sobra embaixo do círculo até o próximo da coluna ou até o fim da capa, em raios. */
const folgaDoNome = (cena: CenaCapa): number => {
  const { w, h } = cena.midia;
  const m = Math.min(w, h);
  const folgas = cena.circulos.map((c) => {
    const abaixo = cena.circulos.filter((o) => o.cy > c.cy && Math.abs(o.cx - c.cx) * w < c.r * m).map((o) => o.cy * h - o.r * m);
    return (Math.min(h, ...abaixo) - (c.cy * h + c.r * m)) / (c.r * m);
  });
  return Math.min(0.7, Math.max(0, ...folgas));
};

/** A própria capa do vídeo (grade de ícones) com a câmera fechando no personagem em destaque. */
export const Capa: React.FC<{ cena: CenaCapa; duracao: number }> = ({ cena, duracao }) => {
  const frame = useCurrentFrame();
  const { w, h } = cena.midia;
  // "cover": a capa preenche a tela; calcula onde o círculo em destaque cai na tela.
  const k = Math.max(LARGURA / w, ALTURA / h);
  const ox = (LARGURA - w * k) / 2;
  const oy = (ALTURA - h * k) / 2;
  const alvo = cena.circulos[cena.destaque];
  // círculo + nome (embaixo dele) preenchem a altura da tela, sem nunca passar das bordas.
  // O zoom vem só do tamanho do círculo na capa (cena.zoom sorteado não vale mais) e é o mesmo em todos os capítulos.
  const folga = cena.folga_nome ?? folgaDoNome(cena);
  const raio = alvo.r * Math.min(w, h) * k;
  const ax = ox + alvo.cx * w * k;
  const ay = oy + alvo.cy * h * k + (raio * folga) / 2;
  const zoom = Math.max(1, (ALTURA - 2 * MARGEM) / (raio * (2 + folga)));
  // continuidade (transição de seção): a câmera já está fechada no ícone em que a transição anterior parou e só
  // DESLIZA (pan, zoom constante) até o capítulo atual. Sem zoom-out; o layout da capa nunca muda.
  const origem = cena.origem !== undefined && cena.origem !== cena.destaque ? cena.circulos[cena.origem] : null;
  if (origem) {
    const ro = origem.r * Math.min(w, h) * k;
    const bx = ox + origem.cx * w * k;
    const by = oy + origem.cy * h * k + (ro * folga) / 2;
    const z = zoom;
    const t = interpolate(frame, [0, Math.max(2, duracao * 0.8)], [0, 1], {
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });
    const px = bx + (ax - bx) * t;
    const py = by + (ay - by) * t;
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
            transformOrigin: "0 0",
            // ponto (px, py) da capa no centro da tela, com zoom z
            transform: `translate(${LARGURA / 2 - (px - ox) * z - ox}px, ${ALTURA / 2 - (py - oy) * z - oy}px) scale(${z})`,
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
