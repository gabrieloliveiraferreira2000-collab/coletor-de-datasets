"""Utilitários compartilhados pelos testes."""
import logging
from pathlib import Path

from coletor_hardware.modelos import Produto

logging.disable(logging.CRITICAL)  # os testes não precisam poluir a saída com logs

FIXTURE_KABUM = Path(__file__).parent / "fixtures" / "kabum_busca_sintetica.html"


def produto(**campos) -> Produto:
    base = {
        "coletado_em": "2026-11-08T12:00:00",
        "loja": "kabum",
        "termo_busca": "rtx 4060",
        "nome": "Placa de Vídeo RTX 4060 Asus",
        "marca": "ASUS",
        "preco_avista": 2339.99,
        "preco_cartao": 2599.99,
        "em_estoque": True,
        "url": "https://www.kabum.com.br/produto/111",
    }
    base.update(campos)
    return Produto(**base)

