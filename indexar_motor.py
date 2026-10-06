import ast
import hashlib
import os
from pathlib import Path
from datetime import datetime

PASTA_RAIZ = Path(__file__).parent

ALVOS = [
    "gerar_caderno.py",
    "geo.py",
    "dxf_pecas(motor core).py",
    "novo_ambiente.py",
    "testar_lote.py",
    "testar_motor.py",
    "launcher.py",
    "server.py",
    "_diagnostico.py",
    "criar_indice_core_motor.py",
]


def sha16(caminho):
    try:
        return hashlib.sha256(open(caminho, "rb").read()).hexdigest()[:16]
    except Exception:
        return "erro"


def extrair(caminho):
    r = {
        "funcoes": [],
        "classes": [],
        "constantes": [],
        "imports": [],
        "doc": "",
        "linhas": 0,
        "erro": None,
    }
    try:
        cod = open(caminho, "r", encoding="utf-8", errors="replace").read()
        r["linhas"] = cod.count("\n") + 1
        tree = ast.parse(cod)
    except SyntaxError as e:
        r["erro"] = str(e)
        return r
    except Exception as e:
        r["erro"] = str(e)
        return r

    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        r["doc"] = tree.body[0].value.value.strip()[:200]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                r["imports"].append(a.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            r["imports"].append(mod + "." + ",".join(a.name for a in node.names))

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    v = ""
                    if isinstance(node.value, ast.Constant):
                        v = repr(node.value.value)[:60]
                    elif isinstance(node.value, ast.List):
                        v = "[lista " + str(len(node.value.elts)) + "]"
                    elif isinstance(node.value, ast.Dict):
                        v = "{dict " + str(len(node.value.keys)) + "}"
                    elif isinstance(node.value, ast.Call):
                        fn = node.value.func
                        nm = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                        v = nm + "(...)"
                    r["constantes"].append({"nome": t.id, "linha": node.lineno, "valor": v})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = (ast.get_docstring(node) or "").strip()[:150].replace("\n", " ")
            args = [a.arg for a in node.args.args]
            end = getattr(node, "end_lineno", node.lineno)
            r["funcoes"].append({"nome": node.name, "linha": node.lineno,
                                  "args": args, "doc": doc, "linhas": end - node.lineno + 1})
        elif isinstance(node, ast.ClassDef):
            mets = [i.name for i in node.body if isinstance(i, (ast.FunctionDef, ast.AsyncFunctionDef))]
            doc = (ast.get_docstring(node) or "").strip()[:150]
            r["classes"].append({"nome": node.name, "linha": node.lineno, "metodos": mets, "doc": doc})
    return r


def gerar_md():
    alvos_set = set()
    todos = []
    for a in ALVOS:
        p = PASTA_RAIZ / a
        if p.exists():
            todos.append(p)
            alvos_set.add(p.resolve())
    for p in sorted(PASTA_RAIZ.glob("*.py")):
        if p.resolve() not in alvos_set and p.name != "indexar_motor.py":
            todos.append(p)

    infos = [extrair(p) for p in todos]
    tf = sum(len(i["funcoes"]) for i in infos)
    tc = sum(len(i["classes"]) for i in infos)
    tco = sum(len(i["constantes"]) for i in infos)

    out = []
    out.append("# INDICE DO MOTOR COMPIERE -- core_motor")
    out.append("")
    out.append("Gerado: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Sumario")
    out.append("")
    out.append("| Arquivos | Funcoes | Classes | Constantes |")
    out.append("|---|---|---|---|")
    out.append("| " + str(len(todos)) + " | " + str(tf) + " | " + str(tc) + " | " + str(tco) + " |")
    out.append("")
    out.append("---")
    out.append("")

    for idx, caminho in enumerate(todos):
        info = infos[idx]
        rel = caminho.name
        sha = sha16(caminho)
        tam = caminho.stat().st_size if caminho.exists() else 0

        out.append("## `" + rel + "`")
        out.append("")
        out.append("- **Bytes:** " + str(tam) + " | **SHA-256(16):** `" + sha + "`")
        out.append("- **Linhas:** " + str(info["linhas"]))
        if info["erro"]:
            out.append("- **ERRO DE PARSE:** " + info["erro"])
        if info["doc"]:
            out.append("- **Modulo:** " + info["doc"])
        out.append("")

        if info["imports"]:
            importados = sorted(set(info["imports"]))[:20]
            out.append("**Imports principais:** `" + "`, `".join(importados) + "`")
            out.append("")

        if info["constantes"]:
            out.append("**Constantes/globais:**")
            out.append("")
            out.append("| Nome | Linha | Valor |")
            out.append("|---|---|---|")
            for c in info["constantes"][:40]:
                out.append("| `" + c["nome"] + "` | " + str(c["linha"]) + " | `" + c["valor"] + "` |")
            if len(info["constantes"]) > 40:
                out.append("| ... | ... | (" + str(len(info["constantes"]) - 40) + " mais) |")
            out.append("")

        if info["classes"]:
            out.append("**Classes:**")
            out.append("")
            for cl in info["classes"]:
                mets = ", ".join("`" + m + "`" for m in cl["metodos"])
                out.append("- `" + cl["nome"] + "` (linha " + str(cl["linha"]) + ") -- metodos: " + (mets or "--"))
                if cl["doc"]:
                    out.append("  > " + cl["doc"])
            out.append("")

        if info["funcoes"]:
            out.append("**Funcoes:**")
            out.append("")
            out.append("| Funcao | Linha | Linhas | Args | Descricao |")
            out.append("|---|---|---|---|---|")
            for f in info["funcoes"]:
                args_str = ", ".join(f["args"])[:40]
                doc_str = f["doc"][:80] if f["doc"] else "--"
                out.append("| `" + f["nome"] + "` | " + str(f["linha"]) + " | " + str(f["linhas"]) + " | `" + args_str + "` | " + doc_str + " |")
            out.append("")

        out.append("---")
        out.append("")

    saida = PASTA_RAIZ / "INDICE_MOTOR.md"
    with open(saida, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(out))
    print("Indice gerado: " + str(saida))
    print("Arquivos indexados: " + str(len(todos)))
    print("Funcoes: " + str(tf) + " | Classes: " + str(tc) + " | Constantes: " + str(tco))


if __name__ == "__main__":
    gerar_md()
