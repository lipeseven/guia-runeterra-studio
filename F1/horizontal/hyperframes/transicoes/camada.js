// Adaptador HyperFrames do kit/transicoes (script clássico). Precisa de window.Transicoes (kit/transicoes/transicoes.global.js).
// `cenas` = elementos (um por cena, posicionados em inset:0 dentro de `pai`); a cada quadro só troca o estilo de cada um
// (o mesmo estilo que o Remotion aplica) e a barra do wipe. Os sons vêm como <audio class="clip"> fixos no HTML
// (Banco.dePedidos(pedidosSfx(ts)) do kit/sfx → para_hyperframes), com o pico no quadro de pico da transição.
//   var seq = CamadaTransicoes.criar(pai, [elA, elB, elC], Transicoes.montarTransicoes(lista, 60), 60);
//   tl.eventCallback("onUpdate", function () { seq.render(tl.time()); });
(function () {
  if (window.CamadaTransicoes) return;
  function kebab(k) { return k.replace(/[A-Z]/g, function (c) { return "-" + c.toLowerCase(); }); }
  function css(estilo) { var s = ""; for (var k in estilo) s += kebab(k) + ":" + estilo[k] + ";"; return s; }
  window.CamadaTransicoes = {
    criar: function (pai, cenas, ts, fps) {
      var barra = document.createElement("div");
      pai.appendChild(barra);
      return {
        render: function (t) {
          var s = window.Transicoes.estadoSequencia(ts, Math.round(t * fps));
          var vis = {};
          s.itens.forEach(function (it, z) { vis[it.cena] = true; cenas[it.cena].style.cssText = css(it.estilo) + "z-index:" + (z + 1); });
          cenas.forEach(function (el, i) { if (!vis[i]) el.style.cssText = "display:none"; });
          barra.style.cssText = s.barra
            ? "position:absolute;z-index:10;left:" + s.barra.x + "px;top:" + s.barra.y + "px;width:" + s.barra.w + "px;height:" + s.barra.h + "px;background:" + s.barra.cor
            : "display:none";
        },
      };
    },
  };
})();
