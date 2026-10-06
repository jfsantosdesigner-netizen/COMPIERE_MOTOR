from pathlib import Path
import json, fitz
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent
AUD = sorted(ROOT.glob("AUDITORIA_SEIS_FONTES_*"))[-1]
rows = json.loads((AUD/"resultado.json").read_text(encoding="utf-8"))
for i, r in enumerate(rows,1):
    if not r.get("pdf"): continue
    doc = fitz.open(r["pdf"])
    pages = list(range(4,min(len(doc),8)))
    sheet = Image.new("RGB", (900, 660), "white")
    draw = ImageDraw.Draw(sheet)
    for j,n in enumerate(pages):
        pix = doc[n].get_pixmap(matrix=fitz.Matrix(0.6,0.6))
        im = Image.frombytes("RGB", (pix.width,pix.height), pix.samples)
        im.thumbnail((440,300))
        x,y = (j%2)*450, (j//2)*330
        sheet.paste(im, (x,y+25))
        draw.text((x+8,y+5), f"{r['ambiente']} - pagina {n+1}", fill="black")
    sheet.save(AUD / f"visual_{i}.png")
    quality = Path(r["pdf"]).with_name(Path(r["pdf"]).stem+"_QUALIDADE.md")
    print(r["ambiente"], "PAGINAS",r["paginas"],"INTEGRIDADE",r.get("integridade",{}).get("aprovado"), "FONTES",r["fontes_preservadas"])
    if quality.exists():
        for line in quality.read_text(encoding="utf-8").splitlines():
            if "INCERTO" in line or "FALH" in line: print(line)
