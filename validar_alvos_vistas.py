from pathlib import Path
from datetime import datetime
import json,subprocess,sys,hashlib
import fitz
root=Path(__file__).resolve().parent
old=root/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'
out=root/('SAIDAS_VISTAS_ALVOS_'+datetime.now().strftime('%Y%m%d_%H%M%S')); out.mkdir()
rows=json.loads((old/'RESULTADOS.json').read_text(encoding='utf-8'))
results=[]
for row in rows:
    if row['status']!='OK' or row['ambiente'] not in ['PRISCILA CLAUDINO\\COZINHA','TIAGO VOLPI\\COZINHA','ADRIANA OJEDA\\DORMITÓRIO']: continue
    src=old/'AMBIENTES'/row['ambiente']
    od=out/row['ambiente'];od.mkdir(parents=True)
    cfg=json.loads((src/'_config.json').read_text(encoding='utf-8'))
    cfg['saida']=str(od/'CADERNO.pdf');cfg['pecas_json']=str(od/'_pecas_dxf.json')
    cp=od/'_config.json';cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    print('GERANDO',row['ambiente'],flush=True)
    run=subprocess.run([sys.executable,'-B',str(root/'gerar_caderno.py'),str(cp)],cwd=root,capture_output=True)
    (od/'EXECUCAO.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,(row['ambiente'],run.stderr[-1000:])
    a=fitz.open(row['pdf']);b=fitz.open(cfg['saida']); assert len(a)==len(b)
    changed=[];changes=[]
    for j,(pa,pb) in enumerate(zip(a,b)):
        assert pa.get_text()==pb.get_text(),(row['ambiente'],j,'texto mudou')
        if pa.get_pixmap().samples!=pb.get_pixmap().samples:
            changed.append(j+1)
            assert any(t in pb.get_text() for t in ['SUPERIORES','INFERIORES','PARTE 1','PARTE 2']),(row['ambiente'],j,'pagina fora da divisão')
            pb.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(str(od/('pagina_'+str(j+1)+'.png')))
    ca=json.loads((od/'CADERNO_CAMERAS.json').read_text(encoding='utf-8'))
    assert all(c['enquadrado'] for c in ca['cameras'])
    before=json.loads(next(src.glob('*_CAMERAS.json')).read_text(encoding='utf-8'))
    assert ca['subimagens']==before['subimagens'],'subimagem alterada'
    z=dict(ambiente=row['ambiente'],paginas=len(b),paginas_alteradas=changed,texto_preservado=True,subimagens_preservadas=True,enquadrado=True)
    results.append(z)
    print(z,flush=True)
(out/'RESULTADOS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('CONCLUIDO',out,flush=True)
