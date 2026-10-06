# -*- coding: utf-8 -*-
"""Detector de especiais sobre o contexto já calculado pelo motor atual."""
from __future__ import annotations
from dataclasses import dataclass, field
import math, os, re, unicodedata
from collections import defaultdict
from .regras import Familia, Destino, FAMILIAS_POR_NOME, NORMAL_POR_NOME, EXCECOES_NORMAL

@dataclass
class Sinais:
    curva: bool = False
    angulo: bool = False
    usinagem: bool = False
    circulo: bool = False
    contornos_fechados: int = 0
    layers: tuple[str, ...] = ()

@dataclass
class Especial:
    familia: Familia
    chave: str
    itens: list[dict] = field(default_factory=list)
    sinais: Sinais = field(default_factory=Sinais)
    motivo: str = ""
    folhas: int = 1

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def _dim(it):
    return tuple(round(float(x.replace(",", ".")), 1) for x in str(it.get("dim", "0x0x0")).lower().split("x")[:3])

def _bbox_dist(a, b):
    d = [max(0.0, max(a[k], b[k]) - min(a[k+3], b[k+3])) for k in range(3)]
    return math.sqrt(sum(x*x for x in d))

def _shape_name(text):
    t = norm(text)
    t = re.sub(r"\b\d+(?:[.,]\d+)?\b", "#", t)
    t = re.sub(r"\br\s*#", "r#", t)
    return t

def _edges_have_angle(raw_piece, tol=1.0):
    """Detecta aresta estrutural não ortogonal sem confundir diagonal de triangulação."""
    faces = raw_piece.get("faces", []) or []
    if not faces:
        return False

    def keypt(p):
        return tuple(round(float(x), 1) for x in p)

    def normal(pts):
        q=[]
        for p in pts:
            p=keypt(p)
            if not q or p != q[-1]:
                q.append(p)
        if len(q)>1 and q[0]==q[-1]:
            q.pop()
        if len(q)<3:
            return None
        a=q[0]
        for j in range(1,len(q)-1):
            b,c=q[j],q[j+1]
            u=[b[k]-a[k] for k in range(3)]; v=[c[k]-a[k] for k in range(3)]
            n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            m=math.sqrt(sum(x*x for x in n))
            if m>1e-6:
                return tuple(x/m for x in n)
        return None

    edges=defaultdict(list)
    for fc in faces:
        pts=[]
        for p in fc:
            kp=keypt(p)
            if not pts or kp!=pts[-1]:
                pts.append(kp)
        if len(pts)>1 and pts[0]==pts[-1]:
            pts.pop()
        n=normal(pts)
        if len(pts)<2:
            continue
        for a,b in zip(pts,pts[1:]+pts[:1]):
            if a==b:
                continue
            k=tuple(sorted((a,b)))
            edges[k].append(n)

    for (a,b), normals in edges.items():
        delta=[abs(b[k]-a[k]) for k in range(3)]
        if sum(v>tol for v in delta)<2:
            continue
        valid=[n for n in normals if n is not None]
        if len(valid)<=1:
            return True
        # Diagonal de triangulação: faces dos dois lados são coplanares.
        n0=valid[0]
        if any(abs(sum(n0[k]*n[k] for k in range(3))) < 0.995 for n in valid[1:]):
            return True
    return False

def scan_dxf(path):
    """Lê apenas sinais geométricos por layer; não altera o leitor DXF do motor."""
    out = defaultdict(lambda: {"curve": False, "circle": False, "closed": 0, "angle": False})
    try:
        import ezdxf
        doc = ezdxf.readfile(path)
    except Exception:
        return out

    def walk(e, inherited=None):
        layer = getattr(getattr(e, "dxf", None), "layer", None) or inherited or "0"
        if inherited and layer == "0":
            layer = inherited
        typ = e.dxftype()
        if typ == "INSERT":
            try:
                for sub in e.virtual_entities():
                    walk(sub, layer)
            except Exception:
                pass
            return
        rec = out[layer]
        if typ in ("ARC", "CIRCLE", "ELLIPSE", "SPLINE"):
            rec["curve"] = True
        if typ == "CIRCLE":
            rec["circle"] = True
            rec["closed"] += 1
        elif typ == "LINE":
            # Linha avulsa pode ser marca/gravação; não define ângulo construtivo sozinha.
            pass
        elif typ == "LWPOLYLINE":
            try:
                pts=[(float(x),float(y)) for x,y,*_ in e.get_points("xy")]
                if e.closed:
                    rec["closed"] += 1
                    pts.append(pts[0])
                for a,b in zip(pts,pts[1:]):
                    if abs(b[0]-a[0])>1.0 and abs(b[1]-a[1])>1.0:
                        rec["angle"]=True; break
            except Exception:
                pass
        elif typ == "POLYLINE":
            try:
                pts=[tuple(v.dxf.location) for v in e.vertices]
                if e.is_closed:
                    rec["closed"] += 1
                    pts.append(pts[0])
                for a,b in zip(pts,pts[1:]):
                    if sum(abs(b[k]-a[k])>1.0 for k in range(3)) >= 2:
                        rec["angle"]=True; break
            except Exception:
                pass

    for ent in doc.modelspace():
        walk(ent)
    return out

def _sinais_item(it, raw, dxf_layers):
    ls = []
    curva = angulo = circulo = False
    fechados = 0
    for pi in it.get("pecas", []):
        if pi < 0 or pi >= len(raw):
            continue
        rp = raw[pi]
        layer = rp.get("layer", "")
        ls.append(layer)
        rec = dxf_layers.get(layer, {})
        curva |= bool(rec.get("curve"))
        circulo |= bool(rec.get("circle"))
        fechados += int(rec.get("closed", 0) or 0)
        angulo |= bool(rec.get("angle")) or _edges_have_angle(rp)
        if re.search(r"\bR\s*\d", f"{it.get('desc','')} {layer}", re.I):
            curva = True
    # Mais de um contorno fechado na mesma layer é forte sinal de abertura/rasgo/furo.
    usinagem = circulo or fechados > 1
    return Sinais(curva=curva, angulo=angulo, usinagem=usinagem,
                  circulo=circulo, contornos_fechados=fechados, layers=tuple(sorted(set(ls))))

def _familia_nome(txt):
    n = norm(txt)
    for fam, termos in FAMILIAS_POR_NOME.items():
        if any(norm(t) in n for t in termos):
            return fam
    return None

def _porta_perfil(it):
    n = norm(it.get("desc"))
    mat = norm(it.get("xml_mat_porta"))
    return ("porta" in n and any(x in n for x in ("perfil", "alumin", "vidro", "espelho"))) or mat in ("vidro", "espelho", "aluminio")

def _excecao_normal(it):
    n = norm(it.get("desc"))
    if "prateleira" in n and "vidro" in n:
        return True
    if any(norm(x) in n for x in EXCECOES_NORMAL + NORMAL_POR_NOME):
        return True
    if it.get("tipo") == "mod" and "curv" in n:
        # Módulo curvo descrito como um módulo do XML = produto pronto de fábrica.
        return True
    return False

def _classificar(it, sinais):
    n = norm(it.get("desc"))
    if _excecao_normal(it):
        return Destino.NORMAL, None, "excecao_explicita"
    fam = _familia_nome(n)
    if fam:
        return Destino.ESPECIAL, fam, "familia"
    if _porta_perfil(it):
        return Destino.ESPECIAL, Familia.PORTA_PERFIL, "porta_com_perfil"
    # Painel NÃO vira especial só pelo nome. O conjunto de painéis é reconhecido
    # pelas relações geométricas já calculadas pelo motor (BLOCOS). Exceção:
    # cabeceira explicitamente nomeada é família de painel por regra do caderno.
    if "cabeceira" in n:
        return Destino.ESPECIAL, Familia.PAINEL, "cabeceira"
    if "nicho" in n and (sinais.curva or sinais.angulo):
        return Destino.ESPECIAL, Familia.NICHO_ESPECIAL, "nicho_geometria"
    if "tampon" in n and (sinais.curva or sinais.angulo or sinais.usinagem):
        return Destino.ESPECIAL, Familia.TAMPONAMENTO_ESPECIAL, "tamponamento_geometria"
    if "fecham" in n and (sinais.curva or sinais.angulo or sinais.usinagem):
        return Destino.ESPECIAL, Familia.USINAGEM if sinais.usinagem else (Familia.CURVO if sinais.curva else Familia.ANGULO), "fechamento_geometria"
    # Módulo XML pronto é tratado como corpo de fábrica. Geometria interna não promove o
    # módulo inteiro a especial; conjuntos especiais fabricados por peças soltas chegam como componentes/grupos.
    if it.get("tipo") == "mod":
        return Destino.NORMAL, None, "modulo_pronto"
    if sinais.usinagem:
        return Destino.ESPECIAL, Familia.USINAGEM, "usinagem_geometrica"
    if sinais.curva:
        return Destino.ESPECIAL, Familia.CURVO, "curva_raio"
    if sinais.angulo:
        return Destino.ESPECIAL, Familia.ANGULO, "angulo_nao_90"
    if any(norm(x) in n for x in NORMAL_POR_NOME):
        return Destino.NORMAL, None, "familia_normal"
    return Destino.NORMAL, None, "normal"

def _folhas(fam):
    if fam == Familia.DIVISORIA:
        return 5
    if fam == Familia.CAMA:
        return 5
    if fam in (Familia.PAINEL, Familia.PAINEL_RIPADO):
        return 2
    return 1

def _pseudo_extras(ns, raw):
    """Cria itens mínimos para LED/metalon presentes no DXF mas fora da lista XML."""
    usados = {pi for it in ns["inst"] for pi in it.get("pecas", [])}
    inst = ns["inst"]
    out = []
    for i, rp in enumerate(raw):
        if i in usados:
            continue
        n = norm(rp.get("layer"))
        fam = Familia.METALON if "metalon" in n else Familia.LED if re.search(r"(^| )led( |$)", n) else None
        if fam is None:
            continue
        b = rp["bb"]
        viz = min(inst, key=lambda o: _bbox_dist(b, o["bb"])) if inst else None
        dm = "x".join(str(int(round(x))) for x in rp.get("dim", [0,0,0]))
        out.append({
            "n": 100000 + i, "desc": rp.get("layer") or fam.value.upper(), "dim": dm,
            "bb": b, "tipo": "comp", "pecas": [i],
            "parede": viz.get("parede") if viz else None, "_familia_forcada": fam,
        })
    return out

def detectar(ns):
    """Retorna lista de Especial sem tocar no documento/PDF do motor base.

    Calibração universal:
    - primeiro reutiliza relações construtivas já descobertas pelo motor (divisórias,
      blocos de painéis, painel usinado);
    - depois aplica famílias explícitas;
    - por último usa geometria pura somente em peças soltas/componentes.
    """
    if "_especiais_detectados" in ns:
        return ns["_especiais_detectados"]
    import json
    raw = json.load(open(ns["cfg"]["pecas_json"], encoding="utf-8"))
    dxf_layers = scan_dxf(ns["cfg"]["dxf"])
    grupos = {}
    consumidos = set()

    def add_group(fam, itens, chave, motivo):
        itens=[i for i in itens if i]
        if not itens:
            return
        sig=Sinais()
        for it in itens:
            s=_sinais_item(it,raw,dxf_layers)
            sig.curva |= s.curva; sig.angulo |= s.angulo; sig.usinagem |= s.usinagem; sig.circulo |= s.circulo
            sig.contornos_fechados=max(sig.contornos_fechados,s.contornos_fechados)
            sig.layers=tuple(sorted(set(sig.layers)|set(s.layers)))
            consumidos.add(id(it))
        key=(fam.value,chave)
        grupos[key]=Especial(familia=fam,chave=chave,itens=list(itens),sinais=sig,motivo=motivo,folhas=_folhas(fam))

    # 1) Relações construtivas fortes vindas do próprio motor atual.
    for k,d in enumerate(ns.get("DIVISORIAS",[]) or [],1):
        add_group(Familia.DIVISORIA,d.get("itens",[]),f"divisoria_{k}","relacao_divisoria")

    for k,g in enumerate(ns.get("DIVISORES",[]) or [],1):
        add_group(Familia.DIVISOR_TALHER,g,f"divisor_{k}","relacao_divisor_mdf")

    for k,b in enumerate(ns.get("BLOCOS",[]) or [],1):
        its=b.get("itens",[]) if isinstance(b,dict) else []
        nome=norm((b.get("bloco","") if isinstance(b,dict) else "") or "painel")
        fam=Familia.PAINEL_RIPADO if "rip" in nome else Familia.PAINEL
        add_group(fam,its,f"bloco_painel_{k}","relacao_conjunto_paineis")

    # Painel com vãos/usinação já reconhecido pelo motor base.
    usin=ns.get("USINADOS",{}) or {}
    if usin:
        for it in ns.get("inst",[]):
            if any(pi in usin for pi in it.get("pecas",[])):
                add_group(Familia.USINAGEM,[it],f"usinagem_{it.get('n',id(it))}","painel_usinado_motor")

    # 2) Famílias explícitas e geometria em peças não consumidas.
    candidatos=list(ns["inst"])+_pseudo_extras(ns,raw)
    for it in candidatos:
        if id(it) in consumidos:
            continue
        sinais=_sinais_item(it,raw,dxf_layers)
        fam_forcada=it.get("_familia_forcada")
        if fam_forcada:
            destino,fam,motivo=Destino.ESPECIAL,fam_forcada,"layer_dxf"
        else:
            destino,fam,motivo=_classificar(it,sinais)
        if destino != Destino.ESPECIAL or fam is None:
            continue
        # Mesma geometria pode agrupar dimensões diferentes.
        base=_shape_name(it.get("desc") or fam.value)
        if fam == Familia.METALON:
            base="ambiente"
        key=(fam.value,base)
        if key not in grupos:
            grupos[key]=Especial(familia=fam,chave=base,sinais=sinais,motivo=motivo,folhas=_folhas(fam))
        grupos[key].itens.append(it)
        g=grupos[key].sinais
        g.curva |= sinais.curva; g.angulo |= sinais.angulo; g.usinagem |= sinais.usinagem; g.circulo |= sinais.circulo
        g.contornos_fechados=max(g.contornos_fechados,sinais.contornos_fechados)
        g.layers=tuple(sorted(set(g.layers)|set(sinais.layers)))

    # 3) Conjunto de peças soltas: só promove o conjunto inteiro quando alguma peça
    # realmente apresenta condição especial. Isso evita transformar móvel normal em especial.
    for k,md in enumerate(ns.get("MOVEIS_DIVERSOS",[]) or [],1):
        its=md.get("itens",[])
        if not its or any(id(i) in consumidos for i in its):
            continue
        ss=[_sinais_item(i,raw,dxf_layers) for i in its]
        if any(s.curva or s.angulo or s.usinagem for s in ss):
            add_group(Familia.CONJUNTO_ESPECIAL,its,f"conjunto_{k}","conjunto_com_geometria_especial")

    return list(grupos.values())
