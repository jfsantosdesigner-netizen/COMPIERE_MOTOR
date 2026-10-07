# -*- coding: utf-8 -*-
"""Etapa 5 — materiais/cores.

Recebe as referências de material já resolvidas pela Unificação (XML x DXF) e
resolve somente aparência: arquivo da biblioteca MATERIAIS, RGB médio e textura.
Não casa XML com DXF e não decide geometria.
"""
import json, os, re, unicodedata
from collections import Counter
import projeto_unificado

PREF = ('duratex', 'arauco', 'guararapes', 'berneck', 'eucatex', 'masisa', 'stelben')

def normalizar(t):
    t = unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()

def parecido(a, b):
    if a == b: return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)) and abs(len(a)-len(b)) <= 2: return True
    if abs(len(a)-len(b)) > 1 or min(len(a), len(b)) < 5: return False
    i=0
    while i < min(len(a),len(b)) and a[i] == b[i]: i += 1
    return a[i+1:] == b[i+1:] or a[i+1:] == b[i:] or a[i:] == b[i+1:]

class Biblioteca:
    def __init__(self, raiz_motor, config=None, pixmap=None, image=None):
        self.raiz=os.path.abspath(raiz_motor); self.config=config or {}; self.pixmap=pixmap; self.image=image
        cfgmat=self.config.get('materiais')
        candidatos=[os.path.join(self.raiz,'MATERIAIS')]
        candidatos.append(cfgmat if cfgmat and os.path.isabs(cfgmat) else os.path.join(self.raiz,cfgmat or 'MATERIAIS'))
        self.pasta=next((p for p in candidatos if os.path.isdir(p)),os.path.join(self.raiz,'MATERIAIS'))
        self.cache_path=os.path.join(self.raiz,'materiais_cores.json')
        self.reserva=os.path.join(self.raiz,'texturas')
        self.lib={}; self.rgb_path={}; self.indice=[]; self.novos={}; self.cache={}; self.texturas={}
        if os.path.exists(self.cache_path):
            for rel,st,rgb in json.load(open(self.cache_path,encoding='utf-8')): self.lib[rel]=[rel,st,rgb]
        if os.path.isdir(self.pasta):
            for d,ds,fs in os.walk(self.pasta):
                ds.sort()
                for fn in sorted(fs):
                    if fn.lower().endswith(('.jpg','.jpeg','.png')):
                        full=os.path.join(d,fn); rel=os.path.relpath(full,self.pasta)
                        self.indice.append([full,self.lib[rel][1] if rel in self.lib else normalizar(os.path.splitext(fn)[0])])
                        if rel in self.lib and self.lib[rel][2]: self.rgb_path[full]=self.lib[rel][2]
        else:
            for rel,(_r,st,rgb) in self.lib.items():
                full=os.path.join(self.pasta,rel); self.indice.append([full,st]); self.rgb_path[full]=rgb

    def _melhor(self,nome):
        tk=normalizar(nome).split(); best=None
        for cand in ([tk]+([tk[:-1]] if len(tk)>1 else [])):
            n=' '.join(cand)
            for path,st in self.indice:
                ws=st.split()
                if st==n: sc=100
                elif all(t in ws for t in cand): sc=60-len(ws)
                elif len(ws)==len(cand) and all(any(parecido(t,w) for w in ws) for t in cand): sc=40-len(ws)
                else: continue
                pl=path.lower(); sc += sum(5 for w in PREF if w in pl)+(2 if '\\fabrica\\' in pl else 0)
                if best is None or sc>best[0]: best=(sc,path)
            if best: break
        return best[1] if best else None

    def cor_material(self,nome):
        if not nome:return None
        if self.cache.get(nome): return tuple(self.cache[nome][0])
        path=self._melhor(nome); rgb=tuple(self.rgb_path[path]) if path and self.rgb_path.get(path) else None
        if path and not rgb and self.pixmap is not None:
            try:
                px=self.pixmap.Pixmap(path)
                if px.colorspace is None or px.colorspace.n != 3: px=self.pixmap.Pixmap(self.pixmap.csRGB,px)
                if px.alpha:px=self.pixmap.Pixmap(px,0)
                sm=px.samples;n=len(sm)//3;step=max(1,n//6000);r=g=b=c=0
                for i in range(0,n,step):r+=sm[3*i];g+=sm[3*i+1];b+=sm[3*i+2];c+=1
                rgb=(r/c/255,g/c/255,b/c/255)
            except Exception:rgb=None
        self.cache[nome]=[list(rgb),path] if rgb else None
        if rgb and path and path not in self.rgb_path and os.path.isdir(self.pasta):
            rel=os.path.relpath(path,self.pasta);self.novos[rel]=[rel,normalizar(os.path.splitext(os.path.basename(path))[0]),list(rgb)]
        return rgb

    def textura(self,nome):
        if self.image is None or not nome:return None
        if nome in self.texturas:return self.texturas[nome]
        im=None;ref=(self.cache.get(nome) or [None,None])[1]
        if ref:
            fn=ref.replace('\\','/').split('/')[-1].lower();ofi=os.path.join(self.reserva,fn)
            try:
                if os.path.exists(ref):im=self.image.open(ref).convert('RGB');im.thumbnail((1024,1024))
                elif os.path.exists(ofi):im=self.image.open(ofi).convert('RGB')
            except Exception:im=None
        self.texturas[nome]=im;return im

    def gravar_cache_cores(self):
        if not self.novos:return 0
        self.lib.update(self.novos)
        json.dump([self.lib[k] for k in sorted(self.lib)],open(self.cache_path,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
        return len(self.novos)

def aplicar(projeto, biblioteca):
    """Aplica aparência às peças usando SOMENTE projeto['materiais_xml']."""
    refs=projeto['materiais_xml']; usadas=Counter(); coloridas=0
    for p in projeto['pecas']:
        nome=refs.get(p['i'])
        if not nome: continue
        rgb=biblioteca.cor_material(nome)
        if rgb:
            ref=(biblioteca.cache.get(nome) or [None,None])[1]
            p['rgb']=rgb;p['mat']=nome
            if ref: p['textura']=ref
            coloridas+=1;usadas[nome]+=1
            projeto['materiais'].setdefault(p['i'],{})['nome']=nome
            projeto['materiais'][p['i']]['rgb']=rgb
            projeto['materiais'][p['i']]['textura']=ref
    # Apar?ncia faz parte da identidade can?nica. Recalcula a assinatura sem
    # repetir XML x DXF: usa itens/ambiente/portas j? decididos pela Etapa 4.
    novo=projeto_unificado.construir(projeto['pecas'], projeto['itens'], projeto['ambiente'],
        projeto['portas']['pecas_xml'], xml=projeto['xml'], materiais_xml=projeto['materiais_xml'],
        diagnostico=projeto['diagnostico'])
    projeto.clear(); projeto.update(novo)
    return {'coloridas':coloridas,'usadas':usadas}
