# -*- coding: utf-8 -*-
"""Roda DENTRO do Blender (blender -b -P blender_ambiente.py -- geo.json pasta_saida). Monta piso+parede, luz e camera.
Deterministico: Cycles em CPU, semente fixa, sem denoise, sem horario/aleatorio."""
import sys, json, math, os
import bpy
from mathutils import Vector

# ======================= AJUSTES (mexa so aqui) =======================
PAREDE_COR = (0.95, 0.94, 0.91)      # sRGB (mesmo do ambiente.py)
PISO_COR = (0.78, 0.78, 0.80)
MOVEL_COR = (0.97, 0.97, 0.97)       # MDF branco (cores reais entram na etapa cores.py)
PEDRA_COR = (0.16, 0.16, 0.17)
ELETRO_COR = (0.72, 0.73, 0.76)
MUNDO_COR, MUNDO_FORCA = (0.85, 0.88, 0.95), 0.35     # luz ambiente (ceu)
SOL_FORCA, SOL_ANGULO_DEG = 3.0, 4.0                  # luz principal e maciez da sombra
SOL_AZIMUTE_DEG, SOL_ELEVACAO_DEG = 35.0, 55.0
REBAIXO_PISO_MM = 0.0                # >0 afunda o piso (separa visualmente piso e parede)
FINAL = len(sys.argv) > sys.argv.index('--') + 3 and sys.argv[-1] == 'final'
AMOSTRAS, SEMENTE = (64, 0) if FINAL else (8, 0)      # previa: 8 amostras (segundos); final: 64
LARGURA, ALTURA = (1600, 1000) if FINAL else (960, 600)
CORTE_PAREDE_PROXIMA_MM = 450        # corta a parede mais perto da camera (vista "casa de boneca")
# ======================================================================
a = sys.argv[sys.argv.index('--') + 1:]
geo = json.load(open(a[0], encoding='utf-8')); saida = a[1]
M = 0.001
lin = lambda c: tuple(x ** 2.2 for x in c)


def malha(nome, faces, cor, dz=0.0, cortar=None):
    vs, fs = [], []
    for f in faces:
        if cortar and cortar(f): continue
        idx = []
        for v in f: vs.append((v[0] * M, v[1] * M, v[2] * M + dz)); idx.append(len(vs) - 1)
        fs.append(idx)
    if not fs: return None
    me = bpy.data.meshes.new(nome); me.from_pydata(vs, [], fs); me.update()
    ob = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(ob)
    mt = bpy.data.materials.new(nome); mt.use_nodes = True
    bsdf = mt.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value = (*lin(cor), 1)
    bsdf.inputs['Roughness'].default_value = 0.9
    me.materials.append(mt)
    for p in me.polygons: p.use_smooth = False
    return ob


todos = [v for f in geo['parede'] + geo['piso'] for v in f]
mn = Vector((min(v[0] for v in todos), min(v[1] for v in todos), min(v[2] for v in todos))) * M
mx = Vector((max(v[0] for v in todos), max(v[1] for v in todos), max(v[2] for v in todos))) * M
c = (mn + mx) / 2; tam = (mx - mn)


def cena(az_cam_deg, elev_deg, nome, corte, dist_k=1.25, alvo_z=None):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    az = math.radians(az_cam_deg); el = math.radians(elev_deg)
    d_h = Vector((math.sin(az), -math.cos(az), 0))          # direcao horizontal do centro para a camera
    dmax = max((Vector((v[0], v[1], 0)) * M - Vector((c.x, c.y, 0))).dot(d_h) for v in todos)
    def cortar(f):
        if not corte: return False
        cen = sum((Vector((v[0], v[1], 0)) * M for v in f), Vector()) / len(f)
        return (cen - Vector((c.x, c.y, 0))).dot(d_h) > dmax - CORTE_PAREDE_PROXIMA_MM * M
    malha('piso', geo['piso'], PISO_COR, dz=-REBAIXO_PISO_MM * M)
    malha('parede', geo['parede'], PAREDE_COR, cortar=cortar)
    for nome_, cor_ in (('moveis', MOVEL_COR), ('pedra', PEDRA_COR), ('eletros', ELETRO_COR)):
        if geo.get(nome_): malha(nome_, geo[nome_], cor_)
    sc = bpy.context.scene
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); bpy.context.collection.objects.link(cam); sc.camera = cam
    R = max(tam.x, tam.y) * dist_k + 1.0
    alvo = Vector((c.x, c.y, alvo_z if alvo_z is not None else c.z))
    cam.location = alvo + Vector((d_h.x * math.cos(el), d_h.y * math.cos(el), math.sin(el))) * R
    cam.data.lens = 28
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sol = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN')); bpy.context.collection.objects.link(sol)
    sol.data.energy = SOL_FORCA; sol.data.angle = math.radians(SOL_ANGULO_DEG)
    sol.rotation_euler = (math.radians(90 - SOL_ELEVACAO_DEG), 0, math.radians(SOL_AZIMUTE_DEG))
    w = bpy.data.worlds.new('w'); w.use_nodes = True; sc.world = w
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*lin(MUNDO_COR), 1); bg.inputs['Strength'].default_value = MUNDO_FORCA
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = AMOSTRAS; sc.cycles.seed = SEMENTE
    sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False; sc.cycles.max_bounces = 3
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.render.resolution_x, sc.render.resolution_y = LARGURA, ALTURA; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(saida, nome)
    bpy.ops.render.render(write_still=True)


cena(215, 48, 'AMBIENTE_diagonal.png', True)
cena(215, 14, 'AMBIENTE_interior.png', True, dist_k=1.0, alvo_z=1.2)
print('RENDER OK')
