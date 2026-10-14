import { AbsoluteFill } from "remotion";
import { EntradaTexto, type EfeitoTexto, type Entrada } from "../efeitos";
import { fonte } from "../estilo";
import { useCores } from "../tema";
import type { Secao } from "../tipos";
import { Icone } from "./Icone";

/** Nome da seção no topo + ícone no canto superior esquerdo (fixos durante a seção). */
export const CabecalhoSecao: React.FC<{ secao: Secao }> = ({ secao }) => {
  const c = useCores();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 10, top: 6 }}>
        <Icone icone={secao.icone} tamanho={252} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 14,
          width: "100%",
          textAlign: "center",
          fontFamily: fonte.rotulo,
          fontWeight: 700,
          fontSize: 96,
          color: c.texto,
          lineHeight: 1.1,
        }}
      >
        {secao.titulo}
      </div>
    </AbsoluteFill>
  );
};

/** Legenda grande embaixo da imagem; o efeito de entrada vem da direção. */
export const Legenda: React.FC<{ texto: string; desde: number; entrada?: Entrada<EfeitoTexto> }> = ({
  texto,
  desde,
  entrada,
}) => {
  const c = useCores();
  return (
    <div style={{ position: "absolute", top: 940, width: "100%", display: "flex", justifyContent: "center" }}>
      <EntradaTexto
        texto={texto}
        desde={desde}
        entrada={entrada}
        style={{ fontFamily: fonte.rotulo, fontWeight: 700, fontSize: 92, color: c.texto, whiteSpace: "nowrap" }}
      />
    </div>
  );
};

/** Crédito do artista (fan art) em letra pequena, sobre a imagem — exigência do canal. */
export const Credito: React.FC<{ texto?: string; direita?: number; baixo?: number }> = ({ texto, direita = 24, baixo = 14 }) =>
  texto ? (
    <div
      style={{
        position: "absolute",
        right: direita,
        bottom: baixo,
        fontFamily: fonte.rotulo,
        fontSize: 24,
        color: "#fff",
        textShadow: "0 0 6px #000, 0 0 2px #000",
        opacity: 0.9,
      }}
    >
      {texto}
    </div>
  ) : null;

/** Texto branco com contorno escuro, para escrever por cima de arte (nomes, rótulos). */
export const sombraTexto = "0 0 18px rgba(0,0,0,0.9), 0 3px 6px rgba(0,0,0,0.9), 0 0 3px #000";
