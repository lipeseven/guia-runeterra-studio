// Tipos do kit/gps (gps.js). Coordenadas: as da pista da volta (three.js, Y para cima, metros): o .glb do circuito
// carregado sem transformação (modo "glb") ou a pista plana de pista/<circuito>_plana.json (modo "plana", y = 0).
export type Vec3 = [number, number, number];

export interface VoltaJSON {
  versao: number; fonte: string; sessao: number; sessao_nome: string; piloto: number; sigla: string; nome: string;
  equipe: string; cor: string; cor2: string; volta: number; duracao: number; setores: (number | null)[]; pista: string;
  /** fase 2b (ausentes nas voltas antigas = Interlagos, glb) */
  circuito?: string; modo_pista?: "glb" | "plana"; ano?: number;
  relogio: { t0: number; dt: number; s: number[]; s_ini: number; s_fim: number };
  caminho: { ds: number; x: number[]; y: number[]; z: number[]; yaw: number[]; pitch: number[]; roll: number[] };
  gps: { t: number[]; x: number[]; z: number[] };
  qualidade: Record<string, unknown>;
}

export interface Pose {
  t: number; s: number; x: number; y: number; z: number;
  /** rotação em Y (rad) para modelo com frente em +Z local; use ordem "YXZ": rotation.set(-pitch, yaw, roll) */
  yaw: number; pitch: number; roll: number;
  frente: Vec3;
  /** m/s */
  vel: number;
  /** false quando t está fora do trecho com dados (carro parado no extremo, nunca some) */
  comDados: boolean;
}

export interface Rastro { pontos: Vec3[]; cor: string; s0: number; s1: number }

export interface Amostrador {
  info: {
    sessao: number; sessaoNome: string; piloto: number; sigla: string; nome: string; equipe: string;
    cor: string; cor2: string; volta: number; duracao: number; setores: (number | null)[]; fonte: string; pista: string;
    circuito: string; modoPista: "glb" | "plana"; ano?: number;
  };
  duracao: number;
  /** primeiro e último tempo com dados (s, relativo ao início da volta; tIni < 0 e tFim > duracao: margens) */
  tIni: number; tFim: number;
  s(t: number): number;
  vel(t: number): number;
  pos(t: number): Vec3;
  posEmS(s: number): Vec3;
  pose(t: number): Pose;
  rastro(t0: number, t1: number, opcoes?: { passo?: number; elev?: number }): Rastro;
}

export function criarAmostrador(volta: VoltaJSON): Amostrador;
export function carregarVolta(
  sessao: number, piloto: number, volta: number,
  opcoes?: { base?: string; fetch?: typeof fetch; ler?: (nome: string) => string | Promise<string> },
): Promise<Amostrador>;
export function relogioComparacao(opcoes?: { fator?: number; inicio?: number }): (tCena: number) => number;
export function faixa(pontos: Vec3[], opcoes?: { largura?: number; afinar?: boolean }):
  { posicoes: Float32Array; alfa: Float32Array; indices: Uint32Array };
export function corNumero(hex: string): number;
export function cameraSeguindo(
  amostradores: Amostrador | Amostrador[], t: number,
  opcoes?: { atras?: number; altura?: number; adiante?: number; janela?: number; lado?: number },
): { pos: Vec3; alvo: Vec3 };

/** pista/<circuito>_plana.json (py/pista.py, modo sem modelo 3D); desenhada por criarPistaPlana (gps_three.js) */
export interface PistaPlanaJSON {
  circuito: string; modo: "plana"; largura_m: number; zebra_m: number; escape_m: number; comprimento_m: number;
  centro: { ds: number; fechada: boolean; x: number[]; z: number[] };
}
