from pathlib import Path
import json,pymupdf as f
from PIL import Image,ImageDraw
root=Path(r'C:\AGENTES COMPIERE\GIT_WORKSPACE_COMPIERE\SAIDAS_EXECUCAO_LIMPA_20261006_071156')
idx=json.loads((root/'INSPECAO_COMPARATIVA'/'INDICE.json').read_text(encoding='utf-8'))
selections=[('cozinha',6,[5,8,14,15]),('suite',8,[6,9,12,15]),('extras',9,[7,8])]
for tag,k,pages in selections:
 doc=f.open(idx[k]['pdf'])
 canvas=Image.new('RGB',(1600,640*((len(pages)+1)//2)),'white'); draw=ImageDraw.Draw(canvas)
 for j,n in enumerate(pages):
  p=doc[n-1]; pix=p.get_pixmap(matrix=f.Matrix(1.2,1.2),alpha=False)
  im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples); im.thumbnail((790,605))
  x=j%2*800; y=j//2*640
  draw.text((x+8,y+5),str(n)+' - '+idx[k]['ambiente'],fill='black')
  canvas.paste(im,(x+(800-im.width)//2,y+25))
 canvas.save(root/'INSPECAO_COMPARATIVA'/(tag+'_detalhes.jpg'),quality=92)
 print(tag)
