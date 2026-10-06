from pathlib import Path
import sys, subprocess, json, hashlib, shutil, datetime
import pymupdf as fitz
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "PROJETOS TESTES" / "RAFAEL CLARET"
OUT = ROOT / "SAIDAS_RAFAEL_SEM_COZINHA" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUT.mkdir(parents=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def limpar():
    # Apenas os quatro ambientes autorizados; cozinha fica fora desta rodada.
    for pasta in SRC.iterdir():
        if not pasta.is_dir() or "COZINHA" in pasta.name.upper(): continue
        for p in pasta.rglob("*"):
            if p.is_file() and (p.suffix.lower() in (".json", ".md5", ".pyc") or p.name.startswith("_prev_")):
                p.unlink()
    for n in ("cores_cache.json", "materiais_index.json"):
        (ROOT / n).unlink(missing_ok=True)
    for p in list(ROOT.rglob("__pycache__")):
        if ".git" not in p.parts and p.is_dir(): shutil.rmtree(p)
    p = ROOT / "_cache_texturas"
    if p.exists(): shutil.rmtree(p)
assets = ROOT / "assets"
resultados=[]
for pasta in sorted(p for p in SRC.iterdir() if p.is_dir() and "COZINHA" not in p.name.upper()):
    xmls=[p for p in pasta.glob("*.xml") if "xplod" not in p.name.lower()]
    mont=[p for p in xmls if "montado" in p.name.lower()] or xmls
    dxfs=list(pasta.glob("*.dxf"))
    if not mont or not dxfs: continue
    xml=max(mont,key=lambda p:p.stat().st_mtime)
    dxf=max(dxfs,key=lambda p:p.stat().st_mtime)
    hashes={str(p):sha(p) for p in (xml,dxf)}
    limpar()
    work=OUT/pasta.name
    work.mkdir()
    cfg=dict(tipo_caderno="MONTAGEM E INSTALAÇÃO", dados=dict(cliente="RAFAEL CLARET",ambiente=pasta.name.replace("_"," ").title(),projetista="JOÃO FELIPE SANTOS",arquiteta="FERNANDA"),layout=str(assets/"LAYOUT_FIXO.pdf"),contrato_fonte=str(assets/"CONTRATO.pdf"),logo=str(assets/"LOGO.png"),materiais="MATERIAIS",xml=str(xml),dxf=str(dxf),pecas_json=str(work/"_pecas_dxf.json"),vistas=[],fontes_frescas=True,saida=str(work/f"CADERNO - {pasta.name}.pdf"))
    config=work/"_config.json"
    config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    print("GERANDO",pasta.name,flush=True)
    with (work/"execucao.log").open("w",encoding="utf-8") as log:
        r=subprocess.run([sys.executable,"-B",str(ROOT/"gerar_caderno.py"),str(config)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    item=dict(ambiente=pasta.name,xml=str(xml),dxf=str(dxf),saida=cfg["saida"],retorno=r.returncode,fontes_preservadas=all(sha(Path(p))==h for p,h in hashes.items()))
    pdf=Path(cfg["saida"])
    if pdf.exists():
        with fitz.open(pdf) as doc:
            item["paginas"]=len(doc)
            item["titulos"]=[page.get_text()[:600] for page in doc]
    integ=pdf.with_name(pdf.stem+"_INTEGRIDADE.json")
    if integ.exists():
        data=json.loads(integ.read_text(encoding="utf-8"))
        item["integridade_aprovada"]=data.get("aprovado")
        item["pendencias_integridade"]=[x for x in data.get("itens",[]) if x.get("status")!="OK"]
    resultados.append(item)
    print(json.dumps({k:v for k,v in item.items() if k not in ("titulos","pendencias_integridade")},ensure_ascii=False),flush=True)
# Cache não permanece como referência para a próxima execução.
limpar()
(OUT/"RESULTADO_RAFAEL.json").write_text(json.dumps(resultados,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASTA="+str(OUT),flush=True)
sys.exit(0 if len(resultados)==4 and all(r["retorno"]==0 and r.get("paginas",0)>0 and r["fontes_preservadas"] for r in resultados) else 1)
