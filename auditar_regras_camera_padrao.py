from pathlib import Path
import sys,json,unicodedata
out,old=map(Path,sys.argv[1:3]);rows=json.loads((out/'RESULTADOS.json').read_text(encoding='utf-8'));checks=[]
def norm(s):return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
for row in rows:
 if row['status']!='OK':continue
 folder=out/'AMBIENTES'/row['ambiente'];data=json.loads(next(folder.glob('*_CAMERAS.json')).read_text(encoding='utf-8'))
 for q in data['subimagens']:
  nome=norm(q['rotulo'])
  if 'canto reto' not in nome and 'canto l' not in nome:continue
  ang=0 if 'canto reto' in nome else 45 if 'direito' in nome else -45
  bb=[min(i['bb'][k] for i in q['itens']) for k in range(3)]+[max(i['bb'][k+3] for i in q['itens']) for k in range(3)]
  renders=[c for c in data['cameras'] if not c['contexto'] and c['camera_key']==q['camera']['camera_key'] and c['alvo']==bb and abs(c['ang']-ang)<.001 and abs(c['elev']-20)<.001]
  focos=all(all(abs(c['foco'][k]-(bb[k]+bb[k+3])/2)<.001 for k in range(3)) for c in renders)
  checks.append(dict(ambiente=row['ambiente'],pagina=q['pagina'],rotulo=q['rotulo'],camera=q['camera'],angulo_correto=q['camera']['ang']==ang and q['camera']['elev']==20,foco_centro=bool(renders) and focos))
oldsrc=json.loads((old/'VERSAO_E_VARREDURA.json').read_text(encoding='utf-8'))['fontes']
newsrc=json.loads((out/'VERSAO_E_VARREDURA.json').read_text(encoding='utf-8'))['fontes']
protected={k:oldsrc[k]==newsrc.get(k) for k in oldsrc if k.startswith(('normal/','normal\\','especiais/','especiais\\')) or k in ('geo.py','integridade.py','camera_comum.py','cotas_comum.py','gerar_caderno_com_especiais.py')}
result=dict(projetos=sum(r['status']=='OK' for r in rows),paginas=sum(r['paginas'] for r in rows),cantos=checks,regras_preservadas=protected)
(out/'AUDITORIA_REGRAS_CAMERA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
