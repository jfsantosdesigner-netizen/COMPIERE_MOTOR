# -*- coding: utf-8 -*-
"""
Executa todos os ambientes de PROJETOS TESTES pelo launcher.py.
A entrada permanece limpa. Cada ambiente e copiado para _EXECUCAO_TESTES
e os resultados sao coletados em SAIDAS_TESTES.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRADAS = ROOT / "PROJETOS TESTES"
SAIDAS = ROOT / "SAIDAS_TESTES"
TEMP = ROOT / "_EXECUCAO_TESTES"
LAUNCHER = ROOT / "launcher.py"

ARQUIVOS_GERADOS = {
    "_config.json",
    "_pecas_dxf.json",
    "_pecas_dxf.json.md5",
}


def tem_projeto(pasta: Path) -> bool:
    xmls = [p for p in pasta.glob("*.xml") if "xplod" not in p.name.lower()]
    return bool(xmls and list(pasta.glob("*.dxf")))


def copiar_entrada(origem: Path, destino: Path) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for item in origem.iterdir():
        if not item.is_file():
            continue
        nome = item.name
        if nome in ARQUIVOS_GERADOS:
            continue
        if item.suffix.lower() == ".pdf" and nome.upper().startswith("CADERNO"):
            continue
        if nome.upper().endswith("_QUALIDADE.MD"):
            continue
        shutil.copy2(item, destino / nome)


def coletar_saida(execucao: Path, saida: Path, log_bruto: bytes) -> list[str]:
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "EXECUCAO.log").write_bytes(log_bruto)

    nomes = ["EXECUCAO.log"]
    padroes = [
        "CADERNO*.pdf",
        "*_QUALIDADE.md",
        "_config.json",
        "_pecas_dxf.json",
        "_pecas_dxf.json.md5",
    ]
    vistos = set()
    for padrao in padroes:
        for arquivo in execucao.glob(padrao):
            if not arquivo.is_file() or arquivo.name in vistos:
                continue
            vistos.add(arquivo.name)
            shutil.copy2(arquivo, saida / arquivo.name)
            nomes.append(arquivo.name)
    return nomes


def main() -> int:
    if not ENTRADAS.exists():
        print(f"ERRO: {ENTRADAS} nao existe.")
        return 2

    if SAIDAS.exists():
        shutil.rmtree(SAIDAS)
    if TEMP.exists():
        shutil.rmtree(TEMP)
    SAIDAS.mkdir(parents=True)
    TEMP.mkdir(parents=True)

    ambientes = sorted(
        p for p in ENTRADAS.rglob("*")
        if p.is_dir() and tem_projeto(p)
    )

    print(f"Ambientes encontrados: {len(ambientes)}", flush=True)
    resultados = []

    for i, origem in enumerate(ambientes, 1):
        rel = origem.relative_to(ENTRADAS)
        execucao = TEMP / rel
        saida = SAIDAS / rel
        copiar_entrada(origem, execucao)

        print(f"[{i}/{len(ambientes)}] {rel}", flush=True)

        processo = subprocess.run(
            [sys.executable, str(LAUNCHER), str(execucao)],
            cwd=str(ROOT),
            input=b"\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        log_bruto = processo.stdout or b""
        gerados = coletar_saida(execucao, saida, log_bruto)
        pdfs = [n for n in gerados if n.lower().endswith(".pdf")]
        ok = processo.returncode == 0 and bool(pdfs)
        resultados.append((str(rel), ok, processo.returncode, pdfs))
        print(f"  -> {'OK' if ok else 'FALHA'} codigo={processo.returncode} pdf={len(pdfs)}", flush=True)

    linhas = [
        "# RELATORIO DE EXECUCAO - PROJETOS TESTES",
        "",
        f"Ambientes encontrados: {len(resultados)}",
        f"Sucessos: {sum(1 for _, ok, _, _ in resultados if ok)}",
        f"Falhas: {sum(1 for _, ok, _, _ in resultados if not ok)}",
        "",
        "| Ambiente | Status | Codigo | PDF |",
        "|---|---:|---:|---|",
    ]

    for rel, ok, codigo, pdfs in resultados:
        linhas.append(
            f"| {rel} | {'OK' if ok else 'FALHA'} | {codigo} | {', '.join(pdfs) or '-'} |"
        )

    (SAIDAS / "RELATORIO_EXECUCAO.md").write_text(
        "\n".join(linhas) + "\n", encoding="utf-8"
    )

    shutil.rmtree(TEMP, ignore_errors=True)

    print("", flush=True)
    print(f"Sucessos: {sum(1 for _, ok, _, _ in resultados if ok)}", flush=True)
    print(f"Falhas: {sum(1 for _, ok, _, _ in resultados if not ok)}", flush=True)
    return 1 if any(not ok for _, ok, _, _ in resultados) else 0


if __name__ == "__main__":
    raise SystemExit(main())
