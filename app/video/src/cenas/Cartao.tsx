import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CabecalhoSecao, Legenda } from "../componentes/CabecalhoSecao";
import { cor } from "../estilo";
import type { CenaCartao, Midia, Secao } from "../tipos";
import { variar } from "../tempo";

const CAIXA = { largura: 1712, altura: 790, topo: 140 };

/** Imagem emoldurada no centro, ajustada à caixa e com zoom lento (direção variável). */
export const ImagemNaCaixa: React.FC<{ midia: Midia; desde: number; ate: number; semente: string }> = ({
  midia,
  desde,
  ate,
  semente,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = Math.min(CAIXA.largura / midia.w, CAIXA.altura / midia.h);
  const w = midia.w * k;
  const h = midia.h * k;
  const entrada = spring({ frame: frame - desde, fps, config: { damping: 14, stiffness: 220 } });
  const zoom = interpolate(frame, [desde, ate], [1, variar(semente, 1.03, 1.07)], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const origem = `${variar(`${semente}x`, 25, 75)}% ${variar(`${semente}y`, 30, 70)}%`;
  return (
    <div
      style={{
        position: "absolute",
        left: (1920 - w) / 2,
        top: CAIXA.topo + (CAIXA.altura - h) / 2,
        width: w,
        height: h,
        overflow: "hidden",
        transform: `scale(${0.94 + 0.06 * entrada})`,
        opacity: Math.min(1, entrada * 1.5),
      }}
    >
      <Img
        src={staticFile(midia.arquivo)}
        style={{ width: "100%", height: "100%", transform: `scale(${zoom})`, transformOrigin: origem }}
      />
    </div>
  );
};

export const Cartao: React.FC<{
  cena: CenaCartao;
  secao?: Secao;
  quadro: (palavra: number) => number; // quadro relativo ao início da cena
  duracao: number;
}> = ({ cena, secao, quadro, duracao }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inicios = cena.itens.map((it, k) => (k === 0 ? 0 : quadro(it.de)));
  let atual = 0;
  inicios.forEach((q, k) => {
    if (frame >= q) atual = k;
  });
  const item = cena.itens[atual];
  const desde = inicios[atual];
  const ate = atual + 1 < inicios.length ? inicios[atual + 1] : duracao;
  const quandoLegenda = item.legenda_em !== undefined ? Math.max(desde, quadro(item.legenda_em)) : desde;
  const popLegenda = spring({ frame: frame - quandoLegenda, fps, config: { damping: 10, stiffness: 260 } });

  return (
    <AbsoluteFill style={{ background: cor.fundo }}>
      <ImagemNaCaixa key={atual} midia={item.midia} desde={desde} ate={ate} semente={`${cena.semente}-${atual}`} />
      {frame >= quandoLegenda && <Legenda texto={item.legenda} escala={0.8 + 0.2 * popLegenda} />}
      {secao && <CabecalhoSecao secao={secao} />}
    </AbsoluteFill>
  );
};
