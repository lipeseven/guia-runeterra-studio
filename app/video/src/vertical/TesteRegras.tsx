// Cena de teste do tema "regras da F1": bandeira amarela e Safety Car, numa pista em perspectiva.
// A pista é um plano com perspectiva real; a câmera anda por ela e tudo é preso às palavras da narração.
import { AbsoluteFill, Audio, Img, staticFile } from "remotion";
import { FONTE, Legenda, Placa, entra, noTrecho, suave, useTempo, type Palavra } from "./kit";

const PINTURAS = ["c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7"]; // arte em F1/arte/carro_cima.py (VectorCraft)
const Carro: React.FC<{ nome: string }> = ({ nome }) => <Img src={staticFile(`f1-teste/${nome}.png`)} style={{ width: 250, height: 450, display: "block" }} />;
const C = 5000; // centro do plano

const L = 12000; // comprimento do plano da pista
const LARG = 760; // largura do asfalto

const Bandeira: React.FC<{ x: number; y: number; forca: number; escala?: number }> = ({ x, y, forca, escala = 1 }) => {
  const t = useTempo();
  if (forca <= 0) return null;
  const ondas = Array.from({ length: 13 }, (_, k) => k * 40);
  const onda = (u: number, d: number) => Math.sin(u * 0.028 + t * 9 + d) * (8 + u * 0.09);
  const cima = ondas.map((u) => `${u} ${onda(u, 0)}`).join(" L");
  const baixo = [...ondas].reverse().map((u) => `${u} ${240 + onda(u, 0.5)}`).join(" L");
  return (
    <svg width={760} height={720} viewBox="-60 -120 760 720" style={{ position: "absolute", left: x, top: y, overflow: "visible", opacity: forca, transform: `scale(${escala * (0.86 + forca * 0.14)})`, transformOrigin: "60px 120px", zIndex: 30 }}>
      <defs>
        <linearGradient id="pano" x1="0" x2="1" y1="0" y2="0.25"><stop offset="0" stopColor="#ffc800" /><stop offset="0.18" stopColor="#fff06a" /><stop offset="0.34" stopColor="#e8a800" /><stop offset="0.52" stopColor="#ffe24a" /><stop offset="0.7" stopColor="#dd9c00" /><stop offset="0.86" stopColor="#ffe65a" /><stop offset="1" stopColor="#f0b400" /></linearGradient>
        <linearGradient id="mastro" x1="0" x2="1"><stop offset="0" stopColor="#6e7682" /><stop offset="0.5" stopColor="#f3f5f8" /><stop offset="1" stopColor="#7c8490" /></linearGradient>
      </defs>
      <rect x={-14} y={-60} width={14} height={640} rx={6} fill="url(#mastro)" />
      <path d={`M${cima} L${baixo} Z`} fill="url(#pano)" stroke="#a87900" strokeWidth={2.5} style={{ filter: "drop-shadow(0 16px 28px rgba(0,0,0,.45))" }} />
    </svg>
  );
};

export const TesteRegras: React.FC<{ palavras: Palavra[] }> = ({ palavras }) => {
  const t = useTempo();
  const em = (x: string, apos = 0) => noTrecho(palavras, x, apos);
  const amarela = em("bandeira amarela"), reduz = em("reduz"), serio = em("Se for"), sc = em("safety car"), fila = em("A fila"), vant = em("a vantagem");
  const fim = palavras[palavras.length - 1].f;

  // câmera: abertura rápida recuando pelo grid, depois acompanha o pelotão
  const abre = suave(t, 0, 1.15);
  const zona = suave(t, sc - 0.35, sc + 0.5);
  const avanço = t * 620 * (1 - suave(t, reduz, serio) * 0.55);
  const foco = L - 600 - avanço - (1 - abre) * 2300 - zona * 170;
  const inclina = 62 - (1 - abre) * 16 + suave(t, fila, fila + 1) * 5;
  const alto = 1 + (1 - abre) * 1.25 - zona * 0.1 - suave(t, fila, fila + 1.2) * 0.13;

  // pelotão: o intervalo entre os carros cai quando a fila se aperta
  const aperta = suave(t, fila + 0.1, vant + 0.9);
  const passo = 480 - aperta * 180;
  const lentos = suave(t, reduz, serio);
  const vezDoSc = entra(t, sc - 0.1, 0.9);
  const yLider = foco - 640;
  const ySc = yLider - 470 - (1 - vezDoSc) * 1300;
  const pisca = Math.sin(t * 26) > 0;
  const amareloNaPista = entra(t, amarela, 0.35) * (1 - suave(t, sc, sc + 0.6));
  const lista = PINTURAS.map((p, k) => ({ p, k, y: yLider + k * passo, x: 540 + [-110, 120, -140, 80, -60, 140, -120, 40][k] * (1 - aperta) + (k % 2 ? 62 : -62) * aperta }));
  const vantagem = 12.4 - 11.6 * suave(t, vant, vant + 0.9);

  return (
    <AbsoluteFill style={{ background: "#0a1420", overflow: "hidden" }}>
      <Audio src={staticFile("f1-teste/voz.wav")} />
      {/* céu ao amanhecer: cor do canal */}
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(#10294d 0%, #3a6a8e 6%, #c79a7c 11%, #f4bf7a 15%, #f4bf7a 40%, #15312b 41%)" }} />
      <AbsoluteFill style={{ perspective: 1050, perspectiveOrigin: "50% 30%" }}>
        <div style={{ position: "absolute", left: 540 - C, top: 1390 - foco, width: 2 * C, height: L, transformOrigin: `${C}px ${foco}px`, transform: `rotateX(${inclina}deg) scale(${alto})`, background: "#1c5832" }}>
          <div style={{ position: "absolute", left: C - 1500, width: 3000, top: 0, bottom: 0, backgroundImage: `url(${staticFile("f1-teste/grama.png")})`, backgroundSize: "1024px 1024px" }} />
          {/* área de escape, zebra, asfalto, linhas */}
          <div style={{ position: "absolute", left: C - LARG / 2 - 210, width: LARG + 420, top: 0, bottom: 0, background: "#c9a97a" }} />
          <div style={{ position: "absolute", left: C - LARG / 2 - 62, width: LARG + 124, top: 0, bottom: 0, background: "repeating-linear-gradient(0deg,#d8283a 0 110px,#f4f4f4 110px 220px)" }} />
          <div style={{ position: "absolute", left: C - LARG / 2, width: LARG, top: 0, bottom: 0, backgroundImage: `url(${staticFile("f1-teste/asfalto.png")})`, backgroundSize: "1024px 1024px" }} />
          {[-1, 1].map((s) => <div key={s} style={{ position: "absolute", left: C + s * (LARG / 2 - 16) - 7, width: 14, top: 0, bottom: 0, background: "#f4f4f4" }} />)}
          {/* trecho amarelo na pista: "aqui ninguém ultrapassa" */}
          <div style={{ position: "absolute", left: C - LARG / 2, width: LARG, top: foco - 2600, height: 3000, opacity: amareloNaPista * 0.1, background: "#ffd400" }} />
          {[-1, 1].map((s) => <div key={s} style={{ position: "absolute", left: C + s * (LARG / 2 - 16) - 11, width: 22, top: foco - 2600, height: 3000, opacity: amareloNaPista, background: "#ffd400", boxShadow: "0 0 40px 10px rgba(255,212,0,.6)" }} />)}
          {/* carros */}
          {lista.map(({ p, k, x, y }) => {
            const eixo = C + (x - 540);
            return (
              <div key={k} style={{ position: "absolute", left: eixo - 125, top: y - 225 }}>
                <Carro nome={p} />
                <div style={{ position: "absolute", left: 235, top: 300, color: "#fff", fontFamily: FONTE, fontSize: 64, fontWeight: 800, opacity: 1 - lentos, transform: "rotate(0deg)" }}>{k + 1}</div>
              </div>
            );
          })}
          {/* safety car */}
          <div style={{ position: "absolute", left: C - 125, top: ySc - 225 }}>
            <Carro nome="sc" />
            <div style={{ position: "absolute", left: 72, top: 205, width: 106, height: 18, borderRadius: 6, background: "#14171d", boxShadow: "0 0 0 2px #333" }}>
              <div style={{ position: "absolute", left: 4, top: 3, width: 44, height: 12, background: pisca ? "#ffb300" : "#4d3a00", boxShadow: pisca ? "0 0 46px 20px rgba(255,170,0,.75)" : "none" }} />
              <div style={{ position: "absolute", right: 4, top: 3, width: 44, height: 12, background: pisca ? "#4d3a00" : "#ffb300", boxShadow: pisca ? "none" : "0 0 46px 20px rgba(255,170,0,.75)" }} />
            </div>
          </div>
        </div>
      </AbsoluteFill>
      {/* névoa no horizonte */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 110, height: 330, background: "linear-gradient(rgba(244,191,122,0), rgba(244,191,122,.85) 32%, rgba(244,191,122,.45) 58%, rgba(244,191,122,0))", zIndex: 5 }} />
      {/* bandeira em primeiro plano, só enquanto a fala é dela */}
      <Bandeira x={120} y={760} escala={0.72} forca={entra(t, amarela - 0.05, 0.3) * (1 - suave(t, serio - 0.2, serio + 0.15))} />
      <Placa texto="NÃO ULTRAPASSE" inicio={reduz + 0.5} ate={serio - 0.1} x={540} y={1720} tam={64} cor="#ffd400" />
      {/* painel SC */}
      {t >= sc - 0.05 && (
        <div style={{ position: "absolute", left: "50%", top: 470, zIndex: 40, transform: `translateX(-50%) scale(${0.7 + entra(t, sc, 0.3) * 0.3})`, opacity: entra(t, sc, 0.2) * (1 - entra(t, fila + 0.1, 0.2)), background: "#0a0c10", border: "6px solid #2a2d33", borderRadius: 18, padding: "6px 34px", fontFamily: "'Consolas', monospace", fontSize: 104, fontWeight: 800, letterSpacing: 8, color: "#ffc400", textShadow: "0 0 26px #ffae00" }}>SC</div>
      )}
      {/* vantagem do líder: cai até quase zero */}
      <Placa texto={`${vantagem.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`} unidade="s de vantagem" inicio={fila + 0.3} x={540} y={640} cor={vantagem < 2 ? "#ff5a4a" : "#ffffff"} tam={84} />
      <Legenda palavras={palavras} chaves={["amarela", "ultrapassa", "safety", "vantagem"]} />
      <AbsoluteFill style={{ background: "#000", opacity: suave(t, fim + 0.1, fim + 0.5), zIndex: 60 }} />
    </AbsoluteFill>
  );
};
