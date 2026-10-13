import { AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ImagemNaCaixa } from "./Cartao";
import { EFEITOS_IMAGEM, EFEITOS_TEXTO, EntradaTexto, MOVIMENTOS, transformMovimento } from "../efeitos";
import { cor, fonte } from "../estilo";
import type { Midia } from "../tipos";

export const POR_EFEITO = 84; // 1,4 s a 60 fps

const Rotulo: React.FC<{ texto: string }> = ({ texto }) => (
  <div
    style={{
      position: "absolute",
      left: 24,
      bottom: 20,
      padding: "6px 16px",
      background: "#111",
      color: "#ffd400",
      fontFamily: "Arial",
      fontWeight: 700,
      fontSize: 34,
      borderRadius: 8,
    }}
  >
    {texto}
  </div>
);

/** Catálogo visual de todos os efeitos, um por vez, com o nome — para o Felipe aprovar ou vetar. */
export const Mostruario: React.FC<{ imagem: Midia; arte: Midia }> = ({ imagem, arte }) => {
  const blocos: { nome: string; render: () => React.ReactNode }[] = [
    ...EFEITOS_TEXTO.map((e) => ({
      nome: `texto: ${e}`,
      render: () => (
        <AbsoluteFill style={{ background: cor.fundo, justifyContent: "center", alignItems: "center" }}>
          <EntradaTexto
            texto="manifestação espiritual"
            desde={10}
            entrada={{ efeito: e, quadros: e === "maquina" || e === "palavras" ? 26 : 14 }}
            style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: 110, color: cor.texto }}
          />
        </AbsoluteFill>
      ),
    })),
    ...EFEITOS_IMAGEM.map((e) => ({
      nome: `imagem: ${e}`,
      render: () => (
        <AbsoluteFill style={{ background: cor.fundo }}>
          <ImagemNaCaixa midia={imagem} desde={10} ate={POR_EFEITO} entrada={{ efeito: e, quadros: 14 }} />
        </AbsoluteFill>
      ),
    })),
    ...MOVIMENTOS.map((m) => ({ nome: `movimento: ${m}`, render: () => <Movimento arte={arte} tipo={m} /> })),
  ];
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {blocos.map((b, k) => (
        <Sequence key={b.nome} from={k * POR_EFEITO} durationInFrames={POR_EFEITO}>
          {b.render()}
          <Rotulo texto={b.nome} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const totalMostruario = EFEITOS_TEXTO.length + EFEITOS_IMAGEM.length + MOVIMENTOS.length;

const Movimento: React.FC<{ arte: Midia; tipo: (typeof MOVIMENTOS)[number] }> = ({ arte, tipo }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, POR_EFEITO], [0, 1]);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <Img
        src={staticFile(arte.arquivo)}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: transformMovimento({ tipo, intensidade: 0.08 }, p) }}
      />
    </AbsoluteFill>
  );
};
