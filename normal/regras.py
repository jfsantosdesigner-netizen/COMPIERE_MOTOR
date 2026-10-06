"""Condições das vistas normais: conjuntos montados e subimagens funcionais."""
import re
from .vidros import estilo,normalizar

def _dim(item):
    try: return [float(item.get(k,'0').replace(',','.')) for k in ('WIDTH','HEIGHT','DEPTH')]
    except (ValueError,AttributeError): return [0.,0.,0.]

def preparar_itens(ns):
    root=ns['XML_TREE']; P=ns['P']; inst=ns['inst']; nodes=list(root.iter('ITEM'))
    bydesc={}
    for node in nodes:
        d=re.sub(r'\s+[\d.,]+x[\d.,]+x[\d.,]+mm\s*$','',node.get('DESCRIPTION','')).strip()
        bydesc.setdefault(d,[]).append(node)
    for item in inst:
        candidatos=bydesc.get(item['desc'],[])
        dims=sorted(ns['geo'].parse_dim(item['dim']))
        node=next((n for n in candidatos if all(abs(a-b)<=2 for a,b in zip(sorted(_dim(n)),dims))),None)
        if node is not None:
            portas=[n for n in node.iter('ITEM') if ('_POR_' in n.get('ID','').upper() or n.get('ID','').upper().startswith('POR_'))]
            portas=[n for n in portas if n.find('REFERENCES') is not None]
            if portas and '_porta_visual' not in item and item.get('xml_mat_porta') in ('vidro','espelho','aluminio'):
                item['_porta_visual']=estilo(portas[0])
            txt=normalizar(' '.join(str(e.attrib) for e in node.iter()))
            if 'pino invis' in txt and item['tipo']=='comp': item['_legenda_normal']='PINO INVISÍVEL'
            if 'removivel' in txt and item['tipo']=='comp': item['_legenda_normal']='REMOVÍVEL'
        if 'prateleira' in normalizar(item['desc']) and 'vidro' in normalizar(item['desc']):
            item['_prateleira_vidro']=True
            vv=estilo(node) if node is not None else dict(rgb=(.83,.91,.92),alpha=.14)
            vv['_sem_perfil']=True
            for pi in item['pecas']:
                P[pi]['rgb']=vv['rgb']; P[pi]['mat']=None; P[pi]['_visual_vidro']=vv
    for porta in ns['por_euronobre']+ns['por_avulsas']:
        if porta['mat'] not in ('vidro','espelho'): continue
        vis=porta.get('visual'); dims=sorted(porta['dim'])
        if not vis: continue
        hosts=[i for i in inst if i.get('_porta_visual')==vis]
        for piece in P:
            b=piece['bb']
            if not any(all(h['bb'][k]-150<=b[k] and b[k+3]<=h['bb'][k+3]+150 for k in range(3)) for h in hosts): continue
            ds=sorted(piece['dim'])
            if ds[0]<=30 and all(abs(a-b)<=15 for a,b in zip(ds[1:],dims[1:])):
                piece['_visual_vidro']=vis; piece['mat']=None; piece['rgb']=vis['rgb']
    # Representações de acessórios internos só usam geometria efetivamente presente.
    usados={pi for i in inst for pi in i['pecas']}; ns['_acessorios_internos']=[]
    rx=re.compile(r'cesto|lixeira|aramad|calceir|porta.?tempero|sapateir',re.I)
    for node in nodes:
        if not rx.search(node.get('DESCRIPTION','')): continue
        if node.get('COMPONENT')=='Y': continue
        dm=sorted(_dim(node))
        if dm[0]<=0: continue
        pecas=[p['i'] for p in P if p['i'] not in usados and all(abs(a-b)<=3 for a,b in zip(sorted(p['dim']),dm))]
        for pi in pecas:
            b=P[pi]['bb']
            hosts=[m for m in inst if m['tipo']=='mod' and all(m['bb'][k]-10<=b[k] and b[k+3]<=m['bb'][k+3]+10 for k in range(3))]
            if not hosts: continue
            host=min(hosts,key=lambda m:(m['bb'][3]-m['bb'][0])*(m['bb'][4]-m['bb'][1])*(m['bb'][5]-m['bb'][2]))
            ns['_acessorios_internos'].append(dict(desc=node.get('DESCRIPTION'),tipo='comp',bb=b,pecas=[pi],
                                                  hospedeiro=host,_sem_listagem=True))
            usados.add(pi)

def montar_gavetas(ns):
    for k,grupo in enumerate(ns.get('GAVETAS',[]),1):
        bb=[min(i['bb'][a] for i in grupo) for a in range(3)]+[max(i['bb'][a+3] for i in grupo) for a in range(3)]
        parede=max(ns['paredes'],key=lambda w:sum(id(i) in {id(j) for j in grupo} for i in w['itens']))
        f=ns['FV'][parede['key']]
        al=0 if bb[3]-bb[0]>=bb[4]-bb[1] else 1; ad=1-al
        chave=('x' if ad==0 else 'y') + ('+' if f[0]+f[1]>0 else '-')
        item=dict(n=100000+k,desc='Gaveta',dim='x'.join(ns['fmt'](v) for v in (bb[al+3]-bb[al],bb[5]-bb[2],bb[ad+3]-bb[ad])),
                  tipo='mod',bb=bb,pecas=list(dict.fromkeys(pi for i in grupo for pi in i['pecas'])),
                  parede=parede['id'],parede_key=parede['key'],_gaveta_montada=True,_camera_detalhe_key=chave)
        ids={id(i) for i in grupo}
        for w in ns['paredes']: w['itens']=[i for i in w['itens'] if id(i) not in ids]
        parede['itens'].append(item);ns['inst'].append(item)

def subimagens(ns,w):
    out=[]; usados=set()
    for item in w['itens']:
        nome=normalizar(item['desc'])
        cond=item.get('_gaveta_montada') or item.get('_prateleira_vidro') or any(x in nome for x in
            ('mesa de cabeceira','criado','canto l','canto reto','adega','cristaleira','cava','puxador usinado'))
        if not cond: continue
        if ('cava' in nome or 'puxador usinado' in nome) and 'porta' in nome: continue
        if item.get('_prateleira_vidro'):
            b=item['bb']; host=next((m for m in w['itens'] if m is not item and m['tipo']=='mod' and
                all(m['bb'][k]-10<=b[k] and b[k+3]<=m['bb'][k+3]+10 for k in range(3))),None)
            if host is None: continue  # prateleira na parede usa balão na imagem principal
        grupo=[item]
        if 'cabeceira' in nome or 'criado' in nome:
            b=item['bb']
            grupo += [o for o in w['itens'] if o is not item and o['tipo']=='comp' and
                ns['geo'].dist_caixas(b,o['bb'])<=6 and o['bb'][5]-o['bb'][2]<=b[5]-b[2]+100 and
                all(o['bb'][k]>=b[k]-100 and o['bb'][k+3]<=b[k+3]+100 for k in (0,1))]
        if id(item) not in usados:
            out.append((grupo,item['desc'],False));usados.update(id(i) for i in grupo)
    for ace in ns.get('_acessorios_internos',[]):
        if ace['hospedeiro'] not in w['itens']: continue
        copia=dict(ace,parede=w['id'])
        out.append(([copia]+[ace['hospedeiro']],'ACESSÓRIO INTERNO',True))
    return out


def corpo_com_frente(itens,key,FV):
    """Corpo fechado de peças retas permanece nas vistas normais, sem prancha extra."""
    if len(itens)<3: return False
    f=FV[key];ad=0 if f[0] else 1;al=1-ad;sg=f[ad]
    u0=min(i['bb'][al] for i in itens);u1=max(i['bb'][al+3] for i in itens)
    z0=min(i['bb'][2] for i in itens);z1=max(i['bb'][5] for i in itens)
    area=(u1-u0)*(z1-z0)
    horizontais=[i for i in itens if i['bb'][5]-i['bb'][2]<=30 and
        i['bb'][al+3]-i['bb'][al]>=(u1-u0)*.5 and i['bb'][ad+3]-i['bb'][ad]>=150]
    if len(horizontais)<2: return False
    frente=min(min(i['bb'][ad]*sg,i['bb'][ad+3]*sg) for i in itens)
    cob=0.
    for i in itens:
        b=i['bb']
        if b[ad+3]-b[ad]>30 or abs(min(b[ad]*sg,b[ad+3]*sg)-frente)>60: continue
        cob+=(b[al+3]-b[al])*(b[5]-b[2])
    return area>0 and cob>=.4*area
