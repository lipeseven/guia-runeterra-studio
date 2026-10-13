// Formato da direção gerada pelo sistema (ver tools/prototipo/preparar.py).
// Cenas são ancoradas em ÍNDICES DE PALAVRAS: trocar a narração só muda os tempos das palavras.

export type Palavra = { t: string; i: number; f: number };

export type Midia = { arquivo: string; w: number; h: number };

export type Icone = {
  nome: string;
  midia: Midia;
  foco: [number, number]; // centro do recorte, em fração da imagem
  diametro: number; // diâmetro do recorte, em fração do menor lado
};

type Base = { de: number; ate: number; semente?: number };

export type CenaGrade = Base & { tipo: "grade"; icones: Icone[]; destaque: number };
export type ItemCartao = { de: number; midia: Midia; legenda: string; legenda_em?: number };
export type CenaCartao = Base & { tipo: "cartao"; itens: ItemCartao[] };
export type CenaTelaCheia = Base & {
  tipo: "telacheia";
  midia: Midia;
  zoom: [number, number];
  foco: [number, number];
};
export type CenaRecorte = Base & { tipo: "recorte"; midia: Midia; legenda: string; legenda_em: number };
export type CenaDialogo = Base & {
  tipo: "dialogo";
  esquerda: Icone;
  direita: Icone;
  destaques: number[];
};

export type Cena = CenaGrade | CenaCartao | CenaTelaCheia | CenaRecorte | CenaDialogo;

export type Secao = { titulo: string; icone: Icone };

export type Trecho = {
  audio: string;
  palavras: Palavra[];
  secao?: Secao;
  cenas: Cena[];
};
