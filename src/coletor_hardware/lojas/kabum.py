"""Leitor da KaBuM!.

A KaBuM! é feita em Next.js: a página de busca traz os produtos em um JSON dentro da tag
``<script id="__NEXT_DATA__">``. Em vez de depender do caminho exato dentro desse JSON
(que pode mudar), o leitor procura qualquer objeto que pareça um produto (tem ``name`` e
``price`` ou ``priceWithDiscount``).

Se o site mudar e o leitor parar de achar produtos, só este arquivo precisa de ajuste.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from coletor_hardware.modelos import Produto

NOME = "kabum"
SITE = "https://www.kabum.com.br"

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


def url_busca(termo: str, pagina: int, itens: int) -> str:
    slug = quote("-".join(termo.split()))
    return f"{SITE}/busca/{slug}?page_number={pagina}&page_size={itens}"


def _achar_produtos(obj: Any) -> Iterator[dict]:
    if isinstance(obj, dict):
        if "name" in obj and ("price" in obj or "priceWithDiscount" in obj):
            yield obj
        for valor in obj.values():
            yield from _achar_produtos(valor)
    elif isinstance(obj, list):
        for valor in obj:
            yield from _achar_produtos(valor)


def extrair_produtos(html: str) -> list[dict]:
    """Devolve os produtos crus (dicts) encontrados na página, ou lista vazia."""
    achado = _NEXT_DATA.search(html)
    if not achado:
        return []
    try:
        dados = json.loads(achado.group(1))
    except json.JSONDecodeError:
        return []
    return list(_achar_produtos(dados))


def _para_float(valor: Any) -> float | None:
    if valor is None or isinstance(valor, bool) or valor == "":
        return None
    if isinstance(valor, str):
        texto = valor.replace("R$", "").strip()
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        valor = texto
    try:
        numero = round(float(valor), 2)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) and numero > 0 else None


def normalizar(bruto: dict, termo: str, coletado_em: str) -> Produto | None:
    """Converte o dict cru da loja em ``Produto``. Sem nome, o item é ignorado."""
    nome = str(bruto.get("name") or "").strip()
    if not nome:
        return None
    cartao = _para_float(bruto.get("price"))
    pix = _para_float(bruto.get("priceWithDiscount"))

    marca = bruto.get("manufacturer")
    if isinstance(marca, dict):
        marca = marca.get("name")

    codigo = bruto.get("code") or bruto.get("id")
    url = str(bruto.get("url") or bruto.get("link") or "")
    if url.startswith("/"):
        url = SITE + url
    elif not url and codigo:
        url = f"{SITE}/produto/{codigo}"

    disponivel = bruto.get("available")
    return Produto(
        coletado_em=coletado_em,
        loja=NOME,
        termo_busca=termo,
        nome=nome,
        marca=str(marca or "").strip(),
        preco_avista=pix if pix is not None else cartao,
        preco_cartao=cartao,
        em_estoque=disponivel if isinstance(disponivel, bool) else None,
        url=url,
    )

