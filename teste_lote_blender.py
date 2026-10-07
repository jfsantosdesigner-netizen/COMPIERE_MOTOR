# -*- coding: utf-8 -*-
import json, os, subprocess, sys, time
from pathlib import Path
MOTOR=Path(r"C:\Users\samsung 01\Meu Drive (jfschange@gmail.com)\COMPIERE - MOTOR\MOTOR ATUAL")
sys.path.insert(0,str(MOTOR))
import testar_blender
roots=[Path(r"C:\Users\samsung 01\Desktop\RECUPERADO_MOTOR_CADERNO\Teste"),
       Path(r"C:\Users\samsung 01\Desktop\RECUPERADO_MOTOR_CADERNO\Teste_backup"),
       Path(r"C:\Users\samsung 01\Desktop\RECUPERADO_MOTOR_CADERNO\COMPIERE_PROJETO\data\inputs")]
pastas=[]
for root in roots:
    if not root.exists(): continue
    for xml in root.rglob("*.xml"):
        p=xml.parent
        if list(p.glob("*.dxf")) and p not in pastas: pastas.append(p)
pastas=sorted(pastas,key=lambda p:str(p))
print("CASOS_ENCONTRADOS",len(pastas),flush=True)
resultados=[]
for n,pasta in enumerate(pastas,1):
    ini=time.time()
    try:
        blender,saida,pdf,cfg=testar_blender.preparar_config(pasta)
        saida.mkdir(exist_ok=True)
        env=dict(os.environ,COMPIERE_RENDER="blender",COMPIERE_BLENDER_AMOSTRAS="8",PYTHONIOENCODING="utf-8")
        print(f"[{n}/{len(pastas)}] INICIO {pasta}",flush=True)
        r=subprocess.run([sys.executable,"-B",str(MOTOR/"gerar_caderno.py"),json.dumps(cfg,ensure_ascii=False)],env=env,cwd=str(MOTOR),capture_output=True,text=True,encoding="utf-8",errors="replace")
        ok=r.returncode==0 and pdf.exists() and pdf.stat().st_size>10000
        detalhe="" if ok else (r.stdout+"\n"+r.stderr)[-3000:]
        resultados.append((str(pasta),"OK" if ok else "FALHA",round(time.time()-ini,1),detalhe))
        print(f"[{n}/{len(pastas)}] {'OK' if ok else 'FALHA'} {time.time()-ini:.1f}s",flush=True)
        if not ok: print(detalhe,flush=True)
    except Exception as e:
        resultados.append((str(pasta),"FALHA",round(time.time()-ini,1),repr(e))); print("FALHA",repr(e),flush=True)
rel=MOTOR/"RELATORIO_TESTE_BLENDER_21.txt"
rel.write_text("\n".join(f"{s} | {t}s | {p}\n{d}" for p,s,t,d in resultados),encoding="utf-8")
print("RESUMO",sum(s=="OK" for _,s,_,_ in resultados),"OK",sum(s!="OK" for _,s,_,_ in resultados),"FALHAS",flush=True)
print("RELATORIO",rel,flush=True)
