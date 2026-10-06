from pathlib import Path
import json,fitz,numpy as np
root=Path(__file__).resolve().parent
old=root/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'
new=root/'SAIDAS_VISTAS_PORTAS_20261006_092455'
before={x['ambiente']:x for x in json.loads((old/'RESULTADOS.json').read_text(encoding='utf-8')) if x['status']=='OK'}
after=json.loads((new/'RESULTADOS.json').read_text(encoding='utf-8'))
summary=[]
for x in after:
    prior=root/'SAIDAS_VISTAS_ALVOS_20261006_091141'/x['ambiente']/'CADERNO.pdf'
    if not prior.exists(): prior=Path(before[x['ambiente']]['pdf'])
    a=fitz.open(prior)
    b=fitz.open(new/'AMBIENTES'/x['ambiente']/'CADERNO.pdf')
    assert len(a)==len(b)
    changed=[]
    for n,(p,q) in enumerate(zip(a,b),1):
        assert p.get_text()==q.get_text(),(x['ambiente'],n,'texto')
        im1=p.get_pixmap();im2=q.get_pixmap()
        if im1.samples!=im2.samples:
            changed.append(n)
            aa=np.frombuffer(im1.samples,np.uint8).reshape(im1.height,im1.width,im1.n)
            ab=np.frombuffer(im2.samples,np.uint8).reshape(im2.height,im2.width,im2.n)
            yy,xx=np.where(np.any(aa!=ab,axis=2))
            assert xx.max()<=275 and yy.min()>160,(x['ambiente'],n,'fora do quadro do detalhe',xx.min(),xx.max(),yy.min(),yy.max())
    assert (not changed) if x['ambiente']!='TIAGO VOLPI\\COZINHA' else changed==[10,16],(x['ambiente'],changed)
    summary.append(dict(ambiente=x['ambiente'],paginas=len(b),alteradas=changed))
(new/'COMPARACAO_PIXELS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('APROVADO',len(summary),'ambientes',sum(r['paginas'] for r in summary),'páginas',[(r['ambiente'],r['alteradas']) for r in summary if r['alteradas']])
