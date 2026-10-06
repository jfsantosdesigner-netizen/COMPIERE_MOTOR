from pathlib import Path
import json
root=Path(__file__).resolve().parent/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'/'AMBIENTES'
for p in root.rglob('*_CAMERAS.json'):
    rel=p.parent.relative_to(root)
    d=json.loads(p.read_text(encoding='utf-8'))
    principal=[c for c in d['cameras'] if c.get('contexto') and c.get('ang',0)==0 and c.get('elev',0)==0 and len(c['paredes'])==1]
    dup={}
    for c in principal:
        key=c['paredes'][0].split('@')[0]
        dup.setdefault(key,set()).add(c['paredes'][0])
    many={k:sorted(v) for k,v in dup.items() if len(v)>1}
    if many:print(rel,many)
