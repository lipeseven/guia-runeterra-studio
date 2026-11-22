# Renderiza os gráficos (mp4 claro + ProRes 4444 alfa) e o GPS (mp4) do catálogo. Um processo por vez.
$ErrorActionPreference = "Stop"
$raiz = "C:\Users\Felipe\Downloads\exclusive Claude"
$cli = "$raiz\node_modules\@remotion\cli\remotion-cli.js"
$aqui = $PSScriptRoot
$out = "$raiz\dados\comum\oficina_craft\biblioteca\catalogo_horizontal\dados"
New-Item -ItemType Directory -Force $out | Out-Null
$pub = "$raiz\F1\horizontal\remotion\public"
function Rend($comp, $arq, $extra) {
  $t = Measure-Command { & node $cli render "$aqui\index.tsx" $comp "$out\$arq" --public-dir $pub --gl=angle --log=error @extra 2>&1 | Select-Object -Last 3 | ForEach-Object { "  $_" } | Out-Host }
  "{0}`t{1:N0}s" -f $arq, $t.TotalSeconds
}
$sel = $args
foreach ($k in "vel","set","dlt") {
  if ($sel.Count -and -not ($sel -contains $k)) { continue }
  Rend "graf-$k" "grafico_$k.mp4" @("--codec=h264","--crf=16")
  Rend "graf-$k-alfa" "grafico_${k}_alfa.mov" @("--codec=prores","--prores-profile=4444","--image-format=png","--pixel-format=yuva444p10le")
}
foreach ($k in "gps-fixa","gps-perseguicao") {
  if ($sel.Count -and -not ($sel -contains $k)) { continue }
  Rend $k "$($k.Replace('-','_')).mp4" @("--codec=h264","--crf=16","--concurrency=1")
}

