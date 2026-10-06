from pathlib import Path
import json,fitz,numpy as np
root=Path(__file__).resolve().parent
old=root/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'
new=root/'SAIDAS_VISTAS_ALVOS_20261006_091141'
rows=json.loads((new/'RESULTADOS.json').read_text(encoding='utf-8'))
prior={r['ambiente']:r for r in json.loads((old/'RESULTADOS.json').read_text(encoding='utf-8'))}
for row in rows:
    a=fitz.open(prior[row['ambiente']]['pdf'])
    b=fitz.open(new/row['ambiente']/'CADERNO.pdf')
    for j in row['paginas_alteradas']:
        x=a[j-1].get_pixmap();y=b[j-1].get_pixmap()
        aa=np.frombuffer(x.samples,np.uint8).reshape(x.height,x.width,x.n)
        ab=np.frombuffer(y.samples,np.uint8).reshape(y.height,y.width,y.n)
        yy,xx=np.where(np.any(aa!=ab,axis=2))
        assert xx.min()>=283,(row,j,xx.min())
        print(row['ambiente'],j,'somente imagem principal')
    row['pixels_fora_imagem_principal_preservados']=True
(new/'RESULTADOS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('APROVADO')
