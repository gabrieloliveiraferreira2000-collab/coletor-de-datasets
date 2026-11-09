"""Filtros definidos pelo usuário: só entra no dataset o que passar por eles."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, field, fields
from pathlib import Path

from coletor_hardware.modelos import Produto


class FiltrosInvalidos(ValueError):
    """O arquivo de filtros tem erro de formato ou valores incoerentes."""


def _norm(texto: object) -> str:
    """Minúsculas, sem acento e sem espaços repetidos (para comparar textos)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _lista_de_textos(nome: str, valor: object) -> list[str]:
    if not isinstance(valor, list) or not all(isinstance(v, str) for v in valor):
        raise FiltrosInvalidos(f"'{nome}' precisa ser uma lista de textos.")
    return [v.strip() for v in valor if v.strip()]


def _checar_numero(nome: str, valor: object) -> None:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        or valor < 0
    ):
        raise FiltrosInvalidos(f"'{nome}' precisa ser um número maior ou igual a zero.")


@dataclass
class Filtros:
    """Critérios que um produto precisa atender para ser gravado.

    A comparação de textos ignora maiúsculas e acentos e funciona por trecho
    (``"4060"`` casa com ``"RTX 4060 Ti"``).
    """

    termos_busca: list[str]
    preco_min: float = 0.0
    preco_max: float | None = None
    marcas: list[str] = field(default_factory=list)
    palavras_obrigatorias: list[str] = field(default_factory=list)
    palavras_proibidas: list[str] = field(default_factory=list)
    somente_em_estoque: bool = True
    max_paginas: int = 2
    itens_por_pagina: int = 20

    def __post_init__(self) -> None:
        self.termos_busca = _lista_de_textos("termos_busca", self.termos_busca)
        if not self.termos_busca:
            raise FiltrosInvalidos("'termos_busca' precisa ter ao menos um termo.")
        self.marcas = _lista_de_textos("marcas", self.marcas)
        self.palavras_obrigatorias = _lista_de_textos(
            "palavras_obrigatorias", self.palavras_obrigatorias
        )
        self.palavras_proibidas = _lista_de_textos("palavras_proibidas", self.palavras_proibidas)

        _checar_numero("preco_min", self.preco_min)
        if self.preco_max is not None:
            _checar_numero("preco_max", self.preco_max)
            if self.preco_max < self.preco_min:
                raise FiltrosInvalidos("'preco_max' não pode ser menor que 'preco_min'.")

        if not isinstance(self.somente_em_estoque, bool):
            raise FiltrosInvalidos("'somente_em_estoque' precisa ser true ou false.")
        for nome in ("max_paginas", "itens_por_pagina"):
            valor = getattr(self, nome)
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
                raise FiltrosInvalidos(f"'{nome}' precisa ser um número inteiro maior que zero.")

    @classmethod
    def de_dict(cls, bruto: object) -> Filtros:
        if not isinstance(bruto, dict):
            raise FiltrosInvalidos("O arquivo de filtros precisa conter um objeto JSON.")
        validos = {campo.name for campo in fields(cls)}
        desconhecidos = sorted(set(bruto) - validos)
        if desconhecidos:
            raise FiltrosInvalidos(f"Chaves desconhecidas nos filtros: {', '.join(desconhecidos)}")
        if "termos_busca" not in bruto:
            raise FiltrosInvalidos("Falta a chave obrigatória 'termos_busca'.")
        return cls(**bruto)

    @classmethod
    def de_arquivo(cls, caminho: str | Path) -> Filtros:
        caminho = Path(caminho)
        try:
            texto = caminho.read_text(encoding="utf-8")
        except FileNotFoundError as erro:
            raise FiltrosInvalidos(f"Arquivo de filtros não encontrado: {caminho}") from erro
        try:
            bruto = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise FiltrosInvalidos(f"JSON inválido em {caminho}: {erro}") from erro
        return cls.de_dict(bruto)


def motivo_rejeicao(produto: Produto, filtros: Filtros) -> str | None:
    """Devolve o motivo pelo qual o produto não passa nos filtros, ou ``None`` se passa."""
    preco = produto.preco_avista
    if preco is None:
        return "sem preço"
    if preco < filtros.preco_min or (filtros.preco_max is not None and preco > filtros.preco_max):
        return "fora da faixa de preço"
    if filtros.somente_em_estoque and produto.em_estoque is not True:
        return "sem estoque confirmado"

    nome = _norm(produto.nome)
    if filtros.marcas:
        texto = f"{_norm(produto.marca)} {nome}"
        if not any(_norm(marca) in texto for marca in filtros.marcas):
            return "marca fora da lista"
    if any(_norm(palavra) not in nome for palavra in filtros.palavras_obrigatorias):
        return "falta palavra obrigatória"
    if any(_norm(palavra) in nome for palavra in filtros.palavras_proibidas):
        return "tem palavra proibida"
    return None

