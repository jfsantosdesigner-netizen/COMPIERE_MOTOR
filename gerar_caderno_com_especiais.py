# -*- coding: utf-8 -*-
"""Executa o gerar_caderno.py intacto e acrescenta as pranchas especiais em outro PDF.

Uso:
    python gerar_caderno_com_especiais.py config.json

O arquivo gerar_caderno.py NÃO é importado nem editado: ele é executado em namespace
isolado com uma configuração temporária. O resultado normal vira a base e os especiais
são acrescentados depois, reutilizando as funções de layout, tabela, render e cotas já
carregadas pelo motor atual.
"""
from __future__ import annotations
import copy, json, os, runpy, shutil, sys, tempfile, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "gerar_caderno.py"

def _abs_cfg(cfg, origem):
    """Resolve caminhos relativos em relação à pasta do config original."""
    origem = Path(origem).resolve().parent
    out = copy.deepcopy(cfg)
    for k in ("layout","contrato_fonte","xml","dxf","pecas_json","logo","materiais"):
        v = out.get(k)
        if not v:
            continue
        p = Path(v)
        if not p.is_absolute():
            out[k] = str((origem / p).resolve())
    return out

def _saida_especial(cfg, config_path):
    if cfg.get("saida_especiais"):
        return str(Path(cfg["saida_especiais"]).resolve())
    normal = Path(cfg.get("saida") or (Path(config_path).resolve().parent / "CADERNO.pdf"))
    return str(normal.with_name(normal.stem + "_COM_ESPECIAIS.pdf"))

def executar(config_path):
    config_path = str(Path(config_path).resolve())
    cfg0 = json.load(open(config_path, encoding="utf-8"))
    cfg = _abs_cfg(cfg0, config_path)
    saida_final = _saida_especial(cfg, config_path)
    Path(saida_final).parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="_compiere_especiais_", dir=str(ROOT)))
    try:
        cfg_base = copy.deepcopy(cfg)
        cfg_base["saida"] = str(work / "BASE_NORMAL.pdf")
        cfg_base["pecas_json"] = str(work / "_pecas_dxf.json")
        temp_cfg = work / "_config_base.json"
        json.dump(cfg_base, open(temp_cfg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

        old_argv = sys.argv[:]
        try:
            sys.argv = [str(BASE), str(temp_cfg)]
            ns = runpy.run_path(str(BASE), run_name="__compiere_base_especiais__")
        finally:
            sys.argv = old_argv

        from especiais.detector import detectar
        from especiais.pranchas import gerar

        especiais = detectar(ns)
        ultimo, rel = gerar(ns, especiais)

        # Salva em outro arquivo; o PDF normal produzido pelo motor base permanece intocado.
        doc = ns["doc"]
        doc.save(saida_final, garbage=3, deflate=True)

        rel_path = str(Path(saida_final).with_suffix("")) + "_ESPECIAIS.md"
        linhas = [
            "# COMPIERE — RELATÓRIO DE PRANCHAS ESPECIAIS",
            "",
            f"- Base normal: {cfg.get('saida','')}",
            f"- Saída com especiais: {saida_final}",
            f"- Casos especiais detectados: {len(especiais)}",
            f"- Última prancha: {ultimo}",
            "",
            "## Detecções",
        ]
        if not rel:
            linhas.append("- Nenhuma prancha especial detectada.")
        for fam, ini, fim, qtd, motivo in rel:
            faixa = str(ini) if ini == fim else f"{ini}-{fim}"
            linhas.append(f"- {fam}: prancha(s) {faixa} | {qtd} item(ns) | regra={motivo}")
            esp = next((e for e in especiais if e.familia.value == fam and len(e.itens) == qtd), None)
            if esp:
                for it in esp.itens:
                    linhas.append(f"  - {it.get('desc','ITEM')} {it.get('dim','')}")
        Path(rel_path).write_text("\n".join(linhas), encoding="utf-8")
        print("ESPECIAIS:", len(especiais))
        print("PDF:", saida_final)
        print("RELATORIO:", rel_path)
        return 0
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        try:
            shutil.rmtree(work, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python gerar_caderno_com_especiais.py config.json")
    raise SystemExit(executar(sys.argv[1]))
