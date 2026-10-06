"""Contornos e vãos executivos compartilhados pelos dois motores."""
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def vaos_prateleiras(verticais, horizontais, altura):
    """Uma peça vertical localizada não divide automaticamente o armário inteiro."""
    vert=[]
    for u0,u1,z0,z1 in verticais:
        encontros={round((h0+h1)/2,1) for a,h0,b,h1 in horizontais
                   if z0-30 <= (h0+h1)/2 <= z1+30 and
                   (abs(b-u0)<=10 or abs(a-u1)<=10)}
        if z1-z0 >= .8*altura or len(encontros)>=2:
            if not any(abs(u0-a)<=1 and abs(u1-b)<=1 for a,b in vert):
                vert.append((u0,u1))
    vert.sort()
    return [(a[1],b[0]) for a,b in zip(vert,vert[1:]) if b[0]-a[1]>100]


def assinatura_vaos(gaps):
    return tuple((round(a,1),round(b,1)) for a,b in gaps)


def mascara_contornos(poligonos, tamanho):
    """Silhueta por peça na mesma ordem das faces; sem triangulação nem linhas ocultas."""
    im=Image.new('I',tamanho,0);desenho=ImageDraw.Draw(im);codigos={}
    for pontos,peca in poligonos:
        codigo=codigos.setdefault(peca,len(codigos)+1)
        desenho.polygon(pontos,fill=codigo)
    a=np.asarray(im);p=np.pad(a,1);vizinhos=(p[1:-1,:-2],p[1:-1,2:],p[:-2,1:-1],p[2:,1:-1])
    borda=(a>0) & np.logical_or.reduce([a>v for v in vizinhos])
    return Image.fromarray((borda*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)),a


def contornos(ns,page,faces,XY):
    fz=ns['fz'];poligonos=[]
    for face in faces:
        q=[XY(x,y) for x,y in face[1]]
        if ns['area2'](q)>=.15:
            poligonos.append((q,face[5] if len(face)>5 else 0))
    if not poligonos:return
    # Folga para não truncar a espessura do traço junto às extremidades da geometria.
    pontos=[p for q,_ in poligonos for p in q]
    rect=fz.Rect(min(x for x,y in pontos)-1,min(y for x,y in pontos)-1,
                 max(x for x,y in pontos)+1,max(y for x,y in pontos)+1)&page.rect
    if rect.is_empty:return
    escala=250/72
    w=max(1,round(rect.width*escala));h=max(1,round(rect.height*escala))
    mask,ids=mascara_contornos([([( (x-rect.x0)*w/rect.width,(y-rect.y0)*h/rect.height)
                               for x,y in q],pi) for q,pi in poligonos],(w,h))
    desenho=Image.new('RGBA',(w,h),(20,20,20,0));desenho.putalpha(mask)
    buf=io.BytesIO();desenho.save(buf,format='PNG')
    page.insert_image(rect,stream=buf.getvalue(),overlay=True)
    ns.setdefault('_auditoria_contornos',[]).append(dict(pagina=page.number+1,
        pecas_visiveis=int(len(np.unique(ids[ids>0]))),pixels_contorno=int(np.count_nonzero(mask)),
        quadro=tuple(rect)))
