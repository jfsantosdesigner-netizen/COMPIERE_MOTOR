from pathlib import Path
from datetime import datetime
import shutil,ast
root=Path(__file__).resolve().parent
p=root/'gerar_caderno.py';s=p.read_text(encoding='utf-8-sig')
backup=root/'_backups'/('VISTAS_PORTAS_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir(parents=True)
shutil.copy2(p,backup/p.name)
old="""        _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+') if _parede_real_atras(_m, _k, _FR) is not None]
        if len(_com_real) == 1 and _m.get('parede_key') != _com_real[0]:"""
new="""        _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+') if _parede_real_atras(_m, _k, _FR) is not None]
        # Um módulo mais raso pode ficar até 160 mm da parede real. Só corrige
        # uma vista-fragmento quando há UMA parede candidata e nenhuma a 80 mm.
        # Cantos conservam a parede e câmera próprias.
        if not _com_real and 'canto' not in _norm(_m['desc']):
            _com_real = [_k for _k in ('x-', 'x+', 'y-', 'y+')
                         if _parede_real_atras(_m, _k, _FR, tol=160) is not None]
            if len(_com_real) == 1:
                print(f"VISTA-FRAGMENTO: {_m['desc']} {_m['dim']} -> parede real {_com_real[0]}")
        if len(_com_real) == 1 and _m.get('parede_key') != _com_real[0]:"""
assert s.count(old)==1
s=s.replace(old,new)
old="""            from normal.cameras import orientar, portas_do_canto
            portas_detalhe = portas_do_canto(globals(), c)
            op = orientar(c, P, PW[w]['key'], _portas() | portas_detalhe)
            if portas_detalhe: op['ocultar_pecas'] = sorted(portas_detalhe)"""
new="""            from normal.cameras import orientar, portas_do_canto, tampas_modulos_deitados
            portas_detalhe = portas_do_canto(globals(), c)
            op = orientar(c, P, PW[w]['key'], _portas() | portas_detalhe)
            tampas_deitadas = tampas_modulos_deitados(c, P)
            if tampas_deitadas:
                # Frente aberta está acima na geometria DXF deitada. Somente
                # no detalhe, a câmera olha para o interior e oculta as tampas.
                op['elev'] = 75
            if portas_detalhe or tampas_deitadas:
                op['ocultar_pecas'] = sorted(portas_detalhe | tampas_deitadas)"""
assert s.count(old)==1
s=s.replace(old,new)
ast.parse(s)
p.write_text('\ufeff'+s,encoding='utf-8')
c=root/'normal'/'cameras.py';t=c.read_text(encoding='utf-8');shutil.copy2(c,backup/'cameras.py')
t+="""

def tampas_modulos_deitados(grupo, pecas):
    \"\"\"Tampas acima de uma caixa deitada, com fundo fino embaixo.

    Exige as duas superfícies reais no DXF; não remove painéis verticais,
    portas decorativas ou módulos normalmente montados em pé.
    \"\"\"
    por_id = {p['i']: p for p in pecas}
    tampas = set()
    for item in grupo:
        if item.get('tipo') != 'mod' or 'canto' in normalizar(item.get('desc','')):
            continue
        b = item['bb']
        larg, prof = b[3]-b[0], b[4]-b[1]
        area = larg * prof
        if area <= 0 or b[5]-b[2] > 1000:
            continue
        placas = [por_id[pi] for pi in item['pecas'] if pi in por_id]
        def cobertura(p):
            q=p['bb']
            return max(0,min(q[3],b[3])-max(q[0],b[0])) * max(0,min(q[4],b[4])-max(q[1],b[1]))
        fundos=[p for p in placas if p['bb'][5]-p['bb'][2]<=10
                and b[2]-2<=p['bb'][2]<=b[2]+30 and cobertura(p)>=.60*area]
        caps=[p for p in placas if p['bb'][5]-p['bb'][2]<=30
              and b[5]-2<=p['bb'][2]<=b[5]+5 and cobertura(p)>=.60*area]
        if fundos and len(caps)==1:
            tampas.add(caps[0]['i'])
    return tampas
"""
ast.parse(t)
c.write_text(t,encoding='utf-8')
print('APLICADO',backup)
