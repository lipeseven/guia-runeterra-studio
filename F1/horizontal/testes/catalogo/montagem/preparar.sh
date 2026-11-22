#!/bin/sh
# Fase C: converte os clipes da oficina para a pasta pública do Remotion (video/_public). H.264 NVENC (opacos), VP9 alfa (com alfa).
O="/c/Users/Felipe/Downloads/exclusive Claude/dados/comum/oficina_craft/biblioteca/catalogo_horizontal"
P="$O/video/_public"; mkdir -p "$P/c" "$P/ov" "$P/ic" "$P/d"
op() { [ -f "$2" ] || ffmpeg -v error -y -i "$1" -an -c:v h264_nvenc -preset p6 -rc vbr -cq 15 -b:v 0 -g 30 -pix_fmt yuv420p "$2"; }
al() { [ -f "$2" ] || ffmpeg -v error -y -i "$1" -an -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 22 -row-mt 1 -deadline good -cpu-used 4 -g 30 "$2"; }
for c in estudio_e1_rack_focus estudio_e2_passagem_3_carros estudio_e3_aproximar_asa pista_p1_helicoptero pista_p2_lateral pista_p3_baixa pista_p4_passagem; do
  op "$O/renders/$c/${c}_60fps.mov" "$P/c/$c.mp4"; done
op "$O/renders/freio_giro_dof/freio_giro_dof_60fps.mov" "$P/c/freio_opaco.mp4"
al "$O/renders/freio_giro_dof/freio_alfa_objeto_60fps.mov" "$P/c/freio_alfa.webm"
for k in vel set dlt; do op "$O/dados/grafico_$k.mp4" "$P/d/grafico_$k.mp4"; al "$O/dados/grafico_${k}_alfa.mov" "$P/d/grafico_${k}_alfa.webm"; done
for k in gps_fixa gps_perseguicao; do op "$O/dados/$k.mp4" "$P/d/$k.mp4"; done
cp -u "$O"/hub/overlays/*.webm "$P/ov/"; cp -u "$O"/hub/icones/*.png "$P/ic/"
cp -u "/c/Users/Felipe/Downloads/exclusive Claude/F1/horizontal/kit/cartoes/exemplo/foto_exemplo.jpg" "$P/foto.jpg"
echo ok; du -sh "$P"
