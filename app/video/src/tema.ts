// Modo visual do vídeo inteiro (guia de estilo §10.1): "claro" = cartões brancos (padrão do canal),
// "escuro" = visual cinematográfico. O diretor escolhe um modo por vídeo, pelo tema.
import { createContext, useContext } from "react";
import { cor } from "./estilo";

export type Tema = "claro" | "escuro";

export const TemaCtx = createContext<Tema>("claro");

export const CORES: Record<Tema, { fundo: string; texto: string; destaque: string; suave: string }> = {
  claro: { fundo: cor.fundo, texto: cor.texto, destaque: cor.destaque, suave: "#555" },
  escuro: { fundo: "#0e0e12", texto: "#f3f3f3", destaque: "#ff4a4a", suave: "#aaa" },
};

export const useCores = () => CORES[useContext(TemaCtx)];
