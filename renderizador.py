# -*- coding: utf-8 -*-
"""Etapa 9: fachada única dos backends de render."""
import glob, json, os, subprocess, tempfile
import cena_render

def localizar_blender():
    c=[]
    if os.environ.get('BLENDER_EXE'): c.append(os.environ['BLENDER_EXE'])
    c += sorted(glob.glob(r'C:\Program Files\Blender Foundation\Blender *\blender.exe'))
    return next((p for p in reversed(c) if os.path.isfile(p)), None)

def pacote(projeto, cena):
    cena_render.validar(cena, projeto); P=projeto['pecas']; A=projeto['ambiente']
    def faces(ids): return [fc for i in sorted(set(ids)) for fc in P[i]['faces']]
    amb=cena['ambiente']; paredes=set(amb['paredes']); pedra=set(amb['pedra']); eletros=set(amb['eletros'])
    return {'versao':1,'unidade':'mm','finalidade':cena['finalidade'],'camera':cena['camera'],
            'moveis':faces(cena['pecas_visiveis']-set(A['duplicadas'])),'paredes':faces(paredes),
            'pedra':faces(pedra),'eletros':faces(eletros),'piso':bool(amb['piso'])}

def renderizar_blender(projeto, cena, largura=1600, altura=1000, amostras=64):
    exe=localizar_blender()
    if not exe: raise RuntimeError('Blender não encontrado; configure BLENDER_EXE')
    dados=pacote(projeto,cena); dados['largura']=largura; dados['altura']=altura; dados['amostras']=amostras
    raiz=os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory(prefix='compiere_render_') as d:
        js=os.path.join(d,'cena.json'); png=os.path.join(d,'cena.png'); dados['saida']=png
        with open(js,'w',encoding='utf-8') as f: json.dump(dados,f)
        r=subprocess.run([exe,'-b','--factory-startup','-P',os.path.join(raiz,'blender_cena.py'),'--',js],capture_output=True,encoding='utf-8',errors='replace')
        if r.returncode or not os.path.exists(png): raise RuntimeError('Blender falhou: '+(r.stderr or r.stdout)[-1500:])
        return open(png,'rb').read()
