// Adaptador HyperFrames do kit/cartoes (script clássico). Precisa de window.Cartoes (kit/cartoes/cartoes.global.js).
// A cada quadro troca o conteúdo de um <svg> pelo SVG que o kit monta (layout e animação no kit, igual ao Remotion).
//   var camada = CamadaCartoes.criar(document.querySelector("#cartoes"), Cartoes.montarCartoes(cena));
//   tl.eventCallback("onUpdate", function () { camada.render(tl.time()); });
(function () {
  if (window.CamadaCartoes) return;
  window.CamadaCartoes = {
    criar: function (svg, montada) {
      var ultimo = null;
      return {
        render: function (t) {
          var s = window.Cartoes.svgCartoes(montada, t);
          if (s !== ultimo) { svg.innerHTML = s; ultimo = s; }
        },
      };
    },
  };
})();
