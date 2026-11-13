// Adaptador HyperFrames do kit/anotacao (script clássico). Precisa de window.Anotacao (kit/anotacao/anotacao.global.js).
// Monta o SVG uma vez a partir do kit e, a cada quadro, só troca atributos (transform, dashoffset, opacity).
//   var camada = CamadaAnotacao.criar(document.querySelector("#anotacoes"), Anotacao.montar(cena, fonte));
//   tl.eventCallback("onUpdate", function () { camada.render(tl.time()); });  // ou dentro de um tween onUpdate
(function () {
  if (window.CamadaAnotacao) return;
  var NS = "http://www.w3.org/2000/svg";
  function el(tag, attrs, pai) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(e);
    return e;
  }
  function traco(pai, tr, cor) {
    return el("path", {
      d: tr.d, fill: "none", stroke: cor, "stroke-width": tr.largura, "stroke-linecap": "round", "stroke-linejoin": "round",
      pathLength: 1, "stroke-dasharray": "1 2", "stroke-dashoffset": 1, opacity: 0,
    }, pai);
  }
  function aplicar(p, tr) {
    p.setAttribute("stroke-dashoffset", (1 - tr.k).toFixed(5));
    p.setAttribute("opacity", tr.k > 0 ? 1 : 0);
  }
  window.CamadaAnotacao = {
    criar: function (svg, montada) {
      var A = window.Anotacao;
      var est0 = A.estado(montada, 0);
      var refs = est0.map(function (it) {
        var g = el("g", { transform: it.transform }, svg);
        var tracos = it.tracos.map(function (tr) { return traco(g, tr, it.cor); });
        var glifos = it.glifos.map(function (gl, gi) {
          var gg = el("g", { transform: gl.transform }, g);
          var ps = [];
          var mascara = null;
          if (gl.outline) {
            var id = "anot-" + it.id + "-" + gi;
            mascara = el("mask", { id: id, maskUnits: "userSpaceOnUse", x: -600, y: -1400, width: 2400, height: 2200 }, gg);
            el("path", { d: gl.outline, fill: it.cor, mask: "url(#" + id + ")" }, gg);
          }
          gl.tracos.forEach(function (tr) { ps.push(traco(tr.tinta ? gg : mascara, tr, tr.tinta ? it.cor : "#fff")); });
          return ps;
        });
        return { g: g, tracos: tracos, glifos: glifos };
      });
      return {
        render: function (t) {
          var est = A.estado(montada, t);
          est.forEach(function (it, i) {
            var r = refs[i];
            r.g.setAttribute("transform", it.transform);
            it.tracos.forEach(function (tr, j) {
              if (r.tracos[j].getAttribute("d") !== tr.d) r.tracos[j].setAttribute("d", tr.d); // seta dinâmica
              aplicar(r.tracos[j], tr);
            });
            it.glifos.forEach(function (gl, gi) { gl.tracos.forEach(function (tr, j) { aplicar(r.glifos[gi][j], tr); }); });
          });
        },
      };
    },
  };
})();
