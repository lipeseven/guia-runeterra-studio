// Equivalente TS de sfx.py (mesma escolha de variação, mesma âncora no pico, mesmos ganhos), sem dependências:
// serve ao Remotion (componente em exemplo/remotion/TrilhaSfx.tsx) e a qualquer script Node/HyperFrames.
//   import { Banco } from "./sfx.ts";  const b = new Banco(catalogoJson);  b.para("impacto", 13.0, 0.8)
// Regras e campos: ver README.md e o cabeçalho de sfx.py. Paridade com o Python conferida por testes.py.

export const CATEGORIAS = [
  "impacto", "riser", "whoosh", "sino", "alerta", "pop", "clique", "tecla",
  // F1 documental (Freesound pela API, 2026-11-14)
  "motor", "pneu", "radio", "cronometro", "grafico", "obturador", "whoosh_grave", "boom", "box", "multidao",
] as const;
export type Categoria = (typeof CATEGORIAS)[number];

export interface ItemCatalogo {
  id: string; categoria: Categoria; arquivo: string; duracao_s: number; pico_s: number;
  lufs_m_max: number; lufs_integrado: number; pico_verdadeiro_dbtp: number; origem: string; licenca: string;
  autor?: string; url?: string; credito_obrigatorio?: boolean; descricao?: string; nota?: string;
  freesound_id?: number; licenca_url?: string;
}
export interface ConfCategoria {
  alvo_lufs_m: number; faixa_lufs_m: [number, number]; dur_max: number; volume_db: number; uso: string;
  ancora?: "inicio";  // ambiente (multidao): pico_s = 0, o som começa na palavra
}
export interface Catalogo { versao: number; categorias: Record<Categoria, ConfCategoria>; itens: ItemCatalogo[] }

export interface Evento {
  id: string; categoria: Categoria; arquivo: string;
  t: number; inicio: number; corte_ini: number; dur: number; ganho_db: number; palavra: string | null;
}
export interface Palavra { t?: string; p?: string; i: number; f: number }
export interface Pedido {
  categoria: Categoria | "capitulo"; t?: number; palavra?: string | number; ocorrencia?: number;
  ponto?: "i" | "f"; intensidade?: number; variacao?: string; dur?: number;
}

export const volume = (e: Evento) => Math.pow(10, e.ganho_db / 20);

export function fnv1a(s: string): number {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(s)) h = Math.imul(h ^ b, 0x01000193) >>> 0;
  return h >>> 0;
}

const r4 = (x: number) => Math.round(x * 1e4) / 1e4;
const r2 = (x: number) => Math.round(x * 1e2) / 1e2;

function norm(s: string): string {
  return s.toLocaleLowerCase("pt-BR").normalize("NFD").replace(/\p{Mn}/gu, "")
    .replace(/[^\p{L}\p{N}_,.]+/gu, "").replace(/^[.,]+|[.,]+$/g, "");
}

export function acharPalavra(palavras: Palavra[], alvo: string | number, ocorrencia = 1): Palavra {
  if (typeof alvo === "number") return palavras[alvo];
  const achadas = palavras.filter((p) => norm(p.t ?? p.p ?? "") === norm(alvo));
  if (achadas.length < ocorrencia) throw new Error(`palavra-âncora não encontrada: ${alvo} (ocorrência ${ocorrencia})`);
  return achadas[ocorrencia - 1];
}

export class Banco {
  readonly itens: Record<string, ItemCatalogo> = {};
  readonly porCat: Record<string, string[]> = {};
  private conta: Record<string, number> = {};
  private recentes: Record<string, string[]> = {};

  readonly catalogo: Catalogo;
  readonly semente: number;

  constructor(catalogo: Catalogo, semente = 0) {
    this.catalogo = catalogo;
    this.semente = semente;
    for (const i of catalogo.itens) {
      this.itens[i.id] = i;
      (this.porCat[i.categoria] ??= []).push(i.id);
    }
    // mesma ordem do Python (sorted por ponto de código)
    for (const k of Object.keys(this.porCat)) this.porCat[k].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  }

  escolher(categoria: Categoria): string {
    const ids = this.porCat[categoria];
    const k = this.conta[categoria] ?? 0;
    this.conta[categoria] = k + 1;
    const h = fnv1a(`${this.semente}:${categoria}:${k}`);
    const rec = (this.recentes[categoria] ??= []);
    const evita = new Set(ids.length > 1 ? rec.slice(-Math.min(2, ids.length - 1)) : []);
    let cand = ids[h % ids.length];
    for (let j = 0; j < ids.length; j++) {
      cand = ids[(h + j) % ids.length];
      if (!evita.has(cand)) break;
    }
    rec.push(cand);
    return cand;
  }

  para(categoria: Categoria, t: number, intensidade = 0.7, variacao?: string, dur?: number, palavra: string | null = null): Evento {
    const c = this.catalogo.categorias[categoria];
    if (!c) throw new Error(`categoria desconhecida: ${categoria}`);
    const id = variacao ?? this.escolher(categoria);
    const it = this.itens[id];
    let inicio = t - it.pico_s;
    const corte = Math.max(0, -inicio);
    inicio = Math.max(0, inicio);
    const d = Math.min(it.duracao_s - corte, c.dur_max, dur ? dur : 1e9);
    const ganho = c.volume_db - 9 * (1 - Math.min(1, Math.max(0, intensidade)));
    return { id, categoria, arquivo: it.arquivo, t: r4(t), inicio: r4(inicio), corte_ini: r4(corte), dur: r4(d), ganho_db: r2(ganho), palavra };
  }

  paraPalavra(categoria: Categoria, palavras: Palavra[], alvo: string | number, intensidade = 0.7, ocorrencia = 1, ponto: "i" | "f" = "i"): Evento {
    const p = acharPalavra(palavras, alvo, ocorrencia);
    return this.para(categoria, p[ponto], intensidade, undefined, undefined, p.t ?? p.p ?? null);
  }

  /** Linhas de crédito (descrição do vídeo) dos sons CC BY usados nos eventos — igual a Banco.creditos do Python. */
  creditos(eventos: Evento[]): string[] {
    const vistos = new Set<string>();
    const out: string[] = [];
    for (const e of eventos) {
      const it = this.itens[e.id];
      if (it.credito_obrigatorio && it.url && !vistos.has(it.url)) {
        vistos.add(it.url);
        out.push(`"${it.descricao}" de ${it.autor} (${it.url}), ${it.licenca}`);
      }
    }
    return out;
  }

  capitulo(t: number, intensidade = 0.9): Evento[] {
    return [this.para("riser", t, intensidade), this.para("impacto", t, intensidade)];
  }

  dePedidos(pedidos: Pedido[], palavras: Palavra[] = []): Evento[] {
    const out: Evento[] = [];
    for (const p of pedidos) {
      const t = p.t !== undefined ? p.t : acharPalavra(palavras, p.palavra!, p.ocorrencia ?? 1)[p.ponto ?? "i"];
      if (p.categoria === "capitulo") out.push(...this.capitulo(t, p.intensidade ?? 0.9));
      else out.push(this.para(p.categoria, t, p.intensidade ?? 0.7, p.variacao, p.dur,
        p.palavra !== undefined ? String(p.palavra) : null));
    }
    return out;
  }
}
