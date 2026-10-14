import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CabecalhoSecao, Credito, Legenda } from "../componentes/CabecalhoSecao";
import { estiloEntradaImagem, transformMovimento, type EfeitoImagem, type Entrada, type Movimento } from "../efeitos";
import { useCores } from "../tema";
import type { CenaCartao, Midia, Secao } from "../tipos";

const CAIXA = { largura: 1712, altura: 790, topo: 140 };

/** Imagem emoldurada no centro, ajustada à caixa, com entrada e movimento vindos da direção. */
export const ImagemNaCaixa: React.FC<{
  midia: Midia;
  desde: number;
  ate: number;
  entrada?: Entrada<EfeitoImagem>;
  movimento?: Movimento;
}> = ({ midia, desde, ate, entrada, movimento }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = Math.min(CAIXA.largura / midia.w, CAIXA.altura / midia.h);
  const w = midia.w * k;
  const h = midia.h * k;
  const p = interpolate(frame, [desde, ate], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: (1920 - w) / 2,
        top: CAIXA.topo + (CAIXA.altura - h) / 2,
        width: w,
        height: h,
        overflow: "hidden",
        ...estiloEntradaImagem(frame, fps, desde, entrada),
      }}
    >
      <Img
        src={staticFile(midia.arquivo)}
        style={{ width: "100%", height: "100%", transform: transformMovimento(movimento, p) }}
      />
      <Credito texto={midia.credito} direita={12} baixo={8} />
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
  const cores = useCores();
  const inicios = cena.itens.map((it, k) => (k === 0 ? 0 : quadro(it.de)));
  let atual = 0;
  inicios.forEach((q, k) => {
    if (frame >= q) atual = k;
  });
  const item = cena.itens[atual];
  const desde = inicios[atual];
  const ate = atual + 1 < inicios.length ? inicios[atual + 1] : duracao;
  const quandoLegenda = item.legenda_em !== undefined ? Math.max(desde, quadro(item.legenda_em)) : desde;

  return (
    <AbsoluteFill style={{ background: cores.fundo }}>
      <ImagemNaCaixa
        key={atual}
        midia={item.midia}
        desde={desde}
        ate={ate}
        entrada={item.entrada_img}
        movimento={item.movimento}
      />
      <Legenda key={`l${atual}`} texto={item.legenda} desde={quandoLegenda} entrada={item.entrada_legenda} />
      {secao && <CabecalhoSecao secao={secao} />}
    </AbsoluteFill>
  );
};
