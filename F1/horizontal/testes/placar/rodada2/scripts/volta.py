import json
B=r"C:\Users\Felipe\Downloads\exclusive Claude\F1\horizontal\kit"
for f in [r"\gps\voltas\11400_44_19.json",r"\graficos\comparacoes\11400_44-19_63-21.json"]:
    d=json.load(open(B+f,encoding='utf-8'))
    def desc(o,p="",dep=0):
        if dep>3: return
        if isinstance(o,dict):
            for k,v in o.items():
                if isinstance(v,(dict,list)): print(p+k, type(v).__name__, len(v)); desc(v,p+"  ",dep+1)
                else: print(p+k,"=",str(v)[:80])
        elif isinstance(o,list) and o:
            if isinstance(o[0],(dict,list)): desc(o[0],p+"  ",dep+1)
            else: print(p,"[0..]",o[:5])
    print("==",f); desc(d)
