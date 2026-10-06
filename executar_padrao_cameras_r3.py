# -*- coding: utf-8 -*-
"""Execucao limpa de diagnostico, sem alterar as regras do motor."""
import os, sys, json, shutil, subprocess, time, hashlib, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
STAMP=datetime.now().strftime("%Y%m%d_%H%M%S")
OUT=ROOT/("SAIDAS_PADRAO_CAMERAS_R3_"+STAMP)
OUT.mkdir()
PDFS=OUT/"PDFS_JUNTOS"; PDFS.mkdir()
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
os.environ["PYTHONUTF8"]="1"
os.environ["PYTHONIOENCODING"]="utf-8"
def git(*args):
    return subprocess.run(["git","-C",str(ROOT),*args],capture_output=True,text=True,encoding="utf-8",errors="replace").stdout.strip()
commit=git("rev-parse","HEAD")
sources={}
inventory=[]
for base in [ROOT.parent/"core_motor",ROOT,ROOT.parent/"_prev_novo",ROOT.parent/"_ARQUIVO_2026-10-05"]:
    for directory,dirs,files in os.walk(base):
        dirs[:]=[d for d in dirs if d not in {".git","node_modules",".venv","venv","texturas","__pycache__"} and not d.startswith("_compiere_especiais_")]
        for name in files:
            if name.endswith(".py") and name.startswith("gerar_caderno"):
                p=Path(directory)/name
                inventory.append({"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"mtime":p.stat().st_mtime})
for p in ROOT.rglob("*.py"):
    if any(x in p.parts for x in (".git","_backups","__pycache__")): continue
    if len(p.relative_to(ROOT).parts)<=2 and not p.name.startswith("_"):
        sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/"VERSAO_E_VARREDURA.json").write_text(json.dumps({"commit":commit,"status_antes":git("status","--short"),"versoes":inventory,"fontes":sources},ensure_ascii=False,indent=2),encoding="utf-8")
print("VERSAO",commit,"SAIDA",OUT,flush=True)
# Somente caches regeneraveis; os resultados anteriores permanecem.
removed=[]
for directory,dirs,files in os.walk(ROOT,topdown=True):
    dirs[:]=[d for d in dirs if d not in {".git","_backups",".venv","venv","node_modules"} and Path(directory)/d != OUT]
    for d in list(dirs):
        if d in {"__pycache__",".pytest_cache",".mypy_cache",".ruff_cache","_cache_texturas"} or d.startswith("_compiere_especiais_"):
            p=Path(directory)/d
            shutil.rmtree(p)
            removed.append(str(p)); dirs.remove(d)
    for name in files:
        if name in {"cores_cache.json","_pecas_dxf.json","_pecas_dxf.json.md5"} or name.endswith((".pyc",".pyo")):
            p=Path(directory)/name
            p.unlink(); removed.append(str(p))
(OUT/"CACHES_REMOVIDOS.json").write_text(json.dumps(removed,ensure_ascii=False,indent=2),encoding="utf-8")
print("CACHES_REMOVIDOS",len(removed),flush=True)
cmd=[sys.executable,"-B","-m","unittest","test_camera_comum","test_cotas_comum","normal.test_regras","normal.test_ocultas","test_integridade","normal.test_cameras","-v"]
test=subprocess.run(cmd,cwd=ROOT,capture_output=True)
(OUT/"TESTES.log").write_bytes(test.stdout+b"\n"+test.stderr)
print("TESTES_RETORNO",test.returncode,flush=True)
if test.returncode: raise SystemExit("Testes falharam; lote nao iniciado.")
PAD=json.loads((ROOT/"padrao.json").read_text(encoding="utf-8"))
ENT=ROOT/"PROJETOS TESTES"
projects=sorted({p.parent for p in ENT.rglob("*.xml")})
rows=[]
def persist():
    (OUT/"RESULTADOS.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
for i,p in enumerate(projects,1):
    rel=p.relative_to(ENT)
    xmls=[x for x in p.glob("*.xml") if not re.search(r"x?plod",x.name,re.I)]
    dxfs=list(p.glob("*.dxf"))
    row={"ambiente":str(rel),"status":"INCOMPLETO","retorno":None,"pdf":"","paginas":0,"segundos":0}
    if not xmls or not dxfs:
        row["motivo"]="Falta XML montado" if not xmls else "Falta DXF"
        rows.append(row); persist(); print("INCOMPLETO",rel,row["motivo"],flush=True); continue
    od=OUT/"AMBIENTES"/rel; od.mkdir(parents=True)
    mont=[x for x in xmls if "montado" in x.name.lower()] or xmls
    cliente=re.sub(r"^PROJETO\s+","",p.parent.name,flags=re.I).upper()
    amb=re.sub(r"^EXECUTIVO\s*-?\s*","",p.name,flags=re.I).strip().title()
    dados={"cliente":cliente,"ambiente":amb,"projetista":PAD["projetista"],"arquiteta":PAD["arquiteta"]}
    for extra in (p.parent/"dados.json",p/"dados.json"):
        if extra.exists(): dados.update(json.loads(extra.read_text(encoding="utf-8")))
    asset=lambda key,f: str(Path(PAD.get(key) or ROOT/"assets"/f).resolve())
    pdf=od/("CADERNO - "+amb.upper()+" - PADRAO.pdf")
    cfg={"tipo_caderno":PAD["tipo_caderno"],"dados":dados,
        "layout":asset("layout","LAYOUT_FIXO.pdf"),"contrato_fonte":asset("contrato_fonte","CONTRATO.pdf"),
        "logo":asset("logo","LOGO.png"),"materiais":PAD.get("materiais"),
        "xml":str(max(mont,key=lambda x:x.stat().st_mtime)),"dxf":str(max(dxfs,key=lambda x:x.stat().st_mtime)),
        "pecas_json":str(od/"_pecas_dxf.json"),"vistas":[],
        "saida":str(pdf)}
    config=od/"_config.json"; config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"[{i}/{len(projects)}] {rel}",flush=True)
    start=time.time()
    cp=subprocess.run([sys.executable,"-B",str(ROOT/"gerar_caderno.py"),str(config)],cwd=ROOT,capture_output=True)
    (od/"EXECUCAO.log").write_bytes(cp.stdout+b"\n--- STDERR ---\n"+cp.stderr)
    row.update(retorno=cp.returncode,segundos=round(time.time()-start,1),status="FALHA")
    if cp.returncode==0 and pdf.exists():
        import fitz
        with fitz.open(pdf) as doc:
            row["paginas"]=len(doc)
            row["paginas_sem_texto"]=[n+1 for n,page in enumerate(doc) if not page.get_text().strip()]
            row["paginas_normais"]=len(doc)
        report=pdf.with_name(pdf.stem+"_ESPECIAIS.md")
        if report.exists(): row["especiais"]=report.read_text(encoding="utf-8")
        name=" - ".join(rel.parts)+" - PADRAO.pdf"
        target=PDFS/name; shutil.copy2(pdf,target)
        row.update(status="OK",pdf=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    else:
        row["motivo"]=(cp.stderr or cp.stdout).decode("utf-8",errors="replace")[-2500:]
    rows.append(row); persist()
    print("RESULTADO",row["status"],"PAGINAS",row["paginas"],"TEMPO",row["segundos"],flush=True)
lines=["# Execucao limpa COMPIERE","",f"Commit: {commit}",f"Caches removidos: {len(removed)}",
    f"Testes: retorno {test.returncode}",f"PDFs completos: {sum(r['status']=='OK' for r in rows)}",
    f"Falhas: {sum(r['status']=='FALHA' for r in rows)}",f"Incompletos: {sum(r['status']=='INCOMPLETO' for r in rows)}",
    f"Paginas geradas: {sum(r['paginas'] for r in rows)}","",
    "Resultado de execucao e abertura dos PDFs. Nao equivale a aprovacao visual ou construtiva.","",
    "| Ambiente | Status | Paginas | Segundos |","|---|---|---:|---:|"]
for r in rows: lines.append(f"| {r['ambiente']} | {r['status']} | {r['paginas']} | {r['segundos']} |")
(OUT/"RELATORIO_EXECUCAO.md").write_text("\n".join(lines),encoding="utf-8")
changes=[]
for name,sha in sources.items():
    p=ROOT/name
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha: changes.append(name)
print("FONTES_ALTERADOS",changes,flush=True)
print("\n".join(lines[:10]),flush=True)
print("CONCLUIDO",OUT,flush=True)