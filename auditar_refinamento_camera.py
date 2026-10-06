from pathlib import Path
import sys,json
import fitz,numpy as np
from PIL import Image,ImageDraw
new,old=map(Path,sys.argv[1:3]);out=new/'REVISAO_CAMERAS';out.mkdir(exist_ok=True)
rows=json.loads((new/'RESULTADOS.json').read_text(encoding='utf-8'))
prior={r['ambiente']:r for r in json.loads((old/'RESULTADOS.json').read_text(encoding='utf-8'))}
checks=[]
for idx,r in enumerate(rows,1):
 if r['status']!='OK':continue
 a,b=fitz.open(prior[r['ambiente']]['pdf']),fitz.open(r['pdf'])
 od=new/'AMBIENTES'/r['ambiente'];cd=list(od.glob('*_CAMERAS.json'))
 data=json.loads(cd[0].read_text(encoding='utf-8'))
 sub=data['subimagens'];expected={q['pagina']-1 for q in sub}
 changed=[];unexpected=[];cards=[]
 for j in range(len(b)):
  p,q=a[j],b[j];pa,pb=p.get_pixmap(),q.get_pixmap()
  aa=np.frombuffer(pa.samples,dtype=np.uint8).reshape(pa.height,pa.width,pa.n)
  ab=np.frombuffer(pb.samples,dtype=np.uint8).reshape(pb.height,pb.width,pb.n)
  diff=np.any(aa!=ab,axis=2)
  if not diff.any():continue
  changed.append(j+1)
  # Only the detail image area under the table may change.
  rects=[d['rect'] for d in q.get_drawings() if abs(d['rect'].x0-26)<1 and abs(d['rect'].width-248)<1 and d['rect'].y0>150 and d['rect'].height>40]
  mask=np.zeros(diff.shape,dtype=bool)
  for rect in rects:
   x0,y0,x1,y1=map(int,(rect.x0-2,rect.y0-2,rect.x1+3,rect.y1+3));mask[y0:y1,x0:x1]=True
  if j not in expected or np.any(diff & ~mask):unexpected.append(j+1)
  for k,rect in enumerate(rects):
   if not any(rect.intersects(fitz.Rect(v['quadro'])) for v in data['cameras'] if not v['contexto'] and (v['ang']!=0 or v['elev']!=0)):continue
   imgs=[]
   for page in (p,q):
    pix=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),clip=rect)
    imgs.append(Image.frombytes('RGB',[pix.width,pix.height],pix.samples))
   h=max(i.height for i in imgs);card=Image.new('RGB',(imgs[0].width+imgs[1].width+12,h+24),'white');dr=ImageDraw.Draw(card)
   dr.text((3,3),f'ANTES / DEPOIS - pagina {j+1}',fill='black');card.paste(imgs[0],(0,24));card.paste(imgs[1],(imgs[0].width+12,24));cards.append(card)
 if cards:
  height=sum(c.height for c in cards)+8*(len(cards)-1);sheet=Image.new('RGB',(max(c.width for c in cards),height),'white');y=0
  for c in cards:sheet.paste(c,(0,y));y+=c.height+8
  sheet.save(out/f'{idx:02}_detalhes.jpg',quality=88)
 integ=list(od.glob('*_INTEGRIDADE.json'))
 ck=dict(ambiente=r['ambiente'],paginas=len(b),paginas_iguais=len(a)==len(b),
  integridade=json.loads(integ[0].read_text(encoding='utf-8'))['aprovado'],
  paginas_alteradas=changed,alteracoes_fora_detalhes=unexpected,
  cameras_enquadradas=all(c['enquadrado'] for c in data['cameras']),
  detalhes=len(sub),ocultas=len(data['ocultas']),
  texto_cotas_preservado=all(a[j].get_text()==b[j].get_text() for j in range(len(b)) if 'MEDIDAS E ALTURAS' in b[j].get_text()))
 checks.append(ck);a.close();b.close()
(out/'RESULTADO.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
