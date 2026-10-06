from pathlib import Path
p=Path(__file__).resolve().parent/'gerar_caderno.py'
s=p.read_text(encoding='utf-8-sig')
assert 'orientar, revelar_canto, portas_do_canto' in s
s=s.replace('orientar, revelar_canto, portas_do_canto','orientar, portas_do_canto')
s=s.replace("            op = revelar_canto(globals(), c, w, fz.Rect(r_.x0+2,r_.y0+14,r_.x1-2,r_.y1-2), op)\n",'')
s=s.replace("                   ocultas=globals().get('_auditoria_ocultas',[]),\n                   orientacao_cantos=globals().get('_auditoria_orientacao_cantos',[])), _ca, ensure_ascii=False, indent=2)","                   ocultas=globals().get('_auditoria_ocultas',[])), _ca, ensure_ascii=False, indent=2)")
s=s.replace('        camera=cam, alvo=U, enquadrado=_enquadrado,',"        camera=cam, foco=tc, camera_key=kw.get('camera_key',PW[pids[0]]['key']),\n        alvo=U, enquadrado=_enquadrado,")
p.write_text(s,encoding='utf-8-sig')
print('REGRAS EXPLICITAS APLICADAS')
