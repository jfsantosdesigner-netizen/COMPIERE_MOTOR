from pathlib import Path
from datetime import datetime
import json,subprocess,sys,time
import fitz
root=Path(__file__).resolve().parent
previous=root/'SAIDAS_PADRAO_CAMERAS_R6_20261006_085204'
out=root/('SAIDAS_VISTAS_PORTAS_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
rows=json.loads((previous/'RESULTADOS.json').read_text(encoding='utf-8'))
results=[]
for n,row in enumerate(rows,1):
    if row['status']!='OK':continue
    src=previous/'AMBIENTES'/row['ambiente']
    dest=out/'AMBIENTES'/row['ambiente'];dest.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((src/'_config.json').read_text(encoding='utf-8'))
    cfg['saida']=str(dest/'CADERNO.pdf')
    cfg['pecas_json']=str(dest/'_pecas_dxf.json')
    cpath=dest/'_config.json';cpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'[{n}/{len(rows)}] {row["ambiente"]}',flush=True)
    start=time.time()
    run=subprocess.run([sys.executable,'-B',str(root/'gerar_caderno.py'),str(cpath)],cwd=root,capture_output=True)
    (dest/'EXECUCAO.log').write_bytes(run.stdout+run.stderr)
    result=dict(ambiente=row['ambiente'],retorno=run.returncode,segundos=round(time.time()-start,1),paginas_antes=row['paginas'])
    if run.returncode==0 and Path(cfg['saida']).exists():
        with fitz.open(cfg['saida']) as doc:
            result['paginas_depois']=len(doc)
            for j,p in enumerate(doc):
                if 'DETALHE - NICHO' in p.get_text() and row['ambiente']=='TIAGO VOLPI\\COZINHA' and j+1 in (10,16):
                    p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(str(dest/f'pagina_{j+1}.png'))
        audit=json.loads((dest/'CADERNO_CAMERAS.json').read_text(encoding='utf-8'))
        result['subimagens']=[dict(pagina=s['pagina'],rotulo=s['rotulo'],camera=s['camera']) for s in audit['subimagens']]
        result['enquadrado']=all(c['enquadrado'] for c in audit['cameras'])
        result['vista_fragmento']=[line for line in run.stdout.decode('utf-8',errors='replace').splitlines() if 'VISTA-FRAGMENTO:' in line]
        result['status']='OK'
    else:
        result['status']='FALHA'
        result['erro']=(run.stderr or run.stdout).decode('utf-8',errors='replace')[-2000:]
    results.append(result)
    (out/'RESULTADOS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RESULTADO',result['status'],result.get('paginas_depois'),len(result.get('vista_fragmento',[])),flush=True)
print('CONCLUIDO',out,flush=True)
