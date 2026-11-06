import { useEffect, useRef, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile } from "remotion";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// Teste do estilo do horizontal (estudo das referências, 2026-11-05): estúdio claro, palavra gigante ATRÁS do carro
// (camadas: fundo → palavra → carro 3D com fundo transparente → nota à mão). Carro = .glb baixado (public dir).
const W = 1920;
const H = 1080;

export const TesteEstudio: React.FC<{ arquivo: string; palavra: string; cor: string; nota: string }> = ({ arquivo, palavra, cor, nota }) => {
  const tela = useRef<HTMLCanvasElement>(null);
  const [espera] = useState(() => delayRender("carregando o .glb"));

  useEffect(() => {
    const r = new THREE.WebGLRenderer({ canvas: tela.current!, antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setSize(W, H, false);
    r.setClearColor(0x000000, 0);
    r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.3;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    const cena = new THREE.Scene();
    const pm = new THREE.PMREMGenerator(r);
    cena.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    const luz = new THREE.DirectionalLight(0xffffff, 2.2);
    luz.position.set(1.5, 10, 2.5);
    luz.castShadow = true;
    luz.shadow.mapSize.set(4096, 4096);
    luz.shadow.radius = 14;
    Object.assign(luz.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 0.5, far: 30 });
    cena.add(luz);
    const chao = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.22 }));
    chao.rotation.x = -Math.PI / 2;
    chao.receiveShadow = true;
    cena.add(chao);
    const cam = new THREE.PerspectiveCamera(22, W / H, 0.1, 200);

    new GLTFLoader().load(staticFile(arquivo), (g) => {
      const carro = g.scene;
      carro.traverse((o) => {
        if ((o as THREE.Mesh).isMesh) {
          o.castShadow = true;
          o.receiveShadow = true;
        }
      });
      // de pé no chão, centrado, comprimento real de 2026 (5,4 m), frente para -z
      let caixa = new THREE.Box3().setFromObject(carro);
      const t = caixa.getSize(new THREE.Vector3());
      if (t.z < t.x) carro.rotation.y = Math.PI / 2;
      caixa = new THREE.Box3().setFromObject(carro);
      const s = 5.4 / Math.max(...caixa.getSize(new THREE.Vector3()).toArray());
      carro.scale.multiplyScalar(s);
      caixa = new THREE.Box3().setFromObject(carro);
      const c = caixa.getCenter(new THREE.Vector3());
      carro.position.sub(new THREE.Vector3(c.x, caixa.min.y, c.z));
      cena.add(carro);
      cam.position.set(6.4, 1.5, 7.9);
      cam.lookAt(-0.15, 0.5, -0.2);
      r.render(cena, cam);
      continueRender(espera);
    });
    return () => r.dispose();
  }, [arquivo, espera]);

  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 62%, #f7f6f2 0%, #e6e4de 70%, #d9d6cf 100%)" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, textAlign: "center", fontFamily: "Bahnschrift", fontStretch: "condensed", fontWeight: 700, fontSize: 470, letterSpacing: -6, lineHeight: 1, color: cor }}>
        {palavra}
      </div>
      <canvas ref={tela} width={W} height={H} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <div style={{ position: "absolute", left: 1290, top: 250, width: 520, fontFamily: "Ink Free", fontSize: 50, lineHeight: 1.1, color: "#1d1d1d", transform: "rotate(-4deg)" }}>
        {nota}
      </div>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <path d="M 1360 420 C 1300 470, 1240 480, 1150 470" stroke="#1d1d1d" strokeWidth={5} fill="none" strokeLinecap="round" />
        <path d="M 1172 452 L 1148 470 L 1174 486" stroke="#1d1d1d" strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </AbsoluteFill>
  );
};
