from pathlib import Path
from datetime import datetime
import shutil, ast
root=Path(__file__).resolve().parent
p=root/'gerar_caderno.py'
s=p.read_text(encoding='utf-8')
old="    its = itens if itens is not None else [i for w in pids for i in PW[w]['itens']]"
new="""    # Vista dividida: o alvo acompanha a listagem; vizinhos continuam como contexto.
    # itens_vista não transforma a imagem principal em subimagem isolada.
    its = kw.get('itens_vista')
    if its is None:
        its = itens if itens is not None else [i for w in pids for i in PW[w]['itens']]"""
old2="        render3d(p, _RI, s_['paredes'], letra=s_['letra'], contexto=True, sem_balao=_sb,ang=0,elev=0)"
new2="""        _alvos_vista = None
        if s_.get('ids') is not None:
            _alvos_vista = [i for w in s_['paredes'] for i in PW[w]['itens'] if id(i) in s_['ids']]
        render3d(p, _RI, s_['paredes'], letra=s_['letra'], contexto=True,
                 itens_vista=_alvos_vista, sem_balao=_sb, ang=0, elev=0)"""
assert s.count(old)==1 and s.count(old2)==1
updated=s.replace(old,new).replace(old2,new2)
ast.parse(updated.lstrip(chr(65279)))
backup=root/'_backups'/('VISTAS_ALVOS_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir(parents=True)
shutil.copy2(p,backup/p.name)
p.write_text(updated,encoding='utf-8')
print('APLICADO',backup)
