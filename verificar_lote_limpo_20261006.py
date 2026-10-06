# -*- coding: utf-8 -*-
import json, re, hashlib, sys
from pathlib import Path
import fitz
root=Path(__file__).resolve().parent
out=Path(sys.argv[1])
rows=json.loads((out/"RESULTADOS.json").read_text(encoding="utf-8"))
checks=[]; notes=[]
for row in rows:
    if row["status"]!="OK":
        notes.append({"ambiente":row["ambiente"],"status":row["status"],"motivo":row.get("motivo","")})
        continue
    p=Path(row["pdf"])
    render_errors=[]
    with fitz.open(p) as doc:
        for i,page in enumerate(doc):
            try: page.get_pixmap(matrix=fitz.Matrix(.3,.3),alpha=False)
            except Exception as e: render_errors.append({"pagina":i+1,"erro":str(e)})
    log=out/"AMBIENTES"/row["ambiente"]/"EXECUCAO.log"
    text=log.read_text(encoding="utf-8",errors="replace")
    warnings=[x for x in text.splitlines() if any(w in x for w in ("AVISO:","INCERTO |","FORA DA LISTAGEM:"))]
    checks.append({"ambiente":row["ambiente"],"paginas":row["paginas"],"erros_renderizacao":render_errors,"avisos":warnings})
changed=[]
record=json.loads((out/"VERSAO_E_VARREDURA.json").read_text(encoding="utf-8"))
for name,sha in record["fontes"].items():
    p=root/name
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha: changed.append(name)
(out/"VERIFICACAO_TECNICA.json").write_text(json.dumps({"fontes_alterados":changed,"pdfs":checks,"bloqueios":notes},ensure_ascii=False,indent=2),encoding="utf-8")
lines=["","## Verificacao tecnica desta execucao","",
    f"- PDFs abertos e paginas renderizadas: {len(checks)} / {sum(x['paginas'] for x in checks)}.",
    f"- Erros de renderizacao: {sum(len(x['erros_renderizacao']) for x in checks)}.",
    f"- Fontes do motor alterados: {len(changed)}.",
    "- Esta verificacao comprova execucao e integridade de leitura; falta auditoria visual e construtiva.","","## Bloqueios"]
for x in notes: lines.extend(["",f"### {x['ambiente']} — {x['status']}","",x["motivo"]])
lines.extend(["","## Avisos dos PDFs gerados"])
for x in checks:
    if x["avisos"]: lines.extend(["",f"### {x['ambiente']}",""]+["- "+w.strip(" -") for w in x["avisos"]])
with (out/"RELATORIO_EXECUCAO.md").open("a",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print(json.dumps({"pdfs":len(checks),"paginas":sum(x["paginas"] for x in checks),"erros_renderizacao":sum(len(x["erros_renderizacao"]) for x in checks),"fontes_alterados":changed,"bloqueios":[{"ambiente":x["ambiente"],"status":x["status"]} for x in notes]},ensure_ascii=False,indent=2))
