from pathlib import Path
p=Path(__file__).resolve().parent/'gerar_caderno.py'
s=p.read_text(encoding='utf-8-sig')
assert 'from normal.cameras import orientar\n' in s
s=s.replace('from normal.cameras import orientar\n','from normal.cameras import orientar, revelar_canto\n',1)
s=s.replace("            op = orientar(c, P, PW[w]['key'], _portas())\n", "            op = orientar(c, P, PW[w]['key'], _portas())\n            op = revelar_canto(globals(), c, w, fz.Rect(r_.x0+2,r_.y0+14,r_.x1-2,r_.y1-2), op)\n",1)
s=s.replace("                   ocultas=globals().get('_auditoria_ocultas',[])), _ca, ensure_ascii=False, indent=2)","                   ocultas=globals().get('_auditoria_ocultas',[]),\n                   orientacao_cantos=globals().get('_auditoria_orientacao_cantos',[])), _ca, ensure_ascii=False, indent=2)",1)
p.write_text(s,encoding='utf-8-sig')
print('R3 APLICADA')
