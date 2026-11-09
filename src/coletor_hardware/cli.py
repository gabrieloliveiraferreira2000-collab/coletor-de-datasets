"""Interface de linha de comando."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from coletor_hardware.coleta import coletar
from coletor_hardware.filtros import Filtros, FiltrosInvalidos
from coletor_hardware.http import Cliente, ClienteLocal
from coletor_hardware.lojas import LOJAS

log = logging.getLogger("coletor_hardware")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coletor-hardware",
        description="Coleta preços à vista de hardware de PC e grava só o que passa nos filtros.",
    )
    parser.add_argument(
        "--filtros", type=Path, default=Path("filtros.json"), help="arquivo de filtros (JSON)"
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("data/dataset_hardware.csv"),
        help="CSV de saída; novas coletas são acrescentadas ao final",
    )
    parser.add_argument("--loja", choices=sorted(LOJAS), default="kabum")
    parser.add_argument(
        "--html",
        type=Path,
        help="usa uma página de busca salva no disco em vez de acessar o site (modo offline)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="mostra mais detalhes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s", force=True
    )

    try:
        filtros = Filtros.de_arquivo(args.filtros)
    except FiltrosInvalidos as erro:
        log.error("%s", erro)
        if not args.filtros.exists():
            log.error("Dica: copie filtros.example.json para filtros.json e edite.")
        return 2

    loja = LOJAS[args.loja]
    if args.html is not None:
        if not args.html.is_file():
            log.error("Arquivo HTML não encontrado: %s", args.html)
            return 2
        fonte = ClienteLocal(args.html)
    else:
        fonte = Cliente(loja.SITE)

    resumo = coletar(filtros, loja, fonte, args.saida, pasta_debug=args.saida.parent)

    log.info("")
    log.info("Gravados em %s: %d", args.saida, resumo.gravados)
    log.info("Descartados pelos filtros: %d", resumo.total_descartados)
    for motivo, quantidade in resumo.descartes.most_common():
        log.info("  - %s: %d", motivo, quantidade)

    leitor_falhou = resumo.paginas_sem_produtos > 0 and resumo.gravados == 0
    return 1 if leitor_falhou else 0

