from pathlib import Path
p=Path(__file__).resolve().parent/'normal'/'test_cameras.py'
s=p.read_text(encoding='utf-8')
s=s.replace('from .cameras import orientar, portas_do_canto','from .cameras import orientar, portas_do_canto, tampas_modulos_deitados')
marker="    def test_portas_internas_do_canto_exigem_medidas_xml(self):"
block="""    def test_tampa_de_caixa_deitada_somente_no_detalhe(self):
        b=[172, -4155, 0, 585, -3548, 432]
        pecas=[dict(i=1,bb=[187,-4141,18,570,-3562,24]),
               dict(i=2,bb=[175,-4153,432,582,-3550,450]),
               dict(i=3,bb=[173,-4137,0,191,-3566,432])]
        modulo=dict(tipo='mod',desc='Armário Superior',bb=b,pecas=[1,2,3])
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),{2})
        pecas[1]['bb'][2]=380
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),set())
        pecas[1]['bb'][2]=432
        modulo['desc']='Armário Canto L Direito'
        self.assertEqual(tampas_modulos_deitados([modulo],pecas),set())

"""
assert marker in s and 'test_tampa_de_caixa_deitada' not in s
p.write_text(s.replace(marker,block+marker),encoding='utf-8')
