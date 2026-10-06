# -*- coding: utf-8 -*-
"""Geradores de pranchas especiais reaproveitando as funções do gerar_caderno.py."""
from __future__ import annotations
from collections import Counter
import math, re
from .regras import Familia
from .visual import analisar, renderizar

def _nova_prancha_especial(ns, n, titulo):
    """Cria especial a partir de uma prancha normal já gerada pelo próprio motor."""
    fz=ns["fz"]; doc=ns["doc"]
    src=ns.get("_layout_especial_src")
    if src is None:
        src=fz.open(ns["cfg"]["saida"])
        ns["_layout_especial_src"]=src
    idx=min(4, src.page_count-1)
    doc.insert_pdf(src, from_page=idx, to_page=idx)
    p=doc[-1]

    # Limpa somente a área útil da prancha clonada; cabeçalho/quadro/logo permanecem.
    area=ns["AREA_IN"]
    p.draw_rect(area, color=None, fill=ns["BRANCO"], overlay=True)

    # Substitui título e número da prancha.
    p.draw_rect(fz.Rect(200,118,710,140),color=None,fill=ns["BRANCO"],overlay=True)
    p.draw_rect(fz.Rect(712,52,816,96),color=None,fill=ns["BRANCO"],overlay=True)
    p.insert_text((419.5-fz.get_text_length(titulo,"hebo",16)/2,135),titulo,
                  fontname="hebo",fontsize=16,color=ns["RED"],overlay=True)
    p.insert_text((764-fz.get_text_length("PRANCHA","hebo",18)/2,62),"PRANCHA",
                  fontname="hebo",fontsize=18,overlay=True)
    s=f"{n:02d}"
    p.insert_text((764-fz.get_text_length(s,"hebo",18)/2,85),s,
                  fontname="hebo",fontsize=18,overlay=True)
    return p

TITULOS = {
    Familia.CAMA: "CAMA - DETALHAMENTO ESPECIAL",
    Familia.LED: "LED - DETALHAMENTO",
    Familia.PORTA_PERFIL: "PORTA COM PERFIL - DETALHAMENTO",
    Familia.METALON: "METALON - DETALHAMENTO",
    Familia.DIVISORIA: "DIVISÓRIA - DETALHAMENTO",
    Familia.DIVISOR_TALHER: "DIVISOR DE TALHER - DETALHAMENTO",
    Familia.SAPATEIRA: "SAPATEIRA - DETALHAMENTO",
    Familia.FRUTEIRA: "FRUTEIRA - DETALHAMENTO",
    Familia.PORTA_TEMPERO_INCLINADO: "PORTA-TEMPERO INCLINADO",
    Familia.PAINEL: "PAINEL - DETALHAMENTO",
    Familia.PAINEL_RIPADO: "PAINEL RIPADO - DETALHAMENTO",
    Familia.USINAGEM: "USINAGEM - DETALHAMENTO",
    Familia.GAVETA_ESPECIAL: "GAVETA ESPECIAL",
    Familia.TAMPONAMENTO_ESPECIAL: "TAMPONAMENTO ESPECIAL",
    Familia.CURVO: "CURVO / RAIO - DETALHAMENTO",
    Familia.ANGULO: "ÂNGULO ESPECIAL - DETALHAMENTO",
    Familia.NICHO_ESPECIAL: "NICHO ESPECIAL",
    Familia.VIDRO_APLICADO: "VIDRO APLICADO - DETALHAMENTO",
    Familia.FUNDO_FALSO: "FUNDO FALSO / REMOVÍVEL",
    Familia.PAINEL_TECNICO: "PAINEL TÉCNICO / ACESSO",
    Familia.CONJUNTO_ESPECIAL: "CONJUNTO ESPECIAL",
}

def _fmt(v):
    return str(int(round(v))) if abs(v-round(v)) < .05 else f"{v:.1f}".replace(".", ",")

def _linhas(itens, ripado=False):
    """Tabela consolidada. Ripas iguais viram uma linha com quantidade."""
    counts = Counter((i.get("desc","ITEM"), i.get("dim","")) for i in itens)
    out = []
    for (desc, dim), q in counts.items():
        d = desc
        if q > 1:
            if ripado and re.search(r"ripa", desc, re.I):
                d = f"{q} RIPAS - {desc}"
            else:
                d = f"{q}x {desc}"
        out.append((d, dim, ""))
    return out

def _walls(ns, itens):
    pw = ns["PW"]
    ws = []
    for i in itens:
        w = i.get("parede")
        if w in pw and w not in ws:
            ws.append(w)
    if not ws and pw:
        ws = [next(iter(pw))]
    return ws

def _desenhar_referencia(ns,page,rect,itens,contexto=None,interno=False):
    """Destaca o especial no hospedeiro real, com chamada de localização."""
    fz=ns['fz']; ws=_walls(ns,itens)
    if not ws or not itens or rect.height<30: return
    page.draw_rect(rect,color=ns['PRETO'],width=.45)
    page.insert_text((rect.x0+4,rect.y0+10),'ONDE FICA',fontname='hebo',fontsize=7.5,color=ns['RED'])
    r=fz.Rect(rect.x0+3,rect.y0+14,rect.x1-3,rect.y1-3)
    if contexto is None:
        contexto=_contexto_gaveta_divisor(ns,itens,interno=interno)
    cores={}
    alvos={pi for i in itens for pi in i['pecas']}
    vizinhos=contexto if contexto else [i for i in ns['PW'][ws[0]]['itens'] if id(i) not in {id(j) for j in itens}]
    for i in vizinhos:
        for pi in i['pecas']:
            if pi in alvos or pi in cores: continue
            obj=ns['P'][pi]
            cores[pi]=(obj.get('rgb'),obj.get('mat'))
            obj['rgb']=(.85,.85,.85); obj['mat']=None
    try:
        if contexto:
            _,pontos,caixas=renderizar(ns,page,r,[ws[0]],itens=itens+contexto,
                ang=30 if interno else 0,elev=35 if interno else 0,
                sem_portas=interno,dmin=3200,isolado=True)
        else:
            _,pontos,caixas=renderizar(ns,page,r,[ws[0]],contexto=True,
                isolado=False,ang=0,elev=0)
        boxes=[fz.Rect(caixas[id(i)]) for i in itens if id(i) in caixas]
        if boxes:
            b=fz.Rect(boxes[0])
            for box in boxes[1:]: b|=box
            b=fz.Rect(max(r.x0,b.x0-2),max(r.y0,b.y0-2),min(r.x1,b.x1+2),min(r.y1,b.y1+2))
            page.draw_rect(b,color=ns['RED'],width=.8)
    finally:
        for pi,(rgb,mat) in cores.items():
            obj=ns['P'][pi]
            if rgb is None: obj.pop('rgb',None)
            else: obj['rgb']=rgb
            if mat is None: obj.pop('mat',None)
            else: obj['mat']=mat

def _contextos(ns,page,rect,itens,interno=False):
    ws=_walls(ns,itens)
    if not ws or rect.height<35: return
    fz=ns['fz']; h=rect.height/len(ws)
    for k,w in enumerate(ws):
        grupo=[i for i in itens if i.get('parede')==w] or itens
        _desenhar_referencia(ns,page,fz.Rect(rect.x0,rect.y0+k*h,rect.x1,rect.y0+(k+1)*h),grupo,interno=interno)

def _temporary_wall(ns, itens, tag):
    """Parede temporária para reutilizar geom_parede/_cotas_em sem tocar nas paredes reais."""
    pw = ns["PW"]
    ws = _walls(ns, itens)
    src = pw[ws[0]]
    wid = f"__ESP_{tag}_{abs(hash(tuple(id(i) for i in itens)))%1000000}"
    pw[wid] = dict(key=src["key"], plano=src["plano"], itens=itens, id=wid)
    antigos = [i.get("parede") for i in itens]
    for i in itens:
        i["parede"] = wid
    return wid, antigos

def _restore_wall(ns, itens, wid, antigos):
    for i, old in zip(itens, antigos):
        if old is None:
            i.pop("parede", None)
        else:
            i["parede"] = old
    ns["PW"].pop(wid, None)

def _page_generic(ns,esp,n,titulo=None):
    fz=ns['fz']; area=ns['AREA_IN']; itens=esp.itens
    p=_nova_prancha_especial(ns,n,titulo or TITULOS.get(esp.familia,'DETALHAMENTO ESPECIAL'))
    rmain=fz.Rect(area.x0+258,area.y0,area.x1,area.y0+area.height*.52)
    ri=fz.Rect(rmain.x0+3,rmain.y0+3,rmain.x1-3,rmain.y1-3)
    vis=_analisar_face(ns,ri,itens)
    letra=f'ESP_{n}_{esp.familia.value}'
    ns['_numerar'](vis,letra,agrupar=True)
    yb=ns['tabela'](p,_linhas(vis),area.x0,area.y0)
    interno=esp.familia in (Familia.SAPATEIRA,Familia.FRUTEIRA,Familia.PORTA_TEMPERO_INCLINADO,
                           Familia.GAVETA_ESPECIAL,Familia.FUNDO_FALSO,Familia.PAINEL_TECNICO)
    _contextos(ns,p,fz.Rect(area.x0,yb+10,area.x0+248,area.y1),itens,interno=interno)
    p.draw_rect(rmain,color=ns['PRETO'],width=.5)
    _render_divisoria_face(ns,p,ri,itens,letra=letra,listados=vis)
    rcota=fz.Rect(area.x0+258,area.y0+area.height*.56,area.x1,area.y1)
    wid,old=_temporary_wall(ns,itens,esp.familia.value)
    try:
        G=ns['geom_parede'](ns['PW'][wid])
        ns['_cotas_em'](p,[G],rcota,['DETALHE'])
    finally:
        _restore_wall(ns,itens,wid,old)
    return p

def _contexto_gaveta_divisor(ns, itens, interno=True):
    """Localiza a gaveta montada ou o menor módulo que contém o divisor."""
    bb=[min(i["bb"][k] for i in itens) for k in range(3)]+[max(i["bb"][k+3] for i in itens) for k in range(3)]
    centro=[(bb[k]+bb[k+3])/2 for k in range(3)]
    ids={id(i) for i in itens}
    candidatos=[]
    for grupo in (ns.get("GAVETAS",[]) or []) if interno else []:
        if not grupo or any(id(i) in ids for i in grupo):
            continue
        b=[min(i["bb"][k] for i in grupo) for k in range(3)]+[max(i["bb"][k+3] for i in grupo) for k in range(3)]
        if all(b[k]-40 <= centro[k] <= b[k+3]+40 for k in range(3)):
            candidatos.append((0,(b[3]-b[0])*(b[4]-b[1]),grupo))
    for i in ns.get("inst",[]):
        if id(i) in ids or i.get("tipo")!="mod":
            continue
        b=i["bb"]
        if all(b[k]-40 <= centro[k] <= b[k+3]+40 for k in range(3)):
            candidatos.append((1,(b[3]-b[0])*(b[4]-b[1])*(b[5]-b[2]),[i]))
    if candidatos:
        hospedeiros=min(candidatos,key=lambda c:(c[0],c[1]))[2]
    else:
        # Só peças vizinhas à gaveta, nunca uma parede inteira do ambiente.
        hospedeiros=[i for i in ns.get("inst",[]) if id(i) not in ids and
            all(i["bb"][k] <= bb[k+3]+80 and i["bb"][k+3] >= bb[k]-80 for k in range(3))]
    context=[]
    divisor_p={pi for i in itens for pi in i["pecas"]}
    for i in hospedeiros:
        pecas=[]
        for pi in i["pecas"]:
            if pi in divisor_p:
                continue
            b=ns["P"][pi]["bb"]
            # Retira tampo/prateleira acima da gaveta para revelar a aplicação interna.
            if interno and b[5]-b[2] <= 40 and b[2] >= bb[5]-5:
                continue
            pecas.append(pi)
        if pecas:
            copia=dict(i); copia["pecas"]=pecas
            bbs=[ns["P"][pi]["bb"] for pi in pecas]
            copia["bb"]=[min(b[k] for b in bbs) for k in range(3)]+[max(b[k+3] for b in bbs) for k in range(3)]
            context.append(copia)
    print("ESPECIAL - HOSPEDEIRO:",[(i.get("desc",""),i.get("dim","")) for i in context])
    return context

def _page_divisor(ns, esp, n):
    """Reutiliza o 3D e a vista superior cotada da prancha normal de divisor."""
    from types import FunctionType
    fz=ns["fz"]; area=ns["AREA_IN"]
    itens=esp.itens
    contexto=_contexto_gaveta_divisor(ns,itens)
    wid,old=_temporary_wall(ns,itens,"DIVISOR")
    env=dict(ns["_prancha_peca"].__globals__)
    env.update(ns)
    env["n"]=n-1; env["_nl"]=0; env["letras"]=(f"ESP_DIVISOR_{n}",)
    resultado={}
    def nova(doc,numero,titulo):
        p=_nova_prancha_especial(ns,numero,titulo)
        resultado["pagina"]=p
        return p
    def numerar(ordenados,letra):
        vis=list(ordenados)
        for tentativa in range(6):
            tmp=fz.open(); pg=tmp.new_page(width=842,height=595)
            try: yb=ns['tabela'](pg,_linhas(vis),area.x0,area.y0)
            finally: tmp.close()
            h=area.y1-yb-12
            r=fz.Rect(area.x0+2,yb+14,area.x0+246,yb+12+h*.58-2)
            novos=_analisar_face(ns,r,ordenados,ang=30,elev=35,dmin=3200,margem=60)
            if {id(i) for i in novos}=={id(i) for i in vis}: break
            vis=novos
        else: raise ValueError('Visibilidade do divisor não estabilizou no quadro')
        resultado['visiveis']=vis
        ns['_numerar'](vis,letra,agrupar=True)
        return _linhas(vis)
    def tabela(p,linhas,x,y):
        yb=ns["tabela"](p,linhas,x,y)
        resultado["yb"]=yb
        return yb
    def render(p,rect,pids,**kw):
        # A referência é desenhada abaixo, usando apenas a gaveta hospedeira.
        if kw.get("sem_portas"):
            return
        letra=kw.pop('letra',None); grupo=kw.pop('itens',itens)
        kw['dmin']=3200
        return _render_divisoria_face(ns,p,rect,grupo,letra=letra,
                                     listados=resultado['visiveis'],**kw)
    env.update(nova_prancha=nova,_numerar=numerar,tabela=tabela,render3d=render)
    try:
        fn=FunctionType(ns["_prancha_peca"].__code__,env)
        fn(itens,"DIVISOR DE GAVETA - DETALHAMENTO","DIVISOR")
        p=resultado["pagina"]; yb=resultado["yb"]
        h=area.y1-yb-12
        ref=fz.Rect(area.x0,yb+12+h*.58+6,area.x0+248,area.y1)
        _desenhar_referencia(ns,p,ref,itens,contexto=contexto,interno=True)
        return p
    finally:
        _restore_wall(ns,itens,wid,old)


def _page_painel(ns,esp,n,cotas=False):
    fz=ns['fz']; area=ns['AREA_IN']; itens=esp.itens
    p=_nova_prancha_especial(ns,n,'PAINEL - COTAS' if cotas else 'PAINEL - LISTAGEM')
    x0=area.x0+258
    rs=[fz.Rect(x0,area.y0,area.x1,(area.y0+area.y1)/2-4),
        fz.Rect(x0,(area.y0+area.y1)/2+4,area.x1,area.y1)]
    vispor=[]
    for r,ang in zip(rs,(0,180)):
        vispor.append(_analisar_face(ns,fz.Rect(r.x0+3,r.y0+14,r.x1-3,r.y1-3),itens,ang=ang))
    ids={id(i) for v in vispor for i in v}; vis=[i for i in itens if id(i) in ids]
    letra=f'ESP_PAINEL_{n}'
    if not cotas:
        ns['_numerar'](vis,letra,agrupar=True)
        yb=ns['tabela'](p,_linhas(vis),area.x0,area.y0)
        ctx=fz.Rect(area.x0,yb+10,area.x0+248,area.y1)
    else: ctx=fz.Rect(area.x0,area.y1-130,area.x0+248,area.y1)
    _contextos(ns,p,ctx,itens)
    for k,(r,ang,lab) in enumerate(zip(rs,(0,180),('FRENTE','TRÁS'))):
        p.draw_rect(r,color=ns['PRETO'],width=.5)
        ri=fz.Rect(r.x0+3,r.y0+14,r.x1-3,r.y1-3)
        if cotas and k==0:
            wid,old=_temporary_wall(ns,itens,'PAINEL_COTA')
            try: ns['_cotas_em'](p,[ns['geom_parede'](ns['PW'][wid])],ri,['FRENTE'])
            finally: _restore_wall(ns,itens,wid,old)
        else:
            _render_divisoria_face(ns,p,ri,itens,ang=ang,
                                  letra=None if cotas else letra,listados=vispor[k])
        p.insert_text((r.x0+6,r.y0+11),lab,fontname='hebo',fontsize=8,color=ns['RED'])
    return p

def _gap_ripas(itens):
    """Estimativa geométrica do vão entre ripas no eixo de maior repetição."""
    rs=[i for i in itens if re.search(r"ripa",i.get("desc",""),re.I)]
    if len(rs)<2:
        return None
    for ax in (0,1):
        seq=sorted((i["bb"][ax],i["bb"][ax+3]) for i in rs)
        gaps=[b[0]-a[1] for a,b in zip(seq,seq[1:]) if 0 < b[0]-a[1] < 500]
        if gaps:
            return sum(gaps)/len(gaps)
    return None

def _page_ripado_1(ns,esp,n):
    fz=ns['fz']; area=ns['AREA_IN']; itens=esp.itens
    p=_nova_prancha_especial(ns,n,'PAINEL / PORTA RIPADA - LISTAGEM')
    r=fz.Rect(area.x0+258,area.y0,area.x1,area.y1-110)
    ri=fz.Rect(r.x0+3,r.y0+3,r.x1-3,r.y1-3)
    vis=_analisar_face(ns,ri,itens); letra=f'ESP_RIPADO_{n}'
    ns['_numerar'](vis,letra,agrupar=True)
    yb=ns['tabela'](p,_linhas(vis,True),area.x0,area.y0)
    _contextos(ns,p,fz.Rect(area.x0,yb+10,area.x0+248,area.y1),itens)
    p.draw_rect(r,color=ns['PRETO'],width=.5)
    _render_divisoria_face(ns,p,ri,itens,letra=letra,listados=vis)
    gap=_gap_ripas(itens); cx,cy=area.x1-65,area.y1-55
    p.draw_circle((cx,cy),48,color=ns['PRETO'],width=.7)
    p.insert_text((cx-34,cy-12),'ENTRE RIPAS',fontname='hebo',fontsize=7,color=ns['RED'])
    txt='CONFERIR VÃO' if gap is None else f'VÃO: {_fmt(gap)} mm'
    p.insert_text((cx-35,cy+6),txt,fontname='helv',fontsize=7)
    return p

def _page_ripado_2(ns,esp,n):
    fz=ns['fz']; area=ns['AREA_IN']; itens=esp.itens
    p=_nova_prancha_especial(ns,n,'PAINEL RIPADO - BASE + RIPAS')
    rip=[i for i in itens if re.search(r'ripa',i.get('desc',''),re.I)]
    sem=[i for i in itens if id(i) not in {id(j) for j in rip}]
    x0=area.x0+258; mid=(area.y0+area.y1)/2
    rs=[fz.Rect(x0,area.y0,area.x1,mid-4),fz.Rect(x0,mid+4,area.x1,area.y1)]
    grupos=[sem or itens,itens]
    vispor=[_analisar_face(ns,fz.Rect(r.x0+3,r.y0+14,r.x1-3,r.y1-3),g) for r,g in zip(rs,grupos)]
    ids={id(i) for v in vispor for i in v}; vis=[i for i in itens if id(i) in ids]
    letra=f'ESP_RIPADO_BASE_{n}'; ns['_numerar'](vis,letra,agrupar=True)
    yb=ns['tabela'](p,_linhas(vis,True),area.x0,area.y0)
    _contextos(ns,p,fz.Rect(area.x0,yb+10,area.x0+248,area.y1-110),itens)
    cx,cy=area.x0+124,area.y1-55
    p.draw_circle((cx,cy),48,color=ns['PRETO'],width=.7)
    p.insert_text((cx-25,cy-4),'DETALHE',fontname='hebo',fontsize=7,color=ns['RED'])
    p.insert_text((cx-30,cy+10),'RIPAS / LED',fontname='helv',fontsize=6.5)
    for r,g,v,lab in zip(rs,grupos,vispor,('SEM RIPAS','COM RIPAS')):
        p.draw_rect(r,color=ns['PRETO'],width=.5)
        _render_divisoria_face(ns,p,fz.Rect(r.x0+3,r.y0+14,r.x1-3,r.y1-3),g,
                              letra=letra,listados=v)
        p.insert_text((r.x0+6,r.y0+11),lab,fontname='hebo',fontsize=8,color=ns['RED'])
    return p

def _temporary_wall_key(ns, itens, tag, key):
    """Parede virtual orientada para uma face específica da divisória."""
    pw=ns["PW"]
    ws=_walls(ns,itens)
    src=pw[ws[0]] if ws else next(iter(pw.values()))
    safe=key.replace("+","P").replace("-","M")
    wid=f"__ESP_{tag}_{safe}_{abs(hash(tuple(id(i) for i in itens)))%1000000}"
    pw[wid]=dict(key=key, plano=src.get("plano",0), itens=itens, id=wid, divisoria=True)
    antigos=[i.get("parede") for i in itens]
    for i in itens:
        i["parede"]=wid
    return wid,antigos

def _divisoria_orientacoes(ns, esp):
    """Define as duas faces ortogonais da divisória em L: frontal e lateral."""
    pw=ns["PW"]; itens=esp.itens
    ws=_walls(ns,itens)
    w0=next((w for w in ws if pw.get(w,{}).get("divisoria")), ws[0] if ws else None)
    key_frente=pw[w0]["key"] if w0 else "x+"

    ax_frente=0 if key_frente.startswith("x") else 1
    ax_lateral=1-ax_frente

    U=list(itens[0]["bb"])
    for it in itens[1:]:
        b=it["bb"]
        U=[min(U[k],b[k]) for k in range(3)] + [max(U[k+3],b[k+3]) for k in range(3)]
    meio=(U[ax_lateral]+U[ax_lateral+3])/2

    # Escolhe o lado lateral olhando do ambiente para a divisória.
    ids={id(i) for i in itens}
    outros=[i for i in ns.get("inst",[]) if id(i) not in ids]
    if outros:
        centro=sum((i["bb"][ax_lateral]+i["bb"][ax_lateral+3])/2 for i in outros)/len(outros)
    else:
        centro=meio-1
    sinal="+" if centro < meio else "-"
    key_lateral=("x" if ax_lateral==0 else "y")+sinal

    # Segurança: frontal e lateral sempre precisam usar eixos diferentes.
    if key_lateral[0] == key_frente[0]:
        key_lateral=("y" if key_frente.startswith("x") else "x")+sinal
    return (("FRONTAL",key_frente),("LATERAL",key_lateral))

def _divisoria_itens_por_face(esp, orientacoes):
    """Distribui as peças pelos planos estruturais das duas pernas do L."""
    grupos={rotulo:[] for rotulo,key in orientacoes}
    eixos=[0 if key.startswith("x") else 1 for rotulo,key in orientacoes]
    suportes=[[],[]]
    for item in esp.itens:
        b=item["bb"]; dx=b[3]-b[0]; dy=b[4]-b[1]; dz=b[5]-b[2]
        if dz<=40 and max(dx,dy)>1.5*max(1,min(dx,dy)):
            # Travessas horizontais identificam a perna, não a seção da ripa.
            ax_normal=0 if dy>dx else 1
            if ax_normal in eixos:
                suportes[eixos.index(ax_normal)].append(item)
    planos=[]
    for indice,ax in enumerate(eixos):
        base=suportes[indice]
        if not base:
            base=[i for i in esp.itens if
                (i["bb"][4]-i["bb"][1] > i["bb"][3]-i["bb"][0]) == (ax==0)] or esp.itens
        valores=sorted((i["bb"][ax]+i["bb"][ax+3])/2 for i in base)
        planos.append(valores[len(valores)//2])
    for item in esp.itens:
        b=item["bb"]
        dist=[abs((b[ax]+b[ax+3])/2-pl) for ax,pl in zip(eixos,planos)]
        # A peça pertence ao plano de montagem, inclusive ripas profundas.
        if abs(dist[0]-dist[1])<=.5:
            larguras=[b[4]-b[1] if ax==0 else b[3]-b[0] for ax in eixos]
            indice=0 if larguras[0]>=larguras[1] else 1
        else:
            indice=0 if dist[0]<dist[1] else 1
        grupos[orientacoes[indice][0]].append(item)
    ids=[{id(i) for i in grupos[rotulo]} for rotulo,key in orientacoes]
    assert not ids[0]&ids[1], "Peça repetida entre frontal e lateral"
    assert ids[0]|ids[1]=={id(i) for i in esp.itens}, "Peça sem face"
    for rotulo,key in orientacoes:
        print("DIVISORIA - FACE:",rotulo,"PECAS",len(grupos[rotulo]))
    return grupos

def _analisar_face(ns,rect,itens,key=None,**kw):
    if not itens: return []
    key=key or ns['PW'][_walls(ns,itens)[0]]['key']
    wid,old=_temporary_wall_key(ns,itens,'ANALISE',key)
    try:
        vis,_,_=analisar(ns,rect,[wid],itens=itens,**kw)
        return vis
    finally: _restore_wall(ns,itens,wid,old)

def _render_divisoria_face(ns,page,rect,itens,key=None,elev=0,letra=None,listados=None,**kw):
    """Padrão comum: câmera centrada, visibilidade real e balões por ocorrência visível."""
    if not itens: return
    key=key or ns['PW'][_walls(ns,itens)[0]]['key']
    wid,old=_temporary_wall_key(ns,itens,'RENDER',key)
    try:
        return renderizar(ns,page,rect,[wid],itens=itens,elev=elev,letra=letra,
                          listados=listados,**kw)
    finally: _restore_wall(ns,itens,wid,old)

def _page_divisoria_listagem(ns,esp,n,rotulo,key,itens):
    """Listagem e imagem somente das peças pertencentes à face indicada."""
    fz=ns["fz"]; area=ns["AREA_IN"]
    p=_nova_prancha_especial(ns,n,f"DIVISÓRIA - LISTAGEM {rotulo}")
    # Mesma ordem da tabela: itens iguais recebem o mesmo número pelo motor normal.
    letra=f"ESP_DIV_{n}_{rotulo}"
    r= fz.Rect(area.x0+262,area.y0+16,area.x1-4,area.y1-4)
    vis=_analisar_face(ns,r,itens,key)
    ns['_numerar'](vis,letra,agrupar=True)
    yb=ns['tabela'](p,_linhas(vis),area.x0,area.y0)

    # Subimagem de localização no ambiente.
    rc=fz.Rect(area.x0,yb+8,area.x0+248,area.y1)
    if rc.height > 45:
        _contextos(ns,p,rc,esp.itens)

    # Imagem principal: montagem completa da face, com todas as ocorrências.
    r=fz.Rect(area.x0+258,area.y0,area.x1,area.y1)
    p.draw_rect(r,color=ns["PRETO"],width=.5)
    p.insert_text((r.x0+6,r.y0+12),f"VISTA {rotulo}",
                  fontname="hebo",fontsize=8,color=ns["RED"])
    _render_divisoria_face(ns,p,fz.Rect(r.x0+4,r.y0+16,r.x1-4,r.y1-4),
                           itens,key,elev=0,letra=letra,listados=vis)
    return p

def _page_divisoria_cotas(ns,esp,n,orientacoes):
    """Frontal e lateral em uma folha 2D, sem subimagem, como nas vistas normais."""
    area=ns["AREA_IN"]
    p=_nova_prancha_especial(ns,n,"DIVISÓRIA - COTAS FRONTAL E LATERAL")
    geometrias=[]
    rotulos=[]
    for rotulo,key in orientacoes:
        wid,old=_temporary_wall_key(ns,esp.itens,"DIV_COTA",key)
        try:
            geometrias.append(ns["geom_parede"](ns["PW"][wid]))
            rotulos.append(f"VISTA {rotulo}")
        finally:
            _restore_wall(ns,esp.itens,wid,old)
    # A própria ferramenta normal define escala comum e divide as duas colunas.
    ns["_cotas_em"](p,geometrias,area,rotulos)
    return p

def _page_sequencia_divisoria(ns,esp,n):
    fz=ns["fz"]; area=ns["AREA_IN"]; doc=ns["doc"]
    p=_nova_prancha_especial(ns,n,"DIVISÓRIA - SEQUÊNCIA DE MONTAGEM")
    # ordem estrutural: peças largas/base primeiro; ripas por último.
    its=sorted(esp.itens,key=lambda i:(bool(re.search(r"ripa",i.get("desc",""),re.I)),
                                       i["bb"][2],-(i["bb"][3]-i["bb"][0])*(i["bb"][4]-i["bb"][1])))
    ws=_walls(ns,its)
    for k in range(4):
        col=k%2; row=k//2
        r=fz.Rect(area.x0+col*area.width/2,area.y0+row*area.height/2,
                  area.x0+(col+1)*area.width/2,area.y0+(row+1)*area.height/2)
        p.draw_rect(r,color=ns["PRETO"],width=.5)
        q=max(1,math.ceil(len(its)*(k+1)/4)); parcial=its[:q]
        if ws and parcial:
            _render_divisoria_face(ns,p,fz.Rect(r.x0+3,r.y0+16,r.x1-3,r.y1-3),parcial,
                                  ang=0,elev=0,dmin=3200,margem=60,isolado=True)
        p.insert_text((r.x0+6,r.y0+11),f"{k+1}ª ETAPA",fontname="hebo",fontsize=8,color=ns["RED"])
    return p

def gerar(ns, especiais):
    """Acrescenta especiais ao doc do motor base. Retorna (ultimo_numero, relatorio)."""
    n=int(ns.get("n",len(ns["doc"])))
    rel=[]
    for esp in especiais:
        if not esp.itens:
            continue
        inicio=n+1
        if esp.familia==Familia.DIVISOR_TALHER:
            n+=1; _page_divisor(ns,esp,n)
        elif esp.familia==Familia.PAINEL:
            n+=1; _page_painel(ns,esp,n,False)
            n+=1; _page_painel(ns,esp,n,True)
        elif esp.familia==Familia.PAINEL_RIPADO:
            n+=1; _page_ripado_1(ns,esp,n)
            n+=1; _page_ripado_2(ns,esp,n)
        elif esp.familia==Familia.DIVISORIA:
            orientacoes=_divisoria_orientacoes(ns,esp)
            grupos=_divisoria_itens_por_face(esp,orientacoes)
            # Peças exclusivas por face; as cotas continuam na mesma folha.
            for rotulo,key in orientacoes:
                if grupos[rotulo]:
                    n+=1; _page_divisoria_listagem(ns,esp,n,rotulo,key,grupos[rotulo])
            n+=1; _page_divisoria_cotas(ns,esp,n,orientacoes)
            n+=1; _page_sequencia_divisoria(ns,esp,n)
        else:
            n+=1; _page_generic(ns,esp,n)
        rel.append((esp.familia.value,inicio,n,len(esp.itens),esp.motivo))
    ns["n"]=n
    return n,rel
