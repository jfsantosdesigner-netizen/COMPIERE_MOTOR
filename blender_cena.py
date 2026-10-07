import bpy,json,sys,math
from mathutils import Vector
d=json.load(open(sys.argv[sys.argv.index('--')+1],encoding='utf-8')); M=.001
cores={'moveis':(.97,.97,.97),'paredes':(.95,.94,.91),'pedra':(.16,.16,.17),'eletros':(.72,.73,.76)}
def malha(nome,faces,cor):
 v=[]; fs=[]
 for f in faces:
  fs.append(list(range(len(v),len(v)+len(f))));v += [tuple(x*M for x in p) for p in f]
 if not fs:return
 me=bpy.data.meshes.new(nome);me.from_pydata(v,[],fs);ob=bpy.data.objects.new(nome,me);bpy.context.collection.objects.link(ob)
 mt=bpy.data.materials.new(nome);mt.diffuse_color=(*cor,1);me.materials.append(mt)
for k,c in cores.items():malha(k,d.get(k,[]),c)
camd=d['camera']; alvo=Vector(camd.get('alvo',(0,0,1500)))*M; pos=Vector(camd.get('posicao',(5000,-5000,1500)))*M
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));bpy.context.collection.objects.link(cam);bpy.context.scene.camera=cam;cam.location=pos;cam.rotation_euler=(alvo-pos).to_track_quat('-Z','Y').to_euler();cam.data.lens=50
sol=bpy.data.objects.new('Sol',bpy.data.lights.new('Sol','SUN'));bpy.context.collection.objects.link(sol);sol.data.energy=3;sol.rotation_euler=(math.radians(35),0,math.radians(35))
sc=bpy.context.scene
try:sc.render.engine='BLENDER_EEVEE_NEXT'
except:sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=d['largura'];sc.render.resolution_y=d['altura'];sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=d['saida'];sc.render.film_transparent=False
if hasattr(sc,'eevee'):sc.eevee.taa_render_samples=d.get('amostras',64)
sc.world.color=(.85,.88,.95);bpy.ops.render.render(write_still=True);print('RENDER OK')
