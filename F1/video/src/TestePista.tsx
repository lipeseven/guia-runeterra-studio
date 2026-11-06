import { useEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile } from "remotion";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// Conferência de um .glb de circuito: só o grupo pedido (ex.: "tracksplit"), visto de cima, para medir e comparar com o traçado real.
export const TestePista: React.FC<{ arquivo: string; grupo: string; saida?: string }> = ({ arquivo, grupo }) => {
  const tela = useRef<HTMLCanvasElement>(null);
  const [espera] = useState(() => delayRender("carregando o circuito"));
  const [info, setInfo] = useState("");
  useEffect(() => {
    const r = new THREE.WebGLRenderer({ canvas: tela.current!, antialias: true, preserveDrawingBuffer: true });
    r.setSize(2000, 2000, false);
    r.setClearColor(0xffffff, 1);
    const cena = new THREE.Scene();
    cena.add(new THREE.AmbientLight(0xffffff, 1.2), new THREE.DirectionalLight(0xffffff, 1.5));
    new GLTFLoader().load(staticFile(arquivo), (g) => {
      const alvo = g.scene.getObjectByName(grupo) ?? g.scene;
      cena.add(alvo);
      alvo.updateMatrixWorld(true);
      const caixa = new THREE.Box3().setFromObject(alvo);
      const c = caixa.getCenter(new THREE.Vector3());
      const t = caixa.getSize(new THREE.Vector3());
      const lado = Math.max(t.x, t.z) / 2;
      const cam = new THREE.OrthographicCamera(-lado, lado, lado, -lado, 0.1, 10000);
      cam.position.set(c.x, caixa.max.y + 100, c.z);
      cam.up.set(0, 0, -1);
      cam.lookAt(c.x, 0, c.z);
      r.render(cena, cam);
      setInfo(`caixa ${t.x.toFixed(0)} × ${t.z.toFixed(0)} m, altura ${caixa.min.y.toFixed(1)} a ${caixa.max.y.toFixed(1)}; centro ${c.x.toFixed(0)}, ${c.z.toFixed(0)}; lado da imagem ${(lado * 2).toFixed(0)} m`);
      continueRender(espera);
    });
    return () => r.dispose();
  }, [arquivo, grupo, espera]);
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      <canvas ref={tela} width={2000} height={2000} style={{ width: 2000, height: 2000 }} />
      <div style={{ position: "absolute", left: 20, top: 20, fontSize: 34, fontFamily: "Segoe UI", background: "#fff" }}>{info}</div>
    </AbsoluteFill>
  );
};
