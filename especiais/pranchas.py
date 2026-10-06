# -*- coding: utf-8 -*-
"""Geradores de pranchas especiais reaproveitando as funções do gerar_caderno.py."""
from __future__ import annotations
from collections import Counter
import math, re
from .regras import Familia

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

def _contextos(ns, page, rect, itens):
    """Subimagens mostrando todos os locais/parede onde o especial aparece."""
    fz = ns["fz"]; render3d = ns["render3d"]
    ws = _walls(ns, itens)
    if not ws:
        return
    n = len(ws)
    h = rect.height / n
    for k, w in enumerate(ws):
        r = fz.Rect(rect.x0, rect.y0+k*h, rect.x1, rect.y0+(k+1)*h)
        page.draw_rect(r, color=ns["PRETO"], width=.45)
        page.insert_text((r.x0+4, r.y0+10), "ONDE FICA", fontname="hebo", fontsize=7.5, color=ns["RED"])
        render3d(page, fz.Rect(r.x0+2,r.y0+13,r.x1-2,r.y1-2), [w], contexto=True)

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

def _representativos(itens):
    """Se ocorrências iguais estiverem espalhadas, desenha uma só; tabela preserva variações."""
    if len(itens) <= 1:
        return itens
    dims = [i["bb"] for i in itens]
    span = [max(b[k+3] for b in dims)-min(b[k] for b in dims) for k in range(3)]
    one = dims[0]
    own = [one[k+3]-one[k] for k in range(3)]
    if max(span) > max(own)*2.5:
        return [itens[0]]
    return itens

def _page_generic(ns, esp, n, titulo=None):
    fz=ns["fz"]; doc=ns["doc"]; area=ns["AREA_IN"]
    p=ns["nova_prancha"](doc,n,titulo or TITULOS.get(esp.familia,"DETALHAMENTO ESPECIAL"))
    linhas=_linhas(esp.itens, esp.familia==Familia.PAINEL_RIPADO)
    yb=ns["tabela"](p,linhas,area.x0,area.y0)
    # subimagem do ambiente, sempre lateral esquerda
    rc=fz.Rect(area.x0,yb+10,area.x0+248,area.y1)
    _contextos(ns,p,rc,esp.itens)
    # imagem principal isolada em cima à direita
    rmain=fz.Rect(area.x0+258,area.y0,area.x1,area.y0+area.height*.52)
    p.draw_rect(rmain,color=ns["PRETO"],width=.5)
    reps=_representativos(esp.itens)
    ws=_walls(ns,reps)
    if ws:
        ns["render3d"](p,fz.Rect(rmain.x0+2,rmain.y0+2,rmain.x1-2,rmain.y1-2),[ws[0]],
                       itens=reps,ang=25,elev=12,dmin=2200,margem=60,isolado=True)
    # cotas reutilizam o motor atual
    rcota=fz.Rect(area.x0+258,area.y0+area.height*.56,area.x1,area.y1)
    wid,old=_temporary_wall(ns,reps,esp.familia.value)
    try:
        G=ns["geom_parede"](ns["PW"][wid])
        ns["_cotas_em"](p,[G],rcota,["DETALHE"])
    except Exception as e:
        p.insert_text((rcota.x0+8,rcota.y0+20),f"COTAS: verificar geometria ({type(e).__name__})",fontname="helv",fontsize=8)
    finally:
        _restore_wall(ns,reps,wid,old)
    return p

def _page_painel(ns, esp, n, cotas=False):
    fz=ns["fz"]; area=ns["AREA_IN"]; doc=ns["doc"]
    titulo=("PAINEL - COTAS" if cotas else "PAINEL - LISTAGEM")
    p=ns["nova_prancha"](doc,n,titulo)
    if not cotas:
        yb=ns["tabela"](p,_linhas(esp.itens),area.x0,area.y0)
        rctx=fz.Rect(area.x0,yb+10,area.x0+210,area.y1)
        _contextos(ns,p,rctx,esp.itens)
        x0=area.x0+220
    else:
        rctx=fz.Rect(area.x0,area.y1-130,area.x0+210,area.y1)
        _contextos(ns,p,rctx,esp.itens)
        x0=area.x0+220
    reps=_representativos(esp.itens)
    ws=_walls(ns,reps)
    if cotas:
        # frente e trás, ambos isolados. As cotas geométricas ficam na frente.
        r1=fz.Rect(x0,area.y0,area.x1,(area.y0+area.y1)/2-4)
        r2=fz.Rect(x0,(area.y0+area.y1)/2+4,area.x1,area.y1)
        wid,old=_temporary_wall(ns,reps,"painel")
        try:
            G=ns["geom_parede"](ns["PW"][wid]); ns["_cotas_em"](p,[G],r1,["FRENTE"])
        finally:
            _restore_wall(ns,reps,wid,old)
        if ws:
            p.draw_rect(r2,color=ns["PRETO"],width=.5)
            ns["render3d"](p,fz.Rect(r2.x0+2,r2.y0+2,r2.x1-2,r2.y1-2),[ws[0]],
                           itens=reps,ang=180,elev=0,dmin=2200,margem=60,isolado=True)
            p.insert_text((r2.x0+6,r2.y0+12),"TRÁS",fontname="hebo",fontsize=8,color=ns["RED"])
    else:
        r1=fz.Rect(x0,area.y0,area.x1,(area.y0+area.y1)/2-4)
        r2=fz.Rect(x0,(area.y0+area.y1)/2+4,area.x1,area.y1)
        for r,ang,lab in ((r1,0,"FRENTE"),(r2,180,"TRÁS")):
            p.draw_rect(r,color=ns["PRETO"],width=.5)
            if ws:
                ns["render3d"](p,fz.Rect(r.x0+2,r.y0+14,r.x1-2,r.y1-2),[ws[0]],
                               itens=reps,ang=ang,elev=0,dmin=2200,margem=60,isolado=True)
            p.insert_text((r.x0+6,r.y0+11),lab,fontname="hebo",fontsize=8,color=ns["RED"])
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
    p=_page_generic(ns,esp,n,"PAINEL / PORTA RIPADA - LISTAGEM")
    area=ns["AREA_IN"]; gap=_gap_ripas(esp.itens)
    # detalhe redondo no canto inferior direito
    cx,cy=area.x1-75,area.y1-65
    p.draw_circle((cx,cy),48,color=ns["PRETO"],width=.7)
    p.insert_text((cx-35,cy-10),"DISTÂNCIA",fontname="hebo",fontsize=7,color=ns["RED"])
    txt="ENTRE RIPAS" if gap is None else f"VÃO: {_fmt(gap)} mm"
    p.insert_text((cx-35,cy+5),txt,fontname="helv",fontsize=7)
    return p

def _page_ripado_2(ns,esp,n):
    fz=ns["fz"]; area=ns["AREA_IN"]; doc=ns["doc"]
    p=ns["nova_prancha"](doc,n,"PAINEL RIPADO - BASE + RIPAS")
    reps=_representativos(esp.itens); ws=_walls(ns,reps)
    rip=[i for i in reps if re.search(r"ripa",i.get("desc",""),re.I)]
    sem=[i for i in reps if i not in rip]
    rctx=fz.Rect(area.x0,area.y1-135,area.x0+205,area.y1)
    _contextos(ns,p,rctx,esp.itens)
    x0=area.x0+215; mid=(area.y0+area.y1)/2
    for rr,its,lab in ((fz.Rect(x0,area.y0,area.x1,mid-4),sem or reps,"SEM RIPAS"),
                       (fz.Rect(x0,mid+4,area.x1,area.y1),reps,"COM RIPAS")):
        p.draw_rect(rr,color=ns["PRETO"],width=.5)
        if ws and its:
            ns["render3d"](p,fz.Rect(rr.x0+2,rr.y0+14,rr.x1-2,rr.y1-2),[ws[0]],itens=its,
                           ang=0,elev=0,dmin=2200,margem=60,isolado=True)
        p.insert_text((rr.x0+6,rr.y0+11),lab,fontname="hebo",fontsize=8,color=ns["RED"])
    # detalhe circular reservado também para LED quando existir no conjunto
    cx,cy=area.x1-65,area.y1-58
    p.draw_circle((cx,cy),42,color=ns["PRETO"],width=.7)
    p.insert_text((cx-28,cy-3),"DETALHE",fontname="hebo",fontsize=7,color=ns["RED"])
    p.insert_text((cx-30,cy+10),"RIPAS / LED",fontname="helv",fontsize=6.5)
    return p

def _page_sequencia_divisoria(ns,esp,n):
    fz=ns["fz"]; area=ns["AREA_IN"]; doc=ns["doc"]
    p=ns["nova_prancha"](doc,n,"DIVISÓRIA - SEQUÊNCIA DE MONTAGEM")
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
            ns["render3d"](p,fz.Rect(r.x0+3,r.y0+16,r.x1-3,r.y1-3),[ws[0]],itens=parcial,
                           ang=25,elev=10,dmin=2400,margem=60,isolado=True)
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
        if esp.familia==Familia.PAINEL:
            n+=1; _page_painel(ns,esp,n,False)
            n+=1; _page_painel(ns,esp,n,True)
        elif esp.familia==Familia.PAINEL_RIPADO:
            n+=1; _page_ripado_1(ns,esp,n)
            n+=1; _page_ripado_2(ns,esp,n)
        elif esp.familia==Familia.DIVISORIA:
            n+=1; _page_generic(ns,esp,n,"DIVISÓRIA - LISTAGEM")
            n+=1; _page_generic(ns,esp,n,"DIVISÓRIA - COTAS")
            n+=1; _page_sequencia_divisoria(ns,esp,n)
        else:
            n+=1; _page_generic(ns,esp,n)
        rel.append((esp.familia.value,inicio,n,len(esp.itens),esp.motivo))
    ns["n"]=n
    return n,rel
