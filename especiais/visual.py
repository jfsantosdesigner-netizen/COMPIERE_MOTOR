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
                    if isinstance(sub, ast.If) and any(isinstance(x,ast.Continue) for x in sub.body) and any(
                            isinstance(x,ast.Name) and x.id=='itens' for x in ast.walk(sub.test)):
                        sub.test = ast.BoolOp(op=ast.And(),values=[sub.test,
                                         ast.parse('_iso is None',mode='eval').body])
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


from visual_comum import baloes


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
