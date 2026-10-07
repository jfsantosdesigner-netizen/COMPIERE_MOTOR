# -*- coding: utf-8 -*-
"""
fila.py - gera cadernos em fila, um por vez, na ordem alfabetica das pastas.

Uso:
  python fila.py                       -> todos os ambientes de "PROJETOS TESTES"
  python fila.py "<pasta>" ["<pasta>"] -> as pastas dadas (ambiente ou pasta-mae; pasta-mae expande)
  python fila.py --listar [pastas]     -> so mostra a fila, sem gerar nada

Ambiente = pasta com *.xml (fora xplod) + *.dxf direto nela.
Cada ambiente roda pelo mesmo caminho do launcher: novo_ambiente.py <pasta>.
Modo BLINDADO: cada ambiente e limpo (fica so XML + DXF) e gera so PDF + _QUALIDADE.md.
Saida da fila: um unico FILA_RELATORIO.txt (resumo + alertas). Nao existe mais FILA_LOGS.
"""
import sys, os, re, subprocess, time, glob, shutil

sys.dont_write_bytecode = True

AQUI = os.path.dirname(os.path.abspath(__file__))
PADRAO = os.path.join(AQUI, 'PROJETOS TESTES')
RELATORIO = os.path.join(AQUI, 'FILA_RELATORIO.txt')
ALERTA = re.compile(r'AVISO|ATEN|ERRO|FALTA|FALHOU|Traceback|n[ãa]o bateu|n[ãa]o encontrad|CONFERIR', re.I)


def eh_ambiente(pasta):
    xmls = [f for f in glob.glob(os.path.join(pasta, '*.xml')) if not re.search(r'x?plod', os.path.basename(f), re.I)]
    return bool(xmls and glob.glob(os.path.join(pasta, '*.dxf')))


def expandir(raizes):
    achados = []
    for r in raizes:
        r = os.path.abspath(r.strip('"'))
        if not os.path.isdir(r):
            print(f'IGNORADO (nao e pasta): {r}')
            continue
        for d, subs, _ in os.walk(r):
            subs.sort()
            if eh_ambiente(d):
                achados.append(d)
    vistos, fila = set(), []
    for d in sorted(achados):
        if d not in vistos:
            vistos.add(d); fila.append(d)
    return fila


def paginas(pdf):
    try:
        import pymupdf
        with pymupdf.open(pdf) as doc:
            return doc.page_count
    except Exception:
        return None


def rodar(pasta, n):
    t0 = time.time()
    r = subprocess.run([sys.executable, '-B', os.path.join(AQUI, 'novo_ambiente.py'), pasta],
                       cwd=AQUI, capture_output=True, env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1'))
    dur = time.time() - t0
    saida = (r.stdout + b'\n' + r.stderr).decode('utf-8', 'replace')
    nome = os.path.relpath(pasta, PADRAO) if pasta.startswith(PADRAO) else os.path.basename(pasta)
    pdfs = sorted(glob.glob(os.path.join(pasta, 'CADERNO*.pdf')), key=os.path.getmtime, reverse=True)
    pdfs = [p for p in pdfs if os.path.getmtime(p) >= t0 - 1]
    pdf = pdfs[0] if pdfs else None
    alertas = [l.strip()[:160] for l in saida.splitlines() if ALERTA.search(l)]
    return dict(nome=nome, rc=r.returncode, dur=dur, pdf=pdf, pag=paginas(pdf) if pdf else None,
                kb=(os.path.getsize(pdf) // 1024) if pdf else None, alertas=alertas,
                fim=[l for l in saida.splitlines() if l.strip()][-6:])


def main(argv):
    so_listar = '--listar' in argv
    raizes = [a for a in argv if a != '--listar'] or [PADRAO]
    shutil.rmtree(os.path.join(AQUI, 'FILA_LOGS'), ignore_errors=True)   # legado: nao existe mais log por ambiente
    fila = expandir(raizes)
    print(f'Fila: {len(fila)} ambiente(s)')
    for i, p in enumerate(fila, 1):
        print(f'  {i:02d}  {p}')
    if so_listar or not fila:
        return 0
    res = []
    for i, p in enumerate(fila, 1):
        print(f'\n[{i}/{len(fila)}] gerando: {p}', flush=True)
        x = rodar(p, i)
        res.append(x)
        print(f"    {'OK' if x['rc'] == 0 and x['pdf'] else 'FALHOU'}  rc={x['rc']}  {x['dur']:.0f}s  paginas={x['pag']}", flush=True)
    ok = [x for x in res if x['rc'] == 0 and x['pdf']]
    L = [f'FILA: {len(res)} ambiente(s) | OK: {len(ok)} | FALHA: {len(res) - len(ok)}', '']
    L.append('ambiente | status | rc | seg | paginas | KB | alertas')
    for x in res:
        st = 'OK' if x in ok else 'FALHOU'
        L.append(f"{x['nome']} | {st} | {x['rc']} | {x['dur']:.0f} | {x['pag']} | {x['kb']} | {len(x['alertas'])}")
    L.append('')
    for x in res:
        if x['alertas'] or x not in ok:
            L.append(f"--- {x['nome']}")
            L.extend('  ' + a for a in x['alertas'][:12])
            if x not in ok:
                L.extend('  > ' + l[:160] for l in x['fim'])
    open(RELATORIO, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'\nResumo: OK {len(ok)} / {len(res)}  |  relatorio: {RELATORIO}')
    return 0 if len(ok) == len(res) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
