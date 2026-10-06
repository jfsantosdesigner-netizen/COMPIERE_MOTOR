from pathlib import Path
p=Path(__file__).resolve().parent/'gerar_caderno.py'
s=p.read_text(encoding='utf-8-sig')
old="        if kw.get('sem_portas') and p_['i'] in _portas(): continue"
assert old in s
s=s.replace(old,"        if kw.get('sem_portas') and (p_['i'] in _portas() or p_['i'] in kw.get('ocultar_pecas',())): continue",1)
s=s.replace('from normal.cameras import orientar, revelar_canto\n','from normal.cameras import orientar, revelar_canto, portas_do_canto\n',1)
s=s.replace("            op = orientar(c, P, PW[w]['key'], _portas())\n","            portas_detalhe = portas_do_canto(globals(), c)\n            op = orientar(c, P, PW[w]['key'], _portas() | portas_detalhe)\n            if portas_detalhe: op['ocultar_pecas'] = sorted(portas_detalhe)\n",1)
p.write_text(s,encoding='utf-8-sig')
print('R4 APLICADA')
