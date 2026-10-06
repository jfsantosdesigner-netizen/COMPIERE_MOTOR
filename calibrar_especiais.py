# -*- coding: utf-8 -*-
"""Validação em lote do bloco de especiais usando somente PROJETOS TESTES.

Não altera entradas nem gerar_caderno.py. Cada ambiente com XML+DXF é executado pelo
runner isolado. Produz CSV/MD com retorno, PDF e famílias detectadas.
"""
from __future__ import annotations
import csv, re, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TESTES=ROOT/"PROJETOS TESTES"
OUT=ROOT/"SAIDAS_ESPECIAIS"
LOG=OUT/"_CALIBRACAO"
LOG.mkdir(parents=True,exist_ok=True)

def ambientes():
    for p in sorted({x.parent for x in TESTES.rglob("*.dxf")}):
        if list(p.glob("*.xml")):
            yield p

def cliente_amb(p):
    cliente=re.sub(r"^PROJETO\s+","",p.parent.name,flags=re.I).upper()
    amb=re.sub(r"^EXECUTIVO\s*-?\s*","",p.name,flags=re.I).strip().title()
    clean=lambda s: re.sub(r"[^A-Za-z0-9._ -]+","_",s)
    return cliente,amb,OUT/clean(cliente)/clean(amb)

rows=[]; t0=time.time()
for k,p in enumerate(ambientes(),1):
    print(f"[{k}] {p.relative_to(TESTES)}",flush=True)
    t=time.time()
    cp=subprocess.run([sys.executable,str(ROOT/"rodar_especiais.py"),str(p)],
                      cwd=str(ROOT),capture_output=True,text=True,errors="replace")
    cliente,amb,od=cliente_amb(p)
    rels=list(od.glob("*_ESPECIAIS.md"))
    familias=[]
    if rels:
        for ln in rels[0].read_text(encoding="utf-8",errors="replace").splitlines():
            m=re.match(r"- ([a-z_]+): prancha",ln)
            if m: familias.append(m.group(1))
    rows.append({
        "projeto":str(p.relative_to(TESTES)),"retorno":cp.returncode,
        "segundos":round(time.time()-t,2),"familias":";".join(familias),
        "qtd_familias":len(familias),"pdf":str(next(iter(od.glob("*COM ESPECIAIS.pdf")),"")),
    })
    (LOG/(f"{k:02d}.log")).write_text(cp.stdout+"\n--- STDERR ---\n"+cp.stderr,encoding="utf-8")

csvp=LOG/"calibracao.csv"
with csvp.open("w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys() if rows else ["projeto"])
    w.writeheader(); w.writerows(rows)
md=["# CALIBRAÇÃO — PRANCHAS ESPECIAIS","",
    f"- Ambientes executados: {len(rows)}",
    f"- Sucesso: {sum(r['retorno']==0 for r in rows)}",
    f"- Falha: {sum(r['retorno']!=0 for r in rows)}",
    f"- Tempo total: {round(time.time()-t0,1)} s","","## Resultado"]
for r in rows:
    st="OK" if r["retorno"]==0 else "FALHA"
    md.append(f"- {st} | {r['projeto']} | especiais: {r['familias'] or 'nenhuma'} | {r['segundos']} s")
mdp=LOG/"CALIBRACAO.md"; mdp.write_text("\n".join(md),encoding="utf-8")
print(mdp)
raise SystemExit(0 if rows and all(r["retorno"]==0 for r in rows) else 1)
