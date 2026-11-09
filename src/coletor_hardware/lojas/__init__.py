"""Lojas suportadas. Cada loja é um módulo com a mesma interface (ver kabum.py)."""
from types import ModuleType

from coletor_hardware.lojas import kabum

LOJAS: dict[str, ModuleType] = {kabum.NOME: kabum}

