# -*- coding: utf-8 -*-
"""
validar_fase1.py — roda classificar_peca() nos projetos de teste reais,
usando o MESMO caminho de dados do motor (XML + _pecas_dxf.json + geo.casar +
geo.definir_paredes), sem pymupdf, sem cores/texturas e sem gerar PDF.

Reimplementa apenas a parte de ler_xml() que produz (desc, dim) -> linhas/QT,
igual ao gerar_caderno.py original (linhas 40-116), porque o resto dessa
funcao so existe para cores/puxadores, que nao interessam a classificacao.
"""
import os, re, json, sys
import xml.etree.ElementTree as ET
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo
import classificacao as C

ROOT = "/mnt/user-data/uploads/CORE_MOTOR/PROJETOS TESTES"


def fmt(v):
    v = round(v * 2) / 2
    return str(int(round(v))) if abs(v - round(v)) < 0.01 else ('%.1f' % v).replace('.', ',')


def ler_xml_min(path):
    """Extrai (desc, dim) -> linhas/QT e mods_com_porta, igual a ler_xml()
    original, mas sem cores/puxadores/ferragens (irrelevantes aqui)."""
    root = ET.parse(path).getroot()
    mods, comps = OrderedDict(), OrderedDict()
    mods_com_porta = set()
    QT = {}
    for cat in root.iter('CATEGORY'):
        items = cat.find('ITEMS')
        if items is None:
            continue
        cn = (cat.get('DESCRIPTION') or '').upper()
        for it in items.findall('ITEM'):
            a = it.attrib
            U = a.get('ID', '').upper()
            d = a.get('DESCRIPTION', '')
            if '_POR_' in U and 'EUR_' in U:
                continue
            if 'EURONOBRE' in cn or 'PUX' in U:
                continue
            if 'FERRAG' in cn:
                continue
            if re.match(r'\s*cunha', d, re.I):
                continue
            if 'ACESS' in cn or U.startswith('ACE') or U.startswith('EUR_'):
                continue
            if '_POR_' in U or U.startswith('POR_'):
                continue
            try:
                desc = re.sub(r'\s+\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?mm\s*$', '', d).strip()
                dim = 'x'.join(fmt(float(a[k])) for k in ('WIDTH', 'HEIGHT', 'DEPTH'))
            except (KeyError, ValueError):
                continue
            qq = int(float(a.get('QUANTITY') or 1))
            QT[(desc, dim)] = QT.get((desc, dim), 0) + qq
            if U.startswith(('PAI', 'COM_COZ_DIV')):
                comps[(desc, dim)] = 1
            else:
                mods[(desc, dim)] = 1
                _mat_porta = None
                for _ch in it.iter('ITEM'):
                    _cu = _ch.get('ID', '').upper()
                    if not ('_POR_' in _cu or _cu.startswith('POR_')):
                        continue
                    _refs = _ch.find('REFERENCES')
                    if _refs is not None:
                        if _refs.find('VIDRO') is not None and _refs.find('VIDRO').get('REFERENCE', ''):
                            _mat_porta = 'vidro'; break
                        if _refs.find('MAT') is not None and _refs.find('MAT').get('REFERENCE', ''):
                            _mat_porta = _refs.find('MAT').get('REFERENCE', '').lower(); break
                    _mat_porta = 'mdf'; break
                if _mat_porta is not None:
                    mods_com_porta.add((desc, dim))
    return list(mods) + list(comps), QT, mods_com_porta


def descricao_real_do_item(xml_path):
    """Mapa (desc, dim) -> DESCRIPTION original do XML (sem a normalizacao de
    ler_xml), usado so para o gabarito de comparacao."""
    root = ET.parse(xml_path).getroot()
    mapa = {}
    for cat in root.iter('CATEGORY'):
        items = cat.find('ITEMS')
        if items is None:
            continue
        for it in items.findall('ITEM'):
            a = it.attrib
            d = a.get('DESCRIPTION', '')
            try:
                desc_norm = re.sub(r'\s+\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?x\d+(?:[.,]\d+)?mm\s*$', '', d).strip()
                dim = 'x'.join(fmt(float(a[k])) for k in ('WIDTH', 'HEIGHT', 'DEPTH'))
            except (KeyError, ValueError):
                continue
            mapa[(desc_norm, dim)] = d
    return mapa


def achar_projetos(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        pj = [f for f in filenames if f == '_pecas_dxf.json']
        xmls = [f for f in filenames if f.lower().endswith('.xml') and not f.lower().startswith('xplod')]
        if pj and xmls:
            out.append((dirpath, os.path.join(dirpath, pj[0]), os.path.join(dirpath, xmls[0])))
    return sorted(out)


def rodar_projeto(dirpath, pj_path, xml_path):
    linhas, QT, mods_com_porta = ler_xml_min(xml_path)
    gabarito = descricao_real_do_item(xml_path)
    P = geo.carregar(pj_path)
    inst = geo.casar(P, linhas, QT)
    for it in inst:
        if it['tipo'] == 'mod' and (it['desc'], it['dim']) in mods_com_porta:
            it['xml_tem_porta'] = True
    paredes = geo.definir_paredes(inst, P)
    lim = geo.limites(inst)
    linhas_saida = []
    for w in paredes:
        ctx = dict(P=P, lim=lim, mods=[i for i in inst if i['tipo'] == 'mod'], eixo_vista=geo.PAREDES.get(w['key']))
        for it in w['itens']:
            tipo = C.classificar_peca(it, ctx)
            desc_real = gabarito.get((it['desc'], it['dim']), it['desc'])
            val = ''
            if it['tipo'] == 'mod' and tipo.startswith('CANTO'):
                val = 'OK' if C.validar_canto(it, ctx) else 'DIVERGE:' + ','.join(C.paredes_tocadas(it, ctx))
            linhas_saida.append((tipo, desc_real, it['dim'], it['tipo'], val))
    return linhas_saida


def main():
    projetos = achar_projetos(ROOT)
    print(f"Projetos encontrados (XML + _pecas_dxf.json): {len(projetos)}\n")
    todas = []
    for dirpath, pj_path, xml_path in projetos:
        nome = os.path.relpath(dirpath, ROOT)
        try:
            linhas = rodar_projeto(dirpath, pj_path, xml_path)
        except Exception as e:
            print(f"[ERRO] {nome}: {e!r}")
            continue
        for tipo, desc, dim, tipo_pipeline, val in linhas:
            todas.append((nome, tipo, desc, dim, tipo_pipeline, val))
        print(f"[OK] {nome}: {len(linhas)} itens classificados")
    with open(os.path.join(os.path.dirname(__file__), 'saida_classificacao.tsv'), 'w', encoding='utf-8') as f:
        f.write("projeto\ttipo_classificado\tdescricao_xml\tdim\ttipo_pipeline\tvalidacao_geo\n")
        for row in todas:
            f.write('\t'.join(row) + '\n')
    print(f"\nTotal de itens classificados: {len(todas)}")
    print("Salvo em saida_classificacao.tsv")


if __name__ == '__main__':
    main()
