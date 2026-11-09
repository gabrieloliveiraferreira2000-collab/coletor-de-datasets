"""Orquestra a coleta: busca as páginas, lê os produtos, aplica os filtros e grava o CSV."""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Protocol

from coletor_hardware.armazenamento import acrescentar, chaves_gravadas
from coletor_hardware.filtros import Filtros, motivo_rejeicao
from coletor_hardware.modelos import Produto

log = logging.getLogger(__name__)

ARQUIVO_DEBUG = "debug_pagina.html"


class Fonte(Protocol):
    """De onde vêm as páginas: o site (``Cliente``) ou um arquivo local (``ClienteLocal``)."""

    def pode_acessar(self, url: str) -> bool: ...

    def baixar(self, url: str) -> str | None: ...

    def esperar(self) -> None: ...


@dataclass
class Resumo:
    gravados: int = 0
    descartes: Counter = field(default_factory=Counter)
    paginas_sem_produtos: int = 0
    falhas_download: int = 0
    bloqueios_robots: int = 0

    @property
    def total_descartados(self) -> int:
        return sum(self.descartes.values())


def coletar(
    filtros: Filtros,
    loja: ModuleType,
    fonte: Fonte,
    saida: Path,
    pasta_debug: Path | None = None,
    agora: str | None = None,
) -> Resumo:
    """Coleta os termos de ``filtros`` na ``loja`` e grava em ``saida`` só o que passar."""
    agora = agora or datetime.now().isoformat(timespec="seconds")
    resumo = Resumo()
    gravadas = chaves_gravadas(saida)
    vistos: set[tuple[str, str, str]] = set()
    novos: list[Produto] = []
    primeira_pagina = True

    for termo in filtros.termos_busca:
        for pagina in range(1, filtros.max_paginas + 1):
            url = loja.url_busca(termo, pagina, filtros.itens_por_pagina)
            if not fonte.pode_acessar(url):
                log.warning("O robots.txt não permite coletar %s", url)
                resumo.bloqueios_robots += 1
                break
            if not primeira_pagina:
                fonte.esperar()
            primeira_pagina = False

            log.info("[%s] página %d", termo, pagina)
            html = fonte.baixar(url)
            if html is None:
                resumo.falhas_download += 1
                break

            brutos = loja.extrair_produtos(html)
            if not brutos:
                resumo.paginas_sem_produtos += 1
                log.warning("Nenhum produto reconhecido nesta página.")
                if pasta_debug is not None:
                    pasta_debug.mkdir(parents=True, exist_ok=True)
                    (pasta_debug / ARQUIVO_DEBUG).write_text(html, encoding="utf-8")
                    log.warning("Salvei %s para ajustar o leitor.", pasta_debug / ARQUIVO_DEBUG)
                break

            ineditos = 0
            for bruto in brutos:
                produto = loja.normalizar(bruto, termo, agora)
                if produto is None or produto.chave in vistos:
                    continue
                vistos.add(produto.chave)
                ineditos += 1
                if produto.chave in gravadas:
                    continue
                motivo = motivo_rejeicao(produto, filtros)
                if motivo is None:
                    novos.append(produto)
                else:
                    resumo.descartes[motivo] += 1

            if ineditos == 0:
                log.info("Página repetida; encerrando a busca deste termo.")
                break

    resumo.gravados = acrescentar(saida, novos)
    return resumo

