"""Acabamentos de vidro e perfil lidos do XML, sem substituir o material por azul genérico."""
import re,unicodedata

def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(s)) if not unicodedata.combining(c)).lower()

def estilo(item):
    refs={e.tag.upper():e.get('REFERENCE','') for e in item.iter() if e.tag!='ITEM' and e.get('REFERENCE')}
    acabamento=' '.join(refs.get(k,'') for k in ('DESC_ACA','DESC_COR_PAI','DESC_VIDRO','COR_VIDRO','VIDRO','MODEL'))
    perfil=' '.join(refs.get(k,'') for k in ('DESC_ACA_PER','COR_PERFIL','ACABAMENTO_PERFIL','PERFIL'))
    if not acabamento: acabamento=item.get('DESCRIPTION','')
    n=normalizar(acabamento); p=normalizar(perfil)
    rgb=(.83,.91,.92); alpha=.14
    if 'bronze' in n: rgb=(.57,.40,.27); alpha=.28
    elif 'fume' in n or 'cinza' in n: rgb=(.36,.39,.42); alpha=.30
    elif 'verde' in n: rgb=(.38,.63,.52); alpha=.20
    elif 'preto' in n: rgb=(.16,.18,.20); alpha=.65
    if 'reflect' in n or 'reflex' in n: alpha=max(alpha,.38)
    if any(t in n for t in ('acidat','jatead','leitos','opaco','pintad')): alpha=.85
    if 'espelho' in n: rgb=(.75,.77,.79); alpha=1.
    prgb=(.68,.69,.70)
    if 'champ' in p: prgb=(.73,.64,.48)
    elif 'bronze' in p: prgb=(.49,.35,.25)
    elif 'preto' in p: prgb=(.09,.09,.10)
    elif 'branco' in p: prgb=(.94,.94,.94)
    elif 'dourad' in p: prgb=(.78,.61,.25)
    perfil_nome=refs.get('PERFIL','')
    try: largura=float(refs.get('LARGURA_PERFIL',refs.get('ESPESSURA_PERFIL','12')).replace(',','.'))
    except ValueError: largura=12.
    return dict(vidro=acabamento.strip(),perfil=perfil.strip(),rgb=rgb,alpha=alpha,
                perfil_rgb=prgb,perfil_mm=min(60.,max(6.,largura)))

def faces_porta(bb,f,visual):
    """Uma folha no plano frontal: quatro perfis opacos e vidro interno translúcido."""
    ad=0 if f[0] else 1; al=1-ad; sg=f[ad]
    d=bb[ad] if sg>0 else bb[ad+3]
    u0,u1=bb[al],bb[al+3]; z0,z1=bb[2],bb[5]
    esp=min(visual['perfil_mm'],(u1-u0)/4,(z1-z0)/4)
    def quad(a,b,c,e):
        out=[]
        for u,z in ((a,c),(b,c),(b,e),(a,e)):
            v=[0.,0.,z];v[ad]=d;v[al]=u;out.append(tuple(v))
        return out
    out=[(quad(u0+esp,u1-esp,z0+esp,z1-esp),visual['rgb'],visual['alpha'])]
    for a,b,c,e in ((u0,u0+esp,z0,z1),(u1-esp,u1,z0,z1),
                  (u0+esp,u1-esp,z0,z0+esp),(u0+esp,u1-esp,z1-esp,z1)):
        out.append((quad(a,b,c,e),visual['perfil_rgb'],1.))
    return out
