# -*- coding: utf-8 -*-
"""Etapa 4: interpretação única do XML do Promob."""
import hashlib
import re, xml.etree.ElementTree as ET
from collections import Counter, OrderedDict

def _fmt(v):
    v=round(v*2)/2
    return str(int(round(v))) if abs(v-round(v))<.01 else ('%.1f'%v).replace('.',',')

def _modelo(it):
    r=it.find('REFERENCES')
    if r is None:return ''
    for tag in ('MODEL','COR','MAT'):
        e=r.find(tag)
        if e is not None and e.get('REFERENCE'):return e.get('REFERENCE')
    return ''

def ler(path):
    with open(path, 'rb') as arquivo:
        original = arquivo.read()
    root=ET.fromstring(original); mods=OrderedDict(); comps=OrderedDict(); cores={}; pux=OrderedDict(); ferr=OrderedDict(); qt={}
    mods_porta=set(); mats_porta={}; avulsas=[]; euronobre=[]
    for cat in root.iter('CATEGORY'):
        items=cat.find('ITEMS')
        if items is None:continue
        cn=(cat.get('DESCRIPTION') or '').upper()
        for it in items.findall('ITEM'):
            a=it.attrib; U=a.get('ID','').upper(); d=a.get('DESCRIPTION',''); m=_modelo(it)
            if not m:
                for ch in it.iter('ITEM'):
                    if re.search(r'lat|bas',ch.get('ID',''),re.I) and _modelo(ch):m=_modelo(ch);break
            if 'EUR_' in U and '_POR_' in U:
                mat='aluminio' if '_ALU' in U or '_METAL' in U else 'espelho' if '_ESP' in U or 'ESPELHO' in U else 'vidro'
                try:dim=tuple(float(a.get(k,0) or 0) for k in ('WIDTH','HEIGHT','DEPTH'))
                except (ValueError,TypeError):dim=(0,0,0)
                euronobre.append({'id':U,'desc':d,'dim':dim,'mat':mat});continue
            if 'EURONOBRE' in cn or 'PUX' in U:pux[d.split('(')[0].strip()]=1;continue
            if 'FERRAG' in cn:ferr[d.strip()]=1;continue
            if re.match(r'\s*cunha',d,re.I):continue
            if 'ACESS' in cn or U.startswith('ACE') or U.startswith('EUR_'):continue
            if '_POR_' in U or U.startswith('POR_'):
                if m:cores.setdefault('porta',OrderedDict())[m]=1
                mat='vidro' if any(x in U for x in ('GLA','VID','GLASS')) else 'espelho' if 'ESP' in U else 'aluminio' if any(x in U for x in ('ALU','METAL')) else 'mdf'
                try:dim=tuple(float(a.get(k,0) or 0) for k in ('WIDTH','HEIGHT','DEPTH'))
                except (ValueError,TypeError):dim=(0,0,0)
                avulsas.append({'id':U,'desc':d,'dim':dim,'mat':mat});continue
            desc=re.sub(r'\s+\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?mm\s*$','',d).strip()
            dim='x'.join(_fmt(float(a[k])) for k in ('WIDTH','HEIGHT','DEPTH')); qt[(desc,dim)]=qt.get((desc,dim),0)+int(float(a.get('QUANTITY') or 1))
            if U.startswith(('PAI','COM_COZ_DIV')):
                comps[(desc,dim)]=1
                if m:cores.setdefault('tamp',OrderedDict())[m]=1
                continue
            mods[(desc,dim)]=1
            if m:cores.setdefault('caixa',OrderedDict())[m]=1
            mat=None
            for ch in it.iter('ITEM'):
                cu=ch.get('ID','').upper()
                if not ('_POR_' in cu or cu.startswith('POR_')):continue
                refs=ch.find('REFERENCES')
                if refs is not None:
                    v=refs.find('VIDRO'); mt=refs.find('MAT')
                    if v is not None and v.get('REFERENCE',''):mat='vidro';break
                    if mt is not None and mt.get('REFERENCE',''):mat=mt.get('REFERENCE','').lower();break
                mat='mdf';break
            if mat is None and U=='GROUPENTITY':
                for ch in it.iter('ITEM'):
                    refs=ch.find('REFERENCES'); dob=refs.find('DOBRADICA') if refs is not None else None
                    if dob is not None and dob.get('REFERENCE',''):mat='mdf';break
            if mat is not None:mods_porta.add((desc,dim));mats_porta[(desc,dim)]=mat
    materiais, ordem, dimensoes_portas, avisos = {}, {}, [], []
    for e in root.iter('ITEM'):
        referencia = next((g for ch in e if ch.tag != 'ITEM' for g in ch if g.tag == 'MODEL'), None)
        if referencia is not None and referencia.get('REFERENCE'):
            try:
                k = tuple(sorted(round(float(e.get(a))) for a in ('WIDTH', 'HEIGHT', 'DEPTH')))
            except (TypeError, ValueError, OverflowError):
                avisos.append({'id': e.get('ID', ''), 'campo': 'dimensoes_material'})
            else:
                nome = referencia.get('REFERENCE')
                materiais.setdefault(k, Counter())[nome] += 1
                if e.get('COMPONENT') == 'Y' and e.get('UNIQUEPARENTID') == '-2':
                    ordem.setdefault(k, []).append(nome)
        iid = (e.get('ID') or '').upper()
        if iid.startswith('POR_') or '_POR_' in iid:
            try:
                k = tuple(sorted(round(float(e.get(a).replace(',', '.'))) for a in ('WIDTH', 'HEIGHT', 'DEPTH')))
            except (AttributeError, TypeError, ValueError, OverflowError):
                avisos.append({'id': iid, 'campo': 'dimensoes_porta'})
            else:
                if k not in dimensoes_portas:
                    dimensoes_portas.append(k)
    return {'linhas':list(mods)+list(comps),'quantidades':qt,'cores':cores,'puxadores':list(pux),'ferragens':list(ferr),
            'modulos_com_porta':mods_porta,'materiais_porta':mats_porta,'portas_avulsas':avulsas,'portas_euronobre':euronobre,
            'materiais_dimensoes': materiais, 'ordem_materiais': ordem, 'dimensoes_portas': dimensoes_portas,
            'puxador_tipo': _puxador_tipo(root), 'especificacoes': _especificacoes(root),
            'sha256': hashlib.sha256(original).hexdigest(), 'avisos': avisos}


def _puxador_tipo(root):
    for e in root.iter('ITEM'):
        d = e.get('DESCRIPTION', '')
        if not d.lower().startswith('puxador'):
            continue
        if re.search(r'perfil|cava|aba|embutid|usinad', d, re.I):
            return None
        try:
            largura = float(e.get('WIDTH') or 150)
        except (TypeError, ValueError):
            largura = 150.0
        nome = d.lower()
        cor = ((0.80, 0.70, 0.52) if 'champ' in nome else
               (0.83, 0.68, 0.33) if ('dourad' in nome or 'ouro' in nome) else
               (0.12, 0.12, 0.12) if 'preto' in nome else
               (0.62, 0.52, 0.46) if 'rose' in nome else (0.74, 0.74, 0.76))
        return dict(L=max(60.0, min(largura, 1200.0)), cor=cor)
    return None


def _especificacoes(root):
    """Regras existentes da prancha 3; interpreta o XML uma vez, sem I/O adicional."""
    lim = lambda t: re.sub(r'[^\w)\]]+$', '', re.sub(r'\s+', ' ', t or '')).strip()
    cores, espessuras = {}, {}
    def add(cl, cor, esp):
        cores.setdefault(cl, Counter())[cor] += 1
        espessuras.setdefault(cl, set()).add(esp)
    for it in root.iter('ITEM'):
        items = it.find('ITEMS')
        if items is None: continue
        ch = [c for c in items.findall('ITEM') if re.match(r'Chapa .+ Espessura', c.get('DESCRIPTION', ''))]
        if not ch: continue
        m = re.match(r'Chapa (.+?) Espessura ([\d.,]+)\s*mm', ch[0].get('DESCRIPTION'))
        if not m: continue
        cor, esp = m.group(1).strip(), _fmt(float(m.group(2).replace(',', '.')))
        iid, desc = (it.get('ID') or '').lower(), (it.get('DESCRIPTION') or '')
        if re.search(r'(^|_)por_', iid): add('porta', cor, esp)
        elif '_gav' in iid: continue
        elif re.search(r'tamponamento', desc, re.I): add('tamp', cor, esp)
        elif re.search(r'afastador', desc, re.I): add('caixa', cor, esp)
        elif re.search(r'painel|tampo', desc, re.I) or re.search(r'(^|_)(tam|tampo)(_|$)', iid): add('painel', cor, esp)
        elif '_pra' in iid or re.match(r'prat', desc, re.I): add('prat', cor, esp)
        elif '_fun' in iid: espessuras.setdefault('fundo', set()).add(esp)
        else: add('caixa', cor, esp)
    todos = [(it.get('DESCRIPTION') or '', it) for it in root.iter('ITEM')]
    nomes = lambda rx: list(OrderedDict((lim(d), 1) for d, _ in todos if re.search(rx, d, re.I)))
    pux_n, pux_c = [], []
    for desc, it in todos:
        if re.match(r'puxador', desc, re.I):
            refs = {g.tag: g.get('REFERENCE') for g in (it.find('REFERENCES') or [])}
            nome = lim(desc); largura = refs.get('LARGURA')
            if largura and largura + 'mm' not in nome: nome += f' - {largura}mm'
            if nome not in pux_n: pux_n.append(nome)
            acabamento = lim(refs.get('DESC_ACA_PER', ''))
            if acabamento and acabamento not in pux_c: pux_c.append(acabamento)
    esp_nome = lambda d: re.sub(r'\s*[\d.,]+\s*mm$', '', d).strip()
    especiais = list(OrderedDict((esp_nome(lim(d)), 1) for d, it in todos if it.get('COMPONENT') == 'Y' and re.search(r'pist|articulad|aventos|basculant|trilho|cabideiro tubo|lixeira|cesto|porta.?tempero|sapateira|calceiro|gaveteiro aramado', d, re.I)))
    cor = lambda k: ', '.join(c for c, _ in cores.get(k, Counter()).most_common())
    mm = lambda k: ' e '.join(f'{e}mm' for e in sorted(espessuras.get(k, ()), key=lambda t: float(t.replace(',', '.'))))
    caixa = mm('caixa') + (f" (fundo {mm('fundo')})" if espessuras.get('fundo') else '')
    return [('ESPECIFICAÇÕES DO PROJETO', None), ('CORES E ACABAMENTOS:', None),
            ('Caixa Módulos (Interno)', cor('caixa')), ('Portas e Frentes', cor('porta')), ('Tamponamentos', cor('tamp')),
            ('Painéis e Tampos', cor('painel')), ('Puxadores', ', '.join(pux_c)), ('Portas de Vidro', ', '.join(nomes(r'vidro|espelho'))),
            ('FERRAGENS E ACESSÓRIOS:', None),
            ('Dobradiças', ', '.join(nomes(r'^dobradi'))), ('Corrediças', ', '.join(nomes(r'corredi'))),
            ('Puxadores', ', '.join(pux_n)), ('Ferragens especiais', ', '.join(especiais)),
            ('ESPESSURAS:', None),
            ('Caixa Módulos (Interno)', caixa), ('Prateleiras internas', mm('prat')), ('Portas e Frentes', mm('porta')),
            ('Tamponamentos', mm('tamp')), ('Painéis e Tampos e perfil', mm('painel'))]
