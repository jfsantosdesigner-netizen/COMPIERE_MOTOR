from pathlib import Path
p=Path(__file__).resolve().parent/'gerar_caderno.py'
s=p.read_text(encoding='utf-8-sig')
old="            gaveta = next((i for i in c if i.get('_gaveta_montada')),None)\n            op = dict(ang=0,elev=0)\n            if gaveta:\n                # A subimagem mostra a montagem e o fundo; a listagem principal permanece frontal.\n                op.update(camera_key=gaveta['_camera_detalhe_key'],ang=15,elev=22)"
new="            from normal.cameras import orientar\n            op = orientar(c, P, PW[w]['key'], _portas())\n            globals().setdefault('_auditoria_subimagens', []).append(dict(\n                pagina=p.number+1, vista=s_['letra'], rotulo=tp_['rotulo'],\n                itens=[dict(n=i['n'],desc=i['desc'],bb=i['bb'],pecas=i['pecas']) for i in c],\n                camera=op, sem_lista=tp_['sem_lista']))"
assert old in s, 'Trecho original ausente; revisar'
s=s.replace(old,new,1)
s=s.replace("print('\\n'.join(q))","with open(os.path.splitext(cfg['saida'])[0] + '_CAMERAS.json', 'w', encoding='utf-8') as _ca:\n    json.dump(dict(cameras=globals().get('_auditoria_cameras',[]),\n                   subimagens=globals().get('_auditoria_subimagens',[]),\n                   ocultas=globals().get('_auditoria_ocultas',[])), _ca, ensure_ascii=False, indent=2)\n"+"print('\\n'.join(q))",1)
p.write_text(s,encoding='utf-8-sig')
print('CAMERA APLICADA',p)
