import json
r=json.load(open(r"C:\Users\Felipe\Downloads\exclusive Claude\.claude\worktrees\agent-af0167d395c7ae49f\_aval\medidas.json",encoding='utf-8'))
for k in ["gps","anot","regioes","hud_resumo","trilha"]: print(k,json.dumps(r[k],ensure_ascii=False))
for e in r["sfx"]: print(e["evento"],e["t"],"pico",e["pico_s"],"d",e["pico_menos_ancora_ms"],"sfx",e["sfx_rms_db"],"pk",e["sfx_pico_db"],"voz",e["voz_rms_db"],"tri",e["trilha_rms_db"],"s-v",e["sfx_menos_voz_db"],"duck",e["duck_db"])
