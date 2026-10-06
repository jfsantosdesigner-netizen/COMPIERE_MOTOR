# -*- coding: utf-8 -*-
"""Runner isolado do bloco de especiais.

Uso:
    python rodar_especiais.py "C:\\...\\PASTA_DO_AMBIENTE"

Não altera gerar_caderno.py, novo_ambiente.py, launcher.py nem a pasta de entrada.
As saídas ficam em SAIDAS_ESPECIAIS.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PAD=json.load(open(ROOT/"padrao.json",encoding="utf-8"))
ASSETS=ROOT/"assets"
OUTROOT=ROOT/"SAIDAS_ESPECIAIS"

def arquivos(pasta):
    xmls=[p for p in pasta.glob("*.xml") if not re.search(r"x?plod",p.name,re.I)]
    dxfs=list(pasta.glob("*.dxf"))
    mont=[p for p in xmls if "montado" in p.name.lower()] or xmls
    return mont,dxfs

def processar(pasta):
    pasta=Path(pasta).resolve()
    mont,dxfs=arquivos(pasta)
    if not mont or not dxfs:
        print(f"FALTA XML+DXF: {pasta}")
        return 2
    cliente=re.sub(r"^PROJETO\s+","",pasta.parent.name,flags=re.I).upper()
    amb=re.sub(r"^EXECUTIVO\s*-?\s*","",pasta.name,flags=re.I).strip().title()
    dados={"cliente":cliente,"ambiente":amb,"projetista":PAD["projetista"],"arquiteta":PAD["arquiteta"]}
    for extra in (pasta.parent/"dados.json",pasta/"dados.json"):
        if extra.exists():
            dados.update(json.load(open(extra,encoding="utf-8")))
    od=OUTROOT/re.sub(r"[^A-Za-z0-9._ -]+","_",cliente)/re.sub(r"[^A-Za-z0-9._ -]+","_",amb)
    od.mkdir(parents=True,exist_ok=True)
    cfg={
        "tipo_caderno":PAD["tipo_caderno"],"dados":dados,
        "layout":str(Path(PAD.get("layout") or ASSETS/"LAYOUT_FIXO.pdf").resolve()),
        "contrato_fonte":str(Path(PAD.get("contrato_fonte") or ASSETS/"CONTRATO.pdf").resolve()),
        "xml":str(max(mont,key=lambda p:p.stat().st_mtime)),
        "dxf":str(max(dxfs,key=lambda p:p.stat().st_mtime)),
        "pecas_json":str(od/"_pecas_dxf.json"),"vistas":[],
        "logo":str(Path(PAD.get("logo") or ASSETS/"LOGO.png").resolve()),
        "materiais":PAD.get("materiais"),
        "saida":str(od/f"CADERNO - {amb.upper()} - BASE.pdf"),
        "saida_especiais":str(od/f"CADERNO - {amb.upper()} - COM ESPECIAIS.pdf"),
    }
    cj=od/"_config_especiais.json"
    json.dump(cfg,open(cj,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("="*70)
    print("COMPIERE — BLOCO ESPECIAIS")
    print("Entrada :",pasta)
    print("Saída   :",od)
    print("="*70)
    r=subprocess.run([sys.executable,str(ROOT/"gerar_caderno_com_especiais.py"),str(cj)],cwd=str(ROOT))
    return r.returncode

if __name__=="__main__":
    if len(sys.argv)<2:
        raise SystemExit('Uso: python rodar_especiais.py "PASTA_DO_AMBIENTE"')
    raise SystemExit(processar(sys.argv[1].strip('"')))
