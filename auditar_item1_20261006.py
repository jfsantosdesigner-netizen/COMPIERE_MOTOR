import json,sys,hashlib,re
from pathlib import Path
import fitz
out=Path(sys.argv[1]);root=out.parent
base=root/"SAIDAS_EXECUCAO_LIMPA_20261006_071156"
before={r["ambiente"]:r for r in json.loads((base/"RESULTADOS.json").read_text(encoding="utf-8")) if r["status"]=="OK"}
now={r["ambiente"]:r for r in json.loads((out/"RESULTADOS.json").read_text(encoding="utf-8"))}
checks=[]
for amb,b in before.items():
 r=now.get(amb,{})
 if r.get("status")!="OK":
  checks.append({"ambiente":amb,"aprovado":False,"motivo":r.get("motivo","Nao finalizado")});continue
 pd=Path(r["pdf"])
 integ=list((out/"AMBIENTES"/amb).glob("*_INTEGRIDADE.json"))
 val=json.loads(integ[0].read_text(encoding="utf-8"))
 with fitz.open(pd) as doc,fitz.open(b["pdf"]) as old:
  errors=[];changed=[]
  for n,p in enumerate(doc):
   try:
    pix=p.get_pixmap(matrix=fitz.Matrix(.5,.5),alpha=False)
    if n<len(old) and pix.samples!=old[n].get_pixmap(matrix=fitz.Matrix(.5,.5),alpha=False).samples:changed.append(n+1)
   except Exception as e:errors.append({"pagina":n+1,"erro":str(e)})
  texto="\n".join(p.get_text() for p in doc)
  required=[i for i in val["itens"] if i["obrigatorio"]]
  faltas=[i for i in val["itens"] if i["status"]=="FALHA"]
  novo={"ambiente":amb,"aprovado":val["aprovado"] and not errors,
   "paginas_antes":len(old),"paginas_depois":len(doc),"paginas_alteradas":changed,
   "itens_obrigatorios":len(required),"instancias_obrigatorias":sum(i["quantidade_xml"] for i in required),
   "faltas":faltas,"erros_renderizacao":errors,"sem_texto":[n+1 for n,p in enumerate(doc) if not p.get_text().strip()],
   "capa_contrato_preservados":all(doc[n].get_pixmap(matrix=fitz.Matrix(.5,.5)).samples==old[n].get_pixmap(matrix=fitz.Matrix(.5,.5)).samples for n in (0,1))}
  checks.append(novo)
(out/"AUDITORIA_ITEM1.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(checks,ensure_ascii=False,indent=2))
