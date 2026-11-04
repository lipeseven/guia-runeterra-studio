// Vídeo vertical montado pelo diretor do painel: os planos chegam por props (direcao/vertical.json do vídeo).
// Cada plano traz o CÓDIGO da cena, escrito pelo diretor para este vídeo com a API abaixo (F1/docs/api_cenas.md), ou o nome
// de uma cena pronta (	ipo, F1/docs/catalogo_vertical.md). O código roda aqui (new Function): nada dele fica no projeto.
import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { FONTE, Legenda, Placa, entra, suave, type Palavra } from "./kit";
import {
  Chips, FundoLegenda, Z_POLE, Z_PORTICO, bandeira, camCircuito, camera, confete, enquadrar, drawRastro, fumaca, grade, gridX, gridZ, halo,
  luzGantry, luzesDesfocadas, montar, num, poe, poeCinza, poePneu, preparar, seed, solta, type Mundo,
} from "./modelos/mundo";
import { PINTURAS, carro, trocarComposto } from "./modelos/Carro3D";
import { cortar, explodir, isolar, nomesDasPecas, raioX, restaurar } from "./modelos/desmonte";
import { ligar } from "./modelos/ligacoes";
import { aura, brilho, criarCurva, destacar, estercar, naCurva } from "./modelos/efeitos3d";
import { Grafico, Titulo, type GraficoV, type TituloV } from "./Infograficos";
import { apertar, criarVolante, embaralhar, girar, luzesDeTroca, puxar, telaDoVolante } from "./modelos/volante";
import {
  bracos, criarAlfinete, criarEscada, criarKart, criarMapa, criarPiloto, criarPodio, degrau, esconderExtras, numeroNoCarro, obj, pontoNoMapa, rotulo,
  topoDoPodio,
} from "./modelos/extras";

type PlacaV = { texto: string; unidade?: string; i?: number; cor?: string; pos?: string };
export type PlanoV = {
  id: string; i: number; tipo?: string; set?: string; codigo?: string; clima?: string; equipe?: number; n?: number; cor?: string; cores?: string[]; acao?: string;
  modo?: string; angulo?: string; de?: number; ate?: number; valores?: number[]; sai?: number; marcas?: Record<string, number>;
  titulo?: TituloV; grafico?: GraficoV; foco?: boolean; // gráficos informativos (Infograficos.tsx)
  placas?: PlacaV[]; contador?: { de: number; ate: number; unidade?: string; casas?: number; formato?: string; i0?: number; i1?: number; cor_final?: string };
  chips?: { itens: string[]; ativo?: number; i?: number }; selo?: { texto: string; i?: number }; riscado?: { texto: string; i: number };
  medidor?: { texto: string; sub?: string; i?: number }; gota?: { texto: string }; chuva?: boolean;
};
export type PropsVertical = { palavras: Palavra[]; planos: PlanoV[]; audio: string; chaves?: string[] };

export type CV = {
  w: Mundo; p: PlanoV; t: number; s: number; k: number; fim: number; ini: number; m: (nome: string, frac?: number) => number;
  tipo: (nome: string, extra?: Partial<PlanoV>) => void;
};

const COR: Record<string, string> = { branco: "#ffffff", amarelo: "#ffd400", vermelho: "#ff5a4a", verde: "#3bd47a", azul: "#7fc4ff", laranja: "#ffb066", ouro: "#ffd77a" };
const PNEU: Record<string, string> = { macio: "#e6241f", medio: "#ffd21f", duro: "#f2f2f2", intermediario: "#23b458", chuva: "#2b7be8" };
const BANDEIRA: Record<string, number> = { verde: 0, amarela: 1, azul: 2, vermelha: 3, preta: 4, quadriculada: 5 };
const cor = (x?: string, padrao = "#ffffff") => (x && (COR[x] ?? (x.startsWith("#") ? x : undefined))) ?? padrao;
const eq = (p: PlanoV) => Math.max(0, Math.min(10, p.equipe ?? 0)) * 2;

type Tipo = { set: string; clima: string; cena: (c: CV) => void };

// Cenas do piloto, generalizadas. `m(nome)` = tempo da palavra marcada pelo diretor (ou uma fração do plano).
const TIPOS: Record<string, Tipo> = {
  voo_grid: { set: "pista", clima: "tarde", cena: ({ w, s, p }) => {
    const n = p.n ?? 22;
    grade(w, n);
    const v = 1 - Math.pow(1 - Math.min(1, s / 2.1), 3);
    const z = gridZ(n - 1) + 30 + (Z_POLE + 12 - gridZ(n - 1) - 30) * v;
    camera(w, [0.2 + Math.sin(s * 1.1) * 0.4, 2.2 + v * 4.6, z + 9 + s * 0.4], [0, 0.5, z - 10], 48, Math.sin(s * 1.6) * 0.02 * (1 - v));
  } },
  grid_topo: { set: "pista", clima: "tarde", cena: ({ w, s, t, p, m }) => {
    const n = p.n ?? 11;
    const a = m("aparece", 0);
    const vis = Math.min(n, Math.floor(1 + Math.max(0, t - a) * n / 0.9));
    for (let k = 0; k < vis; k++) poe(w, (k * 2) % 22, 0, Z_POLE + k * 7.2);
    camera(w, [0, 92 - s * 3, Z_POLE + 36], [0, 0, Z_POLE + 36], 38, 0, true);
  } },
  dupla: { set: "pista", clima: "tarde", cena: ({ w, s, p }) => {
    poe(w, eq(p), -1.9, Z_POLE);
    poe(w, eq(p) + 1, 1.9, Z_POLE);
    const a = -0.75 + s * 0.28;
    camera(w, [Math.sin(a) * 10, 1.25 + s * 0.2, Z_POLE - 11], [0, 0.65, Z_POLE], 34);
  } },
  grid_recua: { set: "pista", clima: "tarde", cena: ({ w, k, p }) => {
    grade(w, p.n ?? 22);
    const su = suave(k, 0, 1);
    camera(w, [2 - su * 2, 5 + su * 62, Z_POLE - 12 + su * 58], [0, 0, Z_POLE + 46], 42);
  } },
  destaque: { set: "pista", clima: "tarde", cena: ({ w, s, t, p, m }) => {
    poe(w, eq(p), 0, Z_POLE);
    halo(w, 0, 0, Z_POLE, cor(p.cor, "#ffd77a"), 0.55 * entra(t, m("destaque", 0.2), 0.5));
    const a = 2.5 + s * 0.3;
    camera(w, [Math.sin(a) * 8, 1.1 + s * 0.14, Z_POLE + Math.cos(a) * 8], [0, 0.6, Z_POLE], 32);
  } },
  circuito: { set: "circuito", clima: "manha", cena: ({ w, s, k, p }) => {
    const de = p.de ?? 0;
    const ate = p.ate ?? 0;
    drawRastro(w, de + (ate - de) * suave(k, 0.15, 0.95));
    w.marcador.visible = ate > 0;
    camCircuito(w, s, p.angulo === "girado" ? 0.9 : 0.05, 840);
  } },
  perseguicao: { set: "pista", clima: "tarde", cena: ({ w, s, p }) => {
    const z = -80 - 80 * s;
    poe(w, eq(p), 0, z);
    const a = p.angulo ?? "lateral";
    if (a === "traseira") camera(w, [0.8, 1.45, z + 8 - s * 0.6], [0, 1.1, z - 3], 32);
    else if (a === "frontal") camera(w, [1.6 - s * 0.5, 1 + s * 0.15, z - 7 + s * 0.8], [0, 0.7, z + 1], 38, 0.02);
    else if (a === "rasante") camera(w, [-5.4 + s * 0.9, 1 + s * 0.3, z + 8.5], [0, 0.6, z - 2], 46);
    else if (a === "topo") camera(w, [0, 30, z], [0, 0, z], 30, 0, true);
    else camera(w, [7.2, 0.8, z - 2 - s * 2.4], [0, 0.6, z], 38);
  } },
  pelotao: { set: "pista", clima: "sol", cena: ({ w, s, p }) => {
    const n = p.n ?? 22;
    const z = Z_POLE - 86 * s - 1.5 * s * s;
    for (let k = 0; k < n; k++) poe(w, k, gridX(k), z + k * 6.2);
    camera(w, [7, 2 + s * 1.8, z - 18 + s * 4], [0, 0.5, z + 12], 42);
  } },
  eliminacao: { set: "pista", clima: "noite", cena: ({ w, s, t, p, m }) => {
    const n = p.n ?? 22;
    const sai = p.sai ?? 6;
    const a = m("sai", 0.3);
    const fora = suave(t, a, m("saiu", 0.8) + 0.1);
    for (let k = 0; k < n - sai; k++) poe(w, k, gridX(k), gridZ(k));
    for (let k = n - sai; k < n; k++) {
      if (t < a) poe(w, k, gridX(k), gridZ(k));
      else {
        const x = gridX(k) + Math.sign(gridX(k)) * fora * 30;
        poeCinza(w, k, x, gridZ(k));
        halo(w, k, x, gridZ(k), "#ff2a20", 0.95);
      }
    }
    const meio = gridZ(Math.floor(n / 2));
    camera(w, [0, 30 + n * 2 - s * 2, meio + 22 + n], [0, 0, meio], 40);
  } },
  fila: { set: "pista", clima: "noite", cena: ({ w, s, p }) => {
    const n = p.n ?? 10;
    const z = -130 - 74 * s;
    for (let k = 0; k < n; k++) poe(w, k, (k % 2 ? -1 : 1) * 2, z + k * 8);
    camera(w, [5, 1.4 + s * 1.4, z + n * 8 + 6 - s * 12], [0, 0.6, z + n * 2], 34);
  } },
  pole: { set: "pista", clima: "noite", cena: ({ w, s, t, m }) => {
    grade(w, 4);
    halo(w, 0, gridX(0), Z_POLE, "#ffd77a", 0.75 * entra(t, m("destaque", 0.3), 0.4) + 0.2);
    const a = 0.7 + s * 0.22;
    camera(w, [gridX(0) + Math.sin(a) * 9, 3.2 - s * 0.4, Z_POLE - Math.cos(a) * 9], [gridX(0), 0.6, Z_POLE], 30);
  } },
  luzes: { set: "pista", clima: "brasa", cena: ({ w, s, t, p, m }) => {
    grade(w, 12);
    w.portico.visible = true;
    const a = p.marcas?.acende !== undefined ? m("acende") : -1;
    const b = p.marcas?.acesas !== undefined ? m("acesas") : a + 1.5;
    const off = p.marcas?.apaga !== undefined ? m("apaga") : 1e9;
    for (let n = 0; n < 5; n++) luzGantry(w, n, t < off && t >= a + (b - a) * (n / 5));
    if (p.angulo === "perto") camera(w, [0.1, 5.8, Z_PORTICO + 27 - Math.min(s, 2) * 3], [0, 6.2, Z_PORTICO], 30);
    else camera(w, [Math.sin(s) * 0.4, 1 + s * 0.2, Z_POLE + 12 - s * 0.7], [0, 5.4, Z_PORTICO], 40);
  } },
  largada: { set: "pista", clima: "tarde", cena: ({ w, s }) => {
    const pulo = (k: number) => Math.max(0, s - k * 0.012);
    for (let k = 0; k < 22; k++) poe(w, k, gridX(k) * (1 - Math.min(1, s * 0.15)), gridZ(k) - 16 * pulo(k) * pulo(k));
    w.portico.visible = true;
    for (let n = 0; n < 5; n++) luzGantry(w, n, false);
    const z = Z_POLE - 16 * s * s;
    camera(w, [4.2 + Math.sin(s * 40) * 0.03, 0.75 + Math.sin(s * 55) * 0.02, z + 12 + s * 3], [0, 0.4, z - 3], 54, Math.sin(s * 3) * 0.015);
  } },
  pneus: { set: "estudio", clima: "vazio", cena: ({ w, s, t, p, m }) => {
    const cores = (p.cores?.length ? p.cores : ["macio", "medio", "duro"]).slice(0, 3).map((x) => PNEU[x] ?? PNEU.macio);
    w.chao.color.set(p.chuva ? "#28303d" : "#0e1528");
    if (!p.chuva) luzesDesfocadas(w, t);
    if (cores.length === 1) {
      poePneu(w, 0, 0, 1.03, 0, cores[0], s * 4, Math.PI / 2);
      if (p.marcas?.gasta !== undefined && t >= m("gasta")) {
        const g = m("gasta");
        for (let i = 26; i < 110; i++) {
          const u = ((t - g) * (0.9 + seed(i) * 0.7) + seed(i + 7)) % 1;
          const a = seed(i + 2) * 3.1;
          const sp = w.parts[i];
          sp.visible = true;
          sp.position.set(Math.cos(a) * (1 + u * 3.4), 1.03 + Math.sin(a) * (1 + u * 2.4) - u * u * 1.4, 0.4 + seed(i + 5) * 0.6);
          sp.scale.setScalar(0.13 + seed(i + 3) * 0.13);
          (sp.material as THREE.SpriteMaterial).color.set("#34302f");
          (sp.material as THREE.SpriteMaterial).opacity = 1 - u;
          (sp.material as THREE.SpriteMaterial).blending = THREE.NormalBlending;
        }
      }
      const a = -0.5 + s * 0.17;
      camera(w, [Math.sin(a) * 6.6, 2 + Math.sin(s) * 0.2, Math.cos(a) * 6.6], [0, 1.03, 0], 30);
      return;
    }
    const q = (d: number) => {
      if (p.modo !== "queda") return 1.03;
      const u = Math.max(0, s - d);
      return Math.max(1.03, 16 - 42 * u * u) + (u > 0.6 ? Math.abs(Math.sin((u - 0.6) * 9)) * 0.55 * Math.exp(-(u - 0.6) * 4) : 0);
    };
    const passo = cores.length === 2 ? 2.5 : 2.45;
    cores.forEach((c, n) => poePneu(w, n, (n - (cores.length - 1) / 2) * passo, q(n * 0.18), n === 1 && cores.length === 3 ? 0.6 : 0, c, s * 2.5, Math.PI / 2));
    camera(w, [s * 0.4, 2, (cores.length === 3 ? 25 : 17) - s * 0.7], [0, 1.35, 0], 30);
  } },
  pit: { set: "pit", clima: "sol", cena: ({ w, s, k, p, fim }) => {
    const e = eq(p);
    const modo = p.modo ?? "chegada";
    if (modo === "troca") {
      poe(w, e, 0, 0);
      const sai = suave(s, 0.25, 0.6) * (1 - suave(s, 0.9, 1.25));
      [[-1, -1.95], [1, -1.95], [-1, 2.1], [1, 2.1]].forEach(([x, z], n) => {
        w.roda[n].visible = sai > 0.03;
        w.roda[n].position.set(x * (2 + sai * 1.6), 0.56, z);
      });
      w.equipe.forEach((mm, n) => {
        mm.visible = true;
        mm.position.set((n % 2 ? -1 : 1) * 2.3, 0.85, (n < 4 ? -2.1 : 2.1) + (n % 4 > 1 ? 0.9 : -0.6));
      });
      camera(w, [0.5, 19 - k * 5, 0.5], [0, 0, 0], 32, 0, true);
    } else if (modo === "passagem") {
      const z = 120 - 68 * s;
      poe(w, e, 0, z);
      camera(w, [-8, 5.5, z - 6 - s * 3], [0, 0.7, z - 1], 42);
    } else if (modo === "parada") {
      const u = fim > 0 ? s / fim : 0;
      const zz = u < 0.3 ? 40 * Math.pow(1 - u / 0.3, 2) : u < 0.8 ? 0 : -60 * Math.pow((u - 0.8) / 0.2, 2);
      poe(w, e, 0, zz);
      camera(w, [7, 8 - u * 2, zz + 12], [0, 0.4, zz - 1], 38);
    } else {
      const ch = Math.min(1, s / Math.max(0.2, fim * 0.8));
      const z = -130 * Math.pow(1 - ch, 2.2);
      poe(w, e, 0, z);
      w.equipe.forEach((mm, n) => {
        mm.visible = true;
        mm.position.set((n % 2 ? -1 : 1) * (2.1 + (n % 4 > 1 ? 0.8 : 0)), 0.85, (n < 4 ? -2.1 : 2.1) + (n % 4 > 1 ? 0.8 : 0));
      });
      camera(w, [-6 + s, 11, z + 14 - s], [0, 0.6, z - 1], 40);
    }
  } },
  barras: { set: "estudio", clima: "vazio", cena: ({ w, t, p, m, ini, fim }) => {
    w.chao.color.set("#10141f");
    const vals = (p.valores?.length ? p.valores : [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]).slice(0, 10);
    const maior = Math.max(...vals, 1);
    w.barras.forEach((bar, n) => {
      if (n >= vals.length) return;
      const quando = p.marcas?.[`b${n}`] !== undefined ? m(`b${n}`) : ini + 0.2 + (fim * 0.75 * n) / vals.length;
      const v = (vals[n] / maior) * 7.5 * entra(t, quando, 0.45);
      const x = n * 3.05;
      bar.m.visible = v > 0.01;
      bar.m.scale.y = Math.max(0.01, v);
      bar.m.position.set(x, v / 2, 0);
      bar.rotulo.visible = v > 0.05;
      bar.rotulo.position.set(x, v + 1.1, 0);
      (bar.rotulo.material as THREE.SpriteMaterial).opacity = entra(t, quando, 0.3);
    });
    const f = suave(t, ini + fim * 0.3, ini + fim);
    camera(w, [-12 - f, 8 + f * 6, 21 + f], [3.5 + f * 8, 3.2 - f, 0], 38);
  } },
  trofeu: { set: "estudio", clima: "vazio", cena: ({ w, s, t, p, m }) => {
    w.chao.color.set("#14110b");
    w.trofeu.visible = true;
    w.trofeu.position.set(0, 0, 0);
    w.trofeu.rotation.y = s * 0.8;
    if (p.marcas?.confete !== undefined && t >= m("confete")) confete(w, t, m("confete"), 0, 9);
    camera(w, [Math.sin(s * 0.3) * 5, 1.1 + s * 0.28, 6.6 - s * 0.4], [0, 1.9, 0], 34);
  } },
  bandeiras: { set: "pista", clima: "tarde", cena: ({ w, s, t, p }) => {
    const lista = (p.cores?.length ? p.cores : Object.keys(BANDEIRA)).map((c) => BANDEIRA[c] ?? 0);
    lista.forEach((b, n) => bandeira(w, b, -8.5, -400 - n * 5, -0.5, t, 1.15));
    camera(w, [1 - s * 0.5, 2.4, -386 - s * 2], [-8.5, 3.3, -412], 38);
  } },
  bandeira: { set: "pista", clima: "tarde", cena: ({ w, s, t, k, p, m }) => {
    const b = BANDEIRA[p.cor ?? "verde"] ?? 0;
    const acao = p.acao ?? "passam";
    if (acao === "batida") {
      w.amarelo.opacity = b === 1 ? 0.95 : 0;
      bandeira(w, b, -8.5, -700, -0.6, t, 1.25);
      w.batido.visible = true;
      w.batido.position.set(9.4, 0, -722);
      w.batido.rotation.set(0, 0.95, 0.05);
      fumaca(w, t, 9.4, -722);
      for (let n = 0; n < 5; n++) poe(w, n * 4, 2 * (n % 2 ? -1 : 1), -640 - 26 * s + n * 12);
      camera(w, [-14 + s * 0.3, 2.4, -692 - s * 0.3], [-6, 3.3, -702], 38);
    } else if (acao === "ultrapassagem") {
      const lento = -860 - 38 * s;
      poe(w, 14, -suave(s, 1.1, 2) * 2.6, lento);
      poe(w, 2, 1.7, -815 - 72 * s);
      if (s < 1) {
        bandeira(w, b, -7.6, lento - 6, -0.35, t, 1.2);
        camera(w, [-11.8, 2.6, lento + 5], [-6.4, 3.5, lento - 6], 38);
      } else camera(w, [2.2, 36, lento - 11], [-1, 0, lento - 12], 34, 0, true);
    } else if (acao === "param") {
      bandeira(w, b, -8.3, -1000, 0.9, t, 1.4);
      const pa = suave(k, 0, 0.9);
      for (let n = 0; n < 8; n++) poe(w, n * 2, n % 2 ? -2 : 2, -1000 + 60 * (1 - pa) + n * 7.4 + 14);
      camera(w, [-14 + s * 0.4, 2.4, -1009 + s * 0.8], [-5.6, 4.1, -994], 40);
    } else if (acao === "desclassificado") {
      bandeira(w, b, -3.2, -1104, 0.3, t, 1.1);
      const sai = suave(k, 0.2, 1);
      poeCinza(w, 9, 1 - sai * 3.4, -1089 - sai * 7);
      halo(w, 0, 1 - sai * 3.4, -1089 - sai * 7, "#ff2a20", 0.75);
      camera(w, [4.2 - s * 0.6, 2.6, -1081], [-1.4, 2.6, -1100], 42);
    } else if (acao === "chegada") {
      bandeira(w, b, -8.6, -1300, 1.2, t, 1.6);
      w.linhaChegada.position.z = -1305;
      const mm = m("chegada", 0.6);
      const z = t < mm ? -1190 - (t - (mm - 3)) * 28 : -1305 - (t - mm) * 62;
      poe(w, eq(p), 0, z);
      if (t >= mm) confete(w, t, mm, 0, 14);
      const a = 1.2 - s * 0.05;
      camera(w, [-9.2 - Math.sin(a) * 8.5, 2.6, -1300 + Math.cos(a) * 8.5], [-6.3, 4.6, -1300], 40);
    } else {
      bandeira(w, b, -8.5, -500, 1.2, t, 1.25);
      for (let n = 0; n < 7; n++) poe(w, n * 3, n % 2 ? -2 : 2, -390 - 92 * s + n * 16);
      const a = 1.2 + s * 0.16;
      camera(w, [-8.5 - Math.sin(a) * 6.5, 2.4, -500 + Math.cos(a) * 6.5], [-6.6, 3.7, -500], 40);
    }
  } },
  batida: { set: "pista", clima: "tarde", cena: ({ w, s, t }) => {
    w.batido.visible = true;
    w.batido.position.set(9.4, 0, -300);
    w.batido.rotation.set(0, 0.95, 0.05);
    fumaca(w, t, 9.4, -300);
    const tr = Math.sin(t * 61) * 0.05 + Math.sin(t * 37) * 0.04;
    camera(w, [2.5 + s * 0.7 + tr, 1.7 + tr, -284 - s * 2], [9.4, 1.2, -300], 38, Math.sin(t * 43) * 0.012);
  } },
  safety_car: { set: "pista", clima: "tarde", cena: ({ w, s, t, k, p }) => {
    const lidera = p.modo === "lidera";
    const z = -300 - (lidera ? 32 : 24) * s;
    w.sc.visible = true;
    w.sc.position.set(0, 0, z);
    const pisca = Math.sin(t * 26) > 0;
    w.luzesSc[0].emissiveIntensity = pisca ? 3.5 : 0.2;
    w.luzesSc[1].emissiveIntensity = pisca ? 0.2 : 3.5;
    if (lidera) {
      for (let n = 0; n < 10; n++) poe(w, n * 2, n % 2 ? -0.9 : 0.9, z + 14 + n * 7.4);
      camera(w, [4 - k * 3, 9 + k * 34, z + 56 + k * 18], [0, 0, z + 30], 42);
    } else camera(w, [3.2 - s * 1.1, 0.55 + s * 0.18, z - 12 + s * 1.3], [0.25, 0.8, z + 0.3], 40, 0.03 - s * 0.015);
  } },
  espacados: { set: "pista", clima: "chumbo", cena: ({ w, s, k }) => {
    const v = 72 - 40 * suave(k, 0, 0.35);
    const z = -500 - v * s;
    [0, 30, 66, 96].forEach((g, n) => poe(w, n * 4 + 2, n % 2 ? -1.1 : 1.1, z + g));
    camera(w, [0, 92, z + 46], [0, 0, z + 46], 38, 0, true);
  } },
  aproxima: { set: "pista", clima: "tarde", cena: ({ w, s, k, p }) => {
    const z = -200 - 80 * s;
    poe(w, 14, 0, z);
    poe(w, eq(p), 0, z + 28 - 12 * suave(k, 0.05, 0.75));
    camera(w, [-1.4, 58, z + 11], [0, 0, z + 11], 28, 0, true);
  } },
  ultrapassagem: { set: "pista", clima: "noite", cena: ({ w, s, t, p, m }) => {
    const b = m("boost", 0.3);
    const ant = Math.max(0, t - b);
    const zF = -300 - 76 * s;
    const z = zF - 3.5 * ant * ant;
    poe(w, 14, -1.9, zF);
    poe(w, eq(p), 1.9, z + 11);
    solta(w, 80, (i) => {
      const u = (t * 2.4 + seed(i) * 3) % 1;
      return { p: [1.9 + (seed(i + 1) - 0.5) * 1.1, 0.25 + seed(i + 2) * 0.9, z + 14.5 + u * 22], e: 0.26 + (1 - u) * 0.45, cor: "#4bb2ff", o: t >= b ? (1 - u) * 0.9 : 0 };
    }, THREE.AdditiveBlending);
    camera(w, [5.4, 1.5, (zF + z) / 2 + 15], [0.6, 0.8, (zF + z) / 2 + 3], 42);
  } },
  asa: { set: "estudio", clima: "vazio", cena: ({ w, s, t, m }) => {
    w.chao.color.set("#101726");
    luzesDesfocadas(w, t);
    w.asa.visible = true;
    const a = m("abre", 0.2);
    const f = m("fecha", 0.7);
    const ab = suave(t, a, a + 0.5) * (1 - suave(t, f, f + 0.5));
    w.flap.rotation.x = 0.25 + ab * 0.95;
    for (let i = 26; i < 86; i++) {
      const u = (t * 1.4 + seed(i)) % 1;
      const sp = w.parts[i];
      sp.visible = true;
      const sobe = (1 - ab) * Math.max(0, 1 - Math.abs(u - 0.5) * 3) * 0.9;
      sp.position.set((seed(i + 1) - 0.5) * 2.6, 1.95 + seed(i + 2) * 0.22 + sobe, -4 + u * 8);
      sp.scale.set(0.09, 0.09, 1);
      (sp.material as THREE.SpriteMaterial).color.set("#6fc2ff");
      (sp.material as THREE.SpriteMaterial).opacity = 0.5;
      (sp.material as THREE.SpriteMaterial).blending = THREE.AdditiveBlending;
    }
    camera(w, [6.4 - s * 0.26, 3.5, 5.4], [0, 1.45, 0], 30);
  } },
  moedas: { set: "estudio", clima: "claro", cena: ({ w, s, t, m }) => {
    w.chao.color.set("#f3e6cc");
    const tt = m("teto", 0.3);
    const su = suave(t, tt - 0.5, tt + 2);
    const aux = new THREE.Object3D();
    let i = 0;
    [14, 34, 27, 34, 11].forEach((h, n) => {
      const q = Math.min(h, Math.round(4 + su * h * 1.2));
      for (let j = 0; j < q && i < 180; j++, i++) {
        aux.position.set((n - 2) * 1.8, 0.1 + j * 0.21, (n % 2) * 0.9);
        aux.rotation.y = j;
        aux.updateMatrix();
        w.moedas.setMatrixAt(i, aux.matrix);
      }
    });
    w.moedas.count = i;
    w.moedas.visible = true;
    w.moedas.instanceMatrix.needsUpdate = true;
    w.teto.visible = t >= tt - 0.1;
    w.teto.position.set(0, 34 * 0.21 + 0.1, 0);
    camera(w, [-2 + s * 0.3, 4.2, 27 - s * 0.3], [0, 4.3, 0], 32);
  } },
};
export const TIPOS_VERTICAL = Object.keys(TIPOS);

const pneus = (w: Mundo, k: number, composto: string) => trocarComposto(w.carros[k], composto);

// O que o código das cenas enxerga (por nome). O Python lê os nomes entre as marcas para conferir o código com o tsc:
// só nomes aqui dentro (nada de função escrita no bloco).
// API:inicio
export const API = {
  THREE, camera, enquadrar, poe, poeCinza, halo, grade, solta, fumaca, confete, drawRastro, camCircuito, poePneu, luzesDesfocadas, bandeira,
  luzGantry, seed, suave, entra, num, gridX, gridZ, Z_POLE, Z_PORTICO, obj, criarPiloto, bracos, criarKart, criarPodio, topoDoPodio,
  criarEscada, degrau, criarMapa, pontoNoMapa, criarAlfinete, rotulo, numeroNoCarro, carro, PINTURAS, pneus,
  explodir, isolar, raioX, cortar, nomesDasPecas, ligar, destacar, brilho, aura, criarCurva, naCurva, estercar, embaralhar, criarVolante, apertar, girar, puxar, luzesDeTroca, telaDoVolante,
};
// API:fim
const NOMES_API = Object.keys(API);

type Cena = (api: typeof API, c: CV) => void;
function compilar(p: PlanoV): Cena | null {
  try {
    return new Function("API", "c", `const { ${NOMES_API.join(", ")} } = API;\n${p.codigo}`) as Cena;
  } catch (e) {
    console.error(`ERRO_CENA ${p.id}: ${(e as Error).message}`);
    return null;
  }
}

const POS: Record<string, [number, number]> = { baixo: [540, 1630], meio: [540, 1470], esquerda: [300, 1520], direita: [780, 1520], alto: [540, 560] };
const SELO = { background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00", zIndex: 40 } as const;

/** O que o plano põe por cima da cena: placas, contador, fichas, selo, riscado, medidor, gota e chuva. */
function Sobre({ c, tempo }: { c: CV; tempo: (i?: number) => number }): ReactNode {
  const { p, t, ini, fim } = c;
  const extra: ReactNode[] = [];
  if (p.chuva)
    extra.push(
      <svg key="chuva" width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, zIndex: 20 }}>
        {Array.from({ length: 90 }, (_, i) => {
          const x = seed(i) * 1200 - 60;
          const y = (seed(i + 3) * 2100 + t * 2400 * (0.8 + seed(i + 5) * 0.4)) % 2100 - 100;
          return <line key={i} x1={x} y1={y} x2={x - 10} y2={y + 66} stroke="#cfe3ff" strokeOpacity={0.42} strokeWidth={3} />;
        })}
      </svg>,
    );
  // na mesma posição, a placa mais nova toma o lugar da anterior (uma lista falada vira uma troca de placas)
  const vez: Record<string, { pl: PlacaV; em: number; n: number }> = {};
  (p.placas ?? []).forEach((pl, n) => {
    const em = pl.i !== undefined ? tempo(pl.i) : ini;
    const pos = POS[pl.pos ?? "baixo"] ? pl.pos ?? "baixo" : "baixo";
    if (t >= em - 0.01 && (!vez[pos] || em >= vez[pos].em)) vez[pos] = { pl, em, n };
  });
  for (const [pos, { pl, em, n }] of Object.entries(vez)) {
    const [x, y] = POS[pos];
    extra.push(<Placa key={`p${n}`} texto={pl.texto} unidade={pl.unidade} inicio={em} x={x} y={y} cor={cor(pl.cor)} tam={pl.texto.length > 9 ? 58 : 80} />);
  }
  if (p.contador) {
    const ct = p.contador;
    const a = ct.i0 !== undefined ? tempo(ct.i0) : ini + 0.1;
    const b = ct.i1 !== undefined ? tempo(ct.i1) : ini + fim * 0.85;
    const v = ct.de + (ct.ate - ct.de) * suave(t, a, Math.max(a + 0.2, b));
    const fimDoContador = t >= b;
    const texto = ct.formato === "tempo" ? `${Math.floor(v / 3600)}:${String(Math.floor((v % 3600) / 60)).padStart(2, "0")}:${String(Math.floor(v % 60)).padStart(2, "0")}` : num(v, ct.casas ?? 0);
    extra.push(<Placa key="ct" texto={texto} unidade={ct.unidade} inicio={a} x={540} y={(p.placas ?? []).some((x) => (x.pos ?? "baixo") === "baixo") ? 1470 : 1630} cor={fimDoContador ? cor(ct.cor_final, "#ffffff") : "#ffffff"} />);
  }
  if (p.chips) {
    const ch = p.chips;
    if (ch.i === undefined || t >= tempo(ch.i)) extra.push(<Chips key="ch" itens={ch.itens} ativo={ch.ativo ?? -1} y={1600} />);
  }
  if (p.selo && (p.selo.i === undefined || t >= tempo(p.selo.i))) {
    const e = entra(t, p.selo.i !== undefined ? tempo(p.selo.i) : ini, 0.25);
    extra.push(<div key="selo" style={{ ...SELO, position: "absolute", left: "50%", top: 1500, transform: `translateX(-50%) scale(${0.7 + e * 0.3})`, opacity: e }}>{p.selo.texto}</div>);
  }
  if (p.riscado) {
    const r = entra(t, tempo(p.riscado.i), 0.35);
    extra.push(
      <div key="risc" style={{ position: "absolute", left: "50%", top: 1500, transform: "translateX(-50%)", zIndex: 40, fontFamily: FONTE, padding: "6px 44px", borderRadius: 24, background: "rgba(14,17,24,.84)", color: r > 0.5 ? "#9299a6" : "#fff", fontSize: 110, fontWeight: 800 }}>
        {p.riscado.texto}
        <div style={{ position: "absolute", left: "6%", top: "50%", width: `${r * 88}%`, height: 11, borderRadius: 6, background: "#ff3b30", transform: "rotate(-12deg)" }} />
      </div>,
    );
  }
  if (p.medidor) {
    const a = entra(t, p.medidor.i !== undefined ? tempo(p.medidor.i) : ini, 0.6);
    const circ = 2 * Math.PI * 170;
    extra.push(
      <div key="med" style={{ position: "absolute", left: 340, top: 1120, width: 400, height: 400, zIndex: 40, fontFamily: FONTE }}>
        <svg width={400} height={400} viewBox="-200 -200 400 400">
          <circle r={170} fill="rgba(10,12,18,.8)" stroke="#272a33" strokeWidth={28} />
          <circle r={170} fill="none" stroke="#ff7a2a" strokeWidth={28} strokeDasharray={`${(circ / 2) * a} ${circ}`} transform="rotate(-90)" />
          <circle r={170} fill="none" stroke="#2fa6ff" strokeWidth={28} strokeDasharray={`${(circ / 2) * a} ${circ}`} transform="rotate(90)" />
          <text y={-6} textAnchor="middle" fill="#fff" fontSize={86} fontWeight={800}>{p.medidor.texto}</text>
          <text y={50} textAnchor="middle" fill="#7fc4ff" fontSize={34} fontWeight={700}>{p.medidor.sub ?? ""}</text>
        </svg>
      </div>,
    );
  }
  if (p.gota) {
    const e = entra(t, ini, 0.35);
    extra.push(
      <div key="gota" style={{ position: "absolute", left: "50%", top: 1400, transform: `translateX(-50%) scale(${0.8 + e * 0.2})`, opacity: e, display: "flex", alignItems: "center", gap: 18, padding: "14px 38px", borderRadius: 24, background: "rgba(14,17,24,.84)", fontFamily: FONTE, zIndex: 40 }}>
        <svg width={70} height={90} viewBox="0 0 70 90"><path d="M35 3 C35 3 66 42 66 58 A31 31 0 1 1 4 58 C4 42 35 3 35 3 Z" fill="#3bd47a" /></svg>
        <span style={{ color: "#3bd47a", fontSize: 58, fontWeight: 800 }}>{p.gota.texto}</span>
      </div>,
    );
  }
  if (p.titulo) extra.push(<Titulo key="tit" t={t} titulo={p.titulo} inicio={p.titulo.i !== undefined ? tempo(p.titulo.i) : ini} />);
  if (p.grafico) extra.push(<Grafico key="graf" g={p.grafico} t={t} tempo={tempo} ini={ini} fim={fim} foco={p.foco} />);
  return <>{extra}</>;
}

export const Vertical: React.FC<PropsVertical> = ({ palavras, planos, audio, chaves = [] }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const mundo = useRef<Mundo | null>(null);
  const quadro = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = quadro / fps;
  const tempo = (i?: number) => (i === undefined ? 0 : palavras[Math.max(0, Math.min(palavras.length - 1, i))].i);
  const inicios = planos.map((p, n) => (n === 0 ? 0 : tempo(p.i)));
  let ip = 0;
  for (let n = 0; n < inicios.length; n++) if (t >= inicios[n]) ip = n;
  const p = planos[ip];
  const tipo = (p.tipo ? TIPOS[p.tipo] : undefined) ?? TIPOS.perseguicao;
  const clima = p.clima ?? (p.codigo ? "tarde" : tipo.clima);
  const ini = inicios[ip];
  const fim = (inicios[ip + 1] ?? durationInFrames / fps) - ini;
  const cenas = useMemo(() => Object.fromEntries(planos.filter((x) => x.codigo).map((x) => [x.id, compilar(x)])), [planos]);
  const ctx = (w: Mundo): CV => {
    const c: CV = {
      w, p, t, s: t - ini, k: (t - ini) / fim, fim, ini,
      m: (nome, frac = 0.5) => (p.marcas?.[nome] !== undefined ? tempo(p.marcas[nome]) : ini + fim * frac),
      tipo: (nome, extra = {}) => {
        const pronta = TIPOS[nome];
        if (!pronta) throw new Error(`cena pronta desconhecida: ${nome}`);
        preparar(w, extra.clima ?? p.clima ?? pronta.clima, pronta.set);
        pronta.cena({ ...c, p: { ...p, ...extra } });
      },
    };
    return c;
  };
  const [alca] = useState(() => delayRender("desenhando o quadro 3D"));
  useLayoutEffect(() => {
    const w = mundo.current ?? (mundo.current = montar(ref.current!));
    esconderExtras(w);
    restaurar(); // desmonte do quadro anterior (explodir, isolar, raio-X, corte) não vaza para este
    const cena = p.codigo ? cenas[p.id] : null;
    let feito = false;
    if (cena) {
      preparar(w, clima, p.set ?? "pista");
      try {
        cena(API, ctx(w));
        feito = true;
      } catch (e) {
        console.error(`ERRO_CENA ${p.id}: ${(e as Error).message}`);
        esconderExtras(w);
      }
    }
    if (!feito) {
      preparar(w, p.codigo ? "tarde" : clima, tipo.set);
      tipo.cena(ctx(w));
    }
    w.r.render(w.cena, w.cam);
    continueRender(alca);
  });  const c = ctx(mundo.current ?? ({} as Mundo));
  const falaFim = palavras[palavras.length - 1].f;
  const claro = clima === "claro";
  return (
    <AbsoluteFill style={{ background: "#0b0c11" }}>
      <Audio src={staticFile(audio)} />
      {/* modo quadro informativo: a cena 3D escurece e desfoca atrás do gráfico */}
      <canvas ref={ref} width={1080} height={1920} style={{ position: "absolute", width: 1080, height: 1920, filter: p.foco ? "blur(10px) brightness(0.42) saturate(0.85)" : undefined }} />
      {claro && <FundoLegenda />}
      <Sobre c={c} tempo={tempo} />
      <Legenda palavras={palavras} chaves={chaves} />
      <AbsoluteFill style={{ background: "#000", opacity: suave(t, falaFim + 0.05, falaFim + 0.25), zIndex: 99 }} />
    </AbsoluteFill>
  );
};
