from pathlib import Path
import subprocess, sys, shutil, hashlib, json, datetime
import fitz
ROOT = Path(__file__).resolve().parent
BASE = ROOT / "PROJETOS TESTES"
ALVOS = ["CAROLINE_COZINHA", "FELIPE_COZINHA", "ADRIANA OJEDA/DORMITÓRIO", "TIAGO VOLPI/DORMITÓRIO CASAL", "JAQUELINE DA SILVA/CLOSET", "LETICIA MATEUS"]
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
AUD = ROOT / ("AUDITORIA_SEIS_FONTES_" + stamp)
AUD.mkdir()
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
fontes = {}
for rel in ALVOS:
    pasta = BASE / rel
    src = [p for p in pasta.iterdir() if p.suffix.lower() in (".xml", ".dxf")]
    assert any(p.suffix.lower()==".xml" for p in src) and any(p.suffix.lower()==".dxf" for p in src), rel
    fontes[rel] = {p.name:digest(p) for p in src}
    dest = AUD / "anteriores" / rel
    dest.mkdir(parents=True)
    for p in pasta.iterdir():
        if p.is_file() and (p.suffix.lower() in (".json", ".md5") or p.name.startswith(("CADERNO - ", "_prev_"))):
            shutil.copy2(p, dest / p.name)
            p.unlink()
    for p in pasta.rglob("__pycache__"):
        if p.is_dir(): shutil.rmtree(p)
for name in ("cores_cache.json", "materiais_index.json"):
    p = ROOT / name
    if p.exists():
        shutil.copy2(p, AUD / name)
        p.unlink()
p = ROOT / "_cache_texturas"
if p.exists(): shutil.rmtree(p)
resultados = []
for i, rel in enumerate(ALVOS, 1):
    print(f"[{i}/6] {rel}", flush=True)
    pasta = BASE / rel
    log = AUD / (str(i) + ".log")
    with log.open("w", encoding="utf-8") as out:
        r = subprocess.run([sys.executable, "-B", str(ROOT / "novo_ambiente.py"), str(pasta)], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    pdfs = list(pasta.glob("CADERNO - *.pdf"))
    item = dict(ambiente=rel, returncode=r.returncode, log=str(log), fontes_preservadas=all(digest(pasta / n)==h for n,h in fontes[rel].items()))
    if r.returncode==0 and len(pdfs)==1:
        with fitz.open(pdfs[0]) as doc:
            item.update(pdf=str(pdfs[0]), paginas=len(doc), paginas_sem_texto=[n+1 for n,p in enumerate(doc) if not p.get_text().strip()])
        checks = list(pasta.glob("*_INTEGRIDADE.json"))
        if checks: item["integridade"] = json.loads(checks[0].read_text(encoding="utf-8"))
    resultados.append(item)
    (AUD / "resultado.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in item.items() if k!="integridade"}, ensure_ascii=False), flush=True)
print("AUDITORIA=" + str(AUD), flush=True)
sys.exit(0 if all(x["returncode"]==0 and x.get("paginas",0)>0 and x["fontes_preservadas"] for x in resultados) else 1)
