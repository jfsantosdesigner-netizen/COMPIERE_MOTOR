import json,sys
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw
out=Path(sys.argv[1]); dest=out/"INSPECAO_COMPARATIVA"; dest.mkdir(exist_ok=True)
rows=json.loads((out/"RESULTADOS.json").read_text(encoding="utf-8")); index=[]
for i,row in enumerate(rows):
 if row["status"]!="OK": continue
 doc=fitz.open(row["pdf"]); texts=[]
 for n,p in enumerate(doc): texts.append({"pagina":n+1,"texto":p.get_text()})
 (dest/f"{i:02d}_texto.json").write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding="utf-8")
 pages=list(range(2,len(doc)))
 w=640; h=460
 canvas=Image.new("RGB",(w*3,h*((len(pages)+2)//3)),"white"); draw=ImageDraw.Draw(canvas)
 for k,n in enumerate(pages):
  p=doc[n]; pix=p.get_pixmap(matrix=fitz.Matrix(.85,.85),alpha=False)
  im=Image.frombytes("RGB",(pix.width,pix.height),pix.samples); im.thumbnail((w-8,h-30))
  x=(k%3)*w; y=(k//3)*h
  draw.text((x+8,y+5),f"P{n+1} - {row['ambiente']}",fill="black")
  canvas.paste(im,(x+(w-im.width)//2,y+25))
 target=dest/f"{i:02d}_contato.jpg"; canvas.save(target,quality=87)
 index.append({"ambiente":row["ambiente"],"paginas":len(doc),"contato":str(target),"texto":str(dest/f"{i:02d}_texto.json"),"pdf":row["pdf"]})
 doc.close()
(dest/"INDICE.json").write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(index,ensure_ascii=False,indent=2))
