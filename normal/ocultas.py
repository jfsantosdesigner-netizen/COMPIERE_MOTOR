"""Detalhes executivos de peças funcionais encobertas, sem alterar a montagem."""
from .vidros import normalizar
from .regras import subimagens
from visual_comum import baloes


def _uniao(itens):
    return [min(i['bb'][k] for i in itens) for k in range(3)]+[max(i['bb'][k+3] for i in itens) for k in range(3)]


def _dentro(b,h,folga=30):
    return all(h[k]-folga<=b[k] and b[k+3]<=h[k+3]+folga for k in (0,1))


def _hospedeiro(ns,grupo,w):
    b=_uniao(grupo)
    mods=[m for m in w['itens'] if m['tipo']=='mod' and m not in grupo and _dentro(b,m['bb']) and
          ns['geo'].dist_caixas(b,m['bb'])<=180]
    if not mods: return None
    return min(mods,key=lambda m:ns['geo'].dist_caixas(b,m['bb']))


def _conectados(ns,itens):
    restantes=list(itens);out=[]
    while restantes:
        g=[restantes.pop(0)]
        for a in g:
            viz=[b for b in restantes if ns['geo'].dist_caixas(a['bb'],b['bb'])<=6]
            g+=viz;restantes=[b for b in restantes if b not in viz]
        out.append(g)
    return out


def candidatos(ns,w,ocultos):
    """Exceções funcionais primeiro; sobreposição genérica não cria detalhe."""
    ocultos=[i for i in ocultos if i.get('parede')==w['id']]
    ids={id(i) for i in ocultos};out=[];usados=set()
    for g,rotulo,sem_lista in subimagens(ns,w):
        if sem_lista: continue
        alvos=[i for i in g if id(i) in ids]
        if not alvos: continue
        host=_hospedeiro(ns,alvos,w)
        if host is None: continue
        out.append((alvos,host,rotulo));usados.update(id(i) for i in alvos)
    # Moldura/base de apoio: ao menos três tiras conectadas nos dois eixos, sob o módulo.
    # Uma chapa/tamponamento simplesmente sobreposto continua fora da listagem.
    for m in [i for i in w['itens'] if i['tipo']=='mod' and not i.get('_gaveta_montada')]:
        mb=m['bb'];base=[]
        for i in w['itens']:
            if i['tipo']!='comp' or id(i) in usados: continue
            b=i['bb'];dx=b[3]-b[0];dy=b[4]-b[1];dz=b[5]-b[2]
            if _dentro(b,mb) and mb[2]-180<=b[2] and b[5]<=mb[2]+30 and dz<=150 and min(dx,dy)<=120 and max(dx,dy)>=150:
                base.append(i)
        for g in _conectados(ns,base):
            eixos={0 if i['bb'][3]-i['bb'][0]>i['bb'][4]-i['bb'][1] else 1 for i in g}
            if len(g)>=3 and len(eixos)==2 and any(id(i) in ids for i in g):
                out.append((g,m,'BASE DE APOIO — PEÇAS ENCOBERTAS'));usados.update(id(i) for i in g)
    termos=('sarrafo','barrote','cunha','afastador','base trilho','base do trilho','base para trilho','base tecnica','base removivel')
    for i in ocultos:
        if id(i) in usados or not any(t in normalizar(i['desc']) for t in termos): continue
        host=_hospedeiro(ns,[i],w)
        if host is None: continue
        out.append(([i],host,'DETALHE FUNCIONAL — '+i['desc']));usados.add(id(i))
    return out


def _capturar(ns,itens,rect,pontos,vis):
    def callback(buffer,indices,quadro,validos):
        import numpy as np
        a=np.asarray(buffer);h,w=a.shape
        for i in itens:
            codigos=[pc+1 for pc,pi in indices.items() if pi in i['pecas'] and pi in validos]
            if not codigos: continue
            yy,xx=np.nonzero(np.isin(a,codigos))
            if not len(xx): continue
            cx,cy=float(xx.mean()),float(yy.mean());j=int(np.argmin((xx-cx)**2+(yy-cy)**2))
            pontos[id(i)]=(rect.x0+(xx[j]+.5)*rect.width/w,rect.y0+(yy[j]+.5)*rect.height/h)
    return callback


def analisar(ns,w,grupo,rect,op):
    doc=ns['fz'].open();p=doc.new_page(width=842,height=595);pontos={};vis=set()
    try:
        ns['render3d'](p,rect,[w['id']],itens=grupo,visiveis=vis,so_visiveis=True,
                       visibilidade_callback=_capturar(ns,grupo,rect,pontos,vis),**op)
    finally: doc.close()
    return [i for i in grupo if id(i) in pontos],pontos


def planejar(ns,v,ocultos):
    fz=ns['fz'];r=fz.Rect(20,20,250,140);out=[];usados=set()
    for wid in v['paredes']:
        w=ns['PW'][wid];its=[i for i in ocultos if i['parede']==wid]
        for grupo,host,rotulo in candidatos(ns,w,its):
            grupo=[i for i in grupo if id(i) not in usados]
            if not grupo: continue
            op=dict(ang=0,elev=38,dmin=3200,margem=60,margem_pontos=10,isolado=True,sem_portas=True)
            # Acima do móvel: olha de baixo para a face de apoio; abaixo, mostra a montagem por cima.
            if min(i['bb'][2] for i in grupo)>=host['bb'][5]-30: op['elev']=-20
            vis,_=analisar(ns,w,grupo,r,op)
            if not vis: continue
            out.append(dict(w=wid,itens=grupo,listados=vis,hospedeiro=host,rotulo=rotulo,op=op))
            usados.update(id(i) for i in grupo)
            print('SUBIMAGEM FUNCIONAL:',v['titulo'],rotulo,'VISIVEIS',len(vis),'HOSPEDEIRO',host['desc'])
    return out


def renderizar(ns,page,rect,plano,letra,permitidos):
    fz=ns['fz'];grupo=plano['itens'];w=ns['PW'][plano['w']];host=plano['hospedeiro']
    # Referência montada e detalhe compartilham a folha. Nenhuma peça muda de posição.
    refh=min(70,max(55,rect.height*.38)) if rect.height>=110 else rect.height*.42;separador=rect.y1-refh-5
    detalhe=fz.Rect(rect.x0,rect.y0,rect.x1,separador-3)
    referencia=fz.Rect(rect.x0+2,separador+9,rect.x1-2,rect.y1)
    pontos={};vis=set()
    ns['render3d'](page,detalhe,[w['id']],itens=grupo,visiveis=vis,
                   visibilidade_callback=_capturar(ns,grupo,detalhe,pontos,vis),**plano['op'])
    listados=[i for i in plano['listados'] if id(i) in permitidos]
    if any(id(i) not in pontos for i in listados):
        raise ValueError('Detalhe funcional pequeno demais: peça listada não ficou visível')
    baloes(ns,page,detalhe,listados,letra,pontos)
    # Relação física: corpo do hospedeiro preservado, com o conjunto aplicado destacado.
    contexto=[host]+grupo
    caixas={}
    ns['render3d'](page,referencia,[w['id']],itens=contexto,ang=0,elev=0,dmin=4200,margem=60,
                   isolado=False,contexto=True,sem_portas=False,margem_pontos=4,caixas_projetadas=caixas)
    alvo=[caixas[pi] for i in grupo for pi in i['pecas'] if pi in caixas]
    if alvo:
        b=fz.Rect(min(q[0] for q in alvo),min(q[1] for q in alvo),max(q[2] for q in alvo),max(q[3] for q in alvo))
        b=b+(-2,-2,2,2);b=b & referencia
        if not b.is_empty: page.draw_rect(b,color=ns['RED'],width=.8)
    page.draw_line((rect.x0,separador),(rect.x1,separador),color=(.6,.6,.6),width=.3)
    page.insert_text((rect.x0+2,separador+7),'POSIÇÃO NO MÓVEL',fontname='hebo',fontsize=6,color=ns['RED'])
    ns.setdefault('_auditoria_ocultas',[]).append(dict(vista=letra,pagina=page.number+1,
        grupo=plano['rotulo'],listados=len(listados),baloes=len(listados),
        ids_listados=[id(i) for i in listados],ids_visiveis=list(pontos),
        hospedeiro=host['n']))
    return listados
