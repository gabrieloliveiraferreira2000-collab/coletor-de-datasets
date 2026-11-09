"""Leitura e gravação do CSV do dataset (sempre acrescentando, nunca sobrescrevendo)."""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from coletor_hardware.modelos import COLUNAS, Produto


def _tem_conteudo(caminho: Path) -> bool:
    return caminho.exists() and caminho.stat().st_size > 0


def _checar_cabecalho(caminho: Path) -> None:
    with caminho.open(encoding="utf-8-sig", newline="") as arq:
        cabecalho = next(csv.reader(arq), [])
    if cabecalho != COLUNAS:
        raise ValueError(f"{caminho} tem colunas diferentes das esperadas: {cabecalho}")


def chaves_gravadas(caminho: Path) -> set[tuple[str, str, str]]:
    """Chaves (loja, url, dia) dos itens que já estão no CSV."""
    if not _tem_conteudo(caminho):
        return set()
    _checar_cabecalho(caminho)
    with caminho.open(encoding="utf-8-sig", newline="") as arq:
        return {
            (linha["loja"], linha["url"] or linha["nome"], linha["coletado_em"][:10])
            for linha in csv.DictReader(arq)
        }


def acrescentar(caminho: Path, produtos: list[Produto]) -> int:
    """Acrescenta os produtos ao CSV (cria o arquivo e o cabeçalho se preciso)."""
    if not produtos:
        return 0
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not _tem_conteudo(caminho)
    if not novo:
        _checar_cabecalho(caminho)
    with caminho.open("a", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.DictWriter(arq, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerows(asdict(produto) for produto in produtos)
    return len(produtos)

