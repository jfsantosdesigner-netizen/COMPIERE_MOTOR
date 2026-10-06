# GERADOR DE CADERNO v2 — Compiere. Um comando: python gerar_caderno.py config.json
# XML/listagem -> DXF (posição real) -> vistas automáticas -> listagem por vista + balões -> elevações com cotas -> PDF + QUALIDADE
import sys, os, re, json, subprocess, xml.etree.ElementTree as ET
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf as fz, geo
from normal.vidros import estilo, faces_porta
from camera_comum import posicionar, obstaculos, enquadrar, cantos
from cotas_comum import contornos, vaos_prateleiras, assinatura_vaos


cfg = json.load(open(sys.argv[1], encoding='utf-8'))
XML_TREE = ET.parse(cfg['xml'])
# REGRA (v27): PROIBIDO puxar listagem/imagens de PDF — tudo sai do XML + DXF
for _k in ('listagem_pdf', 'imagens', 'capa_img'): cfg.pop(_k, None)
AREA = fz.Rect(19, 142, 823, 577); IN = 7
RED = (0.545, 0, 0); CR = (0.9, 0, 0); PRETO = (0, 0, 0)
BRANCO = (1, 1, 1); MADEIRA = (0.80, 0.63, 0.42); CINZA = (0.93, 0.93, 0.93)
MM = 72 / 25.4
# REGRA (João, 28/09/2026): threshold "40%" que decide se uma face frontal esta COBERTA (=tem porta/frente,
# nao e nicho) ou ABERTA (=nicho). Usado em 3 lugares: _tem_frente_solto(), tem_porta(), nichos().
# Ajustar aqui muda o comportamento das 3 regras de uma vez. Valor original era 0.4 hardcoded.
NICHO_MIN_RATIO = 0.4
ESC = [15, 20, 25, 30, 40, 50, 75, 100, 125, 150]
ESC_COTA = [10, 12.5, 15, 20, 25, 30, 40, 50, 75, 100]   # v15: elevação de cotas usa a maior escala que cabe   # 1:15 e 1:20 só para móvel/parede pequena (ver escala_para)
FV = {'x+': (1, 0), 'x-': (-1, 0), 'y+': (0, 1), 'y-': (0, -1)}
AREA_IN = fz.Rect(AREA.x0 + IN, AREA.y0 + IN, AREA.x1 - IN, AREA.y1 - IN)   # regra: nada encosta no quadro

def fmt(v):
    v = round(v * 2) / 2
    return str(int(round(v))) if abs(v - round(v)) < 0.01 else ('%.1f' % v).replace('.', ',')

# ---------------- entrada ----------------
def modelo(it):
    refs = it.find('REFERENCES')
    if refs is None: return ''
    for tag in ('MODEL', 'COR', 'MAT'):
        e = refs.find(tag)
        if e is not None and e.get('REFERENCE'): return e.get('REFERENCE')
    return ''

import integridade
FONTES_XML = {}
QT = {}
def ler_xml(path):
    root = XML_TREE.getroot() if path == cfg['xml'] else ET.parse(path).getroot()
    mods, comps, cores, pux, ferr = OrderedDict(), OrderedDict(), {}, OrderedDict(), OrderedDict()
    mods_com_porta = set()  # (desc, dim) de módulos com sub-item _POR_ no XML (porta de vidro não exportada no DXF)
    mods_porta_mat = {}    # (desc, dim) → material da porta lido do XML: 'vidro', 'mdf', 'mdp', etc.
    por_avulsas = []       # 005.A: POR_* com material inferido do ID (vidro/espelho/alumínio/mdf) e dimensões
    por_euronobre = []     # 005.A: EUR_*_POR_* (porta Euronobre pronta) com material e dimensões
    for cat in root.iter('CATEGORY'):
        items = cat.find('ITEMS')
        if items is None: continue
        cn = (cat.get('DESCRIPTION') or '').upper()
        for it in items.findall('ITEM'):
            a = it.attrib; U = a.get('ID', '').upper(); d = a.get('DESCRIPTION', ''); m = modelo(it)
            if not m:
                for ch in it.iter('ITEM'):
                    if re.search(r'lat|bas', ch.get('ID', ''), re.I) and modelo(ch): m = modelo(ch); break
            if 'EUR_' in U and '_POR_' in U:
                # 005.A.1: porta Euronobre pronta — material inferido do ID
                _me = 'vidro'  # EU32, EU_GLA, EU_VID → vidro (default p/ Euronobre)
                if '_ALU' in U or '_METAL' in U: _me = 'aluminio'
                elif '_ESP' in U or 'ESPELHO' in U: _me = 'espelho'
                try: _pw = float(a.get('WIDTH', 0) or 0); _ph = float(a.get('HEIGHT', 0) or 0); _pd = float(a.get('DEPTH', 0) or 0)
                except (ValueError, TypeError): _pw = _ph = _pd = 0
                por_euronobre.append({'id': U, 'desc': d, 'dim': (_pw, _ph, _pd), 'mat': _me, 'visual': estilo(it)})
                continue
            if 'EURONOBRE' in cn or 'PUX' in U: pux[d.split('(')[0].strip()] = 1; continue
            if 'FERRAG' in cn: ferr[d.strip()] = 1; continue
            if re.match(r'\s*cunha', d, re.I): continue   # REGRA (v26, João): barrote/cunha não faz parte, lista só material
            if 'ACESS' in cn or U.startswith('ACE') or U.startswith('EUR_'): continue
            if '_POR_' in U or U.startswith('POR_'):   # REGRA (v26): porta avulsa do XML (POR_INF_CUR) = porta, não entra na listagem
                if m: cores.setdefault('porta', OrderedDict())[m] = 1
                # 005.A.2: material inferido pelo ID da porta avulsa (vidro/espelho/alumínio/mdf)
                _ma = 'mdf'
                if 'GLA' in U or 'VID' in U or 'GLASS' in U: _ma = 'vidro'
                elif 'ESP' in U or 'ESPELHO' in U: _ma = 'espelho'
                elif 'ALU' in U or 'METAL' in U: _ma = 'aluminio'
                try: _pw = float(a.get('WIDTH', 0) or 0); _ph = float(a.get('HEIGHT', 0) or 0); _pd = float(a.get('DEPTH', 0) or 0)
                except (ValueError, TypeError): _pw = _ph = _pd = 0
                por_avulsas.append({'id': U, 'desc': d, 'dim': (_pw, _ph, _pd), 'mat': _ma, 'visual': estilo(it)})
                continue
            desc = re.sub(r'\s+\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?mm\s*$', '', d).strip()
            dim = 'x'.join(fmt(float(a[k])) for k in ('WIDTH', 'HEIGHT', 'DEPTH'))
            FONTES_XML[(desc, dim)] = integridade.fonte(it)
            qq = int(float(a.get('QUANTITY') or 1)); QT[(desc, dim)] = QT.get((desc, dim), 0) + qq
            if U.startswith(('PAI', 'COM_COZ_DIV')):
                comps[(desc, dim)] = 1
                if m: cores.setdefault('tamp', OrderedDict())[m] = 1
            else:
                mods[(desc, dim)] = 1
                if m: cores.setdefault('caixa', OrderedDict())[m] = 1
                # REGRA (vidro): sub-item _POR_ no XML mas sem DXF = porta ausente; marca para tem_porta não classificar como nicho.
                # Material lido do XML: tag VIDRO (com REFERENCE) → 'vidro'; tag MAT → valor lido (ex.: 'mdf', 'mdp').
                _mat_porta = None
                for _ch in it.iter('ITEM'):
                    _cu = _ch.get('ID', '').upper()
                    if not ('_POR_' in _cu or _cu.startswith('POR_')): continue
                    _refs = _ch.find('REFERENCES')
                    if _refs is not None:
                        _v = _refs.find('VIDRO')
                        if _v is not None and _v.get('REFERENCE', ''):
                            _mat_porta = 'vidro'; break        # porta de vidro/alumínio (ex.: Euronobre)
                        _mt = _refs.find('MAT')
                        if _mt is not None and _mt.get('REFERENCE', ''):
                            _mat_porta = _mt.get('REFERENCE', '').lower(); break   # ex.: 'mdf', 'mdp'
                    _mat_porta = 'mdf'; break                  # POR_ sem tags de material → assume MDF
                # A2 (v36, GROUPENTITY/DOBRADICA): módulo com ID='GROUPENTITY' sem _POR_ no XML
                # mas com sub-item de dobradiça (REFERENCES/DOBRADICA preenchida) → tem porta de dobradiça.
                if _mat_porta is None and U == 'GROUPENTITY':
                    for _ch in it.iter('ITEM'):
                        _refs = _ch.find('REFERENCES')
                        if _refs is None: continue
                        _dob = _refs.find('DOBRADICA')
                        if _dob is not None and _dob.get('REFERENCE', ''):
                            _mat_porta = 'mdf'; break
                if _mat_porta is not None:
                    mods_com_porta.add((desc, dim))
                    mods_porta_mat[(desc, dim)] = _mat_porta
    return list(mods) + list(comps), cores, list(pux), list(ferr), mods_com_porta, mods_porta_mat, por_avulsas, por_euronobre

linhas_xml, cores, puxs, ferrs, mods_com_porta, mods_porta_mat, por_avulsas, por_euronobre = ler_xml(cfg['xml'])
linhas = linhas_xml

pj = cfg['pecas_json']
# REGRA (v27): a leitura guardada do DXF só vale se o DXF for o MESMO (confere pelo hash); mudou -> lê de novo
import hashlib as _hl
_hx = _hl.md5(open(cfg['dxf'], 'rb').read()).hexdigest() if cfg.get('dxf') and os.path.exists(cfg['dxf']) else ''
if os.path.exists(pj) and _hx and (not os.path.exists(pj + '.md5') or open(pj + '.md5').read().strip() != _hx): os.remove(pj)
if not os.path.exists(pj) and _hx: open(pj + '.md5', 'w').write(_hx)
if not os.path.exists(pj):
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'dxf_pecas(motor core).py'), cfg['dxf'], pj], check=True)
P = geo.carregar(pj)
# Engenharia: XML e DXF são fontes complementares do mesmo projeto.
# Divergência dimensional não é corrigida nem tolerada automaticamente:
# a integridade deve interromper a geração e expor o erro de leitura/processamento.
import math
def _n(a, b, c):
    if len(set((a, b, c))) < 3: return (0, 0, 1)
    e1 = [b[k] - a[k] for k in range(3)]; e2 = [c[k] - a[k] for k in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]); m = math.sqrt(sum(x * x for x in n)) or 1
    return tuple(x / m for x in n)
def preparar(P):
    # REGRA: imagem limpa - cada peça é desenhada como caixa reta (só as bordas, sem triangulação)
    for p_ in P:
        x0, y0, z0, x1, y1, z1 = p_['bb']
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
        N = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
        p_['fq'] = [[[c[i] for i in f_], n_, [True] * 4] for f_, n_ in zip(F, N)]
preparar(P)

# ===== CORES REAIS: XML (cor de cada peça) -> pasta MATERIAIS (textura) -> cor média =====
import unicodedata as _ud, collections as _col, xml.etree.ElementTree as _ET2
def _norm(t):
    t = _ud.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()
_MD = os.path.dirname(os.path.abspath(__file__))
# REGRA (v23, João): o motor procura as cores/texturas SOZINHO, primeiro na pasta MATERIAIS dentro
# do próprio motor, depois no caminho que vier no config.
# REGRA (v34, João): o motor NÃO busca referência fora dele. Material vem da pasta MATERIAIS
# dentro do próprio motor ou do caminho que o config mandar. Nenhum caminho de máquina no código.
_MAT = next((c_ for c_ in (os.path.join(_MD, 'MATERIAIS'),
                           (cfg.get('materiais') if cfg.get('materiais') and os.path.isabs(cfg.get('materiais')) else os.path.join(_MD, cfg.get('materiais') or 'MATERIAIS')))
             if os.path.isdir(c_)), os.path.join(_MD, 'MATERIAIS'))
_MI = os.path.join(_MD, 'materiais_index.json')
_MC = os.path.join(_MD, 'materiais_cores.json')  # [caminho relativo a MATERIAIS, nome, [r,g,b]]: cores prontas, dispensa a pasta MATERIAIS
_rgbx = {}
if not cfg.get('fontes_frescas') and os.path.exists(_MC):
    _idx = []
    for rel_, st_, rgb_ in json.load(open(_MC, encoding='utf-8')):
        _idx.append([os.path.join(_MAT, rel_), st_]); _rgbx[_idx[-1][0]] = rgb_
elif not cfg.get('fontes_frescas') and os.path.exists(_MI): _idx = json.load(open(_MI, encoding='utf-8'))
else:
    _idx = []
    for fonte_material in (_MAT, os.path.join(_MD, 'texturas')):
        for d_, ds_, fs_ in os.walk(fonte_material):
            for f_ in fs_:
                if f_.lower().endswith(('.jpg', '.jpeg', '.png')): _idx.append([os.path.join(d_, f_), _norm(os.path.splitext(f_)[0])])
    json.dump(_idx, open(_MI, 'w', encoding='utf-8'))
_CC = os.path.join(_MD, 'cores_cache.json')
_cc = json.load(open(_CC, encoding='utf-8')) if not cfg.get('fontes_frescas') and os.path.exists(_CC) else {}
_PREF = ('duratex', 'arauco', 'guararapes', 'berneck', 'eucatex', 'masisa', 'stelben')
def _parecido(a, b):
    # REGRA (v15): nome do XML com letra a mais/a menos ou cortado ("Metallic Sued" = "Metalic Suede")
    if a == b: return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)) and abs(len(a) - len(b)) <= 2: return True
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 5: return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]: i += 1
    return a[i + 1:] == b[i + 1:] or a[i + 1:] == b[i:] or a[i:] == b[i + 1:]
def cor_material(nome):
    if not nome: return None
    if _cc.get(nome): return tuple(_cc[nome][0])   # 'sem textura' antigo não bloqueia nova busca
    tk = _norm(nome).split(); best = None
    for cand in ([tk] + ([tk[:-1]] if len(tk) > 1 else [])):
        n = ' '.join(cand)
        for path_, st in _idx:
            ws = st.split()
            if st == n: sc = 100
            elif all(t in ws for t in cand): sc = 60 - len(ws)
            elif len(ws) == len(cand) and all(any(_parecido(t, w_) for w_ in ws) for t in cand): sc = 40 - len(ws)
            else: continue
            pl = path_.lower(); sc += sum(5 for w in _PREF if w in pl) + (2 if '\\fabrica\\' in pl else 0)
            if best is None or sc > best[0]: best = (sc, path_)
        if best: break
    rgb = tuple(_rgbx[best[1]]) if best and _rgbx.get(best[1]) else None
    if best and not rgb:
        try:
            px = fz.Pixmap(best[1])
            if px.colorspace is None or px.colorspace.n != 3: px = fz.Pixmap(fz.csRGB, px)
            if px.alpha: px = fz.Pixmap(px, 0)
            sm = px.samples; npx = len(sm) // 3; st_ = max(1, npx // 6000); r = g = b = c = 0
            for i_ in range(0, npx, st_): r += sm[3 * i_]; g += sm[3 * i_ + 1]; b += sm[3 * i_ + 2]; c += 1
            rgb = (r / c / 255, g / c / 255, b / c / 255)
        except Exception: rgb = None
    _cc[nome] = [list(rgb), best[1]] if rgb else None
    json.dump(_cc, open(_CC, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return rgb
# ===== TEXTURAS REAIS (veio da madeira) no 3D: imagem do material aplicada em perspectiva em cada face =====
try:
    from PIL import Image as _Im, ImageDraw as _ImD
    import numpy as _np
except Exception:
    _Im = None
_TXD = os.path.join(_MD, 'texturas')              # ASSET oficial, versionado: o motor SÓ LÊ, nunca escreve
_TXC = os.path.join(_MD, '_cache_texturas')       # miniatura derivada do MATERIAIS (no .gitignore)
_txc = {}
def textura(nome):
    # REGRA (v32, João): a pasta texturas/ é ENTRADA do motor, não cache. Ela nunca é reescrita pela
    # rodada — assim os binários ficam idênticos em qualquer máquina, o 'git status' para de acusar
    # imagem modificada e rodada fria e rodada quente usam exatamente os mesmos inputs visuais.
    # Miniatura gerada a partir do MATERIAIS vai para _cache_texturas/, fora do versionamento.
    if _Im is None or not nome: return None
    if nome in _txc: return _txc[nome]
    im = None; ref = (_cc.get(nome) or [None, None])[1]
    if ref:
        fn = ref.replace('\\', '/').split('/')[-1].lower()
        ofi = os.path.join(_TXD, fn)              # asset oficial
        cch = os.path.join(_TXC, fn)              # cache derivado
        try:
            if os.path.exists(ofi): im = _Im.open(ofi).convert('RGB')
            elif not cfg.get('fontes_frescas') and os.path.exists(cch): im = _Im.open(cch).convert('RGB')
            else:
                full = ref if os.path.exists(ref) else os.path.join(_MAT, ref.split('MATERIAIS', 1)[-1].lstrip('/\\'))
                if os.path.exists(full):
                    im = _Im.open(full).convert('RGB'); im.thumbnail((1024, 1024))
                    os.makedirs(_TXC, exist_ok=True); im.save(cch, quality=82)
        except Exception: im = None
    _txc[nome] = im; return im
_dm = {}; _ord = {}
for e in XML_TREE.iter('ITEM'):
    m_ = next((g for ch in e if ch.tag != 'ITEM' for g in ch if g.tag == 'MODEL'), None)
    if m_ is None or not m_.get('REFERENCE'): continue
    try: k_ = tuple(sorted(round(float(e.get(a))) for a in ('WIDTH', 'HEIGHT', 'DEPTH')))
    except Exception: continue
    _dm.setdefault(k_, _col.Counter())[m_.get('REFERENCE')] += 1
    if e.get('COMPONENT') == 'Y' and e.get('UNIQUEPARENTID') == '-2': _ord.setdefault(k_, []).append(m_.get('REFERENCE'))
# Peças soltas de MESMA medida e cores diferentes (ex.: 2 tamponamentos 2350x18x70, um Preto e um Chumbo):
# o DXF traz as camadas na ordem inversa do XML -> casa pela ordem.
_fixa = {}; _gp = {}
for p_ in P: _gp.setdefault(tuple(sorted(round(x) for x in p_['dim'])), []).append(p_)
for k_, refs_ in _ord.items():
    g_ = _gp.get(k_, [])
    if len(set(refs_)) > 1 and len(g_) == len(refs_):
        for p_, r_ in zip(sorted(g_, key=lambda t: t['i']), reversed(refs_)): _fixa[p_['i']] = r_
_nc = 0; _usadas = _col.Counter()
for p_ in P:
    k_ = tuple(sorted(round(x) for x in p_['dim'])); c_ = _dm.get(k_)
    if p_['i'] in _fixa: c_ = _col.Counter({_fixa[p_['i']]: 1})
    if not c_:
        for dd in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)):
            c_ = _dm.get(tuple(sorted(a + b for a, b in zip(k_, dd))))
            if c_: break
    if c_:
        nm_ = c_.most_common(1)[0][0]; rgb = cor_material(nm_)
        if rgb: p_['rgb'] = rgb; p_['mat'] = nm_; _nc += 1; _usadas[nm_] += 1
print('CORES: %d pecas coloridas pelo MATERIAIS (medidas no XML: %d)' % (_nc, len(_dm)))
TEX_FALTA = [m_ for m_ in _usadas if _cc.get(m_) and not any(os.path.exists(os.path.join(d_, _cc[m_][1].replace('\\', '/').split('/')[-1].lower())) for d_ in (_TXD, _TXC))]
for nm_, q_ in _usadas.most_common(): print('   %-22s %4d pecas <- %s' % (nm_, q_, os.path.relpath(_cc[nm_][1], _MAT)))
_todas_mats = {r_ for c_ in _dm.values() for r_ in c_}
for nm_ in [k for k, v in _cc.items() if not v and k in _todas_mats]: print('   SEM TEXTURA:', nm_)
inst = geo.casar(P, linhas, QT, FONTES_XML)

# Nova regra: tolera no máximo três ocorrências obrigatórias ausentes no casamento.
# A geometria é reconstruída na posição da melhor evidência DXF, mas SEMPRE com
# as dimensões declaradas no XML. Acima de três faltas, a integridade bloqueia.
def _reproduzir_faltantes_xml():
    import itertools
    usados = {pi for it in inst for pi in it['pecas']}
    conf = integridade.conferir(linhas, QT, inst)
    faltas = [(it['n'], it['descricao'], it['dimensoes_xml'],
               it['quantidade_xml'] - it['quantidade_dxf'])
              for it in conf['itens'] if it['status'] == 'FALHA']
    total = sum(max(0, q) for _, _, _, q in faltas)
    if not total or total > 3:
        return
    for n_, desc_, dm_, qtd_ in faltas:
        alvo = geo.parse_dim(dm_)
        for _ in range(qtd_):
            candidatos = []
            for pc in P:
                if pc['i'] in usados:
                    continue
                melhor = min((sum(abs(a-b) for a,b in zip(perm, pc['dim'])),
                              sum(abs(a-b) <= 3 for a,b in zip(perm, pc['dim'])), perm)
                             for perm in itertools.permutations(alvo))
                if melhor[1] >= 2:
                    candidatos.append((melhor[0], pc, melhor[2]))
            if not candidatos:
                continue
            _, base_, eixos_ = min(candidatos, key=lambda x: x[0])
            centro = [(base_['bb'][k] + base_['bb'][k+3]) / 2 for k in range(3)]
            bb_ = [centro[k] - eixos_[k] / 2 for k in range(3)] + [centro[k] + eixos_[k] / 2 for k in range(3)]
            novo_ = dict(base_)
            novo_.update(i=len(P), dim=list(eixos_), bb=bb_, faces=[], _sintetica_xml=True)
            P.append(novo_); preparar([novo_]); usados.add(base_['i']); usados.add(novo_['i'])
            tipo_ = 'comp' if geo.eh_componente(desc_) or min(alvo) <= 26 else 'mod'
            inst.append(dict(n=n_, desc=desc_, dim=dm_, bb=bb_, tipo=tipo_,
                             pecas=[novo_['i']], sintetica_xml=True))
            print('XML/DXF: peça reconstruída no render pela medida XML | %s | %s' % (desc_, dm_))

_reproduzir_faltantes_xml()
INTEGRIDADE = integridade.conferir(linhas, QT, inst)
nao_achados = [(i["descricao"], i["dimensoes_xml"]) for i in INTEGRIDADE["itens"] if i["quantidade_dxf"] == 0]
_acessorios = [(i["descricao"], i["dimensoes_xml"]) for i in INTEGRIDADE["itens"] if i["status"] == "DISPENSADO"]
_faltando_real = [(i["descricao"], i["dimensoes_xml"]) for i in INTEGRIDADE["itens"] if i["status"] == "FALHA"]
_integridade_path = os.path.splitext(cfg["saida"])[0] + "_INTEGRIDADE.json"
json.dump(INTEGRIDADE, open(_integridade_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for _item in INTEGRIDADE["itens"]:
    print("INTEGRIDADE: %s | %s | XML=%s DXF=%s | %s" % (_item["status"], _item["descricao"], _item["quantidade_xml"], _item["quantidade_dxf"], _item["dimensoes_xml"]))
if not INTEGRIDADE["aprovado"]:
    print("ERRO CRITICO: integridade XML/DXF reprovada. Caderno bloqueado; nenhuma peça obrigatória pode ser omitida.", file=sys.stderr)
    raise SystemExit(2)
# 005.A.3 (v37): casa porta avulsa (POR_* vidro/espelho/alumínio) e porta Euronobre (EUR_*_POR_*)
# com módulo cuja W×H batem (tolerância 15 mm). Sobrepõe o chute A2 (dobradiça=mdf) quando o material
# da porta é vidro/espelho/alumínio.
for _i in inst:
    if _i['tipo'] != 'mod': continue
    _wm, _hm, _dm = geo.parse_dim(_i['dim'])
    _mod_lado = sorted([_wm, _hm])[::-1]  # [maior, menor] entre W e H
    for _p in (por_euronobre + por_avulsas):
        _pdims = sorted([_p['dim'][0], _p['dim'][1], _p['dim'][2]])[::-1]  # ignora a menor (profundidade)
        _por_lado = _pdims[:2]
        if abs(_por_lado[0] - _mod_lado[0]) <= 15 and abs(_por_lado[1] - _mod_lado[1]) <= 15:
            mods_com_porta.add((_i['desc'], _i['dim']))
            mods_porta_mat[(_i['desc'], _i['dim'])] = _p['mat']
            if _p['mat'] in ('vidro','espelho','aluminio'): _i['_porta_visual']=_p['visual']
            break
# REGRA (vidro): módulos com porta ausente do DXF (sub-item _POR_ no XML) marcados aqui para tem_porta reconhecer.
# xml_mat_porta: material lido do XML ('vidro', 'mdf', 'mdp', ...) — usado na face sintética para cor correta.
for _i in inst:
    if _i['tipo'] == 'mod' and (_i.get('desc', ''), _i.get('dim', '')) in mods_com_porta:
        _i['xml_tem_porta'] = True
        _i['xml_mat_porta'] = mods_porta_mat.get((_i.get('desc', ''), _i.get('dim', '')), 'mdf')
from normal.regras import preparar_itens
preparar_itens(globals())
paredes = geo.definir_paredes(inst, P)
# REGRA: mesma parede com módulos de profundidades diferentes (ex.: armário raso 200 mm + balcão 600 mm)
# = UMA parede só. Junta paredes do mesmo lado com planos a até 600 mm e trechos que se tocam/sobrepõem.
def _juntar_paredes(paredes):
    mudou = True
    while mudou:
        mudou = False
        for a in paredes:
            for b in paredes:
                if a is b or a['key'] != b['key'] or abs(a['plano'] - b['plano']) > 600: continue
                ax = 1 if FV[a['key']][0] else 0
                ra = (min(i['bb'][ax] for i in a['itens']), max(i['bb'][ax + 3] for i in a['itens']))
                rb = (min(i['bb'][ax] for i in b['itens']), max(i['bb'][ax + 3] for i in b['itens']))
                if ra[1] < rb[0] - 100 or rb[1] < ra[0] - 100: continue
                sg = FV[a['key']][1 - ax]
                a['plano'] = max(a['plano'] * sg, b['plano'] * sg) * sg   # plano mais "no fundo"
                a['itens'] += b['itens']; paredes.remove(b); mudou = True; break
            if mudou: break
    for w in paredes:
        w['id'] = f"{w['key']}@{round(w['plano'])}"
        for it in w['itens']: it['parede'] = w['id']
    return paredes
paredes = _juntar_paredes(paredes)
# AMBIENTE (referência, NUNCA cotado): peças do DXF que não são móvel do XML nem parede/piso.
# Hoje: PEDRA / bancada / rodabanca = placa horizontal (15–100 mm) na altura da bancada (700–1100 mm).
# Desenhada com as faces reais do DXF (pedra em L sai em L).
_usadas = {pi for i in inst for pi in i['pecas']}
# REGRA (v26): peça do DXF que NÃO está na listagem e ocupa o MESMO lugar de uma peça listada (cópia do painel,
# ex.: painel usinado 1580 sobre o painel 1530 da lista) = duplicada -> não é desenhada (cobria o painel de cinza).
def _vol(b): return max(0, b[3] - b[0]) * max(0, b[4] - b[1]) * max(0, b[5] - b[2])
def _vol_int(A, B): return _vol([max(A[0], B[0]), max(A[1], B[1]), max(A[2], B[2]), min(A[3], B[3]), min(A[4], B[4]), min(A[5], B[5])]) if all(min(A[k + 3], B[k + 3]) > max(A[k], B[k]) for k in range(3)) else 0
_bb_list = [P[pi]['bb'] for pi in _usadas]
DUP_I = {p_['i'] for p_ in P if p_['i'] not in _usadas and _vol(p_['bb']) > 0 and sorted(p_['dim'])[1] >= 50
         and any(_vol_int(p_["bb"], b_) >= 0.8 * max(_vol(p_["bb"]), _vol(b_)) for b_ in _bb_list)}
if DUP_I: print('PEÇAS DUPLICADAS NO DXF (não desenhadas):', len(DUP_I))
PEDRA_COR = (0.16, 0.16, 0.17)
# REGRA (v33, João): parede e piso têm que LER como parede e piso - não podem se perder dentro do
# móvel. O móvel branco e (0.97,0.97,0.97); a parede era (0.94,0.94,0.94), quase o mesmo tom.
# REGRA (João, 2026-09-28): parede "gelo" — cinza-branco levemente quente (R e G acima de B),
# nem cinza puro/frio nem branco puro. Reaplicado após reversão (edição perdida em backup anterior).
PAREDE_COR = (0.95, 0.94, 0.91)
PISO_COR = (0.78, 0.78, 0.80)
AMB = [p_ for p_ in P if p_['i'] not in _usadas and p_['faces'] and 15 <= p_['dim'][2] <= 100
       and max(p_['dim'][0], p_['dim'][1]) >= 500 and min(p_['dim'][0], p_['dim'][1]) >= 250 and 700 <= p_['bb'][2] <= 1100]
AMB_I = {p_['i'] for p_ in AMB}
# PAREDES REAIS do DXF (com vãos de janela/porta quando vierem): peça vertical, espessura 60–400 mm, não casada com móvel.
# PAREDES EM PEÇA ÚNICA (alguns DXF trazem a sala inteira numa camada): usa as FACES reais, nunca a caixa.
MALHA_PAR = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['faces'] and p_['dim'][2] >= 1800
             and max(p_['dim'][0], p_['dim'][1]) >= 1000 and min(p_['dim'][0], p_['dim'][1]) > 400]
MALHA_I = {p_['i'] for p_ in MALHA_PAR}
for p_ in MALHA_PAR: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
# REGRA (João, 28/09/2026 - skill V1, bloco VISTAS): a vista nasce da PAREDE REAL do ambiente (malha LAYER1 do DXF),
# não do plano das costas do móvel. Módulo cujas costas NÃO encostam em parede real (vista-fragmento, ex.: módulo de
# canto girado no closet em U) é levado para a parede real em que ele encosta; as peças soltas que ficaram sem módulo
# vão junto com o módulo mais próximo. Módulo que já está com as costas numa parede real não muda (canto L continua
# na parede do lado das portas - V3). Sem parede real atrás em nenhum lado = ilha/solto: não muda (P4).
# Sem malha de parede no DXF: nada muda (lógica anterior).
def _faces_parede_real():
    out = []   # (eixo 'x'|'y', coordenada, a0, a1)
    fontes = list(MALHA_PAR) + [p_ for p_ in P if p_['i'] not in _usadas and p_['dim'][2] >= 1800
                                and 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
    for p_ in fontes:
        fcs = p_['faces'] if p_['i'] in MALHA_I else caixa_faces_(p_['bb'])
        for fc in fcs:
            xs = [v[0] for v in fc]; ys = [v[1] for v in fc]; zs = [v[2] for v in fc]
            if max(zs) - min(zs) < 1500: continue
            if max(xs) - min(xs) <= 1 and max(ys) - min(ys) >= 300: out.append(('x', sum(xs) / len(xs), min(ys), max(ys)))
            elif max(ys) - min(ys) <= 1 and max(xs) - min(xs) >= 300: out.append(('y', sum(ys) / len(ys), min(xs), max(xs)))
    # faces no MESMO plano (±10 mm) = uma parede só, de ponta a ponta: o vão de porta/janela não quebra a parede
    lin = []
    for e, c, a0, a1 in sorted(out):
        o = next((l for l in lin if l[0] == e and abs(l[1] - c) <= 10), None)
        if o is None: lin.append([e, c, a0, a1])
        else: o[2] = min(o[2], a0); o[3] = max(o[3], a1)
    return [tuple(l) for l in lin]
def caixa_faces_(b):
    x0, y0, z0, x1, y1, z1 = b
    return [[(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]]
def _parede_real_atras(it, key, FR, tol=80):
    b = it['bb']; ax = 'x' if key[0] == 'x' else 'y'; back = geo.plano(key, b)
    a0, a1 = (b[1], b[4]) if ax == 'x' else (b[0], b[3])
    best = None
    for e, c, r0, r1 in FR:
        if e != ax or abs(c - back) > tol: continue
        if min(a1, r1) - max(a0, r0) < 0.5 * (a1 - a0): continue
        if best is None or abs(c - back) < abs(best - back): best = c
    return best
_FR = _faces_parede_real()
if _FR:
    _movidos = []
    for w in list(paredes):
        for it in [i for i in w['itens'] if i['tipo'] == 'mod']:
            if _parede_real_atras(it, w['key'], _FR) is not None: continue      # já está numa parede real
            eixo = geo._ao_longo(it)
            pref = ('y-', 'y+') if eixo == 'x' else ('x-', 'x+')
            outros = tuple(k for k in ('x-', 'x+', 'y-', 'y+') if k not in pref)
            achou = None
            _b = it['bb']
            _quad = abs((_b[3] - _b[0]) - (_b[4] - _b[1])) <= 50   # módulo quadrado: o eixo do XML não decide o lado
            for grupo_ in ((pref, outros) if _quad else (pref,)):
                cands = [(abs(_parede_real_atras(it, k, _FR) - geo.plano(k, it['bb'])), k) for k in grupo_ if _parede_real_atras(it, k, _FR) is not None]
                if cands: achou = min(cands)[1]; break
            if achou is None: continue                                             # ilha / móvel solto
            w['itens'].remove(it); _movidos.append((it, achou))
    for it, k in _movidos:
        pl = geo.plano(k, it['bb'])
        alvo = next((o for o in paredes if o['key'] == k and not o.get('divisoria') and abs(o['plano'] - pl) <= 600), None)
        if alvo is None: alvo = dict(key=k, plano=pl, itens=[]); paredes.append(alvo)
        alvo['itens'].append(it); it['parede_key'] = k
        print(f"VISTA PELA PAREDE REAL: {it['desc']} {it['dim']} -> parede {k}")
    if _movidos:
        _mods_ = [i for w in paredes for i in w['itens'] if i['tipo'] == 'mod']
        for w in list(paredes):
            if any(i['tipo'] == 'mod' for i in w['itens']): continue
            if any(_parede_real_atras(i, w['key'], _FR) is not None for i in w['itens']): continue   # painel na parede real fica
            for it in list(w['itens']):
                m = min(_mods_, key=lambda m: geo.dist_caixas(it['bb'], m['bb']), default=None)
                if m is None or geo.dist_caixas(it['bb'], m['bb']) > 400: continue
                dono = next(o for o in paredes if m in o['itens'])
                w['itens'].remove(it); dono['itens'].append(it)
        paredes = [w for w in paredes if w['itens']]
        paredes = _juntar_paredes(paredes)
# ORDEM 005.B (v37.1): CÂMERA INDEPENDENTE — a parede REAL do ambiente decide a frente, independente
# de orientação do módulo no Promob. Para cada módulo, varre AS QUATRO direções (x-, x+, y-, y+) e
# verifica se há parede real do ambiente a até 80 mm. Se exatamente UMA direção tem, essa é a parede
# das costas, parede_key = essa direção, e a câmera (lado oposto) olha para a frente real.
# Se duas (módulo em canto) ou nenhuma (ilha) → mantém o parede_key atual (lado_frontal/parede_de decidem).
if _FR:
    _any_005b = False
    for _m in [i for i in inst if i['tipo'] == 'mod']:
        _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+') if _parede_real_atras(_m, _k, _FR) is not None]
        # Um módulo mais raso pode ficar até 160 mm da parede real. Só corrige
        # uma vista-fragmento quando há UMA parede candidata e nenhuma a 80 mm.
        # Cantos conservam a parede e câmera próprias.
        if not _com_real and 'canto' not in _norm(_m['desc']):
            _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+')
                         if _parede_real_atras(_m, _k, _FR, tol=160) is not None]
            if len(_com_real) == 1:
                print(f"VISTA-FRAGMENTO: {_m['desc']} {_m['dim']} -> parede real {_com_real[0]}")
        if len(_com_real) == 1 and _m.get('parede_key') != _com_real[0]:
            print(f"005.B: {_m['desc']} {_m['dim']}: {_m.get('parede_key')} -> {_com_real[0]}")
            _m['parede_key'] = _com_real[0]
            _m['frente'] = geo.OPOSTO[_com_real[0]]
            _any_005b = True
    if _any_005b:
        # Rebuild paredes dos módulos; componentes herdam do módulo mais próximo
        paredes = geo._montar([i for i in inst if i['tipo'] == 'mod'])
        _mods_ref = [i for i in inst if i['tipo'] == 'mod']
        for _it in inst:
            if _it['tipo'] == 'mod': continue
            _mp = min(_mods_ref, key=lambda m: geo.dist_caixas(_it['bb'], m['bb'])) if _mods_ref else None
            if _mp and geo.dist_caixas(_it['bb'], _mp['bb']) <= 400:
                _it['parede_key'] = _mp['parede_key']
                dono_ = next((o for o in paredes if _mp in o['itens']), None)
                if dono_ and _it not in dono_['itens']:
                    _it['parede'] = dono_['id']
                    dono_['itens'].append(_it)
        paredes = _juntar_paredes(paredes)
# ELETROS / objetos do ambiente (geladeira, micro-ondas, forno, coifa, revestimento...): peça do DXF que não é móvel,
# parede, pedra, piso nem forro. Só referência (faces reais, cinza médio), NUNCA cotado.
ELETRO_COR = (0.72, 0.73, 0.76)
ELETROS = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['i'] not in MALHA_I and p_['faces']
           and len(p_['faces']) >= 10 and sorted(p_['dim'])[0] >= 40 and sorted(p_['dim'])[1] >= 150 and max(p_['dim']) <= 2200 and p_['dim'][2] >= 100
           and p_['bb'][5] <= 2300 and not (60 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and p_['dim'][2] >= 1800)]
# REGRA (João): blocos QUADRADOS (caixa simples, 12 faces) não entram — atrapalham a imagem. Fica objeto com forma
# real (> 12 faces); em cima da pedra, só o que for baixo (cuba, cooktop: até 300 mm acima da pedra).
_topo_pedra = [p_['bb'][5] for p_ in AMB]
def _eletro_ok(p_):
    if len(p_['faces']) <= 12: return False
    if p_['bb'][2] < 50 and p_['bb'][5] < 250: return False   # base/rodapé solto no chão não é eletro
    for t_ in _topo_pedra:
        if p_['bb'][2] <= t_ + 15 and p_['bb'][5] > t_ - 60: return p_['bb'][5] <= t_ + 300
    return True
ELETROS = [p_ for p_ in ELETROS if _eletro_ok(p_)]
# REGRA (v30): PORTA/FRENTE AVULSA do XML (POR_...) não entra na listagem (v26), mas É DESENHADA junto do móvel onde encosta
# (ex.: frente de gaveta do criado-mudo). Casa pela medida (±1 mm) com peça do DXF ainda sem dono, encostada no móvel.
_por = set()
for e in XML_TREE.iter('ITEM'):
    U_ = (e.get('ID') or '').upper()
    if U_.startswith('POR_') or '_POR_' in U_:
        try: _por.add(tuple(sorted(round(float(e.get(a).replace(',', '.'))) for a in ('WIDTH', 'HEIGHT', 'DEPTH'))))
        except Exception: pass
_dono = {pi for i in inst for pi in i['pecas']}
PORTAS_XML = set()   # REGRA (bloco cotas 28/09/2026): peças do DXF casadas com porta/frente avulsa do XML (POR_) = PORTA (sai das cotas)
for p_ in P:
    if p_['i'] in _dono or not p_['faces']: continue
    k_ = tuple(sorted(round(x) for x in p_['dim']))
    if not any(all(abs(a - b) <= 1 for a, b in zip(k_, q_)) for q_ in _por): continue
    alvo_ = min(inst, key=lambda i: geo.dist_caixas(p_['bb'], i['bb']), default=None)
    if alvo_ is not None and geo.dist_caixas(p_['bb'], alvo_['bb']) <= 5:
        alvo_['pecas'].append(p_['i']); _dono.add(p_['i']); PORTAS_XML.add(p_['i'])
# REGRA (v28, João): móvel feito com GEOMETRIA no Promob (vem no DXF, não no XML) que ENCOSTA num móvel do projeto
# = referência na imagem (como a pedra): forma real, sem listagem/balão/cota.
# v29: peça com medida+cor do XML é PEÇA DE MÓVEL (porta/frente), nunca geometria.
_ja_e = {q['i'] for q in ELETROS}
_inst_bb = [i['bb'] for i in inst]
ELETROS += [p_ for p_ in P if not p_.get('mat') and p_['i'] not in _usadas and p_['i'] not in AMB_I and p_['i'] not in MALHA_I and p_['i'] not in _ja_e and p_['faces']
            and sorted(p_['dim'])[0] >= 15 and sorted(p_['dim'])[1] >= 100 and p_['bb'][5] <= 1300 and p_['bb'][2] >= -5
            and not (p_['dim'][2] < 60 and min(p_['dim'][0], p_['dim'][1]) > 1000) and not (p_['bb'][2] < 50 and p_['bb'][5] < 250)
            and any(geo.dist_caixas(p_['bb'], b_) <= 20 for b_ in _inst_bb)]
ELETRO_I = {p_['i'] for p_ in ELETROS}
for p_ in ELETROS: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
print('AMBIENTE (eletros/objetos):', len(ELETROS), 'peças')
def _arestas(faces):
    # contorno nítido: aresta de borda ou quina (normais diferentes); diagonal de triangulação não aparece
    # só arestas RETAS de verdade (alinhadas a um eixo): quina de parede, vão de janela, borda da pedra.
    # Aresta inclinada = triangulação -> nunca aparece (evita riscos diagonais no desenho).
    reta = lambda a_, b_: sum(1 for k_ in range(3) if abs(a_[k_] - b_[k_]) > 1) <= 1
    ed = {}; nrm = [_n(fc[0], fc[1], fc[2]) for fc in faces]
    kk = lambda v: tuple(round(c, 0) for c in v)
    for i_, fc in enumerate(faces):
        for j_ in range(len(fc)):
            a_, b_ = kk(fc[j_]), kk(fc[(j_ + 1) % len(fc)])
            if a_ == b_: continue
            ed.setdefault(frozenset((a_, b_)), []).append(i_)
    out = []
    for i_, fc in enumerate(faces):
        fl = []
        for j_ in range(len(fc)):
            a_, b_ = kk(fc[j_]), kk(fc[(j_ + 1) % len(fc)])
            fs2 = ed.get(frozenset((a_, b_)), [])
            if a_ == b_ or not reta(a_, b_): fl.append(False); continue
            if len(fs2) < 2: fl.append(True); continue
            n1, n2 = nrm[fs2[0]], nrm[fs2[1]]
            fl.append(abs(sum(x * y for x, y in zip(n1, n2))) < 0.94)
        out.append(fl)
    return out
for p_ in AMB + ELETROS + MALHA_PAR:
    p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]; p_['ft'] = _arestas(p_['faces'])
PAR_DXF = [p_ for p_ in P if p_['i'] not in _usadas and p_['i'] not in {q['i'] for q in AMB} and p_['i'] not in ELETRO_I and 60 <= min(p_['dim'][0], p_['dim'][1]) <= 400
           and max(p_['dim'][0], p_['dim'][1]) >= 100 and p_['dim'][2] >= 100 and max(p_['dim'][0], p_['dim'][1]) < 20000
           and not (p_['bb'][2] < 50 and p_['dim'][2] < 1000)]   # peça baixa no chão (rodapé solto) não é parede
for p_ in AMB: p_['faces'] = [[tuple(v) for v in fc] for fc in p_['faces']]
print('AMBIENTE (pedra):', len(AMB), 'peças')
# O principal recebe apenas o conteúdo do ciclo normal. Relações e pranchas especiais ficam no pacote próprio.
from especiais.relacoes import separar_relacoes, agrupar_paineis, separar_catalogo, _sd, _toca
separar_relacoes(globals())
# 4) CONDIÇÃO (v22, planta do João): PERNA DO L dentro de uma parede (ex.: penteadeira em L) = VISTA PRÓPRIA.
#    Peças soltas da parede que vão bem mais fundo que os módulos (> 300 mm além da frente deles), formando um trecho de
#    600 mm+ na profundidade, viram outra "parede" vista de lado (pelo lado de dentro do L).
_novas = []
for w in [w for w in paredes if not w.get('divisoria')]:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    prof_ = lambda bb: max((w['plano'] - bb[ad]) * sg_, (w['plano'] - bb[ad + 3]) * sg_)
    mods_ = [i for i in w['itens'] if i['tipo'] == 'mod']
    if not mods_: continue
    D_ = max(prof_(m['bb']) for m in mods_)
    perna = [i for i in w['itens'] if i['tipo'] == 'comp' and prof_(i['bb']) > D_ + 300]
    if len(perna) < 2: continue
    p0 = min(min((w['plano'] - i['bb'][ad]) * sg_, (w['plano'] - i['bb'][ad + 3]) * sg_) for i in perna)
    if max(prof_(i['bb']) for i in perna) - max(p0, D_) < 600: continue
    c_perna = sum((i['bb'][al] + i['bb'][al + 3]) / 2 for i in perna) / len(perna)
    c_main = sum((i['bb'][al] + i['bb'][al + 3]) / 2 for i in mods_) / len(mods_)
    maior = c_perna > c_main       # câmera olha do lado de dentro do L (onde está o resto do móvel)
    key = ('x+' if maior else 'x-') if al == 0 else ('y+' if maior else 'y-')
    pl = max(i['bb'][al + 3] for i in perna) if maior else min(i['bb'][al] for i in perna)
    w['itens'] = [i for i in w['itens'] if i not in perna]
    nw = dict(key=key, plano=pl, itens=perna, id=f"{key}@{round(pl)}L", perna_l=True, pai=w['id'])
    for i in perna: i['parede'] = nw['id']
    _novas.append(nw)
paredes += _novas
# REGRA (v28): "parede" com até 2 peças soltas que ENCOSTAM (60 mm) em móvel de outra parede não vira vista: junta na outra
for w in [w for w in paredes if not (w.get('divisoria') or w.get('bloco') or w.get('perna_l'))]:
    if len(w['itens']) > 2 or any(i['tipo'] != 'comp' for i in w['itens']): continue
    alvo = None
    for o in paredes:
        if o is w or o.get('divisoria') or o.get('bloco') or len(o['itens']) <= 2: continue
        if all(any(geo.dist_caixas(i['bb'], j['bb']) <= 60 for j in o['itens']) for i in w['itens']): alvo = o; break
    if alvo:
        for i in w['itens']: i['parede'] = alvo['id']
        alvo['itens'] += w['itens']; w['itens'] = []
paredes = [w for w in paredes if w['itens']]
# 5) CONDIÇÃO (v26): PAREDE CORTADA POR PILAR / VÃO DE PASSAGEM. Os móveis de uma mesma parede ficam
#    dos dois lados de uma parede real que atravessa a faixa dos móveis (pilar, verga de vão de passagem) -> são DOIS
#    ambientes: cada lado vira uma parede (vista) própria, com listagem e cotas só dele (escala maior, leitura por lado).
def _faces_parede():
    for p_ in PAR_DXF + MALHA_PAR:
        for fc in p_['faces']: yield fc
_cortadas = []
for w in [w for w in paredes if not w.get('divisoria') and not w.get('perna_l')]:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]; pl = w['plano']
    mods_ = [i for i in w['itens'] if i['tipo'] == 'mod']
    if len(mods_) < 2: continue
    D_ = max(max((pl - m['bb'][ad]) * sg_, (pl - m['bb'][ad + 3]) * sg_) for m in mods_)
    a0, a1 = min(m['bb'][al] for m in mods_), max(m['bb'][al + 3] for m in mods_)
    cs = []
    for fc in _faces_parede():
        vs = [v[al] for v in fc]
        if max(vs) - min(vs) > 1: continue
        c = vs[0]
        if not a0 + 300 < c < a1 - 300: continue
        d0, d1 = sorted(((pl - min(v[ad] for v in fc)) * sg_, (pl - max(v[ad] for v in fc)) * sg_))
        if min(d1, D_) - max(d0, 0) >= 0.8 * D_: cs.append(c)
    cs.sort(); grp = []
    for c in cs:
        if grp and c - grp[-1][-1] <= 400: grp[-1].append(c)
        else: grp.append([c])
    partes = [w['itens']]
    for g in grp:
        c = (g[0] + g[-1]) / 2; nv = []
        for its_ in partes:
            e_ = [i for i in its_ if (i['bb'][al] + i['bb'][al + 3]) / 2 < c]; d_ = [i for i in its_ if i not in e_]
            le = sum(i['bb'][al + 3] - i['bb'][al] for i in e_ if i['tipo'] == 'mod'); ld = sum(i['bb'][al + 3] - i['bb'][al] for i in d_ if i['tipo'] == 'mod')
            nv += [e_, d_] if le >= 1000 and ld >= 1000 else [its_]
        partes = nv
    if len(partes) > 1: _cortadas.append((w, partes))
for w, partes in _cortadas:
    paredes.remove(w)
    for k_, its_ in enumerate(partes):
        nw = dict(key=w['key'], plano=w['plano'], itens=its_, id=f"{w['id']}{'abcdef'[k_]}", cortada=True)
        for i in its_: i['parede'] = nw['id']
        paredes.append(nw)
agrupar_paineis(globals())
# 7) CONDIÇÃO (v26): PAINEL USINADO. Painel em pé na FRENTE de uma estrutura de nichos aberta (2 laterais + 3 ou mais
#    prateleiras logo atrás, até 150 mm) = painel com VÃOS usinados alinhados aos nichos (o DXF traz o painel inteiro).
#    Vão = largura livre entre as laterais x altura livre entre prateleiras (> 150 mm). O painel é desenhado com os vãos.
def _caixa_fq(b):
    x0, y0, z0, x1, y1, z1 = b
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
    N = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
    return [[[c[i] for i in f_], n_, [True] * 4] for f_, n_ in zip(F, N)]
USINADOS = {}
for w in paredes:
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    cps = [i for i in w['itens'] if i['tipo'] == 'comp']
    for pn in cps:
        b = pn['bb']
        if b[ad + 3] - b[ad] > 25 or b[al + 3] - b[al] < 400 or b[5] - b[2] < 800: continue
        tras = b[ad + 3] if sg_ > 0 else b[ad]
        atr = [i for i in cps if i is not pn and i['bb'][al] >= b[al] - 5 and i['bb'][al + 3] <= b[al + 3] + 5 and i['bb'][2] >= b[2] - 5
               and i['bb'][5] <= b[5] + 5 and 0 <= ((i['bb'][ad] - tras) if sg_ > 0 else (tras - i['bb'][ad + 3])) <= 150]
        prs = sorted([i for i in atr if i['bb'][5] - i['bb'][2] <= 30 and i['bb'][al + 3] - i['bb'][al] >= 150], key=lambda i: i['bb'][2])
        lts = sorted([i for i in atr if i['bb'][al + 3] - i['bb'][al] <= 30 and i['bb'][5] - i['bb'][2] >= 300], key=lambda i: i['bb'][al])
        if len(prs) < 3 or len(lts) < 2: continue
        o0, o1 = lts[0]['bb'][al + 3], lts[-1]['bb'][al]
        vz = [(p0['bb'][5], p1['bb'][2]) for p0, p1 in zip(prs, prs[1:]) if p1['bb'][2] - p0['bb'][5] > 150]
        if not vz or o1 - o0 < 150: continue
        pi = pn['pecas'][0]; USINADOS[pi] = dict(u=(o0, o1), z=vz, al=al)
        cxs = []
        def sub(a0_, a1_, z0_, z1_):
            bb_ = list(b); bb_[al], bb_[al + 3], bb_[2], bb_[5] = a0_, a1_, z0_, z1_; cxs.append(bb_)
        sub(b[al], o0, b[2], b[5]); sub(o1, b[al + 3], b[2], b[5])
        zz = [b[2]] + [v for z_ in vz for v in z_] + [b[5]]
        for z0_, z1_ in zip(zz[0::2], zz[1::2]):
            if z1_ - z0_ > 0.5: sub(o0, o1, z0_, z1_)
        P[pi]['fq'] = [fq_ for c_ in cxs for fq_ in _caixa_fq(c_)]
        print('PAINEL USINADO:', pn['desc'], pn['dim'], '->', len(vz), 'vão(s)')
separar_catalogo(globals())
grupos = geo.agrupar_vistas2(paredes)

# REGRA (ENGENHARIA seção 5): sequência espacial por tipo de ambiente. O caderno deve começar
# pelo grupo de parede que contém o elemento-âncora do ambiente (ex.: cozinha começa pela pia).
# Só rotaciona o PONTO DE PARTIDA da lista de grupos; a continuidade espacial entre eles
# continua vindo de geo.agrupar_vistas2 (não mexe na geometria nem no casamento XML x DXF).
_ANCORA_AMBIENTE = {
    'cozinha': r'\bpia\b|\bcuba\b',
    'varanda': r'\bpia\b|\bcuba\b',
    'gourmet': r'\bpia\b|\bcuba\b',
    'quarto': r'guarda[\s-]?roupa|roupeiro',
    'escritorio': r'bancada|mesa',
    'sala': r'\bpainel\b',
    # REGRA (João, 28/09/2026): banheiro e lavabo. Engenharia manda "leitura frontal" -- comeca
    # pelo elemento que ancora a parede frontal do sanitario (gabinete/cuba/pia). Cobre variacoes:
    # "banheiro", "banheiros", "wc", "bwc", "lavabo", "suite banheiro", "bh casal" etc.
    'banheiro': r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'lavabo':   r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'wc':       r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
    'bwc':      r'gabinete|\bcuba\b|\bpia\b|\bbancada\b',
}
def _ancora_regex(ambiente):
    amb_ = _norm(ambiente or '')
    return next((rx for chave, rx in _ANCORA_AMBIENTE.items() if chave in amb_), None)
_rx_ancora = _ancora_regex(cfg['dados'].get('ambiente'))
if _rx_ancora and grupos:
    _idx_ancora = next((k for k, g in enumerate(grupos)
                         if any(re.search(_rx_ancora, i['desc'], re.I) for w in g for i in PW[w]['itens'])), None)
    if _idx_ancora:   # já é 0 -> nada a fazer; None -> âncora não encontrada, mantém ordem atual
        grupos = grupos[_idx_ancora:] + grupos[:_idx_ancora]
        print(f"SEQUÊNCIA ESPACIAL: ambiente '{cfg['dados'].get('ambiente')}' -> início na parede com a âncora (grupo {_idx_ancora})")

# vistas: liga cada grupo à imagem 3D do config pela peça de referência
V = []
livres = list(grupos)
for cv in cfg['vistas']:
    g = next((g for g in livres if any(cv['ref'] in f"{i['desc']} {i['dim']}" for w in g for i in PW[w]['itens'])), None)
    if g: livres.remove(g); V.append(dict(cv, paredes=sorted(g, key=lambda w: -len(PW[w]['itens']))))
letras = 'ABCDEFGHIJKL'
# REGRA (João): cada parede tem sua LETRA (A, B, C, D... em sequência; em cada L a parede maior primeiro).
# Parede PEQUENA (< PAREDE_PEQ ao longo da parede) vai junto com a parede grande do mesmo L:
#   listagem única com 3D angulado pegando as duas + cotas das duas lado a lado na mesma prancha.
# Paredes grandes = vista própria (3D frontal).
PAREDE_PEQ = 2500  # João: parede < 2,5 m vai junto com a vizinha do L (listagem na diagonal)
def _larg(w):
    ax = 1 if FV[PW[w]['key']][0] else 0
    return max(i['bb'][ax + 3] for i in PW[w]['itens']) - min(i['bb'][ax] for i in PW[w]['itens'])
_nl = len(V)
for g in livres:
    ws = sorted(g, key=lambda w: -_larg(w)); blocos = []
    for w in ws:
        if blocos and _larg(w) < PAREDE_PEQ and len(blocos[0]) < 2: blocos[0].append(w)
        else: blocos.append([w])
    for b in blocos:
        ls = [letras[_nl + k] for k in range(len(b))]; _nl += len(b)
        V.append(dict(letra=ls[0], letras=ls, img3d=None, paredes=b))
# REGRA (v22, planta do João): a vista da PERNA DO L vem logo DEPOIS da vista da parede dela (b -> c); letras em sequência
for v in [v for v in V if len(v['paredes']) == 1 and PW[v['paredes'][0]].get('perna_l')]:
    pai_ = PW[v['paredes'][0]]['pai']; V.remove(v)
    k_ = next((j for j, o in enumerate(V) if pai_ in o['paredes']), len(V) - 1)
    V.insert(k_ + 1, v)
_c = 0
for v in V:
    if v.get('img3d') is None and not v.get('ref'):
        v['letras'] = [letras[_c + k] for k in range(len(v['paredes']))]; v['letra'] = v['letras'][0]
    _c += len(v['paredes'])
for v in V:
    v.setdefault('letras', [v['letra'] + (str(j + 1) if len(v['paredes']) > 1 else '') for j in range(len(v['paredes']))])
    v['titulo'] = 'VISTA ' + v['letras'][0] if len(v['letras']) == 1 else 'VISTAS ' + ' E '.join(v['letras'])
    # REGRA (João): LISTAGEM sempre FRONTAL e POR PAREDE (só os móveis daquela parede); o bloco junta só as cotas.
    v['subs'] = [v] if len(v['paredes']) == 1 else [dict(letra=l_, letras=[l_], titulo='VISTA ' + l_, img3d=None, paredes=[w_]) for w_, l_ in zip(v['paredes'], v['letras'])]
VW = [s_ for v in V for s_ in v['subs']]
# Ordem aprovada: cada vista termina sua listagem e suas cotas antes da próxima.
# As mesmas vistas e seus detalhes funcionais são mantidos; só separa o ciclo.
V = list(VW)
for v in V: v['subs'] = [v]

# REGRA (v33, João): SEM ASTERISCO. Item que o motor não localizou no DXF não é desenhado,
# logo não aparece na imagem frontal e, pela regra da peça escondida, não é listado.

# ---------------- geometria de elevação ----------------
def uu(x, y, f): return x * f[1] - y * f[0]

def area2(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2

def _tick(sh, x, y):
    sh.draw_line((x - 2.2, y + 2.2), (x + 2.2, y - 2.2))

def _txt(page, pos, s, fs, rotate=0, fundo=False):
    if fundo:
        tw = fz.get_text_length(s, 'helv', fs)
        r = fz.Rect(pos[0] - 0.8, pos[1] - fs * 0.8, pos[0] + tw + 0.8, pos[1] + 1) if not rotate else fz.Rect(pos[0] - fs * 0.8, pos[1] - tw - 0.8, pos[0] + 1, pos[1] + 0.8)
        page.draw_rect(r, color=None, fill=(1, 1, 1))
    page.insert_text(pos, s, fontname='helv', fontsize=fs, rotate=rotate)

def cadeia_h(page, us, yl, yobj, X, fs=6.5, fundo=False):
    us = _uniq(us)
    if len(us) < 2: return
    sh = page.new_shape()
    for u in us:
        sh.draw_line((X(u), yobj), (X(u), yl + (2.5 if yl < yobj else -2.5))); sh.finish(color=CR, width=0.25)
    sh.draw_line((X(us[0]), yl), (X(us[-1]), yl)); sh.finish(color=CR, width=0.5)
    for u in us: _tick(sh, X(u), yl)
    sh.finish(color=CR, width=0.6); sh.commit()
    # REGRA (ajuste, item 7 - João): linha cruzar linha é normal, NÃO mexe nisso. O que não pode é
    # o NÚMERO ficar em cima de uma linha (a própria ou outra cota cruzando ali) - por isso o
    # fundo=True é forçado (apaga a linha embaixo do texto) independente do que o chamador passar.
    # Mantém também o desvio se dois números vizinhos colidirem entre si (vão estreito).
    _oc_h = []
    for a, b in zip(us, us[1:]):
        s = fmt(b - a); tw = fz.get_text_length(s, 'helv', fs)
        cx = (X(a) + X(b)) / 2; ty = yl - 1.8
        for _tent in range(3):
            r = fz.Rect(cx - tw / 2 - 1, ty - fs, cx + tw / 2 + 1, ty + 1.5)
            if not any(r.intersects(o_) for o_ in _oc_h): break
            ty += (fs + 2.2) * (1 if yl < yobj else -1)
        _oc_h.append(r)
        _txt(page, (cx - tw / 2, ty), s, fs, fundo=True)

def cadeia_v(page, zs, xl, xobj, Y, fs=6.5, esquerda=True, fundo=False):
    zs = _uniq(zs)
    if len(zs) < 2: return
    sh = page.new_shape()
    for z in zs:
        if xobj is not None:
            sh.draw_line((xobj, Y(z)), (xl + (2.5 if xl > xobj else -2.5), Y(z))); sh.finish(color=CR, width=0.25)
    sh.draw_line((xl, Y(zs[0])), (xl, Y(zs[-1]))); sh.finish(color=CR, width=0.5)
    for z in zs: _tick(sh, xl, Y(z))
    sh.finish(color=CR, width=0.6); sh.commit()
    # REGRA (ajuste, item 7 - cruzamento de linhas/letras): mesma lógica do cadeia_h - texto de
    # cota vertical não pode invadir o texto vizinho; desloca lateralmente se colidir. A posição
    # das linhas/tracinhos das cotas não muda.
    _oc_v = []
    for a, b in zip(zs, zs[1:]):
        s = fmt(b - a); tw = fz.get_text_length(s, 'helv', fs)
        cy = (Y(a) + Y(b)) / 2; tx = xl - 1.8
        for _tent in range(3):
            r = fz.Rect(tx - fs, cy - tw / 2 - 1, tx + 1.5, cy + tw / 2 + 1)
            if not any(r.intersects(o_) for o_ in _oc_v): break
            tx += (fs + 2.2) * (1 if xobj is not None and xl > xobj else -1)
        _oc_v.append(r)
        _txt(page, (tx, cy + tw / 2), s, fs, rotate=90, fundo=True)   # ajuste item 7: fundo sempre ligado, apaga linha embaixo do número

def _uniq(vals, tol=2.0):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol: out.append(v)
    return out

# nível do piso pronto: placa de piso do DXF (grande, fina, no chão). Cotas de altura partem daqui.
ZP = max([p_['bb'][5] for p_ in P if min(p_['dim'][0], p_['dim'][1]) > 1500 and p_['dim'][2] <= 60 and p_['bb'][2] <= 1] or [0])
CORTE = 1100
def _eh_ripa(it):
    try: d_ = sorted(float(x) for x in re.findall(r'[\d.]+', it['dim'].replace(',', '.'))[:3])
    except Exception: return False
    return len(d_) == 3 and d_[0] <= 30 and 60 <= d_[1] <= 200 and d_[2] >= 500

def cotar_divisoria(page, G, ox, fy, k):
    # REGRA (v18, PDF do João): divisória ripada NÃO cota ripa por ripa. Cota: largura total + peças laterais,
    # UMA ripa e UM vão (amostra), altura total e as alturas das partes (bases, painel, travessas).
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']; u0, u1 = G['umin'], G['umax']; ztop_ = max(b['z1'] for b in bx)
    rip = sorted([b for b in bx if _eh_ripa(b['it'])], key=lambda b: b['u0'])
    alt = [b for b in bx if not _eh_ripa(b['it']) and (b['z1'] - b['z0']) >= 0.8 * ztop_]
    cadeia_h(page, [u0, u1] + [v for b in alt for v in (b['u0'], b['u1'])], fy + 14, fy + 2, X)
    cadeia_h(page, [u0, u1], Y(ztop_) - 14, Y(ztop_) - 2, X)
    # REGRA (v18b): o montador precisa da distância entre as ripas -> cota TODOS os vãos, em cada faixa de ripas
    # (embaixo e em cima do painel), com as setas por dentro; a espessura da ripa sai uma vez só.
    faixas = sorted({(round(b['z0'] / 50), round(b['z1'] / 50)) for b in rip if b['z1'] - b['z0'] >= 300})
    feitas = []
    for f0, f1 in faixas:
        zc = (f0 + f1) * 25
        if any(abs(zc - z_) < 250 for z_ in feitas): continue
        estreitas = [b for b in bx if b['z0'] <= zc <= b['z1'] and (b['u1'] - b['u0']) <= 200]
        ed = _uniq(sorted(v for b in estreitas for v in (b['u0'], b['u1'])), 1.0)
        if len(ed) < 4: continue
        feitas.append(zc); yl = Y(zc)
        sh = page.new_shape(); sh.draw_line((X(ed[0]), yl), (X(ed[-1]), yl)); sh.finish(color=CR, width=0.4)
        for u_ in ed: _tick(sh, X(u_), yl)
        sh.finish(color=CR, width=0.5); sh.commit()
        ripa_ok = False
        for a_, c_ in zip(ed, ed[1:]):
            t_ = fmt(c_ - a_); tw = fz.get_text_length(t_, 'helv', 5)
            if (c_ - a_) >= 40 and (c_ - a_) * k >= tw + 1:
                _txt(page, ((X(a_) + X(c_)) / 2 - tw / 2, yl - 1.5), t_, 5, fundo=True)
            elif not ripa_ok and (c_ - a_) < 40:
                _txt(page, (X(c_) + 1, yl + 6), t_, 5, fundo=True); ripa_ok = True
    hor = [b for b in bx if not _eh_ripa(b['it']) and (b['u1'] - b['u0']) >= 0.4 * (u1 - u0)]
    zs = [ZP, ztop_] + [v for b in hor for v in (b['z0'], b['z1'])]
    cadeia_v(page, zs, X(u1) + 16, X(u1) + 2, Y)
    cadeia_v(page, [ZP, ztop_], X(u0) - 16, X(u0) - 2, Y)

def _u_de(G, c, al):   # coordenada do DXF (eixo al) -> coordenada u da elevação
    f = G['f']; return c * (f[1] if al == 0 else -f[0])

def cotar_bloco(page, G, ox, fy, k):
    # REGRA (v26): BLOCO DE PAINÉIS (painel com nichos). Cota: largura total, VÃOS USINADOS do painel (largura e altura
    # de cada vão e das faixas entre eles), altura do painel a partir do piso pronto e até o teto (painel do teto).
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']; f = G['f']; ad = 0 if f[0] else 1
    fin = [b for b in bx if b['it']['bb'][ad + 3] - b['it']['bb'][ad] <= 30]
    pn = max(fin or bx, key=lambda b: (b['u1'] - b['u0']) * (b['z1'] - b['z0']))
    zt = max(b['z1'] for b in bx); u0, u1 = G['umin'], G['umax']
    us_, zs_ = [pn['u0'], pn['u1']], [pn['z0'], pn['z1']]
    ui = USINADOS.get(pn['it']['pecas'][0])
    if ui:
        us_ += [_u_de(G, c, ui['al']) for c in ui['u']]; zs_ += [v for z_ in ui['z'] for v in z_]
    cadeia_h(page, us_, Y(pn['z0']) + 14, Y(pn['z0']) + 2, X, fundo=True)
    cadeia_h(page, [u0, u1], Y(zt) - 14, Y(zt) - 2, X)
    xr = X(max(pn['u1'], u1))
    cadeia_v(page, zs_, xr + 14, X(pn['u1']) + 2, Y)
    cadeia_v(page, [ZP, pn['z0'], pn['z1'], zt], xr + 30, xr + 2, Y)

def cotar(page, G, ox, fy, k):
    if G['w'].get('bloco'): return cotar_bloco(page, G, ox, fy, k)
    if G['w'].get('divisoria'): return cotar_divisoria(page, G, ox, fy, k)
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    bx = G['boxes']
    mb = [b for b in bx if b['it']['tipo'] == 'mod'] or bx
    mu0, mu1 = min(b['u0'] for b in mb), max(b['u1'] for b in mb)
    cad = mb
    sup = [b for b in cad if b['z1'] > CORTE]
    inf = [b for b in cad if b['z0'] < CORTE]
    ytop = Y(G['zmax'])
    if sup:
        us = [v for b in sup for v in (b['u0'], b['u1'])]
        cadeia_h(page, us, ytop - 13, ytop - 2, X)
        if len(_uniq(us)) > 2: cadeia_h(page, [min(us), max(us)], ytop - 26, ytop - 2, X)
    if inf:
        us = [v for b in inf for v in (b['u0'], b['u1'])]
        cadeia_h(page, us, fy + 13, fy + 2, X)
        if len(_uniq(us)) > 2: cadeia_h(page, [min(us), max(us)], fy + 26, fy + 2, X)
    xr, xl = X(G['umax']), X(G['umin'])
    vr, vl = X(G.get('vmax', G['umax'])), X(G.get('vmin', G['umin']))   # REGRA (v15): cotas por FORA das paredes
    dir_ = [b for b in mb if b['u1'] >= G['umax'] - 700]
    esq = [b for b in mb if b['u0'] <= G['umin'] + 700]
    # móvel longe da parede lateral (> 600 mm): a cadeia fica encostada no móvel, não atravessa a parede vazia
    if vr - xr > 600 * k: vr = xr
    if xl - vl > 600 * k: vl = xl
    cadeia_v(page, [ZP] + [v for b in dir_ for v in (b['z0'], b['z1'])], vr + 14, xr + 2, Y)
    cadeia_v(page, [ZP] + [v for b in esq for v in (b['z0'], b['z1'])], vl - 14, xl - 2, Y)
    cadeia_v(page, [ZP, max(b['z1'] for b in mb)], vl - 28, xl - 2, Y)
    # REGRA (João): cotas INTERNAS dentro do móvel, vão por vão.
    #  - horizontal: largura livre entre lateral/divisória/divisória/lateral
    #  - vertical: altura livre entre prateleiras (de uma prateleira à outra, onde entram gavetas etc.)
    f_ = G['f']
    prof = lambda bb: (bb[3] - bb[0]) if f_[0] else (bb[4] - bb[1])
    for b in bx:
        it = b['it']
        if it['tipo'] != 'mod' or b['z1'] - b['z0'] < 350: continue
        vert, hor = [], []
        for pi in it['pecas']:
            bb = P[pi]['bb']; pu0, pz0, pu1, pz1 = geo.caixa_elev(bb, G['f'])
            if prof(bb) < 150: continue                      # portas, frentes, tamponamentos, ferragens
            if pu1 - pu0 <= 30 and pz1 - pz0 >= 300: vert.append((pu0, pu1, pz0, pz1))
            elif 12 <= pz1 - pz0 <= 30 and pu1 - pu0 >= 150: hor.append((pu0, pz0, pu1, pz1))
        vaos = vaos_prateleiras(vert,hor,b['z1']-b['z0'])
        cotados = set()
        for cu0, cu1 in vaos:
            larg = cu1 - cu0
            niv = sorted((z0_, z1_) for u0_, z0_, u1_, z1_ in hor if u0_ <= cu0 + 10 and u1_ >= cu1 - 10)
            gaps = [(a[1], c[0]) for a, c in zip(niv, niv[1:]) if c[0] - a[1] > 40]
            xv = X(cu0 + larg * 0.5)
            assinatura = assinatura_vaos(gaps)
            if assinatura not in cotados:
                for g0,g1 in gaps: cadeia_v(page,[g0,g1],xv,None,Y,fs=5.5,fundo=True)
                cotados.add(assinatura)
            globals().setdefault('_auditoria_vaos_cotas',[]).append(dict(
                modulo=it['desc'],dim=it['dim'],vao=(cu0,cu1),gaps=gaps,assinatura=assinatura))
            zt = (gaps[-1][1] if gaps else b['z1']) - 70
            cadeia_h(page, [cu0, cu1], Y(zt), Y(zt), X, fs=5.5, fundo=True)

def _desenho2d(page, faces, XY):
    """REGRA (v16, João): cotas 2D (frontal e lateral) com as MESMAS cores e TEXTURAS do 3D (madeirado com veio).
    Chapa 1830 x 2750 mm, veio no sentido do comprimento da peça. Sem Pillow/textura = cor lisa (vetor)."""
    its = []
    for f_ in faces:
        pts, cor, ft = f_[1], f_[2], f_[3]
        q = [XY(a, b) for a, b in pts]
        if area2(q) < 0.15: continue
        its.append((q, cor, ft, f_[4] if len(f_) > 4 else None, f_[5] if len(f_) > 5 else 0, pts))
    if not its: return
    if _Im is None or not cfg.get('textura', True) or not any(textura(m_) for _, _, _, m_, _, _ in its if m_):
        sh = page.new_shape()
        for q, cor, ft, _, _, _ in its:
            sh.draw_polyline(q + [q[0]]); sh.finish(color=cor, fill=cor, width=0.45, closePath=True)
            if any(ft):
                for (a_, b_), f_ in zip(zip(q, q[1:] + q[:1]), ft):
                    if f_: sh.draw_line(a_, b_)
                sh.finish(color=(0.2, 0.2, 0.2), width=0.3, closePath=False)
        sh.commit()
        contornos(globals(),page,faces,XY)
        return
    R = fz.Rect(min(x for q in [i[0] for i in its] for x, _ in q), min(y for q in [i[0] for i in its] for _, y in q),
                max(x for q in [i[0] for i in its] for x, _ in q), max(y for q in [i[0] for i in its] for _, y in q)) & page.rect
    if R.is_empty: return
    s_ = 250 / 72.0; W_ = max(1, int(R.width * s_)); H_ = max(1, int(R.height * s_))
    img = _Im.new('RGBA', (W_, H_), (0, 0, 0, 0)); dr = _ImD.Draw(img)
    for q, cor, ft, mat, pc, pts in its:
        Q = [((x - R.x0) * s_, (y - R.y0) * s_) for x, y in q]
        tex = textura(mat) if mat else None
        x0_ = int(max(0, min(a for a, _ in Q))); y0_ = int(max(0, min(b for _, b in Q)))
        x1_ = int(min(W_, max(a for a, _ in Q) + 1)); y1_ = int(min(H_, max(b for _, b in Q) + 1))
        if tex is not None and x1_ - x0_ >= 3 and y1_ - y0_ >= 3:
            Lu = max(a for a, _ in pts) - min(a for a, _ in pts); Lz = max(b for _, b in pts) - min(b for _, b in pts)
            sx_, sy_ = tex.width / CHAPA_L, tex.height / CHAPA_A
            deit = Lu > Lz                                   # peça deitada: veio na horizontal
            Lw, Lh = (Lz, Lu) if deit else (Lu, Lz)
            pw = max(2, min(tex.width, int(Lw * sx_))); ph = max(2, min(tex.height, int(Lh * sy_)))
            ox_ = (pc * 137) % max(1, tex.width - pw + 1); oy_ = (pc * 71) % max(1, tex.height - ph + 1)
            tile = tex.crop((ox_, oy_, ox_ + pw, oy_ + ph))
            if deit: tile = tile.rotate(90, expand=True)
            tile = tile.resize((x1_ - x0_, y1_ - y0_)).convert('RGBA')
            mask = _Im.new('L', tile.size, 0); _ImD.Draw(mask).polygon([(a - x0_, b - y0_) for a, b in Q], fill=255)
            img.paste(tile, (x0_, y0_), mask)
        else:
            dr.polygon(Q, fill=tuple(int(255 * v) for v in cor) + (255,))
        for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
            if fl_: dr.line([a_, b_], fill=(50, 50, 50, 255), width=max(1, int(0.3 * s_)))
    import io as _io
    bio = _io.BytesIO(); img.save(bio, format='PNG', optimize=True)
    page.insert_image(R, stream=bio.getvalue())
    contornos(globals(),page,faces,XY)

# ---------------- pranchas ----------------
lay = fz.open(cfg['layout'])
def nova_prancha(doc, n, titulo):
    p = doc.new_page(width=lay[0].rect.width, height=lay[0].rect.height)
    p.show_pdf_page(p.rect, lay, 0)
    p.draw_rect(fz.Rect(300, 117, 540, 141), color=None, fill=BRANCO)
    p.draw_rect(fz.Rect(712, 52, 816, 96), color=None, fill=BRANCO)
    d = cfg['dados']
    for x, y, t in ((224, 33, d['cliente']), (234, 59, d['ambiente']), (285, 85, d['projetista']), (239, 111, d['arquiteta'])):
        p.insert_text((x, y), t, fontname='hebo', fontsize=10)
    p.insert_text((419.5 - fz.get_text_length(titulo, 'hebo', 16) / 2, 135), titulo, fontname='hebo', fontsize=16, color=RED)
    p.insert_text((764 - fz.get_text_length('PRANCHA', 'hebo', 18) / 2, 62), 'PRANCHA', fontname='hebo', fontsize=18)
    s = '%02d' % n
    p.insert_text((764 - fz.get_text_length(s, 'hebo', 18) / 2, 85), s, fontname='hebo', fontsize=18)
    return p

def tabela(p, linhas, x0, y0, largura=248, nums=None):
    fs, lh = 7.2, 10.5
    cols = [x0, x0 + 24, x0 + 168, x0 + largura]
    sh = p.new_shape()
    sh.draw_rect(fz.Rect(x0, y0, x0 + largura, y0 + lh)); sh.finish(color=PRETO, fill=(1, 1, 0), width=0.5)
    for i in range(len(linhas)):
        r = fz.Rect(x0, y0 + lh * (i + 1), x0 + largura, y0 + lh * (i + 2))
        sh.draw_rect(r); sh.finish(color=PRETO, fill=(0.85, 0.85, 0.85) if i % 2 else BRANCO, width=0.4)
    for c in cols[1:-1]:
        sh.draw_line((c, y0), (c, y0 + lh * (len(linhas) + 1))); sh.finish(color=PRETO, width=0.4)
    sh.commit()
    for t, a, b in (('Item', cols[0], cols[1]), ('Descrição', cols[1], cols[2]), ('Dimensão', cols[2], cols[3])):
        p.insert_text(((a + b) / 2 - fz.get_text_length(t, 'helv', fs) / 2, y0 + lh - 2.8), t, fontname='helv', fontsize=fs)
    for i, (d, dm, m) in enumerate(linhas, 1):
        y = y0 + lh * (i + 1) - 2.8
        s = str(nums[i - 1] if nums else i) + m
        p.insert_text(((cols[0] + cols[1]) / 2 - fz.get_text_length(s, 'helv', fs) / 2, y), s, fontname='helv', fontsize=fs)
        while fz.get_text_length(d, 'helv', fs) > cols[2] - cols[1] - 6: d = d[:-1]
        p.insert_text((cols[1] + 3, y), d, fontname='helv', fontsize=fs)
        p.insert_text(((cols[2] + cols[3]) / 2 - fz.get_text_length(dm, 'helv', fs) / 2, y), dm, fontname='helv', fontsize=fs)
    return y0 + lh * (len(linhas) + 1)

def escala_para(larg_mm, alt_mm, W, H, cheio=False):
    for S in (ESC_COTA if cheio else ESC):
        k = MM / S
        lim = 1.0 if cheio else 0.75 if S < 25 else 1.0   # cotas (v15): ocupa a prancha toda
        if larg_mm * k <= W * lim and alt_mm * k <= H * lim: return S, k
    return ESC[-1], MM / ESC[-1]

import math
def desenhar(page, G, ox, fy, k, baloes=None, letra=None):
    X = lambda u: ox + (u - G['umin']) * k
    Y = lambda z: fy - z * k
    _desenho2d(page, G['faces'], lambda u, z: (X(u), Y(z)))
    sh = page.new_shape()
    sh.draw_line((X(G.get('vmin', G['umin'])) - 6, fy), (X(G.get('vmax', G['umax'])) + 6, fy)); sh.finish(color=PRETO, width=0.9)
    sh.commit()


# ===== REGRAS FIXAS (João, 28/09/2026 - skill P1/P2): LISTAGEM = 3D FRONTAL, PORTAS FECHADAS, COM PAREDES (referência de localização)
#       | COTAS = 2D FRONTAL, MÓVEL ISOLADO (sem paredes, piso, eletros e móveis de outras paredes; pedra real de referência), SEM PORTAS, EM ESCALA, DENTRO DO QUADRO =====
PAREDES_PECAS = [p_ for p_ in P if p_['dim'][2] >= 2000 and 80 <= min(p_['dim'][0], p_['dim'][1]) <= 400 and max(p_['dim'][0], p_['dim'][1]) >= 1000]
def caixa_faces(b):
    x0, y0, z0, x1, y1, z1 = b
    V_ = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return [[V_[a] for a in fc] for fc in [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]]
def paredes_recorte(R):
    out = []
    for p_ in PAREDES_PECAS:
        b = p_['bb']; c = [max(b[k], R[k]) for k in range(3)] + [min(b[k + 3], R[k + 3]) for k in range(3)]
        if all(c[k + 3] - c[k] > 1 for k in range(3)): out.append(c)
    return out

def _vista_limites(w, f, umin_, umax_, zmax_):
    """REGRA (v15): limites da elevação 2D = parede a parede (face interna da parede lateral + espessura) e piso ao teto.
    Sem parede lateral a até 4 m: abre 300 mm além do móvel. Teto = maior altura das paredes reais (até 3,2 m)."""
    axd = 0 if f[0] else 1; sg = f[axd]; pl = w['plano']
    cx = []
    for p_ in PAREDES_PECAS + PAR_DXF: cx.append(p_['bb'])
    for p_ in MALHA_PAR:
        for fc in p_['faces']:
            cx.append([min(v[0] for v in fc), min(v[1] for v in fc), min(v[2] for v in fc), max(v[0] for v in fc), max(v[1] for v in fc), max(v[2] for v in fc)])
    esq, dir_, esp_e, esp_d, tetos = None, None, 150, 150, []; fundo_ = False
    for b in cx:
        if b[5] - b[2] < 1500: continue
        d0, d1 = sorted(((pl - b[axd]) * sg, (pl - b[axd + 3]) * sg))
        if d1 < -30 or d0 > 800: continue      # só paredes na faixa dos móveis (fundo até 800 mm à frente)
        u0, z0, u1, z1 = geo.caixa_elev(b, f)
        if u1 > umin_ + 20 and u0 < umax_ - 20: tetos.append(z1); fundo_ = True; continue
        if u0 >= umax_ - 20 and u0 - umax_ <= 4000 and (dir_ is None or u0 < dir_): dir_ = u0; esp_d = min(max(u1 - u0, 60), 250) if u1 - u0 > 1 else 150
        if u1 <= umin_ + 20 and umin_ - u1 <= 4000 and (esq is None or u1 > esq): esq = u1; esp_e = min(max(u1 - u0, 60), 250) if u1 - u0 > 1 else 150
        tetos.append(z1)
    vmin_ = esq - esp_e if esq is not None else umin_ - 300
    vmax_ = dir_ + esp_d if dir_ is not None else umax_ + 300
    ztop_ = min(max(tetos), 3200) if tetos else zmax_ + 150
    if not fundo_ and zmax_ <= 1200: ztop_ = zmax_ + 300   # REGRA (v31): ilha/península baixa sem parede atrás -> desenho grande
    return vmin_, vmax_, max(ztop_, zmax_ + 50)

def _eh_porta(b, mb, w):
    # REGRA (João, 28/09/2026 - bloco cotas): ÚNICA definição geométrica de porta/frente/basculante/porta de correr.
    # b = caixa da chapa, mb = caixa do módulo. Porta = chapa fina (<= 30 mm na profundidade) na FRENTE do módulo
    # (até 150 mm à frente, 80 mm para dentro - pega porta de correr no trilho interno), dentro da largura/altura do
    # módulo (folga 60 mm). NÃO é porta: chapa dentro da caixa que vai exatamente da base ao topo do módulo e ocupa
    # pelo menos metade da largura (lateral/fechamento do próprio módulo, ex.: braço do canto L).
    # Usada por tem_porta (nicho), _portas (3D sem portas) e _portas_cota (cotas).
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
    perto = lambda bb: min(bb[ad] * sg_, bb[ad + 3] * sg_)
    fr = perto(mb)
    if b[ad + 3] - b[ad] > 30 or (b[al + 3] - b[al]) < 100 or (b[5] - b[2]) < 60: return False
    if not (fr - 150 <= perto(b) <= fr + 80): return False
    if b[al] < mb[al] - 60 or b[al + 3] > mb[al + 3] + 60 or b[2] < mb[2] - 60 or b[5] > mb[5] + 60: return False
    if perto(b) >= fr - 1 and abs(b[2] - mb[2]) <= 2 and abs(b[5] - mb[5]) <= 2 and (b[al + 3] - b[al]) >= 0.5 * (mb[al + 3] - mb[al]):
        return False
    return True

def _portas_cota(w):
    # REGRA (v31 + bloco cotas 28/09/2026): COTAS = SEM PORTAS. Usa a definição única _eh_porta.
    # Porta avulsa do XML (POR_) fica presa ao item mais próximo (às vezes um painel): sai também.
    out = {pi for it in w['itens'] for pi in it['pecas'] if pi in PORTAS_XML}
    protegidas = {pi for it in w['itens'] if it['tipo']=='comp' and
                  re.search(r'fechamento|vista|tampon|painel|rodap|afastador|cunha|porta falsa',it['desc'],re.I)
                  for pi in it['pecas'] if pi not in PORTAS_XML}
    for m in [i for i in w['itens'] if i['tipo'] == 'mod']:
        for pi in m['pecas']:
            if pi not in protegidas and _eh_porta(P[pi]['bb'], m['bb'], w): out.add(pi)
    return out

def geom_parede(w):
    # Cotas: conjunto montado, somente portas retiradas; pedra real como referência.
    f = FV[w['key']]; faces = []; boxes = []; mantidas = set()
    dep = lambda vs: sum(v[0] * f[0] + v[1] * f[1] for v in vs) / len(vs)
    _pc = _portas_cota(w)
    for it in w['itens']:
        cor = MADEIRA if it['tipo'] == 'comp' else BRANCO
        ids = []
        for pi in it['pecas']:
            if pi in _pc: continue
            sd_ = sorted(P[pi]['dim'])
            # Componentes construtivos atribuídos (inclusive vistas estreitas) são preservados.
            # Ferragens internas do módulo seguem a regra de representação, sem cotas.
            if it['tipo']=='mod' and (sd_[1] < 50 or sd_[0] > 60): continue
            if pi not in mantidas:
                for uq,nv,ft in P[pi]['fq']:
                    faces.append((dep(uq),[(uu(v[0],v[1],f),v[2]) for v in uq],
                                  P[pi].get('rgb',cor),ft,P[pi].get('mat'),pi))
                mantidas.add(pi)
            ids.append(pi)
        if ids:
            u0,z0,u1,z1 = geo.caixa_elev(it['bb'],f)
            boxes.append(dict(it=it,u0=u0,z0=z0,u1=u1,z1=z1))
    if not boxes: raise ValueError('Cotas sem geometria construtiva após retirar portas')
    umin_ = min(b['u0'] for b in boxes); umax_ = max(b['u1'] for b in boxes); zmax_ = max(b['z1'] for b in boxes)
    # Pedra não entra na listagem/cadeias. Entra inteira na projeção, sem recorte.
    pedras = []
    bbs = [b['it']['bb'] for b in boxes]
    for p_ in (p for p in P if p['i'] in AMB_I):
        if p_['i'] in mantidas or not any(geo.dist_caixas(p_['bb'],b)<=180 for b in bbs): continue
        su0,sz0,su1,sz1 = geo.caixa_elev(p_['bb'],f)
        sobreposicao = min(su1,umax_)-max(su0,umin_)
        if sobreposicao < .6*max(1,su1-su0): continue  # pedra do outro trecho não amplia esta vista
        pedras.append(p_['i'])
        for fc,ft in zip(p_['faces'],p_['ft']):
            faces.append((dep(fc),[(uu(v[0],v[1],f),v[2]) for v in fc],
                          (.91,.91,.91),ft,None,p_['i']))
    limites = [(b['u0'],b['z0'],b['u1'],b['z1']) for b in boxes]
    limites += [geo.caixa_elev(P[pi]['bb'],f) for pi in pedras]
    vmin_ = min(b[0] for b in limites)-100
    vmax_ = max(b[2] for b in limites)+100
    ztop_ = max(b[3] for b in limites)+50
    faces.sort(key=lambda t:-t[0])
    globals().setdefault('_auditoria_geometria_cotas',[]).append(dict(
        parede=w['id'],mantidas=sorted(mantidas),portas=sorted(_pc),pedras=pedras,
        sem_cortes=True))
    return dict(w=w,f=f,faces=faces,boxes=boxes,umin=umin_,umax=umax_,zmax=zmax_,
                vmin=vmin_,vmax=vmax_,ztop=ztop_,pecas_cotas=mantidas,portas_cotas=_pc,pedras_cotas=pedras)

def _ordem_pecas(fcs, bbs, cam):
    # Ordem de desenho POR PEÇA (pintor): A antes de B quando B está na frente de A.
    # Frente/trás pelo eixo de menor sobreposição das caixas (dobradiça/cabideiro atrás da porta fica atrás).
    import heapq
    fundo = sorted([f_ for f_ in fcs if f_[5] < 0], key=lambda t: -t[1])
    por = {}
    for f_ in fcs:
        if f_[5] >= 0: por.setdefault(f_[5], []).append(f_)
    ids = list(por)
    tela = {}
    for i_ in ids:
        xs_ = [x for f_ in por[i_] for x, _ in f_[2]]; ys_ = [y for f_ in por[i_] for _, y in f_[2]]
        tela[i_] = (min(xs_), min(ys_), max(xs_), max(ys_))
    ctr = {i_: [(bbs[i_][k] + bbs[i_][k + 3]) / 2 for k in range(3)] for i_ in ids}
    dist = {i_: math.dist(ctr[i_], cam) for i_ in ids}
    def frente(a, b):  # 1: a na frente de b | -1: b na frente de a | 0: indefinido
        A, B = bbs[a], bbs[b]
        ov = sorted((min(A[k + 3], B[k + 3]) - max(A[k], B[k]), k) for k in range(3))
        for o_, k in ov:
            ca, cb = ctr[a][k], ctr[b][k]
            if abs(ca - cb) < 1e-6: continue
            if cam[k] > max(ca, cb) or cam[k] < min(ca, cb):
                return 1 if abs(cam[k] - ca) < abs(cam[k] - cb) else -1
            if o_ > 0.5: break
        return 0
    depois = {i_: [] for i_ in ids}; grau = {i_: 0 for i_ in ids}
    for n_, a in enumerate(ids):
        ta = tela[a]
        for b in ids[n_ + 1:]:
            tb = tela[b]
            if ta[2] <= tb[0] or tb[2] <= ta[0] or ta[3] <= tb[1] or tb[3] <= ta[1]: continue
            r_ = frente(a, b)
            if r_ > 0: depois[b].append(a); grau[a] += 1
            elif r_ < 0: depois[a].append(b); grau[b] += 1
    hp = [(-dist[i_], i_) for i_ in ids if grau[i_] == 0]; heapq.heapify(hp)
    feito = set(); out = list(fundo)
    while len(feito) < len(ids):
        if not hp:
            i_ = max((j for j in ids if j not in feito), key=lambda j: dist[j]); grau[i_] = 0
        else: _, i_ = heapq.heappop(hp)
        if i_ in feito: continue
        feito.add(i_); out += sorted(por[i_], key=lambda t: -t[1])
        for j in depois[i_]:
            grau[j] -= 1
            if grau[j] == 0 and j not in feito: heapq.heappush(hp, (-dist[j], j))
    return out

# REGRA (João): a imagem da textura = UMA CHAPA de MDF de 1830 mm (largura) x 2750 mm (altura, sentido do veio).
# Cada peça usa o pedaço da chapa proporcional ao seu tamanho (peça maior que a chapa repete a chapa).
CHAPA_L, CHAPA_A = 1830.0, 2750.0
def _persp(dst, src_):
    # coeficientes PIL PERSPECTIVE: saída (dst) -> entrada (src_)
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src_):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return _np.linalg.solve(_np.array(A, float), _np.array(B, float)).tolist()

def _raster3d(page, rect, fcs, T, pmat, dpi=170):
    s_ = dpi / 72.0; W_ = max(1, int(rect.width * s_)); H_ = max(1, int(rect.height * s_))
    img = _Im.new('RGB', (W_, H_), (255, 255, 255)); dr = _ImD.Draw(img)
    px = lambda x, y: ((T(x, y)[0] - rect.x0) * s_, (T(x, y)[1] - rect.y0) * s_)
    for f_ in fcs:
        q, c_, ft, pc, vs, fs_ = f_[2], f_[3], f_[4], f_[5], f_[6], f_[7]
        Q = [px(x, y) for x, y in q]
        if area2(Q) < 0.5: continue
        alpha=f_[8] if len(f_)>8 else 1.
        tex = textura(pmat.get(pc)) if alpha>=.999 and cfg.get('textura',True) and pc is not None and pc >= 0 and len(vs) == 4 else None
        x0_ = int(max(0, min(a for a, _ in Q))); y0_ = int(max(0, min(b for _, b in Q)))
        x1_ = int(min(W_, max(a for a, _ in Q) + 1)); y1_ = int(min(H_, max(b for _, b in Q) + 1))
        if tex is not None and x1_ - x0_ >= 3 and y1_ - y0_ >= 3:
            L1 = math.dist(vs[0], vs[1]); L2 = math.dist(vs[0], vs[3])
            sx_, sy_ = tex.width / CHAPA_L, tex.height / CHAPA_A   # px por mm da chapa
            # veio (altura da chapa) acompanha o lado mais comprido da peça
            if L1 >= L2: corners = [vs[0], vs[3], vs[2], vs[1]]; Lw, Lh = L2, L1
            else: corners = [vs[0], vs[1], vs[2], vs[3]]; Lw, Lh = L1, L2
            pw = max(2, int(Lw * sx_)); ph = max(2, int(Lh * sy_))
            if pw <= tex.width and ph <= tex.height:
                ox_ = (pc * 137) % max(1, tex.width - pw + 1); oy_ = (pc * 71) % max(1, tex.height - ph + 1)   # pedaço da chapa varia por peça
                tile = tex.crop((ox_, oy_, ox_ + pw, oy_ + ph))
            else:
                tile = _Im.new('RGB', (pw, ph))
                for ty in range(0, ph, tex.height):
                    for tx in range(0, pw, tex.width): tile.paste(tex, (tx, ty))
            if max(pw, ph) > 1400: tile = tile.resize((max(2, pw * 1400 // max(pw, ph)), max(2, ph * 1400 // max(pw, ph)))); pw, ph = tile.size
            if fs_ < 0.999: tile = tile.point(lambda v: int(v * fs_))
            iq = [q[vs.index(c3_)] for c3_ in corners]
            dst = [(px(*p2)[0] - x0_, px(*p2)[1] - y0_) for p2 in iq]
            try:
                co = _persp(dst, [(0, 0), (pw, 0), (pw, ph), (0, ph)])
                patch = tile.transform((x1_ - x0_, y1_ - y0_), _Im.PERSPECTIVE, co, _Im.BILINEAR)
                mask = _Im.new('L', patch.size, 0); _ImD.Draw(mask).polygon([(a - x0_, b - y0_) for a, b in Q], fill=255)
                img.paste(patch, (x0_, y0_), mask)
            except Exception:
                dr.polygon(Q, fill=tuple(int(255 * v) for v in c_))
        else:
            if alpha<.999:
                mask=_Im.new('L',img.size,0); _ImD.Draw(mask).polygon(Q,fill=int(255*alpha))
                tint=_Im.new('RGB',img.size,tuple(int(255*v) for v in c_))
                img.paste(tint,(0,0),mask)
            else: dr.polygon(Q, fill=tuple(int(255 * v) for v in c_))
        for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
            if fl_: dr.line([a_, b_], fill=(50, 50, 50), width=max(1, int(0.35 * s_)))
    import io as _io
    bio = _io.BytesIO(); img.save(bio, format='JPEG', quality=88)
    page.insert_image(rect, stream=bio.getvalue())






# ===== PUXADORES (v23, João): o DXF do Promob NÃO traz o puxador; o motor GERA pela regra =====
# Tipo/medida/cor = item "Puxador..." do XML (ex.: Linear Pino Champagne 200 x 15,8 x 37,5). Puxador de perfil/cava/aba = sem barra.
# Porta/frente = chapa fina na frente do módulo (geometria). Porta de giro: puxador VERTICAL do lado OPOSTO às dobradiças
# (dobradiças do DXF), 40 mm da borda; alto (armário) na altura da mão (~1,05 m), balcão perto do topo, aéreo perto de baixo.
# Gaveta/basculante (mais larga que alta): HORIZONTAL centrado, perto do topo (aéreo: perto de baixo).
def _puxador_xml():
    for e in XML_TREE.iter('ITEM'):
        d_ = e.get('DESCRIPTION', '')
        if d_.lower().startswith('puxador'):
            if re.search(r'perfil|cava|aba|embutid|usinad', d_, re.I): return None
            try: L_ = float(e.get('WIDTH') or 150)
            except Exception: L_ = 150.0
            n_ = d_.lower()
            cor_ = (0.80, 0.70, 0.52) if 'champ' in n_ else (0.83, 0.68, 0.33) if ('dourad' in n_ or 'ouro' in n_) else \
                   (0.12, 0.12, 0.12) if 'preto' in n_ else (0.62, 0.52, 0.46) if 'rose' in n_ else (0.74, 0.74, 0.76)
            return dict(L=max(60.0, min(L_, 1200.0)), cor=cor_)
    return None
PUX_TIPO = _puxador_xml() if cfg.get('xml') else None
_DOBR = [p_ for p_ in P if (lambda d: 12 <= d[0] <= 32 and 40 <= d[1] <= 65 and 65 <= d[2] <= 95)(sorted(p_['dim']))]
def _gerar_puxadores():
    out = []
    if not PUX_TIPO: return out
    L_ = PUX_TIPO['L']; ja = set()
    for w in paredes:
        f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad; sg_ = f_[ad]
        perto = lambda bb: min(bb[ad] * sg_, bb[ad + 3] * sg_)
        for m in w['itens']:
            if m['tipo'] != 'mod': continue
            mb = m['bb']; fr = perto(mb)
            for p_ in P:
                b = p_['bb']
                if p_['i'] in ja or b[ad + 3] - b[ad] > 30 or (b[al + 3] - b[al]) < 100 or (b[5] - b[2]) < 100: continue
                if not (fr - 40 <= perto(b) <= fr + 5): continue
                if b[al] < mb[al] - 30 or b[al + 3] > mb[al + 3] + 30 or b[2] < mb[2] - 30 or b[5] > mb[5] + 30: continue
                ja.add(p_['i'])
                du, dz = b[al + 3] - b[al], b[5] - b[2]
                face = b[ad] if sg_ > 0 else b[ad + 3]; sai = -sg_     # lado de fora da porta
                if dz >= du:   # porta de giro
                    hs = [h for h in _DOBR if b[al] - 40 <= (h['bb'][al] + h['bb'][al + 3]) / 2 <= b[al + 3] + 40
                          and b[2] <= (h['bb'][2] + h['bb'][5]) / 2 <= b[5] and 0 <= (min(h['bb'][ad] * sg_, h['bb'][ad + 3] * sg_) - perto(b)) <= 160]
                    if not hs: continue
                    hc = sum((h['bb'][al] + h['bb'][al + 3]) / 2 for h in hs) / len(hs)
                    uc = b[al + 3] - 40 if abs(hc - b[al]) < abs(hc - b[al + 3]) else b[al] + 40
                    Lr = min(L_, dz - 120)
                    if dz >= 1200: zc = min(max(1050, b[2] + Lr / 2 + 80), b[5] - Lr / 2 - 80)
                    elif b[5] <= 1100: zc = b[5] - 60 - Lr / 2
                    elif b[2] >= 1200: zc = b[2] + 60 + Lr / 2
                    else: zc = (b[2] + b[5]) / 2
                    seg = dict(eixo='z', c_al=uc, z0=zc - Lr / 2, z1=zc + Lr / 2)
                else:          # gaveta / basculante
                    Lr = min(L_, du - 120); uc = (b[al] + b[al + 3]) / 2
                    zc = b[2] + 40 if b[2] >= 1200 else b[5] - 40
                    seg = dict(eixo='u', u0=uc - Lr / 2, u1=uc + Lr / 2, zc=zc)
                caixas = []
                def cx(a0, a1, dd0, dd1, z0, z1):
                    bb = [0.0] * 6; bb[al], bb[al + 3] = a0, a1; bb[2], bb[5] = z0, z1
                    p0, p1 = face + sai * dd0, face + sai * dd1; bb[ad], bb[ad + 3] = min(p0, p1), max(p0, p1); return bb
                if seg['eixo'] == 'z':
                    u = seg['c_al']
                    caixas.append(cx(u - 7.9, u + 7.9, 27, 37.5, seg['z0'], seg['z1']))                 # barra
                    for zz in (seg['z0'] + 6, seg['z1'] - 16): caixas.append(cx(u - 5, u + 5, 0, 27, zz, zz + 10))   # pés
                else:
                    z = seg['zc']
                    caixas.append(cx(seg['u0'], seg['u1'], 27, 37.5, z - 7.9, z + 7.9))
                    for uu_ in (seg['u0'] + 6, seg['u1'] - 16): caixas.append(cx(uu_, uu_ + 10, 0, 27, z - 5, z + 5))
                out.append(dict(porta=p_['i'], caixas=caixas))
    return out

_PT = None
def _portas():   # chapas finas na frente dos módulos (portas/frentes) - definição única: _eh_porta
    global _PT
    if _PT is None:
        _PT = set(PORTAS_XML)
        for w in paredes:
            for m in [i for i in w['itens'] if i['tipo'] == 'mod']:
                for p_ in P:
                    if _eh_porta(p_['bb'], m['bb'], w): _PT.add(p_['i'])
    return _PT

def tem_porta(m, w):
    # REGRA (v33, João): móvel com porta/frente nunca é nicho. Porta = _eh_porta (definição única, bloco cotas
    # 28/09/2026). Tem porta quando as portas cobrem >= NICHO_MIN_RATIO da face frontal do módulo.
    # REGRA (vidro, v35+): porta de vidro NÃO está no DXF; fallback no XML: módulo marcado xml_tem_porta = tem porta.
    f_ = FV[w['key']]; ad = 0 if f_[0] else 1; al = 1 - ad
    mb = m['bb']; area_ = (mb[al + 3] - mb[al]) * (mb[5] - mb[2]); cob = 0.0
    for p_ in P:
        b = p_['bb']
        if not _eh_porta(b, mb, w): continue
        cob += max(0, min(b[al + 3], mb[al + 3]) - max(b[al], mb[al])) * max(0, min(b[5], mb[5]) - max(b[2], mb[2]))
    if cob >= NICHO_MIN_RATIO * area_: return True
    return bool(m.get('xml_tem_porta'))  # cristaleira/vitrô: porta de vidro → XML diz que tem porta, DXF não tem

def detalhes(w):
    # Engenharia: subimagem nasce de nicho identificado pela geometria/dimensão.
    # A ausência de uma porta no DXF é erro de leitura e não cria uma regra visual paralela.
    gs = [list(g) for g in nichos(w) + abertos(w)]
    toca = lambda A, B: all(min(A[k + 3], B[k + 3]) - max(A[k], B[k]) > -5 for k in range(3))
    mudou = True
    while mudou:
        mudou = False
        for i0 in range(len(gs)):
            for j0 in range(i0 + 1, len(gs)):
                if any(toca(a['bb'], b['bb']) for a in gs[i0] for b in gs[j0]):
                    gs[i0] += gs.pop(j0); mudou = True; break
            if mudou: break
    return gs

def abertos(w):
    # REGRA (João): NICHO = estrutura ABERTA, SEM PORTA (sem porta/basculante/gaveta), com ou sem prateleira.
    # Módulo sem porta (até 2 m x 1,2 m) + tamponamentos/painéis encostados = DETALHE. Armário com porta NUNCA é nicho.
    f_ = FV[w['key']]; al = 1 if f_[0] else 0; out = []; ja = set()
    for g in nichos(w):
        for i in g: ja.add(id(i))
    for m in w['itens']:
        if m['tipo'] != 'mod' or id(m) in ja: continue
        if not re.search(r'\bnicho\b', m.get('desc', ''), re.I): continue
        mb = m['bb']
        if mb[al + 3] - mb[al] > 2000 or mb[5] - mb[2] > 1200 or tem_porta(m, w): continue
        g = [m] + [o for o in w['itens'] if o['tipo'] == 'comp' and id(o) not in ja
                   and all(min(o['bb'][k + 3], mb[k + 3]) - max(o['bb'][k], mb[k]) > -5 for k in range(3))
                   and (o['bb'][5] - o['bb'][2]) <= (mb[5] - mb[2]) + 150   # REGRA (v26): painel alto (tamponamento até o teto) não entra no detalhe do nicho
                   and o['bb'][al] >= mb[al] - 150 and o['bb'][al + 3] <= mb[al + 3] + 150]
        for i in g: ja.add(id(i))
        out.append(g)
    return out

def nichos(w):
    # REGRA (João): TODO NICHO ABERTO vira detalhe. Nicho = conjunto de painéis/tamponamentos encostados entre si
    # (peças "Vista" de acabamento não entram no agrupamento), com 3+ peças e 2+ horizontais, até 2 m de largura e 1,2 m de altura.
    cs = [i for i in w['itens'] if i['tipo'] == 'comp'
          and re.search(r'painel|tamponamento', i.get('desc', ''), re.I)]; grupos_ = []
    toca = lambda A, B: all(min(A[k + 3], B[k + 3]) - max(A[k], B[k]) > -3 for k in range(3))
    for i in cs:
        junto = [g for g in grupos_ if any(toca(i['bb'], j['bb']) for j in g)]
        novo = [i] + [j for g in junto for j in g]
        grupos_ = [g for g in grupos_ if g not in junto] + [novo]
    out = []
    for g in grupos_:
        U_ = list(g[0]['bb'])
        for i in g: U_ = geo.uniao(U_, i['bb'])
        ext = [U_[k + 3] - U_[k] for k in range(3)]
        hz = sum(1 for i in g if i['bb'][5] - i['bb'][2] <= 30)
        ax_ = 1 if FV[w['key']][0] else 0
        if not (len(g) >= 4 and hz >= 2 and ext[ax_] <= 2000 and ext[2] <= 1200): continue
        # REGRA (v31): nicho tem a FRENTE ABERTA. Chapas do conjunto em pé de frente p/ a câmera, na face da frente,
        # cobrindo >= 40% da frente = caixa fechada -> não é nicho.
        ad_ = 1 - ax_; sg_ = FV[w['key']][ad_]; perto = lambda bb: min(bb[ad_] * sg_, bb[ad_ + 3] * sg_)
        fr_ = min(perto(i['bb']) for i in g); cob_ = 0.0
        for i in g:
            b = i['bb']
            if b[ad_ + 3] - b[ad_] <= 30 and perto(b) <= fr_ + 40 and b[5] - b[2] > 30: cob_ += (b[ax_ + 3] - b[ax_]) * (b[5] - b[2])
        if cob_ >= NICHO_MIN_RATIO * ext[ax_] * ext[2]: continue
        # REGRA (v33, João): MOVEL COM PORTA NAO E NICHO. Se qualquer modulo com porta ocupa o
        # mesmo espaco do conjunto, o conjunto inteiro deixa de ser nicho.
        if any(tem_porta(m, w) and all(min(U_[k + 3], m['bb'][k + 3]) - max(U_[k], m['bb'][k]) > -5 for k in range(3))
               for m in w['itens'] if m['tipo'] == 'mod'): continue
        out.append(g)
    return out

def render3d(page, rect, pids, letra=None, itens=None, ang=None, dmin=4200, contexto=False, **kw):
    # contexto=True (REGRA João): mostra o AMBIENTE em volta (móveis e pedra das paredes vizinhas, perto desta parede)
    # para orientar; balões/listagem continuam só nos móveis da parede da vista.
    # Vista dividida: o alvo acompanha a listagem; vizinhos continuam como contexto.
    # itens_vista não transforma a imagem principal em subimagem isolada.
    its = kw.get('itens_vista')
    if its is None:
        its = itens if itens is not None else [i for w in pids for i in PW[w]['itens']]
    if not its: return
    U = list(its[0]['bb'])
    for i in its: U = geo.uniao(U, i['bb'])
    E = [U[0] - 80, U[1] - 80, U[2] - 80, U[3] + 80, U[4] + 80, U[5] + 80]
    f = FV[kw.get('camera_key', PW[pids[0]]['key'])]; a = 0.0
    if len(pids) > 1 and kw.get('papel') == 'geral':
        f2 = FV[PW[pids[1]]['key']]
        cruz = f[0] * f2[1] - f[1] * f2[0]
        if cruz: a = math.radians(22 if cruz > 0 else -22)  # conjunto em L: complemento geral
    if ang is not None: a = math.radians(ang)
    hx = f[0] * math.cos(a) - f[1] * math.sin(a); hy = f[0] * math.sin(a) + f[1] * math.cos(a)
    # REGRA (v33, João): a vista frontal fica EXATAMENTE no centro - sem inclinação nenhuma.
    # Câmera na altura do meio do móvel e sem elevação: as arestas verticais saem no prumo.
    e = math.radians(kw.get('elev', 0))
    fw = (hx * math.cos(e), hy * math.cos(e), -math.sin(e))
    rn = math.hypot(hy, hx); r = (hy / rn, -hx / rn, 0.0)
    up = (r[1] * fw[2] - r[2] * fw[1], r[2] * fw[0] - r[0] * fw[2], r[0] * fw[1] - r[1] * fw[0])
    dot = lambda a_, b_: a_[0] * b_[0] + a_[1] * b_[1] + a_[2] * b_[2]
    ctx = contexto and len(pids) == 1 and not kw.get('isolado')
    tc, D, cam = posicionar(U, fw, dmin, ambiente=ctx,
                            caixas=[p['bb'] for p in P] if ctx else ())
    _tg = {pi for i in its for pi in i['pecas']}
    _retirados = obstaculos(inst, P, _tg, fw) if contexto else set()
    _retirados.difference_update(_tg)
    if ctx:
        w0 = PW[pids[0]]; axd = 0 if f[0] else 1; axl = 1 - axd; sg = f[axd]
        prof_ = lambda bb: min((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg)
        # REGRA (v33, João): a vista e sempre frontal, entao a parede que fica NA FRENTE do móvel
        # nao e recortada: ela simplesmente NAO ENTRA. Assim a câmera pode se afastar ou aproximar
        # sem ninguem ter que acertar posicao de corte.
        _pf_mov = max((w0['plano'] - U[axd]) * sg, (w0['plano'] - U[axd + 3]) * sg)
        _na_frente = lambda bb: min((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg) > _pf_mov + 50
        _donos = {}
        for item in sorted(inst, key=lambda i: i['tipo'] != 'mod'):
            for pi_ in item['pecas']: _donos.setdefault(pi_, item['bb'])
        def dentro_(bb, pi=None):
            if pi in _tg: return True
            if pi in _retirados: return False
            bb = _donos.get(pi, bb)  # vizinho é selecionado inteiro, nunca chapa por chapa
            if not (prof_(bb) <= max(1800, _pf_mov+900) and bb[axl + 3] >= U[axl] - 1800 and bb[axl] <= U[axl + 3] + 1800): return False
            # REGRA (v26, só parede cortada / bloco): o que fica todo ATRÁS do plano da vista (outro ambiente) não aparece
            if (w0.get('cortada') or w0.get('bloco')) and max((w0['plano'] - bb[axd]) * sg, (w0['plano'] - bb[axd + 3]) * sg) < -100: return False
            cz = sum(((bb[k_] + bb[k_ + 3]) / 2 - cam[k_]) * fw[k_] for k_ in range(3))
            return cz > 200  # obstáculos são retirados por entidade, sem apagar vizinhos por distância
    cor = {}
    for i in inst:
        for pi in i['pecas']: cor[pi] = MADEIRA if i['tipo'] == 'comp' else (0.97, 0.97, 0.97)
    src = []; shell = []; _pmat = {}; _pidx = {}
    _iso = {pi for i in its for pi in i['pecas']} if kw.get('isolado') else None   # REGRA (v18): móvel complexo SOZINHO
    for p_ in P:
        b = p_['bb']
        sd_ = sorted(p_['dim'])
        if _iso is not None and p_['i'] not in _iso: continue
        if kw.get('sem_portas') and (p_['i'] in _portas() or p_['i'] in kw.get('ocultar_pecas',())): continue
        if p_['i'] in DUP_I or p_['i'] in _retirados: continue
        # Especial vizinho pode orientar no ambiente; tabela/balões permanecem só dos alvos da vista.
        _referencia_especial = ctx and p_['i'] in _ESPECIAL_I and p_['i'] not in _tg
        if p_['i'] in AMB_I or p_['i'] in ELETRO_I:
            if itens and not ctx and not kw.get('representacao_interna'): continue   # detalhe (nicho/costas): só os móveis, sem pedra/eletros
            if (dentro_(b, p_['i']) if ctx else all(b[k] <= E[k + 3] and b[k + 3] >= E[k] for k in range(3))):
                c0_ = PEDRA_COR if p_['i'] in AMB_I else ELETRO_COR
                for fc, fl in zip(p_['faces'], p_['ft']): src.append((fc, c0_, fl, 1, len(shell)))
                _pidx[len(shell)] = p_['i']
                shell.append(b)
            continue
        if not kw.get('representacao_interna') and not _referencia_especial and (sd_[1] < 50 or sd_[0] > 60): continue  # REGRA: 3D só com MDF (chapas); suportes, dobradiças, cabideiros, pés = fora
        if (dentro_(b, p_['i']) if ctx else (all(b[k] >= E[k] for k in range(3)) and all(b[k + 3] <= E[k + 3] for k in range(3)))):
            base = p_.get('rgb') or cor.get(p_['i'], (0.80, 0.80, 0.83))
            _pmat[len(shell)] = p_.get('mat'); _pidx[len(shell)] = p_['i']
            visual=p_.get('_visual_vidro')
            if visual:
                if visual.get('_sem_perfil'):
                    fc=max(p_['fq'],key=lambda v:sum(p[2] for p in v[0])/len(v[0]))[0]
                    src.append((fc,visual['rgb'],[True]*len(fc),1,len(shell),visual['alpha']))
                else:
                    for fc,rgb,alpha in faces_porta(b,f,visual):
                        src.append((fc,rgb,[True]*4,1,len(shell),alpha))
            else:
                for uq, nv, ft in p_['fq']: src.append((uq, base, ft, 1, len(shell)))
            shell.append(b)
    for px_ in PUXADORES:   # REGRA (v23): puxador aparece junto com a porta dele
        if px_['porta'] in _pidx.values():
            for bx_ in px_['caixas']:
                for fc in caixa_faces(bx_): src.append((fc, PUX_TIPO['cor'], [True] * 4, 1, len(shell)))
                shell.append(bx_)
    # REGRA (v36, PORTA AUSENTE DO DXF): módulo com xml_tem_porta=True mas sem porta no DXF
    # recebe face sintética frontal fechada na prancha de listagem (portas fechadas).
    # Não se aplica em cotas (sem_portas=True) nem em subimagens de nicho (itens!=None).
    # ORDEM 006 (v37.2): face sintética liberada também em subimagem de porta ausente (xml_tem_porta).
    # Subimagem de nicho/aberto continua sem face sintética (seus 'its' não têm xml_tem_porta).
    _permite_face = (not itens) or any(_i.get('xml_tem_porta') for _i in its if _i.get('tipo') == 'mod')
    if not kw.get('sem_portas') and _permite_face:
        _w0 = PW[pids[0]]; _axd = 0 if f[0] else 1; _axl = 1 - _axd
        for _m in its:
            if _m['tipo'] != 'mod' or not _m.get('xml_tem_porta'): continue
            _mb = _m['bb']
            _area_m = (_mb[_axl + 3] - _mb[_axl]) * (_mb[5] - _mb[2])
            if _area_m <= 0: continue
            _cob = 0.0
            for _pp in P:
                if not _eh_porta(_pp['bb'], _mb, _w0): continue
                _b = _pp['bb']
                _cob += max(0, min(_b[_axl + 3], _mb[_axl + 3]) - max(_b[_axl], _mb[_axl])) * \
                        max(0, min(_b[5], _mb[5]) - max(_b[2], _mb[2]))
            if _cob >= NICHO_MIN_RATIO * _area_m: continue
            _sg = f[_axd]
            _xf = _mb[_axd + 3] if _sg < 0 else _mb[_axd]
            if _m['pecas']: _pidx[len(shell)] = _m['pecas'][0]
            _mat_ = _m.get('xml_mat_porta', 'mdf')
            visual=_m.get('_porta_visual')
            if _mat_ in ('vidro','espelho','aluminio') and visual:
                if _mat_=='aluminio':
                    visual=dict(visual,rgb=visual['perfil_rgb'],alpha=1.)
                folhas=faces_porta(_mb,f,visual)
                for _face,_cor_m,_alpha in folhas:
                    src.append((_face,_cor_m,[True]*4,1,len(shell),_alpha))
                sb=list(_mb); sb[_axd]=_xf-.2; sb[_axd+3]=_xf+.2
                shell.append(sb)
            else:
                _cor_m = next((pp_.get('rgb') for pp_ in P if pp_['i'] in _m['pecas'] and pp_.get('rgb')), (0.97,0.97,0.97))
                if _axd==0:
                    _face=[(_xf,_mb[1],_mb[2]),(_xf,_mb[4],_mb[2]),(_xf,_mb[4],_mb[5]),(_xf,_mb[1],_mb[5])]
                else:
                    _face=[(_mb[0],_xf,_mb[2]),(_mb[3],_xf,_mb[2]),(_mb[3],_xf,_mb[5]),(_mb[0],_xf,_mb[5])]
                src.append((_face,_cor_m,[True]*4,1,len(shell)))
                shell.append(list(_mb))
    mg = kw.get('margem', 700); R = [U[0] - mg, U[1] - mg, 0 if mg >= 700 else U[2] - mg, U[3] + mg, U[4] + mg, U[5] + min(150, mg)]
    if ctx and MALHA_PAR:
        _cob = []; _ilha = U[5] <= 1200   # móvel baixo solto (ilha/bancada): sem parede inventada nem laterais distantes
        for p_ in MALHA_PAR:
            if _na_frente(p_['bb']): continue  # retira a parede inteira, nunca corta faces do móvel
            for fc, fl in zip(p_['faces'], p_['ft']):
                c_ = [sum(v[k_] for v in fc) / len(fc) for k_ in range(3)]
                if min((w0['plano'] - v[axd]) * sg for v in fc) > 1300: continue
                if min((w0['plano'] - v[axd]) * sg for v in fc) > _pf_mov + 50: continue   # v33: parede da frente sai inteira
                if c_[axl] < U[axl] - 700 or c_[axl] > U[axl + 3] + 700: continue
                if max(v[axd] for v in fc) - min(v[axd] for v in fc) < 1:   # face "de frente" para a câmera
                    pf = (w0['plano'] - c_[axd]) * sg
                    if pf > 100: continue            # parede NA FRENTE do fundo dos móveis: esconderia móvel
                    lo_, hi_ = max(U[axl], min(v[axl] for v in fc)), min(U[axl + 3], max(v[axl] for v in fc))
                    if hi_ > lo_: _cob.append((lo_, hi_))
                elif _ilha: continue
                src.append((fc, PAREDE_COR, fl, 0, -1))
        _tot = 0; _fim = U[axl]
        for lo_, hi_ in sorted(_cob):
            lo_ = max(lo_, _fim)
            if hi_ > lo_: _tot += hi_ - lo_; _fim = hi_
        if not _ilha and not w0.get('divisoria') and _tot < 0.5 * (U[axl + 3] - U[axl]):   # REGRA: parede real cobre < metade dos móveis -> parede de fundo de referência
            bf = [0.0] * 6; bf[axl] = U[axl] - 400; bf[axl + 3] = U[axl + 3] + 400; bf[2] = 0; bf[5] = U[5] + 150
            pl0 = w0['plano']; bf[axd], bf[axd + 3] = (pl0, pl0 + 100) if sg > 0 else (pl0 - 100, pl0)
            for fc in caixa_faces(bf): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    if ctx and (PAR_DXF or MALHA_PAR):
        # REGRA (João): paredes reais do DXF que compõem o L (fundo e laterais), com janela/abertura; tira só as que ficam na frente
        for p_ in PAR_DXF:
            b = p_['bb']
            if prof_(b) > 1300 or b[axl + 3] < U[axl] - 1800 or b[axl] > U[axl + 3] + 1800: continue
            if _na_frente(b): continue   # v33: parede da frente sai inteira, sem recorte
            for fc in caixa_faces(b): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    elif _iso is None:
        if ctx: R[axl] -= 1800; R[axl + 3] += 1800
        for p_ in PAREDES_PECAS:
            b = p_['bb']
            if p_['i'] in _retirados or (ctx and _na_frente(b)): continue
            if not all(b[k] <= R[k+3] and b[k+3] >= R[k] for k in range(3)): continue
            for fc in caixa_faces(b): src.append((fc, PAREDE_COR, [True] * 4, 0, -1))
    # REGRA (João, 2026-09-28, REAPLICADO): piso não depende mais de "vista com 1 parede só" (ctx).
    # Antes o piso usava eixo/plano de PW[pids[0]] -> em vista de canto (2 paredes, L), ctx era False
    # e o piso não saía (bug: "gerei 11 suíte e não saiu com piso"). Agora é uma laje plana sob toda
    # a área visível (bounding box dos itens + margem), independente de quantas paredes tem a vista.
    # Lógica de parede (_na_frente/etc.) não foi tocada.
    if contexto and not kw.get('isolado'):
        _pz = [U[0] - 4000, U[1] - 4000, -20, U[3] + 4000, U[4] + 4000, 0]
        src.append((caixa_faces(_pz)[1], PISO_COR, [True] * 4, 0, -1))
    L = (0.35, -0.45, 0.82); nl = math.sqrt(dot(L, L))
    def pj(v):
        rel = (v[0] - cam[0], v[1] - cam[1], v[2] - cam[2]); z = dot(rel, fw)
        return (dot(rel, r) / z, dot(rel, up) / z, z)
    fcs = []
    for entrada in src:
        vs,base,ft,gr,pc=entrada[:5]
        alpha=entrada[5] if len(entrada)>5 else 1.
        pp = [pj(v) for v in vs]
        if min(t[2] for t in pp) < 50: continue
        nm = _n(vs[0], vs[1], vs[2]); fs_ = 0.72 + 0.28 * abs(dot(nm, L)) / nl
        fcs.append((gr, sum(t[2] for t in pp) / len(pp), [(t[0], t[1]) for t in pp], tuple(min(1, x * fs_) for x in base), ft, pc, vs, fs_, alpha))
    if not fcs: return
    fcs = _ordem_pecas(fcs, shell, cam)
    xs = [x for f_ in fcs for x, _ in f_[2]]; ys = [y for f_ in fcs for _, y in f_[2]]
    if itens:   # detalhe: enquadra só as peças do detalhe (zoom)
        _alvo = {pi for i in its for pi in i['pecas']}; _bi = {pc_: b_ for pc_, b_ in enumerate(shell)}
        cc = [pj((b_[i0], b_[1 + j0], b_[2 + k0])) for pc_, b_ in _bi.items() if _pidx.get(pc_) in _alvo for i0 in (0, 3) for j0 in (0, 3) for k0 in (0, 3)]
        cc = [c_ for c_ in cc if c_[2] > 50]
        if cc: xs = [c_[0] for c_ in cc]; ys = [c_[1] for c_ in cc]
    if ctx:  # conjunto completo e contexto próximo, com vizinhos enquadrados por inteiro
        vizinhos = [i['bb'] for i in inst if not set(i['pecas']) & _retirados
                    and any(pi in _pidx.values() for pi in i['pecas'])]
        Uq = enquadrar(U, axl, vizinhos)
        cc = [pj((Uq[i0], Uq[1 + j0], Uq[2 + k0])) for i0 in (0, 3) for j0 in (0, 3) for k0 in (0, 3)]
        cc = [c_ for c_ in cc if c_[2] > 50]
        xs = [c_[0] for c_ in cc]; ys = [c_[1] for c_ in cc]
    # O bbox XML pode ser maior que as faces efetivamente exportadas no DXF.
    # Enquadra também o envelope completo do conjunto, em todas as categorias.
    _proj_alvo = [pj(v) for v in cantos(U)]
    xs += [q[0] for q in _proj_alvo]; ys += [q[1] for q in _proj_alvo]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mgf = kw.get('margem_pontos', 22 if itens else 4 if ctx else 16)
    k = min((rect.width - mgf) / (x1 - x0), (rect.height - mgf) / (y1 - y0))
    ox = rect.x0 + (rect.width - (x1 - x0) * k) / 2; oy = rect.y0 + (rect.height - (y1 - y0) * k) / 2
    T = lambda x, y: (ox + (x - x0) * k, oy + (y1 - y) * k)
    _enquadrado = all(rect.x0-.1 <= T(q[0],q[1])[0] <= rect.x1+.1 and
                      rect.y0-.1 <= T(q[0],q[1])[1] <= rect.y1+.1 for q in _proj_alvo)
    if not _enquadrado: raise ValueError('Câmera recortou o conjunto listado')
    globals().setdefault('_auditoria_cameras', []).append(dict(
        paredes=list(pids), contexto=ctx, ang=math.degrees(a), elev=math.degrees(e),
        camera=cam, foco=tc, camera_key=kw.get('camera_key',PW[pids[0]]['key']),
        alvo=U, enquadrado=_enquadrado,
        retirados=sorted(_retirados), alvos=sorted(_tg), quadro=tuple(rect)))
    if kw.get('caixas_projetadas') is not None:
        for face in fcs:
            pi = _pidx.get(face[5])
            if pi is None: continue
            for x_,y_ in face[2]:
                px_,py_ = T(x_,y_)
                b_ = kw['caixas_projetadas'].setdefault(pi,[px_,py_,px_,py_])
                b_[0]=min(b_[0],px_); b_[1]=min(b_[1],py_)
                b_[2]=max(b_[2],px_); b_[3]=max(b_[3],py_)
    if kw.get('visiveis') is not None and _Im is not None:
        # REGRA (v25): quais peças APARECEM nesta imagem (buffer de identificação, desenho na mesma ordem das faces)
        _s = 2.0; _W = max(1, int(rect.width * _s)); _H = max(1, int(rect.height * _s))
        _ib = _Im.new('I', (_W, _H), 0); _dr = _ImD.Draw(_ib)
        for f_ in fcs:
            Q_ = [((T(x_, y_)[0] - rect.x0) * _s, (T(x_, y_)[1] - rect.y0) * _s) for x_, y_ in f_[2]]
            if len(Q_) >= 3: _dr.polygon(Q_, fill=(f_[5] + 1) if f_[5] is not None and f_[5] >= 0 else 0)
        _vv, _cc = _np.unique(_np.asarray(_ib), return_counts=True)
        _bx = {}
        for f_ in fcs:
            if f_[5] is None or f_[5] < 0: continue
            for x_, y_ in f_[2]:
                px_, py_ = T(x_, y_); b_ = _bx.setdefault(f_[5], [px_, py_, px_, py_])
                b_[0] = min(b_[0], px_); b_[1] = min(b_[1], py_); b_[2] = max(b_[2], px_); b_[3] = max(b_[3], py_)
        for v_, c_ in zip(_vv, _cc):
            pc_ = int(v_) - 1
            if v_ <= 0 or pc_ not in _pidx or pc_ not in _bx: continue
            b_ = _bx[pc_]; area_ = max(1.0, (b_[2] - b_[0]) * (b_[3] - b_[1]) * _s * _s)
            if c_ >= 40 and c_ / area_ >= 0.05: kw['visiveis'].add(_pidx[pc_])   # peça aparece DE VERDADE (15%+ dela)
        if callable(kw.get('visibilidade_callback')):
            kw['visibilidade_callback'](_ib,_pidx,rect,kw['visiveis'])
        if kw.get('so_visiveis'): return
    if _Im is not None and (any(len(f_)>8 and f_[8]<.999 for f_ in fcs) or (cfg.get('textura', True) and any(textura(m_) for m_ in _pmat.values()))):
        _raster3d(page, rect, fcs, T, _pmat)
    else:
        if ctx: _tmp = fz.open(); _tp = _tmp.new_page(width=page.rect.width, height=page.rect.height); sh = _tp.new_shape()
        else: sh = page.new_shape()
        for f_ in fcs:
            q, c_, ft = f_[2], f_[3], f_[4]
            Q = [T(x, y) for x, y in q]
            if area2(Q) < 0.1: continue
            sh.draw_polyline(Q + [Q[0]]); sh.finish(color=c_, fill=c_, width=0.5, closePath=True,fill_opacity=f_[8] if len(f_)>8 else 1.)
            if any(ft):
                for (a_, b_), fl_ in zip(zip(Q, Q[1:] + Q[:1]), ft):
                    if fl_: sh.draw_line(a_, b_)
                sh.finish(color=(0.2, 0.2, 0.2), width=0.35, closePath=False)
        sh.commit()
        if ctx: page.show_pdf_page(rect, _tmp, 0, clip=rect)
    if letra:
        _marcados = []; _pontos = {}; _ja_bal = set()
        for i in its:
            nb = i.get('num_' + letra)
            if not nb or id(i) in kw.get('sem_balao', ()): continue
            if PW.get(i.get('parede'), {}).get('divisoria'):   # REGRA (v18): divisória = UM balão por tipo de peça
                if nb in _ja_bal: continue
                _ja_bal.add(nb)
            b = i['bb']; fi = FV[kw.get('camera_key', PW[i['parede']]['key'])]; axi = 0 if fi[0] else 1
            c3 = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]
            c3[axi] = b[axi] if (fi[axi] > 0) != bool(kw.get('costas')) else b[axi + 3]
            _us = USINADOS.get(i['pecas'][0])
            if _us: c3[_us['al']] = (b[_us['al']] + _us['u'][0]) / 2   # painel usinado: balão na faixa cheia, não no vão
            t3 = pj(c3); cx, cy = T(t3[0], t3[1]); t_ = str(nb); wv = fz.get_text_length(t_, 'hebo', 7) + 4
            if kw.get('posicoes') is not None: kw['posicoes'][id(i)] = (cx, cy)
            _marcados.append(i); _pontos[id(i)] = (cx,cy)
        from visual_comum import baloes
        baloes(globals(),page,rect,_marcados,letra,_pontos)


# puxador por regra DESLIGADO (João: posições erradas). Só liga com "puxadores_regra": true no config.
PUXADORES = _gerar_puxadores() if cfg.get('puxadores_regra') else []
print('PUXADORES:', len(PUXADORES), '(regra desligada; o DXF não traz puxador)' if not PUXADORES else 'gerados')
# REGRA (v33, João): PEÇA ESCONDIDA NÃO É LISTADA. Antes de montar a tabela, o motor desenha a
# imagem frontal da vista num rascunho e anota quais peças realmente aparecem nela. Item que não
# tem nenhuma peça visível fica FORA da tabela e não ganha balão. Exceção funcional:
# apoio/fixação ou detalhe previsto no documento pode aparecer em subimagem montada,
# com referência ao hospedeiro e balões somente das ocorrências visíveis no detalhe.
# (precisa vir depois de render3d estar definido)
# DECISÃO D1 (João, 28/09/2026): elementos com mesma (desc, dim) → mesmo número em TODAS as vistas.
# Na tabela: uma linha, sem quantidade. Na imagem: cada ocorrência tem balão próprio com mesmo número.
def _numerar(ordenados, letra, agrupar=False):
    lin = []
    for i in ordenados:
        k = (i['desc'], i['dim'])
        if agrupar and k in lin: i['num_' + letra] = lin.index(k) + 1; continue
        lin.append(k); i['num_' + letra] = len(lin)
    legendas={(i['desc'],i['dim']):i.get('_legenda_normal','') for i in ordenados}
    return [(d+(' - '+legendas[(d,dm)] if legendas[(d,dm)] else ''),dm,'') for d,dm in lin]

for v in VW:
    its = [i for w in v['paredes'] for i in PW[w]['itens']]
    _vis_v = set()
    _tmp_v = fz.open(); _pg_v = _tmp_v.new_page(width=842, height=595)
    render3d(_pg_v, fz.Rect(AREA_IN.x0 + 258, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1), v['paredes'],
             contexto=True, visiveis=_vis_v, so_visiveis=True)
    # REGRA (João, 28/09/2026 - bloco 1): só PEÇA SOLTA pode ser escondida (base sob módulo,
    # tamponamento sob superior). MÓDULO da vista nunca é escondido nem sai da listagem.
    _fora_v = [i for i in its if i['tipo'] != 'mod' and not any(pi in _vis_v for pi in i['pecas'])]
    from normal.ocultas import planejar
    v['_detalhes_ocultos'] = planejar(globals(),v,_fora_v)
    _em_detalhe = {id(i) for plano in v['_detalhes_ocultos'] for i in plano['listados']}
    _fora_v = [i for i in _fora_v if id(i) not in _em_detalhe]
    _tmp_v.close()
    if _fora_v:
        print('ESCONDIDAS (fora da listagem) em %s: %d' % (v['titulo'], len(_fora_v)))
        for i in _fora_v: print('    %s %s' % (i['desc'], i['dim']))
        its = [i for i in its if i not in _fora_v]
    v['itens_listados'] = its
    ordem = sorted(its, key=lambda i: (i['tipo'] != 'mod', i['n']))
    # Peças ou módulos iguais compartilham o número; todas as ocorrências recebem balão.
    v['linhas'] = _numerar(ordem, v['letra'], agrupar=True)

# ---------------- montagem ----------------
doc = fz.open(); n = 0; relat = []
n += 1; p = nova_prancha(doc, n, 'CAPA')
render3d(p, fz.Rect(AREA_IN.x0, AREA_IN.y0 + 34, AREA_IN.x1, AREA_IN.y1), [w['id'] for w in paredes], contexto=True, papel='geral')
t = f"CADERNO DE {cfg['tipo_caderno']} - {cfg['dados']['ambiente'].upper()}"
p.insert_text((419.5 - fz.get_text_length(t, 'hebo', 18) / 2, AREA_IN.y0 + 22), t, fontname='hebo', fontsize=18, color=RED)

n += 1; p = nova_prancha(doc, n, 'CONTRATO')
ct = fz.open(cfg['contrato_fonte']); clip = fz.Rect(AREA.x0 + 2, 143, AREA.x1 - 2, 540)
p.show_pdf_page(clip, ct, 0, clip=clip)

# PRANCHA 3: especificações + planta do DXF com cotas e indicação das vistas
n += 1; p = nova_prancha(doc, n, 'PLANTA - ESPECIFICAÇÕES DO PROJETO')
esp = fz.Rect(AREA_IN.x0, AREA_IN.y0, AREA_IN.x0 + 225, AREA_IN.y1)
p.draw_rect(esp, color=PRETO, width=0.6)
# REGRA (reativado): xml_confere agora usa _faltando_real (peças reais que faltam, excluindo
# acessórios/ferragens). Se alguma peça real da listagem não foi localizada no DXF, specs entram
# como CONFERIR (ENGENHARIA.pdf Parte 2, item 4). Acessórios sem DXF são normais e não afetam.
confere = not _faltando_real
# REGRA (João): especificações no modelo fixo, preenchidas com o que está no XML (nome exato). Sem item no projeto = em branco.
def _espec(xml):
    lim = lambda t: re.sub(r'[^\w)\]]+$', '', re.sub(r'\s+', ' ', t or '')).strip()
    root_ = XML_TREE.getroot() if xml == cfg['xml'] else ET.parse(xml).getroot()
    cor_, esp_ = {}, {}
    def add(cl, c, e):
        cor_.setdefault(cl, _col.Counter())[c] += 1
        esp_.setdefault(cl, set()).add(e)
    for it in root_.iter('ITEM'):
        its_ = it.find('ITEMS')
        if its_ is None: continue
        ch = [c for c in its_.findall('ITEM') if re.match(r'Chapa .+ Espessura', c.get('DESCRIPTION', ''))]
        if not ch: continue
        m_ = re.match(r'Chapa (.+?) Espessura ([\d.,]+)\s*mm', ch[0].get('DESCRIPTION'))
        if not m_: continue
        c, e = m_.group(1).strip(), fmt(float(m_.group(2).replace(',', '.')))
        I, D = (it.get('ID') or '').lower(), (it.get('DESCRIPTION') or '')
        if re.search(r'(^|_)por_', I): add('porta', c, e)
        elif '_gav' in I: continue                                   # corpo da gaveta
        elif re.search(r'tamponamento', D, re.I): add('tamp', c, e)
        elif re.search(r'afastador', D, re.I): add('caixa', c, e)
        elif re.search(r'painel|tampo', D, re.I) or re.search(r'(^|_)(tam|tampo)(_|$)', I): add('painel', c, e)
        elif '_pra' in I or re.match(r'prat', D, re.I): add('prat', c, e)
        elif '_fun' in I: esp_.setdefault('fundo', set()).add(e)
        else: add('caixa', c, e)
    todos_ = [(it.get('DESCRIPTION') or '', it) for it in root_.iter('ITEM')]
    nomes = lambda rx: list(OrderedDict((lim(d), 1) for d, _ in todos_ if re.search(rx, d, re.I)))
    pux_n, pux_c = [], []
    for d, it in todos_:
        if re.match(r'puxador', d, re.I):
            rf = {g.tag: g.get('REFERENCE') for g in (it.find('REFERENCES') or [])}
            n_ = lim(d); lg = rf.get('LARGURA')
            if lg and lg + 'mm' not in n_: n_ += f' - {lg}mm'
            if n_ not in pux_n: pux_n.append(n_)
            a_ = lim(rf.get('DESC_ACA_PER', ''))
            if a_ and a_ not in pux_c: pux_c.append(a_)
    esp_nome = lambda d: re.sub(r'\s*[\d.,]+\s*mm$', '', d).strip()
    especiais = list(OrderedDict((esp_nome(lim(d)), 1) for d, it in todos_ if it.get('COMPONENT') == 'Y' and re.search(r'pist|articulad|aventos|basculant|trilho|cabideiro tubo|lixeira|cesto|porta.?tempero|sapateira|calceiro|gaveteiro aramado', d, re.I)))
    cor = lambda k: ', '.join(c for c, _ in cor_.get(k, _col.Counter()).most_common())
    mm = lambda k: ' e '.join(f'{e}mm' for e in sorted(esp_.get(k, ()), key=lambda t: float(t.replace(',', '.'))))
    cx = mm('caixa') + (f" (fundo {mm('fundo')})" if esp_.get('fundo') else '')
    return [('ESPECIFICAÇÕES DO PROJETO', None), ('CORES E ACABAMENTOS:', None),
            ('Caixa Módulos (Interno)', cor('caixa')), ('Portas e Frentes', cor('porta')), ('Tamponamentos', cor('tamp')),
            ('Painéis e Tampos', cor('painel')), ('Puxadores', ', '.join(pux_c)), ('Portas de Vidro', ', '.join(nomes(r'vidro|espelho'))),
            ('FERRAGENS E ACESSÓRIOS:', None),
            ('Dobradiças', ', '.join(nomes(r'^dobradi'))), ('Corrediças', ', '.join(nomes(r'corredi'))),
            ('Puxadores', ', '.join(pux_n)), ('Ferragens especiais', ', '.join(especiais)),
            ('ESPESSURAS:', None),
            ('Caixa Módulos (Interno)', cx), ('Prateleiras internas', mm('prat')), ('Portas e Frentes', mm('porta')),
            ('Tamponamentos', mm('tamp')), ('Painéis e Tampos e perfil', mm('painel'))]
itens_esp = _espec(cfg['xml'])
if not confere:
    itens_esp = [(r_, v_ if v_ is None or 'mm' in v_ else 'CONFERIR') for r_, v_ in itens_esp]
_FH, _FB = fz.Font('helv'), fz.Font('hebo')
def _quebra(t, larg, fs):
    ls, cur = [], ''
    for w_ in t.split(' '):
        tt = (cur + ' ' + w_).strip()
        if cur and _FB.text_length(tt, fs) > larg: ls.append(cur); cur = w_
        else: cur = tt
    return ls + ([cur] if cur else [])
y = esp.y0 + 14
for rot, v in itens_esp:
    if v is None:
        if y > esp.y0 + 20: y += 4
        p.insert_text((esp.x0 + 6, y), rot, fontname='hebo', fontsize=8.5, color=RED if y == esp.y0 + 14 else PRETO)
        y += 14; continue
    rt = rot + ': '; rw = _FH.text_length(rt, 7.3) + 1.5
    p.insert_text((esp.x0 + 6, y), rt, fontname='helv', fontsize=7.3)
    ls = _quebra(v, esp.width - 12 - rw, 7.3) if v else []
    if len(ls) > 1: ls = _quebra(v, esp.width - 18, 7.3); y += 9.5; x_ = esp.x0 + 12
    else: x_ = esp.x0 + 6 + rw
    for l_ in ls:
        p.insert_text((x_, y), l_, fontname='hebo', fontsize=7.3, color=(0.7, 0, 0) if v == 'CONFERIR' else PRETO); y += 9.5
    y += 3.5 if ls else 13
if not confere:
    p.insert_text((esp.x0 + 6, esp.y1 - 8), f'{len(_faltando_real)} item(ns) do XML não bateu(ram) com o DXF — conferir', fontname='helv', fontsize=6.5, color=(0.7, 0, 0))
# planta
pr = fz.Rect(esp.x1 + 8, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1)
todos = [pi for it in inst for pi in it['pecas']]
xs0 = min(P[i]['bb'][0] for i in todos); xs1 = max(P[i]['bb'][3] for i in todos)
ys0 = min(P[i]['bb'][1] for i in todos); ys1 = max(P[i]['bb'][4] for i in todos)
S, k = escala_para(xs1 - xs0, ys1 - ys0, pr.width - 110, pr.height - 90)
ox = pr.x0 + (pr.width - (xs1 - xs0) * k) / 2; oy = pr.y0 + (pr.height - (ys1 - ys0) * k) / 2
PX = lambda x: ox + (x - xs0) * k
PY = lambda y_: oy + (ys1 - y_) * k
cor_de = {}
for it in inst:
    for pi in it['pecas']: cor_de[pi] = MADEIRA if it['tipo'] == 'comp' else BRANCO
fcs = []
# REGRA (João): planta só com MÓVEIS e PAREDES (sem forro, sanca, pedra, eletros por cima dos móveis)
_par_ids = {p_['i'] for p_ in PAREDES_PECAS} | {p_['i'] for p_ in PAR_DXF}
_linhas_par = set()
for p_ in MALHA_PAR:   # paredes em peça única: faces verticais viram as linhas das paredes (vãos ficam abertos)
    for fc in p_['faces']:
        zs_ = [v[2] for v in fc]
        if max(zs_) - min(zs_) < 500 or min(zs_) > 1200: continue
        xy = sorted({(round(v[0]), round(v[1])) for v in fc})
        if len(xy) >= 2 and math.dist(xy[0], xy[-1]) > 20: _linhas_par.add((xy[0], xy[-1]))
for p_ in P:
    b = p_['bb']
    if p_['i'] not in _usadas and p_['i'] not in _par_ids: continue
    if p_['i'] in _usadas and (sorted(p_['dim'])[1] < 50 or sorted(p_['dim'])[0] > 60): continue
    if b[3] < xs0 - 300 or b[0] > xs1 + 300 or b[4] < ys0 - 300 or b[1] > ys1 + 300 or b[2] > 2600: continue
    if p_['dim'][0] > 6000 or p_['dim'][1] > 6000: continue
    if p_['dim'][2] < 40 and p_['dim'][0] > 1200 and p_['dim'][1] > 1200: continue
    for uq, nv, ft in p_['fq']:
        q = [(PX(v[0]), PY(v[1])) for v in uq]
        if area2(q) < 0.2: continue
        fcs.append((max(v[2] for v in uq), q, cor_de.get(p_['i']), ft))
fcs.sort(key=lambda t: t[0])
sh = p.new_shape()
for z, q, cor, ft in fcs:
    q = [(min(max(a, pr.x0), pr.x1), min(max(b_, pr.y0), pr.y1)) for a, b_ in q]
    fill = cor or BRANCO
    sh.draw_polyline(q + [q[0]]); sh.finish(color=fill, fill=fill, width=0.4, closePath=True)
    if any(ft):
        for (a_, b_), f_ in zip(zip(q, q[1:] + q[:1]), ft):
            if f_: sh.draw_line(a_, b_)
        sh.finish(color=PRETO if cor is None else (0.3, 0.3, 0.3), width=0.5 if cor is None else 0.3, closePath=False)
sh.commit()
def _clip(x0, y0, x1, y1, R):   # v30: linha de parede não sai do quadro da planta
    t0, t1 = 0.0, 1.0; dx, dy = x1 - x0, y1 - y0
    for pp, qq in ((-dx, x0 - R.x0), (dx, R.x1 - x0), (-dy, y0 - R.y0), (dy, R.y1 - y0)):
        if pp == 0:
            if qq < 0: return None
        else:
            t = qq / pp
            if pp < 0: t0 = max(t0, t)
            else: t1 = min(t1, t)
    return None if t0 > t1 else ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))
for (a_, b_) in _linhas_par:
    _sg = _clip(PX(a_[0]), PY(a_[1]), PX(b_[0]), PY(b_[1]), pr)
    if _sg: p.draw_line(_sg[0], _sg[1], color=PRETO, width=0.9)
for w in paredes:          # REGRA (v28, João): planta = cota de CADA CONJUNTO de móveis (comprimento + largura), sem cotar o vão entre eles
    f = FV[w['key']]; ax = 1 if w['key'][0] == 'x' else 0; ad = 1 - ax; gr = []
    for i in sorted(w['itens'], key=lambda i: i['bb'][ax]):
        if gr and i['bb'][ax] <= max(j['bb'][ax + 3] for j in gr[-1]) + 50: gr[-1].append(i)
        else: gr.append([i])
    for g in gr:
        a0, a1 = min(i['bb'][ax] for i in g), max(i['bb'][ax + 3] for i in g); d0, d1 = min(i['bb'][ad] for i in g), max(i['bb'][ad + 3] for i in g)
        if ax == 1:
            cadeia_v(p, [a0, a1], PX(w['plano']) + (16 if f[0] > 0 else -16), PX(w['plano']), PY, fs=7)
            cadeia_h(p, [d0, d1], PY(a0) + 14, PY(a0), PX, fs=7)
        else:
            cadeia_h(p, [a0, a1], PY(w['plano']) + (16 if f[1] < 0 else -16), PY(w['plano']), PX, fs=7)
            cadeia_v(p, [d0, d1], PX(a1) + 14, PX(a1), PY, fs=7)
_circ = []
for v in V:                # setas das vistas (uma por parede); se encostar em outra, desliza ao longo da parede
  for wid, letra_ in zip(v['paredes'], v['letras']):
    w = PW[wid]; f = FV[w['key']]; its = w['itens']
    # REGRA (João 28/09/2026): câmera fica no AMBIENTE, aponta para a PAREDE. Fundo=parede, frente=ambiente.
    # f_arr aponta PARA a parede (mesma direção da câmera), coloca o símbolo no lado do ambiente.
    f_arr = FV[w['key']]
    cx = sum((i['bb'][0] + i['bb'][3]) / 2 for i in its) / len(its); cy = sum((i['bb'][1] + i['bb'][4]) / 2 for i in its) / len(its)
    ex, ey = PX(cx) - f_arr[0] * 30, PY(cy) + f_arr[1] * 30
    for _t in range(8):
        sx, sy = ex - f_arr[0] * 32, ey + f_arr[1] * 32
        cc_ = (sx - f_arr[0] * 8, sy + f_arr[1] * 8); seg = [(sx, sy), (ex, ey), cc_]
        if all(math.dist(a_, b_) > 22 for a_ in seg for b_ in _circ): break
        ex += 30 * abs(f_arr[1]) * (1 if _t % 2 == 0 else -2); ey += 30 * abs(f_arr[0]) * (1 if _t % 2 == 0 else -2)
    _circ += [(sx, sy), (ex, ey), (sx - f_arr[0] * 8, sy + f_arr[1] * 8)]
    p.draw_line((sx, sy), (ex, ey), color=RED, width=1.4)
    p.draw_polyline([(ex + f_arr[1] * 4 - f_arr[0] * 7, ey + f_arr[0] * 4 + f_arr[1] * 7), (ex, ey), (ex - f_arr[1] * 4 - f_arr[0] * 7, ey - f_arr[0] * 4 + f_arr[1] * 7)], color=RED, width=1.4)
    p.draw_circle((sx - f_arr[0] * 8, sy + f_arr[1] * 8), 7, color=RED, fill=BRANCO, width=1)
    p.insert_text((sx - f_arr[0] * 8 - 3.5, sy + f_arr[1] * 8 + 3.5), letra_, fontname='hebo', fontsize=10, color=RED)
lab = f'PLANTA BAIXA - ESC. 1:{S}'
p.insert_text((pr.x0 + pr.width / 2 - fz.get_text_length(lab, 'hebo', 8) / 2, pr.y1 - 3), lab, fontname='hebo', fontsize=8)

# VISÃO GERAL: no máximo quatro imagens limpas, sem balões ou cotas.
_vg = ([x for x in VW if not PW[x['paredes'][0]].get('divisoria')] or VW)[:4]
for _ini in range(0, len(_vg), 4):
    n += 1; p = nova_prancha(doc, n, 'VISÃO GERAL DOS MÓVEIS')
    com_img = [dict(titulo=x['titulo'], paredes=x['paredes'], img3d=None) for x in _vg]
    m = len(com_img); a = AREA_IN; xm = a.x0 + a.width / 2; ym = a.y0 + a.height / 2
    if m == 1:
        cel = [a]
    elif m == 2:
        # Duas imagens: divisão vertical, uma metade para cada vista.
        cel = [fz.Rect(a.x0, a.y0, xm, a.y1), fz.Rect(xm, a.y0, a.x1, a.y1)]
    elif m == 3:
        # Três imagens: esquerda inteira; direita dividida em duas.
        cel = [fz.Rect(a.x0, a.y0, xm, a.y1),
               fz.Rect(xm, a.y0, a.x1, ym), fz.Rect(xm, ym, a.x1, a.y1)]
    else:
        cel = [fz.Rect(a.x0, a.y0, xm, ym), fz.Rect(xm, a.y0, a.x1, ym),
               fz.Rect(a.x0, ym, xm, a.y1), fz.Rect(xm, ym, a.x1, a.y1)]
    for v, c in zip(com_img, cel):
        render3d(p, fz.Rect(c.x0 + 4, c.y0 + 16, c.x1 - 4, c.y1 - 4), v['paredes'], contexto=True)
        p.insert_text((c.x0 + 6, c.y0 + 11), v['titulo'], fontname='hebo', fontsize=10, color=RED)
    if m >= 2:
        p.draw_line((xm, a.y0), (xm, a.y1), color=PRETO, width=0.6)
    if m == 3:
        p.draw_line((xm, ym), (a.x1, ym), color=PRETO, width=0.6)
    elif m == 4:
        p.draw_line((a.x0, ym), (a.x1, ym), color=PRETO, width=0.6)

# REGRA (v26, João): LISTAGEM POLUÍDA (mais de 15 linhas) = DUAS pranchas: SUPERIORES (armários de cima e altos) e
# INFERIORES (balcões). Cada uma com a tabela e os balões só das suas peças (numeração própria). Sem os dois grupos:
# divide a parede ao meio (PARTE 1 / PARTE 2).
LIST_MAX = 25; _extra = 0   # Nova regra: acima de 25 linhas, dividir a listagem.
def _partes(s_):
    global _extra
    # REGRA (v34, João): usa a lista JÁ FILTRADA (sem as peças escondidas). Antes esta função relia a
    # lista original e as escondidas voltavam com balão quando a listagem se dividia em duas pranchas.
    its = s_['itens_listados'] if 'itens_listados' in s_ else [i for w in s_['paredes'] for i in PW[w]['itens']]
    if len(s_['linhas']) <= LIST_MAX or not its: return [s_]
    sup = [i for i in its if (i['bb'][2] + i['bb'][5]) / 2 > 1300]; inf = [i for i in its if i not in sup]
    if sup and inf: gs = [('SUPERIORES', sup), ('INFERIORES', inf)]
    else:
        f_ = FV[PW[s_['paredes'][0]]['key']]; al = 1 if f_[0] else 0
        o_ = sorted(its, key=lambda i: (i['bb'][al] + i['bb'][al + 3]) / 2); h_ = len(o_) // 2
        gs = [('PARTE 1', o_[:h_]), ('PARTE 2', o_[h_:])]
    # Qualquer grupo ainda maior que 15 é repartido novamente.
    # A paginação não possui máximo fixo: prevalecem legibilidade e integridade.
    blocos = []
    for nome, g in gs:
        partes = [g[i:i + LIST_MAX] for i in range(0, len(g), LIST_MAX)]
        for j, parte in enumerate(partes, 1):
            sufixo = f' {j}' if len(partes) > 1 else ''
            blocos.append((nome + sufixo, parte))
    gs = blocos
    out = []
    for k_, (nome, g) in enumerate(gs):
        key = f"{s_['letra']}{k_ + 1}"
        lin = _numerar(sorted(g, key=lambda i: (i['tipo'] != 'mod', i['n'])), key, agrupar=True)
        out.append(dict(letra=key, titulo=f"{s_['titulo']} - {nome}", linhas=lin, paredes=s_['paredes'], ids={id(i) for i in g}, primeiro=k_ == 0, base=s_))
    _extra += len(out) - 1
    return out

def _cotas_em(p, GS, R, rotulos):
    # REGRA (v15 + bloco cotas 28/09/2026): elevações 2D (móvel isolado) lado a lado dentro do retângulo R, mesma
    # escala nas colunas, a maior escala que cabe (até 1:10). Usada nas vistas (R = prancha inteira) e nas
    # pranchas extras (R = área à direita da listagem).
    nc = len(GS); zm = max(G['ztop'] for G in GS)
    Wm = [G['vmax'] - G['vmin'] for G in GS]
    S, k = escala_para(sum(Wm), zm, R.width - 80 * nc, R.height - 62, cheio=True)
    sobra = (R.width - sum(w_ * k + 80 for w_ in Wm)) / nc
    cws = [w_ * k + 80 + sobra for w_ in Wm]
    fy = R.y0 + (R.height - 62 - zm * k) / 2 + 22 + zm * k
    for j, G in enumerate(GS):
        cw = cws[j]; cx0 = R.x0 + sum(cws[:j])
        ox = cx0 + (cw - Wm[j] * k) / 2 + (G['umin'] - G['vmin']) * k
        desenhar(p, G, ox, fy, k)
        cotar(p, G, ox, fy, k)
        lab = f"{rotulos[j]} - ESC. 1:{S:g}"
        p.insert_text((cx0 + cw / 2 - fz.get_text_length(lab, 'hebo', 8.5) / 2, min(fy + 44, R.y1 - 2)), lab, fontname='hebo', fontsize=8.5)
        if j: p.draw_line((cx0, R.y0 - IN), (cx0, R.y1 + IN), color=PRETO, width=0.6)

# por bloco: listagem de cada parede (frontal) e depois as cotas do bloco (paredes lado a lado)
for v in V:
    GS = [geom_parede(PW[w]) for w in v['paredes']]
    for s_ in [q_ for s0_ in v['subs'] for q_ in _partes(s0_)]:
        n += 1; p = nova_prancha(doc, n, f"MÓDULOS E PAINÉIS - {s_['titulo']}")
        yb = tabela(p, s_['linhas'], AREA_IN.x0, AREA_IN.y0)
        # Engenharia: somente nichos identificados por XML + geometria/dimensão
        # geram subimagem no motor padrão. Não há exceções semânticas por nome de produto.
        nis = [(w,c,{'rotulo':'DETALHE - NICHO','sem_lista':False}) for w in s_['paredes'] for c in detalhes(PW[w])]
        # Canto reto e canto L recuperam as câmeras funcionais anteriores.
        from normal.regras import subimagens
        for w in s_['paredes']:
            for grupo, rotulo, sem_lista in subimagens(globals(), PW[w]):
                if not re.search(r'canto\s+(?:reto|l)\b', rotulo, re.I):
                    continue
                ids_ = {id(i) for i in grupo}
                nis = [(ww,g,t) for ww,g,t in nis if not ids_.intersection(id(i) for i in g)]
                nis.append((w, grupo, {'rotulo':'DETALHE - ' + rotulo.upper(), 'sem_lista':False, 'canto':True}))
        planos = s_.get('_detalhes_ocultos',s_.get('base',{}).get('_detalhes_ocultos',[]))
        for plano in planos:
            ids = {id(i) for i in plano['itens']}
            nis = [(ww,g,t) for ww,g,t in nis if not ids.intersection(id(i) for i in g)]
            nis.append((plano['w'],plano['listados'],dict(rotulo=plano['rotulo'],sem_lista=False,oculto=plano)))
        if s_.get('ids') is not None:
            nis = [(w, c, t) for w, c, t in nis if any(id(i) in s_['ids'] for i in c)]
        _sb = {id(i) for _,c,t in nis if not t['sem_lista'] for i in c}
        _RI = fz.Rect(AREA_IN.x0 + 258, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1)
        _alvos_vista = None
        if s_.get('ids') is not None:
            _alvos_vista = [i for w in s_['paredes'] for i in PW[w]['itens'] if id(i) in s_['ids']]
        _caixas_main = {}
        render3d(p, _RI, s_['paredes'], letra=s_['letra'], contexto=True,
                 itens_vista=_alvos_vista, sem_balao=_sb, ang=0, elev=0,
                 caixas_projetadas=_caixas_main)
        # REGRA (João, 28/09/2026 - skill P1.1): TODOS os nichos da vista ficam na MESMA prancha (caixa dividida),
        # com os números da listagem. Não existe prancha "NICHO k" com listagem própria.
        def _dq(p, w, c, tp_, r_):
            # REGRA (v33, João): o nicho aparece SEM AMBIENTE - sem parede, sem chao, sozinho no
            # espaco (isolado=True), com os seus proprios baloes e a numeracao da listagem.
            # ORDEM 006 (v37.2): módulo com porta ausente no DXF (xml_tem_porta=True) vai FRONTAL (ang=0)
            # para mostrar a face sintética; nicho/aberto segue com ângulo.
            p.draw_rect(r_, color=PRETO, width=0.5)
            p.insert_text((r_.x0 + 4, r_.y0 + 10), tp_['rotulo'], fontname='hebo', fontsize=7.5, color=RED)
            if tp_.get('oculto'):
                from normal.ocultas import renderizar
                permitidos = s_.get('ids',{id(i) for i in s_.get('itens_listados',[])})
                renderizar(globals(),p,fz.Rect(r_.x0+2,r_.y0+14,r_.x1-2,r_.y1-2),tp_['oculto'],s_['letra'],permitidos)
                return
            from normal.cameras import orientar, portas_do_canto, tampas_modulos_deitados
            portas_detalhe = portas_do_canto(globals(), c)
            if tp_.get('rotulo') == 'DETALHE - NICHO':
                # Nicho: câmera frontal, centralizada pelo enquadramento dinâmico.
                op = dict(camera_key=PW[w]['key'], ang=0, elev=0)
            else:
                op = orientar(c, P, PW[w]['key'], _portas() | portas_detalhe)
            tampas_deitadas = tampas_modulos_deitados(c, P)
            if tampas_deitadas:
                # Frente aberta está acima na geometria DXF deitada. Somente
                # no detalhe, a câmera olha para o interior e oculta as tampas.
                op['elev'] = 75
            if portas_detalhe or tampas_deitadas:
                op['ocultar_pecas'] = sorted(portas_detalhe | tampas_deitadas)
            globals().setdefault('_auditoria_subimagens', []).append(dict(
                pagina=p.number+1, vista=s_['letra'], rotulo=tp_['rotulo'],
                itens=[dict(n=i['n'],desc=i['desc'],bb=i['bb'],pecas=i['pecas']) for i in c],
                camera=op, sem_lista=tp_['sem_lista']))
            render3d(p, fz.Rect(r_.x0 + 2, r_.y0 + 14, r_.x1 - 2, r_.y1 - 2), [w], letra=None if tp_['sem_lista'] else s_['letra'], itens=c,
                     representacao_interna=tp_['sem_lista'], dmin=3200, margem=60, isolado=True,sem_portas=True,**op)

        def _seta_referencia_oculta(pg_, caixa_det_, tp_, caixas_):
            plano_ = tp_.get('oculto')
            if not plano_: return
            host_ = plano_['hospedeiro']
            bb_ = [caixas_[pi] for pi in host_['pecas'] if pi in caixas_]
            if not bb_: return
            alvo_ = fz.Rect(min(q[0] for q in bb_), min(q[1] for q in bb_),
                            max(q[2] for q in bb_), max(q[3] for q in bb_))
            fim_ = (alvo_.x0 - 5, alvo_.y0 + alvo_.height * .72)
            ini_ = (caixa_det_.x1, caixa_det_.y0 + caixa_det_.height * .55)
            guia_ = min(_RI.x0 - 5, fim_[0] - 12)
            pts_ = [ini_, (guia_, ini_[1]), (guia_, fim_[1]), fim_]
            pg_.draw_polyline(pts_, color=RED, width=1)
            pg_.draw_polyline([(fim_[0]-7, fim_[1]-3), fim_, (fim_[0]-7, fim_[1]+3)], color=RED, width=1)

        if nis:
            # Exatamente uma subimagem por prancha.
            y0_ = yb + 18
            if AREA_IN.y1 - y0_ >= 90:
                w, c, tp_ = nis[0]
                rd_ = fz.Rect(AREA_IN.x0, y0_, AREA_IN.x0 + 248, AREA_IN.y1)
                _dq(p, w, c, tp_, rd_)
                _seta_referencia_oculta(p, rd_, tp_, _caixas_main)
                extras_nicho = nis[1:]
            else:
                extras_nicho = nis
            for k2_, (w, c, tp_) in enumerate(extras_nicho, 1):
                n += 1
                pd = nova_prancha(doc, n, f"{tp_['rotulo']} — {s_['titulo']}")
                if tp_.get('oculto'):
                    rd_ = fz.Rect(AREA_IN.x0, AREA_IN.y0, AREA_IN.x0 + 330, AREA_IN.y1)
                    rr_ = fz.Rect(AREA_IN.x0 + 342, AREA_IN.y0, AREA_IN.x1, AREA_IN.y1)
                    caixas_ = {}
                    render3d(pd, rr_, s_['paredes'], contexto=True, sem_balao={id(i) for i in _alvos_vista or []},
                             itens_vista=_alvos_vista, ang=0, elev=0, caixas_projetadas=caixas_)
                    _dq(pd, w, c, tp_, rd_)
                    _seta_referencia_oculta(pd, rd_, tp_, caixas_)
                else:
                    _dq(pd, w, c, tp_, AREA_IN)
    # cotas
    n += 1; p = nova_prancha(doc, n, f"MEDIDAS E ALTURAS - {v['titulo']}")
    _cotas_em(p, GS, AREA_IN, [f"VISTA {l_}" for l_ in v['letras']])


# ===== CAPA (design fixo: quadro externo + logo + cliente + EXECUTIVO - AMBIENTE) =====
_W, _H = doc[0].rect.width, doc[0].rect.height
doc.delete_page(0); cp = doc.new_page(0, width=_W, height=_H)
_lp = fz.open(cfg['layout'])[0]
_rs = [d_['rect'] for d_ in _lp.get_drawings() if d_['rect'].width > _W * 0.8 and d_['rect'].height > _H * 0.8]
fr = max(_rs, key=lambda r: r.width * r.height) if _rs else fz.Rect(17, 17, _W - 17, _H - 17)
AC = (0.78, 0.56, 0.29); CZ = (0.30, 0.30, 0.32); cx = (fr.x0 + fr.x1) / 2
cp.draw_rect(fz.Rect(fr.x0, fr.y0, fr.x0 + 10, fr.y1), color=None, fill=AC)
cp.draw_rect(fr, color=PRETO, width=1.2)
_lg = cfg.get('logo') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'LOGO.png')
yb = fr.y0 + 200
if _lg and os.path.exists(_lg):
    _im = fz.Pixmap(_lg); lw = 340; lh = lw * _im.height / _im.width
    cp.insert_image(fz.Rect(cx - lw / 2, fr.y0 + 90, cx + lw / 2, fr.y0 + 90 + lh), filename=_lg); yb = fr.y0 + 90 + lh
y = yb + 40
cp.draw_line((cx - 45, y), (cx + 45, y), color=AC, width=2)
_nm = cfg['dados']['cliente'].upper(); fs_ = 32
while fz.get_text_length(_nm, 'hebo', fs_) > fr.width - 140: fs_ -= 1
cp.insert_text((cx - fz.get_text_length(_nm, 'hebo', fs_) / 2, y + 50), _nm, fontname='hebo', fontsize=fs_, color=CZ)
_sb = 'EXECUTIVO - ' + cfg['dados']['ambiente'].upper()
cp.insert_text((cx - fz.get_text_length(_sb, 'helv', 16) / 2, y + 82), _sb, fontname='helv', fontsize=16, color=AC)
try:
    doc.save(cfg['saida'], garbage=3, deflate=True)
except Exception:
    import time as _t; cfg['saida'] = os.path.splitext(cfg['saida'])[0] + _t.strftime('_%H%M%S') + '.pdf'; doc.save(cfg['saida'], garbage=3, deflate=True)

# ---------------- QUALIDADE (nível 1, por script) ----------------
q = [f"# QUALIDADE — {cfg['dados']['cliente']} / {cfg['dados']['ambiente']} (gerado por script)", '',
     f"- APROVADO | {n} pranchas na ordem final, incluindo paginação dinâmica de vistas, listagens e nichos",
     f"- {'APROVADO' if not _faltando_real else 'INCERTO'} | itens localizados no DXF: {len(linhas) - len(nao_achados)}/{len(linhas)}" + (f" ({len(_acessorios)} acessório(s) sem DXF — normal)" if _acessorios else '')]
for d, dm in _faltando_real: q.append(f"  - FORA DA LISTAGEM: {d} {dm} (não localizado no DXF, logo não aparece na imagem)")
for d, dm in _acessorios: q.append(f"  - ACESSÓRIO (sem DXF, normal): {d} {dm}")
q.append(f"- {'APROVADO' if confere else 'INCERTO'} | XML confere com o projeto (baseado em itens localizados no DXF)" + ('' if confere else f' — {len(_faltando_real)} item(ns) sem correspondência no DXF, ver acima'))
TEX_FALTA = [m_ for m_ in TEX_FALTA if not textura(m_)] + [m_ for m_, v_ in _cc.items() if not v_ and m_ in _todas_mats]
q.append(f"- {'APROVADO' if not TEX_FALTA else 'INCERTO'} | texturas dos materiais" + ('' if not TEX_FALTA else ' — faltando (sai cor lisa): ' + ', '.join(TEX_FALTA)))
for v in VW:
    _ex = []
    for w_ in v['paredes']:
        _nq = detalhes(PW[w_])
        if _nq: _ex.append(f"{len(_nq)} nicho(s) em subimagem")
        if PW[w_].get('perna_l'): _ex.append("perna do L com vista própria")
    q.append(f"- {v['titulo']}: paredes {', '.join(v['paredes'])} | {len(v['linhas'])} linhas de listagem" + (' | CONDIÇÕES -> ' + ', '.join(_ex) if _ex else ''))
q += [f"  {v['letra']}{i}: {d} {dm}" for v in VW for i, (d, dm, m_) in enumerate(v['linhas'], 1)]
open(os.path.splitext(cfg['saida'])[0] + '_QUALIDADE.md', 'w', encoding='utf-8').write('\n'.join(q))
with open(os.path.splitext(cfg['saida'])[0] + '_CAMERAS.json', 'w', encoding='utf-8') as _ca:
    json.dump(dict(cameras=globals().get('_auditoria_cameras',[]),
                   subimagens=globals().get('_auditoria_subimagens',[]),
                   ocultas=globals().get('_auditoria_ocultas',[])), _ca, ensure_ascii=False, indent=2)
print('\n'.join(q))
for i in range(len(doc)):
    doc[i].get_pixmap(dpi=80).save(os.path.join(os.path.dirname(cfg['saida']), f'_prev_{i + 1}.png'))
print('OK', cfg['saida'])
