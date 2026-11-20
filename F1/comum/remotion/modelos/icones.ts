// Ícones de traço (24×24, estilo linha) dos gráficos informativos: os mesmos desenhos servem ao 2D (SVG) e ao 3D
// (Path2D num canvas, nas ligações aos botões). Só formas genéricas, sem marca de ninguém.
export const ICONES: Record<string, string[]> = {
  radio: ["M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z", "M6 11a6 6 0 0 0 12 0", "M12 17v4", "M9 21h6"],
  raio: ["M13 2 4 14h7l-1 8 9-12h-7z"],
  engrenagem: ["M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z", "M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"],
  bateria: ["M3 7h15a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z", "M21 10v4", "M5 10v4M8 10v4M11 10v4"],
  freio: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 3v2M12 19v2M3 12h2M19 12h2"],
  diferencial: ["M3 6h4v12H3zM17 6h4v12h-4z", "M7 12h10", "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"],
  alerta: ["M12 3 2 20h20z", "M12 9v5", "M12 17h.01"],
  volante: ["M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z", "M9 9h6v4H9z", "M6 9h.01M18 9h.01M7 14h.01M17 14h.01"],
  pneu: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"],
  seletor: ["M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z", "M12 12 15 7"],
  cronometro: ["M12 6a8 8 0 1 0 0 16 8 8 0 0 0 0-16z", "M12 10v4l2 2", "M10 2h4", "M12 2v4"],
  nuvem: ["M7 18h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 9.2 4.5 4.5 0 0 0 7 18z"],
  chuva: ["M7 14h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 5.2 4.5 4.5 0 0 0 7 14z", "M8 17l-1 3M12 17l-1 3M16 17l-1 3"],
  calendario: ["M4 6h16v14H4z", "M4 10h16", "M8 3v4M16 3v4", "M8 14h2M12 14h2M16 14h0.01"],
  bandeira: ["M5 21V4", "M5 4h14v9H5", "M9 4v9M13 4v9M5 8.5h14"],
  trofeu: ["M8 4h8v5a4 4 0 0 1-8 0z", "M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4", "M12 13v4", "M8 20h8"],
  pista: ["M6 20c-2-3 0-6 3-7s4-4 2-7", "M14 20c2-2 4-5 1-8", "M9 6c2-2 6-2 7 1"],
  motor: ["M4 9h3l2-2h5l2 2h2v3h2v-2h1v6h-1v-2h-2v3h-3l-2 2H9l-2-2H4z"],
};

/** Desenha o ícone num canvas 2D (traço branco), centrado em (cx, cy) com o lado `lado`. */
export function desenharIcone(x: CanvasRenderingContext2D, nome: string, cx: number, cy: number, lado: number, cor = "#ffffff") {
  const s = lado / 24;
  x.save();
  x.translate(cx - lado / 2, cy - lado / 2);
  x.scale(s, s);
  x.strokeStyle = cor;
  x.lineWidth = 1.8;
  x.lineCap = "round";
  x.lineJoin = "round";
  for (const d of ICONES[nome] ?? ICONES.engrenagem) x.stroke(new Path2D(d));
  x.restore();
}
