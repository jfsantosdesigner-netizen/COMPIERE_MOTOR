# Gera o caderno de UM ambiente (XML montado + DXF).
# Uso: python novo_ambiente.py <pasta_do_ambiente>
# Ou arraste a pasta sobre GERAR_CADERNO.bat.
import sys, os, glob, json, re, subprocess

sys.stdout.reconfigure(encoding='utf-8')
M = os.path.dirname(os.path.abspath(__file__))
pad = {'tipo_caderno': 'MONTAGEM E INSTALAÇÃO', 'projetista': 'JOÃO FELIPE SANTOS', 'arquiteta': 'FERNANDA', 'materiais': 'MATERIAIS'}
_ASSETS = os.path.join(M, 'assets')


def _tem_projeto(pasta):
    """True se a pasta tem XML+DXF direto nela (é um ambiente, não uma pasta-mãe)."""
    xmls = [f for f in glob.glob(os.path.join(pasta, '*.xml')) if not re.search(r'x?plod', os.path.basename(f), re.I)]
    dxfs = glob.glob(os.path.join(pasta, '*.dxf'))
    return bool(xmls and dxfs)


def processar(pasta):
    """Gera o caderno de UM ambiente. Retorna True/False (sucesso/falha), nunca lança."""
    pasta = os.path.abspath(pasta)
    xmls = [f for f in glob.glob(os.path.join(pasta, '*.xml')) if not re.search(r'x?plod', os.path.basename(f), re.I)]
    mont = [f for f in xmls if 'montado' in f.lower()] or xmls
    dxfs = glob.glob(os.path.join(pasta, '*.dxf'))
    if not mont or not dxfs:
        print(f'FALTA: "{pasta}" não tem XML MONTADO + DXF -> pulado')
        return False
    cliente = re.sub(r'^PROJETO\s+', '', os.path.basename(os.path.dirname(pasta)), flags=re.I).upper()
    amb = re.sub(r'^EXECUTIVO\s*-?\s*', '', os.path.basename(pasta), flags=re.I).strip().title()
    if os.path.basename(os.path.dirname(pasta)).upper() == 'PROJETOS TESTES':
        cliente = os.path.basename(pasta).split('_')[0].upper()
        amb = 'Cozinha' if 'COZINHA' in os.path.basename(pasta).upper() else 'Closet'
    dados = {'cliente': cliente, 'ambiente': amb, 'projetista': pad['projetista'], 'arquiteta': pad['arquiteta']}
    # Layout/contrato/logo SEMPRE relativos à própria pasta do motor (M).
    # Configuração nova; nenhum JSON anterior é entrada deste fluxo.
    cfg = {'tipo_caderno': pad['tipo_caderno'], 'dados': dados, 'fontes_frescas': True,
           'layout': pad.get('layout') or os.path.join(_ASSETS, 'LAYOUT_FIXO.pdf'),
           'contrato_fonte': pad.get('contrato_fonte') or os.path.join(_ASSETS, 'CONTRATO.pdf'),
           'xml': max(mont, key=os.path.getmtime), 'dxf': max(dxfs, key=os.path.getmtime),
           'pecas_json': os.path.join(pasta, '_pecas_dxf.json'), 'vistas': [],
           'logo': pad.get('logo') or os.path.join(_ASSETS, 'LOGO.png'), 'materiais': pad.get('materiais'),
           'saida': os.path.join(pasta, f'CADERNO - {amb.upper()}.pdf')}
    for cache in (cfg['pecas_json'], cfg['pecas_json'] + '.md5'):
        if os.path.isfile(cache): os.remove(cache)
    cj = os.path.join(pasta, '_config.json')
    json.dump(cfg, open(cj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Gerando:', dados['cliente'], '/', amb, '...')
    r = subprocess.run([sys.executable, os.path.join(M, 'gerar_caderno.py'), cj])
    for f in glob.glob(os.path.join(os.path.dirname(cfg['saida']), '_prev_*.png')):
        os.remove(f)
    ok = (r.returncode == 0)
    print(('OK' if ok else 'FALHOU — ver mensagens acima') + f': {dados["cliente"]} / {amb}')
    return ok


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Arraste 1 pasta de ambiente (com XML + DXF) sobre o GERAR_CADERNO.bat.')
    pasta = os.path.abspath(sys.argv[1].strip('"'))
    if not os.path.isdir(pasta):
        sys.exit(f'ERRO: "{pasta}" não é uma pasta válida.')
    # Se arrastou uma pasta-mãe (sem XML/DXF direto), avisa e sai
    if not _tem_projeto(pasta):
        # Verifica se é pasta-mãe com subpastas de ambiente
        filhas = [d for d in os.listdir(pasta)
                  if os.path.isdir(os.path.join(pasta, d)) and _tem_projeto(os.path.join(pasta, d))]
        if filhas:
            print(f'AVISO: "{os.path.basename(pasta)}" é uma pasta-mãe com {len(filhas)} ambiente(s):')
            for d in sorted(filhas):
                print(f'  - {d}')
            sys.exit('Arraste cada pasta de ambiente individualmente sobre o GERAR_CADERNO.bat.')
        else:
            sys.exit(f'FALTA: "{pasta}" não tem XML MONTADO + DXF.')
    if not processar(pasta):
        sys.exit(1)
