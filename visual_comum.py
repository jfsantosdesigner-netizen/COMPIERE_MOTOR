"""Distribuição comum dos balões de listagem."""
import math

def baloes(ns, page, rect, itens, letra, posicoes):
    fz=ns['fz']; ocupados=[]; chamadas=[]
    for item in itens:
        numero=item.get('num_'+letra)
        if id(item) not in posicoes or not numero:
            raise ValueError('Peça listada sem posição visível de balão')
        cx,cy=posicoes[id(item)]
        texto=str(numero); largura=fz.get_text_length(texto,'hebo',7)+4
        candidatos=[(cx,cy)]
        for raio in (10,18,28,40,56,76,100,130):
            candidatos.extend((cx+raio*math.cos(2*math.pi*k/24),
                               cy+raio*math.sin(2*math.pi*k/24)) for k in range(24))
        candidatos.extend((bx,by) for by in range(int(rect.y0)+10,int(rect.y1)-8,16)
                          for bx in range(int(rect.x0)+12,int(rect.x1)-10,20))
        escolhido=None
        for bx,by in candidatos:
            r=fz.Rect(bx-largura/2,by-5.5,bx+largura/2,by+5.5)
            folga=fz.Rect(r.x0-1.5,r.y0-1.5,r.x1+1.5,r.y1+1.5)
            if rect.contains(folga) and not any(folga.intersects(o) for o in ocupados):
                escolhido=(bx,by,r,folga); break
        if escolhido is None:
            raise ValueError('Sem espaço para balões: dividir a listagem')
        bx,by,r,folga=escolhido
        chamadas.append((cx,cy,bx,by,r,texto))
        ocupados.append(folga)
    # Chamadas primeiro: uma linha nova nunca risca o número de um balão anterior.
    for cx,cy,bx,by,r,texto in chamadas:
        if abs(bx-cx)>1 or abs(by-cy)>1:
            page.draw_line((cx,cy),(bx,by),color=ns['PRETO'],width=.35)
            page.draw_circle((cx,cy),.9,color=ns['PRETO'],fill=ns['PRETO'])
    for cx,cy,bx,by,r,texto in chamadas:
        page.draw_rect(r,color=ns['PRETO'],fill=(1,1,0),width=.4)
        page.insert_text((r.x0+2,by+2.5),texto,fontname='hebo',fontsize=7)
    return len(ocupados)
