"""Modelo de dados de um item coletado."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Produto:
    """Um produto em uma loja, em um instante de coleta.

    ``preco_avista`` é o preço pago à vista (PIX, quando a loja informa); se a loja não
    mostra um preço à vista separado, é o próprio preço normal. ``em_estoque`` é ``None``
    quando a página não informa a disponibilidade.
    """

    coletado_em: str
    loja: str
    termo_busca: str
    nome: str
    marca: str
    preco_avista: float | None
    preco_cartao: float | None
    em_estoque: bool | None
    url: str

    @property
    def chave(self) -> tuple[str, str, str]:
        """Identifica o item no dia: o mesmo produto não é gravado duas vezes por dia."""
        return (self.loja, self.url or self.nome, self.coletado_em[:10])


COLUNAS = [campo.name for campo in fields(Produto)]

