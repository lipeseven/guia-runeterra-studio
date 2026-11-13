// Adaptador HyperFrames do kit/graficos (window.Graficos, de kit/graficos/graficos.global.js).
// Por quadro só troca atributos (d, opacity) dos elementos; o SVG é criado uma vez, em ordem de pintura.
// Uso:  var camada = CamadaGrafico.criar(svg, Graficos.montar(specs, dados, larguras));
//       timeline: onUpdate -> camada.render(t)
(function () {
  var NS = "http://www.w3.org/2000/svg";
  function criar(svg, m) {
    var nos = {};
    // cria todos os nós na ordem do estado final de cada gráfico (mesma ordem de pintura do Remotion)
    m.graficos.forEach(function (g) {
      g.elementos.forEach(function (e) {
        var n;
        if (e.tipo === "texto") {
          n = document.createElementNS(NS, "text");
          n.setAttribute("x", e.x); n.setAttribute("y", e.y);
          n.setAttribute("font-family", m.fonteCss); n.setAttribute("font-size", e.tam); n.setAttribute("font-weight", e.peso);
          n.setAttribute("fill", e.cor); n.setAttribute("text-anchor", e.ancora);
          n.textContent = e.texto;
        } else {
          n = document.createElementNS(NS, "path");
          n.setAttribute("stroke-linejoin", "round");
          if (e.tipo === "linha") {
            n.setAttribute("fill", "none"); n.setAttribute("stroke", e.cor); n.setAttribute("stroke-width", e.largura);
            n.setAttribute("stroke-linecap", e.tracejado ? "butt" : "round");
            if (e.tracejado) n.setAttribute("stroke-dasharray", e.tracejado);
          } else {
            n.setAttribute("fill", e.cor); n.setAttribute("stroke", "none");
          }
        }
        n.setAttribute("opacity", 0);
        svg.appendChild(n);
        nos[e.id] = n;
      });
    });
    return {
      render: function (t) {
        var vis = {};
        Graficos.estado(m, t).forEach(function (d) {
          var n = nos[d.id];
          vis[d.id] = true;
          if (d.tipo === "path") n.setAttribute("d", d.d);
          n.setAttribute("opacity", d.opac);
        });
        for (var id in nos) if (!vis[id]) nos[id].setAttribute("opacity", 0);
      },
      nos: nos,
    };
  }
  window.CamadaGrafico = { criar: criar };
})();
