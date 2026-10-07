# -*- coding: utf-8 -*-
"""Launcher gráfico e seguro para testar o backend Blender."""
import json, os, re, subprocess, sys, threading
from pathlib import Path
import renderizador

RAIZ = Path(__file__).resolve().parent

def preparar_config(pasta):
    """Valida a entrada e monta a configuração sem alterar a pasta escolhida."""
    pasta = Path(pasta).resolve()
    if not pasta.is_dir(): raise ValueError('A pasta escolhida não existe.')
    xmls = sorted(x for x in pasta.glob('*.xml') if not re.search(r'x?plod', x.name, re.I))
    dxfs = sorted(pasta.glob('*.dxf'))
    if not xmls or not dxfs: raise ValueError('A pasta precisa conter pelo menos um arquivo XML e um DXF.')
    blender = renderizador.localizar_blender()
    if not blender: raise ValueError('Blender não encontrado. Instale-o ou configure BLENDER_EXE.')
    with open(RAIZ/'padrao.json', encoding='utf-8') as arq: pad = json.load(arq)
    saida = pasta/'_TESTE_BLENDER'; pdf = saida/f'CADERNO BLENDER - {pasta.name.upper()}.pdf'
    cfg = {'tipo_caderno': pad['tipo_caderno'],
           'dados': {'cliente': pasta.parent.name.upper(), 'ambiente': pasta.name.title(),
                     'projetista': pad['projetista'], 'arquiteta': pad['arquiteta']},
           'layout': str(RAIZ/'assets'/'LAYOUT_FIXO.pdf'),
           'contrato_fonte': str(RAIZ/'assets'/'CONTRATO.pdf'), 'logo': str(RAIZ/'assets'/'LOGO.png'),
           'xml': str(xmls[0]), 'dxf': str(dxfs[0]), 'vistas': [],
           'materiais': pad.get('materiais'), 'saida': str(pdf)}
    return blender, saida, pdf, cfg

class Launcher:
    def __init__(self, raiz):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.raiz = tk, raiz
        raiz.title('Compiere — Teste Blender'); raiz.geometry('760x520'); raiz.minsize(680,460); raiz.configure(bg='#17202a')
        topo=tk.Frame(raiz,bg='#17202a',padx=24,pady=20); topo.pack(fill='x')
        tk.Label(topo,text='COMPIERE  •  TESTE BLENDER',bg='#17202a',fg='#f4d03f',font=('Segoe UI',17,'bold')).pack(anchor='w')
        tk.Label(topo,text='Gera uma cópia de teste sem alterar os arquivos do cliente.',bg='#17202a',fg='#d5d8dc',font=('Segoe UI',10)).pack(anchor='w',pady=(4,0))
        corpo=tk.Frame(raiz,bg='#ecf0f1',padx=24,pady=18); corpo.pack(fill='both',expand=True)
        tk.Label(corpo,text='Pasta do ambiente (XML + DXF)',bg='#ecf0f1',fg='#17202a',font=('Segoe UI',10,'bold')).pack(anchor='w')
        linha=tk.Frame(corpo,bg='#ecf0f1'); linha.pack(fill='x',pady=(7,13))
        self.pasta=tk.StringVar(value=sys.argv[1].strip('"') if len(sys.argv)>1 else '')
        ttk.Entry(linha,textvariable=self.pasta).pack(side='left',fill='x',expand=True)
        ttk.Button(linha,text='Escolher pasta',command=self.escolher).pack(side='left',padx=(8,0))
        self.botao=tk.Button(corpo,text='INICIAR TESTE',command=self.iniciar,bg='#f4d03f',fg='#17202a',activebackground='#f7dc6f',relief='flat',padx=22,pady=10,font=('Segoe UI',11,'bold')); self.botao.pack(anchor='w')
        self.status=tk.StringVar(value='Pronto para testar.')
        tk.Label(corpo,textvariable=self.status,bg='#ecf0f1',fg='#566573',font=('Segoe UI',9)).pack(anchor='w',pady=(10,6))
        self.log=tk.Text(corpo,height=13,bg='#101820',fg='#d5d8dc',insertbackground='white',relief='flat',padx=10,pady=10,font=('Consolas',9),state='disabled'); self.log.pack(fill='both',expand=True)
    def escrever(self,texto):
        self.log.configure(state='normal'); self.log.insert('end',texto.rstrip()+'\n'); self.log.see('end'); self.log.configure(state='disabled')
    def escolher(self):
        from tkinter import filedialog
        pasta=filedialog.askdirectory(title='Escolha o ambiente com XML + DXF')
        if pasta: self.pasta.set(pasta)
    def iniciar(self):
        from tkinter import messagebox
        try: blender,saida,pdf,cfg=preparar_config(self.pasta.get())
        except Exception as exc: messagebox.showerror('Não foi possível iniciar',str(exc)); return
        saida.mkdir(exist_ok=True); self.botao.configure(state='disabled'); self.status.set('Teste em andamento. O Blender trabalha em segundo plano...')
        self.escrever('Blender: '+blender); self.escrever('Saída protegida: '+str(pdf))
        threading.Thread(target=self.executar,args=(cfg,pdf),daemon=True).start()
    def executar(self,cfg,pdf):
        env=dict(os.environ,COMPIERE_RENDER='blender',COMPIERE_BLENDER_AMOSTRAS='16',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
        comando=[sys.executable,'-B',str(RAIZ/'gerar_caderno.py'),json.dumps(cfg,ensure_ascii=False)]
        proc=subprocess.Popen(comando,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        for linha in proc.stdout: self.raiz.after(0,self.escrever,linha)
        codigo=proc.wait(); self.raiz.after(0,self.finalizar,codigo,pdf)
    def finalizar(self,codigo,pdf):
        from tkinter import messagebox
        self.botao.configure(state='normal')
        if codigo==0 and pdf.exists():
            self.status.set('Teste concluído com sucesso.'); self.escrever('CONCLUÍDO: '+str(pdf))
            if messagebox.askyesno('Teste concluído','PDF criado com sucesso. Abrir agora?'): os.startfile(str(pdf))
        else:
            self.status.set('O teste falhou. Veja o diagnóstico acima.'); messagebox.showerror('Teste falhou','O PDF não foi concluído. Consulte o painel de diagnóstico.')

def main():
    import tkinter as tk
    raiz=tk.Tk(); Launcher(raiz); raiz.mainloop(); return 0
if __name__=='__main__': raise SystemExit(main())
