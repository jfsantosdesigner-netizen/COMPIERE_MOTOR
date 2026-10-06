from pathlib import Path
import json,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
base=root/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'/'AMBIENTES'
for ambiente,pg in [('TIAGO VOLPI/COZINHA',10),('TIAGO VOLPI/COZINHA',16),('RENAN/Nova pasta',7),('ADRIANA OJEDA/DORMITÓRIO 2',9),('PRISCILA CLAUDINO/COZINHA',6)]:
    d=base/ambiente
    cfg=json.loads((d/'_config.json').read_text(encoding='utf-8'))
    P=json.loads((d/'_pecas_dxf.json').read_text(encoding='utf-8'))
    data=json.loads(next(d.glob('*_CAMERAS.json')).read_text(encoding='utf-8'))
    targets=[s for s in data['subimagens'] if s['pagina']==pg]
    print('\nAMBIENTE',ambiente,'PAGINA',pg)
    names=set()
    for s in targets:
        print('CAMERA',s['camera'])
        for i in s['itens']:
            print('ITEM',i['desc'],i['bb'],i['pecas'])
            names.add(i['desc'])
            for pi in i['pecas']:
                p=P[pi];print(' PECA',pi,[round(v) for v in p['bb']],[round(v) for v in p['dim']])
    tree=ET.parse(cfg['xml'])
    for e in tree.iter('ITEM'):
        if e.get('DESCRIPTION') in names:
            print('XML',e.get('ID'),e.get('DESCRIPTION'),[e.get(k) for k in ('WIDTH','HEIGHT','DEPTH')])
            for c in e.iter('ITEM'):
                if c is e: continue
                if 'POR_' in (c.get('ID') or '').upper() or 'PORTA' in (c.get('DESCRIPTION') or '').upper():
                    print(' PORTA_XML',c.get('ID'),c.get('DESCRIPTION'),[c.get(k) for k in ('WIDTH','HEIGHT','DEPTH')])
