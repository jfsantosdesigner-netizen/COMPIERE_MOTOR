# -*- coding: utf-8 -*-
# Gera o caderno de UM ambiente (XML + DXF) em modo BLINDADO: sem cache, sem memoria entre rodadas.
# Uso: python novo_ambiente.py <pasta_do_ambiente>   (ou arraste a pasta sobre GERAR_CADERNO.bat)
#
# REGRA (BLINDAGEM, Joao, 06/10/2026):
#   ENTRADA : so o .xml e o .dxf originais da pasta. Todo o resto da pasta e APAGADO antes de gerar.
#   SAIDA   : so "CADERNO - <AMBIENTE>.pdf" e "CADERNO - <AMBIENTE>_QUALIDADE.md" (o relatorio).
#   Json intermediario, config e pecas do DXF vivem numa pasta temporaria que e apagada ao final.
#   Nenhum __pycache__, nenhum cache de cor/textura/material, nenhum arquivo com horario no nome.
import sys, os, glob, json, re, subprocess, tempfile, shutil

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
M = os.path.dirname(os.path.abspath(__file__))
pad = json.load(open(os.path.join(M, 'padrao.json'), encoding='utf-8'))
_ASSETS = os.path.join(M, 'assets')
ORIGEM = ('.xml', '.dxf')   # unicos arquivos que sobrevivem na pasta do ambiente


def _xmls(pasta):
    return sorted(f for f in glob.glob(os.path.join(pasta, '*.xml')) if not re.search(r'x?plod', os.path.basename(f), re.I))


def _dxfs(pasta):
    return sorted(glob.glob(os.path.join(pasta, '*.dxf')))


def _tem_projeto(pasta):
    """True se a pasta tem XML+DXF direto nela (e um ambiente, nao uma pasta-mae)."""
    return bool(_xmls(pasta) and _dxfs(pasta))


def limpar_motor():
    shutil.rmtree(os.path.join(M, '__pycache__'), ignore_errors=True)


def limpar(pasta):
    """Apaga TUDO que esta direto na pasta do ambiente, menos .xml e .dxf. Nao entra em subpastas.
    Recusa pastas perigosas (raiz do disco, a pasta do motor ou qualquer pasta que contenha o motor)."""
    pasta = os.path.abspath(pasta)
    if os.path.dirname(pasta) == pasta:
        raise RuntimeError(f'recusado: "{pasta}" e a raiz do disco')
    if pasta == M or M.startswith(pasta.rstrip('\\/') + os.sep):
        raise RuntimeError(f'recusado: "{pasta}" e (ou contem) a pasta do motor')
    if not _tem_projeto(pasta):
        raise RuntimeError(f'recusado: "{pasta}" nao tem XML + DXF')
    apagados, subpastas = [], []
    for nome in sorted(os.listdir(pasta)):
        p = os.path.join(pasta, nome)
        if os.path.isdir(p):
            subpastas.append(nome); continue
        if nome.lower().endswith(ORIGEM):
            continue
        os.remove(p)   # se falhar (ex.: PDF aberto no leitor), levanta erro e NADA e gerado
        apagados.append(nome)
    return apagados, subpastas


def _saidas_validas(nome):
    return nome.upper().startswith('CADERNO') and (nome.lower().endswith('.pdf') or nome.endswith('_QUALIDADE.md'))


def processar(pasta):
    """Gera o caderno de UM ambiente. Retorna True/False (sucesso/falha), nunca lanca."""
    pasta = os.path.abspath(pasta)
    xmls, dxfs = _xmls(pasta), _dxfs(pasta)
    if not xmls or not dxfs:
        print(f'FALTA: "{pasta}" não tem XML MONTADO + DXF -> pulado')
        return False
    mont = [f for f in xmls if 'montado' in f.lower()] or xmls
    xml, dxf = mont[0], dxfs[0]   # deterministico: ordem alfabetica (antes: o mais novo por data = estado escondido)
    if len(mont) > 1 or len(dxfs) > 1:
        print(f'AVISO: {len(mont)} XML e {len(dxfs)} DXF na pasta; usando por ordem alfabetica: {os.path.basename(xml)} + {os.path.basename(dxf)}')
    cliente = re.sub(r'^PROJETO\s+', '', os.path.basename(os.path.dirname(pasta)), flags=re.I).upper()
    amb = re.sub(r'^EXECUTIVO\s*-?\s*', '', os.path.basename(pasta), flags=re.I).strip().title()
    dados = {'cliente': cliente, 'ambiente': amb, 'projetista': pad['projetista'], 'arquiteta': pad['arquiteta']}
    extra = os.path.join(os.path.dirname(pasta), 'dados.json')   # dados do CLIENTE (pasta-mae); a pasta do ambiente nao guarda nada
    if os.path.exists(extra):
        dados.update(json.load(open(extra, encoding='utf-8')))
    try:
        limpar_motor()
        apagados, subpastas = limpar(pasta)
    except Exception as e:
        print(f'ERRO ao limpar a pasta (feche o PDF se estiver aberto): {e}')
        return False
    print(f'LIMPEZA: {len(apagados)} arquivo(s) apagado(s); ficaram só XML + DXF' + (f' | subpastas intocadas: {", ".join(subpastas)}' if subpastas else ''))
    for a in apagados:
        print('   apagado:', a)
    tmp = tempfile.mkdtemp(prefix='compiere_')
    ok = False
    try:
        cfg = {'tipo_caderno': pad['tipo_caderno'], 'dados': dados,
               'layout': pad.get('layout') or os.path.join(_ASSETS, 'LAYOUT_FIXO.pdf'),
               'contrato_fonte': pad.get('contrato_fonte') or os.path.join(_ASSETS, 'CONTRATO.pdf'),
               'xml': xml, 'dxf': dxf, 'pecas_json': os.path.join(tmp, '_pecas_dxf.json'), 'vistas': [],
               'logo': pad.get('logo') or os.path.join(_ASSETS, 'LOGO.png'), 'materiais': pad.get('materiais'),
               'saida': os.path.join(pasta, f'CADERNO - {amb.upper()}.pdf')}
        cj = os.path.join(tmp, '_config.json')
        json.dump(cfg, open(cj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Gerando:', dados['cliente'], '/', amb, '...')
        r = subprocess.run([sys.executable, '-B', os.path.join(M, 'gerar_caderno.py'), cj],
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        ok = (r.returncode == 0 and os.path.exists(cfg['saida']))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        limpar_motor()
    # confere a saida: so PDF + relatorio; qualquer outra coisa criada no caminho e removida
    for nome in sorted(os.listdir(pasta)):
        p = os.path.join(pasta, nome)
        if os.path.isfile(p) and not nome.lower().endswith(ORIGEM) and (not ok or not _saidas_validas(nome)):
            os.remove(p)
            print('   removido (não é saída válida):', nome)
    print(('OK' if ok else 'FALHOU — ver mensagens acima') + f': {dados["cliente"]} / {amb}')
    return ok


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Arraste 1 pasta de ambiente (com XML + DXF) sobre o GERAR_CADERNO.bat.')
    pasta = os.path.abspath(sys.argv[1].strip('"'))
    if not os.path.isdir(pasta):
        sys.exit(f'ERRO: "{pasta}" não é uma pasta válida.')
    if not _tem_projeto(pasta):
        filhas = [d for d in os.listdir(pasta)
                  if os.path.isdir(os.path.join(pasta, d)) and _tem_projeto(os.path.join(pasta, d))]
        if filhas:
            print(f'AVISO: "{os.path.basename(pasta)}" é uma pasta-mãe com {len(filhas)} ambiente(s):')
            for d in sorted(filhas):
                print(f'  - {d}')
            sys.exit('Arraste cada pasta de ambiente individualmente sobre o GERAR_CADERNO.bat (ou use GERAR_FILA.bat).')
        sys.exit(f'FALTA: "{pasta}" não tem XML MONTADO + DXF.')
    if not processar(pasta):
        sys.exit(1)
