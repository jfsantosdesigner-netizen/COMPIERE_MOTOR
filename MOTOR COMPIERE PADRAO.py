import os, sys, glob, subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_NIVEIS = 3
def escolher():
    r=tk.Tk(); r.withdraw(); r.attributes("-topmost",True)
    p=filedialog.askdirectory(title="Selecione ambiente, cliente ou pasta de projetos")
    r.destroy(); return os.path.abspath(p) if p else ""
def tem_fontes(p):
    xml=[x for x in glob.glob(os.path.join(p,"*.xml")) if "xplod" not in os.path.basename(x).lower()]
    return bool(xml and glob.glob(os.path.join(p,"*.dxf")))
def ambientes(base):
    ach=[]
    if tem_fontes(base): ach.append(base)
    base_depth=base.rstrip(os.sep).count(os.sep)
    for atual,dirs,files in os.walk(base):
        nivel=atual.rstrip(os.sep).count(os.sep)-base_depth
        if nivel>=MAX_NIVEIS: dirs[:]=[]
        if nivel>0 and nivel<=MAX_NIVEIS and tem_fontes(atual): ach.append(atual)
    return sorted(set(ach))
def limpar_pecas(p):
    for n in ("_pecas_dxf.json","_pecas_dxf.json.md5"):
        f=os.path.join(p,n)
        if os.path.isfile(f): os.remove(f)

base=os.path.abspath(sys.argv[1]) if len(sys.argv)>1 else escolher()
if not base: raise SystemExit(0)
alvos=ambientes(base)
if not alvos:
    messagebox.showerror("Motor Compiere","Nenhum ambiente com XML + DXF encontrado até 3 níveis.")
    raise SystemExit(1)
ok=0
for i,p in enumerate(alvos,1):
    limpar_pecas(p)
    print(f"\n[{i}/{len(alvos)}] {p}")
    if subprocess.call([sys.executable,"-B",os.path.join(ROOT,"novo_ambiente.py"),p],cwd=ROOT)==0: ok+=1
messagebox.showinfo("Motor Compiere Padrão",f"Finalizado.\nAmbientes: {len(alvos)}\nSucessos: {ok}\nFalhas: {len(alvos)-ok}")
raise SystemExit(0 if ok==len(alvos) else 1)
