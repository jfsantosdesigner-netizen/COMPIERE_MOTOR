import json,re,sys,unicodedata
from pathlib import Path
import pymupdf as fitz
out=Path(sys.argv[1]);dest=out/"AUDITORIA_PADRAO";dest.mkdir(exist_ok=True)
norm=lambda t: unicodedata.normalize("NFKD",t).encode("ascii","ignore").decode().upper()
rows=json.loads((out/"RESULTADOS.json").read_text(encoding="utf-8"))
checks=[]
for row in rows:
 if row["status"]!="OK":continue
 events=[];sub=[];errors=[]
 with fitz.open(row["pdf"]) as doc:
  for n,p in enumerate(doc):
   t=p.get_text();s=norm(t)
   m=re.search(r"(MODULOS E PAINEIS|MEDIDAS E ALTURAS)\s*-\s*(VISTAS? [A-Z](?: E [A-Z])?)",s)
   if m:events.append({"pagina":n+1,"tipo":"LISTAGEM" if m[1]=="MODULOS E PAINEIS" else "COTAS","vista":m[2]})
   labels=[l for l in t.splitlines() if any(w in norm(l) for w in ("DETALHE - NICHO","BASE DE APOIO","POSICAO NO MOVEL","GAVETA","CANTO L","CANTO RETO","ADEGA","CRISTALEIRA","ACESSORIO INTERNO","PRATELEIRA DE VIDRO","MESA DE CABECEIRA"))]
   if labels:sub.append({"pagina":n+1,"rotulos":labels})
   try:p.get_pixmap(matrix=fitz.Matrix(.3,.3),alpha=False)
   except Exception as e:errors.append(str(e))
  special=[n+1 for n,p in enumerate(doc) if any(w in norm(p.get_text()) for w in ("SEQUENCIA DE MONTAGEM","SAPATEIRA - DETALHAMENTO","CURVO / RAIO - DETALHAMENTO","DIVISOR DE GAVETA - DETALHAMENTO","PORTA COM PERFIL - DETALHAMENTO"))]
 violations=[];pending=None
 for e in events:
  if e["tipo"]=="LISTAGEM":
   if pending and pending!=e["vista"]:violations.append("Listagem "+pending+" sem cotas antes de "+e["vista"])
   pending=e["vista"]
  else:
   if pending!=e["vista"]:violations.append("Cotas "+e["vista"]+" sem listagem correspondente imediata")
   pending=None
 if pending:violations.append("Listagem "+pending+" sem cotas")
 integ=next((out/"AMBIENTES"/row["ambiente"]).glob("*_INTEGRIDADE.json"))
 val=json.loads(integ.read_text(encoding="utf-8"))
 checks.append({"ambiente":row["ambiente"],"paginas":row["paginas"],"integridade":val["aprovado"],"sequencia_aprovada":not violations,"violacoes":violations,"eventos":events,"subimagens_rotulos":sub,"erros_render":errors,"pranchas_especiais":special})
(dest/"RESULTADO.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps([{"ambiente":c["ambiente"],"paginas":c["paginas"],"integridade":c["integridade"],"sequencia_aprovada":c["sequencia_aprovada"],"violacoes":c["violacoes"],"erros_render":c["erros_render"],"pranchas_especiais":c["pranchas_especiais"]} for c in checks],ensure_ascii=False,indent=2))
