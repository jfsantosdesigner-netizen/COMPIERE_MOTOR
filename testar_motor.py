# Testa o leitor novo do dxf_pecas.py contra um DXF real.
# Uso:
#   python testar_motor.py                     -> tenta achar um DXF nas subpastas
#   python testar_motor.py caminho\arquivo.dxf -> le esse DXF em especifico
#
# Reporta:
#   - Contagem de cada tipo de entidade no modelspace bruto (INSERT, 3DSOLID etc.)
#   - Quantos INSERTs foram expandidos com sucesso (indica leitura de blocos)
#   - Quantos 3DSOLIDs geraram faces (indica leitura de solidos)
#   - Total final de pecas (layers com bbox valido) apos varredura completa
import sys, os, glob, collections
try:
    import ezdxf
except ImportError:
    print('ERRO: ezdxf nao instalado. Rode:  pip install ezdxf')
    sys.exit(1)

# importa o leitor novo (mesma pasta)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import dxf_pecas as DP


def _achar_dxf():
    """Procura um DXF nas subpastas do motor / OneDrive / Desktop."""
    candidatos = []
    for raiz in (_HERE, os.path.dirname(_HERE), os.path.expanduser('~/Desktop'),
                 os.path.expanduser('~/OneDrive/Desktop'),
                 os.path.expanduser('~/OneDrive/\u00c1rea de Trabalho')):
        if os.path.isdir(raiz):
            for arq in glob.glob(os.path.join(raiz, '**', '*.dxf'), recursive=True):
                candidatos.append(arq)
    if not candidatos:
        return None
    # pega o DXF mais recente
    candidatos.sort(key=lambda a: os.path.getmtime(a), reverse=True)
    return candidatos[0]


def testar(dxf_path):
    print('=' * 72)
    print(f'DXF: {dxf_path}')
    print(f'ezdxf: {ezdxf.__version__}')
    print('=' * 72)

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # ------- Contagem BRUTA de tipos no modelspace -------
    tipos_brutos = collections.Counter()
    for e in msp:
        tipos_brutos[e.dxftype()] += 1

    print('\n[TIPOS DE ENTIDADE NO MODELSPACE (bruto)]')
    for t, n in tipos_brutos.most_common():
        marca = ''
        if t == 'INSERT': marca = '  <-- bloco (sera expandido)'
        if t in ('3DSOLID', 'SOLID3D', 'BODY', 'REGION'): marca = '  <-- solido 3D'
        if t == 'MESH': marca = '  <-- malha 3D'
        if t == 'SPLINE': marca = '  <-- curva'
        print(f'  {t:14s} {n:6d}{marca}')

    # ------- Rodar o leitor e contar sucessos -------
    pecas = {}
    inserts_ok = inserts_erro = 0
    solids_ok = solids_erro = 0
    solid_layers_com_face = set()
    insert_layers_novas = set()

    # marca as layers que ja tinham faces ANTES de cada INSERT/SOLID pra ver se cresceram depois
    for e in msp:
        t = e.dxftype()
        if t == 'INSERT':
            layers_antes = {L for L, p in pecas.items() if p['faces']}
            tam_antes = sum(len(p['faces']) for p in pecas.values())
            try:
                DP._processar(e, layer_pai=None, pecas=pecas)
                tam_depois = sum(len(p['faces']) for p in pecas.values())
                if tam_depois > tam_antes:
                    inserts_ok += 1
                    for L, p in pecas.items():
                        if p['faces'] and L not in layers_antes:
                            insert_layers_novas.add(L)
                else:
                    inserts_ok += 1   # expandiu sem erro, mas o bloco pode nao ter geometria de face
            except Exception as ex:
                inserts_erro += 1
                print(f'  INSERT ERRO: {ex}')
        elif t in ('3DSOLID', 'SOLID3D', 'BODY', 'REGION'):
            L = e.dxf.layer
            faces_antes = len(pecas.get(L, {'faces': []})['faces'])
            try:
                DP._processar(e, layer_pai=None, pecas=pecas)
                faces_depois = len(pecas.get(L, {'faces': []})['faces'])
                if faces_depois > faces_antes:
                    solids_ok += 1
                    solid_layers_com_face.add(L)
                else:
                    solids_erro += 1
            except Exception as ex:
                solids_erro += 1
                print(f'  3DSOLID ERRO: {ex}')
        else:
            try:
                DP._processar(e, layer_pai=None, pecas=pecas)
            except Exception:
                pass

    # ------- Relatorio -------
    print('\n[RESULTADO DA VARREDURA]')
    print(f'  INSERT lidos.......: {inserts_ok} ok, {inserts_erro} erro')
    if insert_layers_novas:
        print(f'  Layers criadas por expansao de INSERT: {len(insert_layers_novas)}')
        for L in list(insert_layers_novas)[:5]:
            print(f'     - {L}')
        if len(insert_layers_novas) > 5:
            print(f'     ... e mais {len(insert_layers_novas) - 5}')
    print(f'  3DSOLID lidos......: {solids_ok} com face, {solids_erro} sem face/erro')
    if solid_layers_com_face:
        print(f'  Layers com face vinda de 3DSOLID: {len(solid_layers_com_face)}')
        for L in list(solid_layers_com_face)[:5]:
            print(f'     - {L}')

    # ------- Total final de pecas -------
    pecas_validas = 0
    for L, p in pecas.items():
        b = p['bb']
        if b[0] <= b[3] and b[1] <= b[4] and b[2] <= b[5]:
            pecas_validas += 1

    print(f'\n[TOTAL FINAL]')
    print(f'  Layers com geometria (=pecas)....: {pecas_validas}')
    print(f'  Layers com pelo menos 1 face 3D..: {sum(1 for p in pecas.values() if p["faces"])}')
    print('=' * 72)

    # Veredito
    tem_insert = tipos_brutos.get('INSERT', 0) > 0
    tem_solid = tipos_brutos.get('3DSOLID', 0) + tipos_brutos.get('BODY', 0) + tipos_brutos.get('REGION', 0) > 0
    if tem_insert and inserts_ok > 0:
        print('OK: leitor conseguiu processar INSERTs (blocos).')
    elif tem_insert:
        print('FALHA: DXF tem INSERTs mas nenhum foi lido com sucesso.')
    else:
        print('INFO: este DXF nao contem INSERTs (nao pode testar essa parte com ele).')
    if tem_solid and solids_ok > 0:
        print('OK: leitor conseguiu extrair face(s) de 3DSOLID.')
    elif tem_solid:
        print('FALHA: DXF tem 3DSOLID mas nenhum gerou face.')
    else:
        print('INFO: este DXF nao contem 3DSOLID (nao pode testar essa parte com ele).')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arq = sys.argv[1].strip('"')
    else:
        print('Procurando um DXF nas subpastas...')
        arq = _achar_dxf()
        if not arq:
            print('Nenhum .dxf encontrado. Passe o caminho como argumento:')
            print('   python testar_motor.py "C:\\caminho\\para\\arquivo.dxf"')
            sys.exit(1)
        print(f'Achei (mais recente): {arq}\n')
    testar(arq)
