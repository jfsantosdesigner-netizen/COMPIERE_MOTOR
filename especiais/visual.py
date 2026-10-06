"""Padrão visual dos especiais, isolado do motor normal."""
from __future__ import annotations
import ast
import inspect
import math
import textwrap
from .regras import PADRAO_CAMERA_ESPECIAL


def _ancoras(buffer, indices, itens, rect, kw):
    import numpy as np
    a = np.asarray(buffer)
    h, w = a.shape
    validos = kw['visiveis']
    pontos = kw.setdefault('_ancoras', {})
    caixas = kw.setdefault('_caixas', {})
    for item in itens:
        codigos = [pc + 1 for pc, pi in indices.items()
                   if pi in item['pecas'] and pi in validos]
        if not codigos:
            continue
        yy, xx = np.nonzero(np.isin(a, codigos))
        if not len(xx):
            continue
        # O ponto de chamada fica em um pixel visível da peça, nunca atrás dela.
        cx, cy = float(np.mean(xx)), float(np.mean(yy))
        j = int(np.argmin((xx-cx)**2 + (yy-cy)**2))
        pontos[id(item)] = (rect.x0+(xx[j]+.5)*rect.width/w,
                            rect.y0+(yy[j]+.5)*rect.height/h)
        caixas[id(item)] = (rect.x0+xx.min()*rect.width/w,
                            rect.y0+yy.min()*rect.height/h,
                            rect.x0+(xx.max()+1)*rect.width/w,
                            rect.y0+(yy.max()+1)*rect.height/h)


def _motor(ns):
    """Adapta apenas a cópia em memória do renderer para os especiais."""
    fn = ns.get('_renderer_especial')
    if fn is None:
        base = ns['render3d']
        tree = ast.parse(textwrap.dedent(inspect.getsource(base)))
        func = tree.body[0]
        blocos = [n for n in func.body if isinstance(n, ast.If)
                  and "kw.get('visiveis')" in ast.unparse(n.test)]
        if len(blocos) != 1:
            raise RuntimeError('Renderer sem bloco único de visibilidade')
        bloco = blocos[0]
        j = next(k for k, n in enumerate(bloco.body) if isinstance(n, ast.If)
                 and "kw.get('so_visiveis')" in ast.unparse(n.test))
        bloco.body.insert(j, ast.parse('_esp_ancoras(_ib, _pidx, its, rect, kw)').body[0])
        # O filtro normal de chapas MDF não deve apagar metalon/vidro/LED do especial.
        for node in ast.walk(func):
            if isinstance(node, ast.If) and 'sd_[1]' in ast.unparse(node.test):
                node.test = ast.BoolOp(op=ast.And(), values=[node.test,
                                      ast.parse('_iso is None', mode='eval').body])
            if isinstance(node, ast.If) and 'AMB_I' in ast.unparse(node.test) and 'ELETRO_I' in ast.unparse(node.test):
                for sub in node.body:
                    if isinstance(sub, ast.If) and ast.unparse(sub.test) == 'itens':
                        sub.test = ast.parse('itens and _iso is None', mode='eval').body
                    if isinstance(sub, ast.If) and any(isinstance(x, ast.Expr) and
                            ast.unparse(x).startswith('shell.append') for x in sub.body):
                        k = next(k for k,x in enumerate(sub.body) if isinstance(x,ast.Expr)
                                 and ast.unparse(x).startswith('shell.append'))
                        sub.body.insert(k,ast.parse("_pidx[len(shell)] = p_['i']").body[0])
        ast.fix_missing_locations(tree)
        env = dict(base.__globals__)
        env['_esp_ancoras'] = _ancoras
        exec(compile(tree, base.__code__.co_filename, 'exec'), env)
        fn = env['render3d']
        ns['_renderer_especial'] = fn
    fn.__globals__.update(ns)
    if fn.__globals__.get('_Im') is None:
        raise RuntimeError('Visibilidade dos especiais requer Pillow')
    return fn


def analisar(ns, rect, pids, itens=None, **kw):
    """Mede a visibilidade na mesma câmera/quadro usados na imagem final."""
    fz = ns['fz']
    doc = fz.open()
    p = doc.new_page(width=max(842,rect.x1+1),height=max(595,rect.y1+1))
    pontos, caixas, vis = {}, {}, set()
    op = dict(PADRAO_CAMERA_ESPECIAL)
    op.update(kw)
    try:
        _motor(ns)(p,rect,pids,itens=itens,visiveis=vis,so_visiveis=True,
                   _ancoras=pontos,_caixas=caixas,**op)
    finally:
        doc.close()
    candidatos = itens if itens is not None else [i for w in pids for i in ns['PW'][w]['itens']]
    return [i for i in candidatos if id(i) in pontos], pontos, caixas


def baloes(ns, page, rect, itens, letra, posicoes):
    fz=ns['fz']; ocupados=[]
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
        if abs(bx-cx)>1 or abs(by-cy)>1:
            page.draw_line((cx,cy),(bx,by),color=ns['PRETO'],width=.35)
            page.draw_circle((cx,cy),.9,color=ns['PRETO'],fill=ns['PRETO'])
        page.draw_rect(r,color=ns['PRETO'],fill=(1,1,0),width=.4)
        page.insert_text((r.x0+2,by+2.5),texto,fontname='hebo',fontsize=7)
        ocupados.append(folga)
    return len(ocupados)


def renderizar(ns,page,rect,pids,itens=None,letra=None,listados=None,**kw):
    pontos,caixas,vis={}, {}, set()
    op=dict(PADRAO_CAMERA_ESPECIAL)
    op.update(kw)
    _motor(ns)(page,rect,pids,itens=itens,visiveis=vis,
               _ancoras=pontos,_caixas=caixas,**op)
    todos=itens if itens is not None else [i for w in pids for i in ns['PW'][w]['itens']]
    vistos=[i for i in todos if id(i) in pontos]
    if letra:
        permitidos={id(i) for i in listados} if listados is not None else {id(i) for i in vistos}
        if not permitidos <= {id(i) for i in vistos}:
            raise ValueError('Tabela inclui ocorrência oculta nesta imagem')
        marcados=[i for i in vistos if id(i) in permitidos]
        quantidade=baloes(ns,page,rect,marcados,letra,pontos)
        print('ESPECIAL - VISUAL:',letra,'TOTAL',len(todos),'VISIVEIS',len(vistos),'BALOES',quantidade)
        ns.setdefault('_auditoria_visual',[]).append(dict(letra=letra,pagina=page.number,quadro=tuple(rect),total=len(todos),
            visiveis=len(vistos),baloes=quantidade,listados=len(permitidos),
            ids_visiveis=[id(i) for i in vistos],ids_baloes=[id(i) for i in marcados]))
    return vistos,pontos,caixas
