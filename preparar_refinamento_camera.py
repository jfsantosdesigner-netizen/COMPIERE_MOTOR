from pathlib import Path
import shutil,hashlib
root=Path(__file__).resolve().parent
b=root/'_backups'/'CAMERAS_PADRAO_20261006';b.mkdir(exist_ok=True)
p=root/'gerar_caderno.py'
assert 'VW = [s_ for v in V' in p.read_text(encoding='utf-8-sig')
assert not (b/'gerar_caderno.py').exists(), 'Backup ja existe; interrompido para preservar'
shutil.copy2(p,b/'gerar_caderno.py')
print('BACKUP',str(b),hashlib.sha256(p.read_bytes()).hexdigest())
