// Formato da direção gerada pelo sistema (ver tools/prototipo/preparar.py).
// Cenas são ancoradas em ÍNDICES DE PALAVRAS: trocar a narração só muda os tempos das palavras.
import type { EfeitoImagem, EfeitoTexto, Entrada, Movimento } from "./efeitos";

export type Palavra = { t: string; i: number; f: number };

export type Midia = { arquivo: string; w: number; h: number };

export type Icone = {
  nome: string;
  midia: Midia;
  foco: [number, number]; // centro do recorte, em fração da imagem
  diametro: number; // diâmetro do recorte, em fração do menor lado
};

/** Círculo detectado na capa (tools/capa.py): cx/cy em fração da imagem, r em fração do menor lado. */
export type CirculoCapa = { nome: string; cx: number; cy: number; r: number };

type Base = { de: number; ate: number; semente?: number };

export type CenaCapa = Base & {
  tipo: "capa";
  midia: Midia;
  circulos: CirculoCapa[];
  destaque: number;
  zoom: number;
};
export type ItemCartao = {
  de: number;
  midia: Midia;
  legenda: string;
  legenda_em?: number;
  entrada_img?: Entrada<EfeitoImagem>;
  entrada_legenda?: Entrada<EfeitoTexto>;
  movimento?: Movimento;
};
export type CenaCartao = Base & { tipo: "cartao"; itens: ItemCartao[] };
export type CenaTelaCheia = Base & {
  tipo: "telacheia";
  midia: Midia;
  foco: [number, number];
  movimento: Movimento;
  entrada_img?: Entrada<EfeitoImagem>;
};
export type CenaRecorte = Base & {
  tipo: "recorte";
  midia: Midia;
  legenda: string;
  legenda_em: number;
  entrada_img?: Entrada<EfeitoImagem>;
  entrada_legenda?: Entrada<EfeitoTexto>;
};
export type CenaDialogo = Base & {
  tipo: "dialogo";
  esquerda: Icone;
  direita: Icone;
  destaques: number[];
};

export type Cena = CenaCapa | CenaCartao | CenaTelaCheia | CenaRecorte | CenaDialogo;

export type Secao = { titulo: string; icone: Icone };

export type Trecho = {
  audio: string;
  palavras: Palavra[];
  secao?: Secao;
  cenas: Cena[];
};

/** Ícone redondo recortado de dentro de um círculo da capa (sem pegar a borda preta original). */
export const iconeDaCapa = (capa: Midia, c: CirculoCapa): Icone => ({
  nome: c.nome,
  midia: capa,
  foco: [c.cx, c.cy],
  diametro: 2 * c.r * 0.93,
});
