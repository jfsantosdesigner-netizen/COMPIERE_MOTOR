import json,re,sys,hashlib
from pathlib import Path
import pymupdf as fz
out=Path(sys.argv[1]);old=Path(sys.argv[2])
before={r["ambiente"]:r for r in json.loads((old/"RESULTADOS.json").read_text(encoding="utf-8")) if r["status"]=="OK"}
now={r["ambiente"]:r for r in json.loads((out/"RESULTADOS.json").read_text(encoding="utf-8"))}
results=[]
for amb,b in before.items():
 r=now.get(amb,{})
 if r.get("status")!="OK":results.append({"ambiente":amb,"preservado":False,"motivo":"Geracao pendente ou falhou"});continue
 def lista(doc):
  out={}
  for n,p in enumerate(doc):
   text=p.get_text()
   if "MÓDULOS E PAINÉIS -" not in text:continue
   title=next(l for l in text.splitlines() if "MÓDULOS E PAINÉIS -" in l)
   pix=p.get_pixmap(matrix=fz.Matrix(1,1),clip=fz.Rect(0,125,p.rect.width,p.rect.height),alpha=False)
   out[title]={"pagina":n+1,"hash_conteudo":hashlib.sha256(pix.samples).hexdigest()}
  return out
 with fz.open(b["pdf"]) as d0,fz.open(r["pdf"]) as d1:
  a,c=lista(d0),lista(d1)
  dif=[k for k in set(a)|set(c) if k not in a or k not in c or a[k]["hash_conteudo"]!=c[k]["hash_conteudo"]]
  results.append({"ambiente":amb,"preservado":not dif,"listagens_antes":len(a),"listagens_depois":len(c),"listagens_alteradas":dif,
                  "paginas_antes":len(d0),"paginas_depois":len(d1),"listagens_novas":c})
rec0=json.loads((old/"VERSAO_E_VARREDURA.json").read_text(encoding="utf-8"))["fontes"]
rec1=json.loads((out/"VERSAO_E_VARREDURA.json").read_text(encoding="utf-8"))["fontes"]
mods={f:rec0.get(f)==rec1.get(f) for f in ("normal/regras.py","normal/ocultas.py","normal/vidros.py")}
report={"modulos_subimagem_preservados":mods,"projetos":results}
(out/"PRESERVACAO_SUBIMAGENS.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
