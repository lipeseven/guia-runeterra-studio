// Adaptador HyperFrames do kit/foco (script clássico). Precisa de window.Foco (kit/foco/foco.global.js).
// Cria, dentro de `pai` (posicionado por cima da cena, ex.: <div style="position:absolute;inset:0">), duas <div> por foco
// e a cada quadro só aplica os estilos que o kit calcula (backdrop-filter + máscara + véu).
//   var camada = CamadaFoco.criar(document.querySelector("#foco"), Foco.montarFoco(cena));
//   tl.eventCallback("onUpdate", function () { camada.render(tl.time()); });  // ou dentro de um tween onUpdate
(function () {
  if (window.CamadaFoco) return;
  function kebab(k) { return k.replace(/^Webkit/, "-webkit-").replace(/[A-Z]/g, function (c) { return "-" + c.toLowerCase(); }); }
  function aplicar(el, estilo) {
    var css = "";
    for (var k in estilo) css += kebab(k) + ":" + estilo[k] + ";";
    el.style.cssText = css;
  }
  window.CamadaFoco = {
    criar: function (pai, montada) {
      var F = window.Foco;
      var refs = {};
      montada.focos.forEach(function (f) {
        var a = document.createElement("div"), b = document.createElement("div");
        a.style.display = b.style.display = "none";
        pai.appendChild(a); pai.appendChild(b);
        refs[f.id] = { camada: a, veu: b };
      });
      return {
        render: function (t) {
          var ativos = {};
          F.estadoFoco(montada, t).forEach(function (e) {
            var s = F.estilos(e), r = refs[e.id];
            aplicar(r.camada, s.camada); aplicar(r.veu, s.veu);
            ativos[e.id] = true;
          });
          for (var id in refs) if (!ativos[id]) { refs[id].camada.style.cssText = "display:none"; refs[id].veu.style.cssText = "display:none"; }
        },
      };
    },
  };
})();
