"""Motor de coleta web com perfil declarativo, seletores CSS e filtros por campo."""

from __future__ import annotations

import csv
import json
import logging
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


@dataclass
class Regra:
    campo: str
    operador: str
    valor: str


@dataclass
class Perfil:
    nome: str
    url_busca: str
    seletor_item: str
    campos: dict[str, str]
    termos_busca: list[str] = field(default_factory=list)
    max_paginas: int = 1
    regras: list[Regra] = field(default_factory=list)
    pausa_segundos: float = 2.0

    @classmethod
    def de_dict(cls, dados: object) -> "Perfil":
        if not isinstance(dados, dict):
            raise ValueError("O perfil precisa ser um objeto JSON.")
        obrigatorios = ("nome", "url_busca", "seletor_item", "campos")
        faltantes = [chave for chave in obrigatorios if not dados.get(chave)]
        if faltantes:
            raise ValueError("Preencha os campos obrigatórios: " + ", ".join(faltantes))
        campos = dados["campos"]
        if not isinstance(campos, dict) or not campos:
            raise ValueError("Informe ao menos um campo e seu seletor CSS.")
        campos_validos = all(
            isinstance(k, str) and isinstance(v, str) and v.strip()
            for k, v in campos.items()
        )
        if not campos_validos:
            raise ValueError("Cada campo precisa ter um nome e um seletor CSS.")
        campos = {k.strip(): v.strip() for k, v in campos.items()}
        if any(not nome for nome in campos):
            raise ValueError("Os nomes dos campos não podem ficar vazios.")
        if len(campos) != len(dados["campos"]):
            raise ValueError("Os nomes dos campos precisam ser únicos.")
        termos = dados.get("termos_busca", [])
        regras_brutas = dados.get("regras", [])
        if not isinstance(termos, list) or not all(isinstance(t, str) for t in termos):
            raise ValueError("Os termos de busca precisam ser uma lista de textos.")
        if not isinstance(regras_brutas, list):
            raise ValueError("As regras de filtro precisam estar em uma lista.")
        regras = []
        for regra in regras_brutas:
            if not isinstance(regra, dict) or not isinstance(regra.get("operador"), str):
                raise ValueError("Cada filtro precisa ser um objeto com operador válido.")
            if regra["operador"] not in {
                "contém", "igual", "não contém"
            }:
                raise ValueError("Operador inválido. Use contém, igual ou não contém.")
            if not regra.get("campo") or "valor" not in regra:
                raise ValueError("Cada regra precisa de campo e valor.")
            regras.append(
                Regra(str(regra["campo"]).strip(), regra["operador"], str(regra["valor"]))
            )
        campos_reservados = {"coletado_em", "fonte", "termo_busca"}
        desconhecidos = {r.campo for r in regras} - (set(campos) | campos_reservados)
        if desconhecidos:
            nomes = ", ".join(sorted(desconhecidos))
            raise ValueError(f"Os filtros citam campos que não existem: {nomes}")
        try:
            paginas_brutas = dados.get("max_paginas", 1)
            pausa_bruta = dados.get("pausa_segundos", 2.0)
            if (
                isinstance(paginas_brutas, bool)
                or not isinstance(paginas_brutas, int)
                or isinstance(pausa_bruta, bool)
                or not isinstance(pausa_bruta, (int, float))
            ):
                raise ValueError
            paginas = paginas_brutas
            pausa = float(pausa_bruta)
        except (TypeError, ValueError) as erro:
            raise ValueError("Páginas e pausa precisam ser números válidos.") from erro
        if not 1 <= paginas <= 100:
            raise ValueError("O limite de páginas deve ficar entre 1 e 100.")
        if not 1 <= pausa <= 60:
            raise ValueError("A pausa deve ficar entre 1 e 60 segundos.")
        url = str(dados["url_busca"]).strip()
        parsed = urlparse(url.replace("{termo}", "busca").replace("{pagina}", "1"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A URL precisa começar com http:// ou https://.")
        if {k.strip() for k in campos} & {"coletado_em", "fonte", "termo_busca"}:
            raise ValueError("Os nomes coletado_em, fonte e termo_busca são reservados.")
        nome = str(dados["nome"]).strip()
        seletor_item = str(dados["seletor_item"]).strip()
        if not nome or not seletor_item:
            raise ValueError("Informe um nome para a fonte e um seletor CSS para os resultados.")
        return cls(
            nome=nome,
            url_busca=url,
            seletor_item=seletor_item,
            campos=campos,
            termos_busca=[t.strip() for t in termos if t.strip()] or [""],
            max_paginas=paginas,
            regras=regras,
            pausa_segundos=pausa,
        )

    @classmethod
    def de_arquivo(cls, caminho: str | Path) -> "Perfil":
        try:
            dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        except FileNotFoundError as erro:
            raise ValueError(f"Perfil não encontrado: {caminho}") from erro
        except json.JSONDecodeError as erro:
            raise ValueError(f"JSON inválido no perfil: {erro}") from erro
        return cls.de_dict(dados)

    def para_dict(self) -> dict:
        return {
            **asdict(self),
            "regras": [asdict(regra) for regra in self.regras],
        }


def _ler_valor(item, seletor: str) -> str:
    """Extrai texto ou atributo conforme seletor CSS opcional `seletor :: atributo`."""
    partes = seletor.rsplit(" :: ", 1)
    css = partes[0].strip()
    atributo = partes[1].strip() if len(partes) == 2 else "texto"
    elemento = item.select_one(css)
    if elemento is None:
        return ""
    if atributo == "texto":
        return " ".join(elemento.stripped_strings)
    return str(elemento.get(atributo, "")).strip()


def _passa_regras(registro: dict[str, str], regras: list[Regra]) -> bool:
    for regra in regras:
        valor = registro.get(regra.campo, "").casefold()
        esperado = regra.valor.casefold()
        if regra.operador == "contém" and esperado not in valor:
            return False
        if regra.operador == "igual" and valor != esperado:
            return False
        if regra.operador == "não contém" and esperado in valor:
            return False
    return True


def _pode_acessar(
    url: str,
    sessao: requests.Session,
    cache: dict[str, RobotFileParser | None],
) -> bool:
    parsed = urlparse(url)
    origem = f"{parsed.scheme}://{parsed.netloc}"
    if origem not in cache:
        rp = RobotFileParser()
        rp.set_url(f"{origem}/robots.txt")
        try:
            resposta = sessao.get(rp.url, timeout=15)
            if resposta.status_code == 200:
                rp.parse(resposta.text.splitlines())
                cache[origem] = rp
            else:
                log.warning(
                    "robots.txt respondeu %s para %s; coleta bloqueada por segurança.",
                    resposta.status_code,
                    origem,
                )
                cache[origem] = None
        except requests.RequestException:
            log.warning("Não foi possível consultar robots.txt de %s; coleta bloqueada.", origem)
            cache[origem] = None
    regras = cache[origem]
    return regras is not None and regras.can_fetch("ColetorDeDatasets/0.2", url)


def coletar(
    perfil: Perfil,
    destino: str | Path,
    ao_atualizar: Callable[[str], None] | None = None,
    sessao: requests.Session | None = None,
) -> tuple[int, int]:
    """Coleta páginas permitidas, filtra registros e grava um CSV novo.

    Devolve `(gravados, descartados)`. A callback serve para exibir andamento na interface.
    """
    sessao = sessao or requests.Session()
    sessao.headers.update(
        {
            "User-Agent": "ColetorDeDatasets/0.2 (aplicativo educacional)",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
    )
    cache_robots: dict[str, RobotFileParser | None] = {}
    registros: list[dict[str, str]] = []
    descartados = 0
    primeira = True
    termos = perfil.termos_busca or [""]

    for termo in termos:
        for pagina in range(1, perfil.max_paginas + 1):
            url = perfil.url_busca.format(termo=quote_plus(termo), pagina=pagina)
            if not _pode_acessar(url, sessao, cache_robots):
                raise PermissionError(
                    f"A coleta foi interrompida: robots.txt não permite acessar {url}"
                )
            if not primeira:
                time.sleep(random.uniform(perfil.pausa_segundos, perfil.pausa_segundos + 1.0))
            primeira = False
            if ao_atualizar:
                ao_atualizar(f"Buscando “{termo or perfil.nome}” — página {pagina}")
            resposta = sessao.get(url, timeout=25)
            resposta.raise_for_status()
            sopa = BeautifulSoup(resposta.text, "html.parser")
            try:
                itens = sopa.select(perfil.seletor_item)
            except Exception as erro:
                raise ValueError(f"Seletor de itens inválido: {perfil.seletor_item}") from erro
            if not itens:
                break
            for item in itens:
                registro = {
                    "coletado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "fonte": perfil.nome,
                    "termo_busca": termo,
                }
                for nome, seletor in perfil.campos.items():
                    try:
                        registro[nome] = _ler_valor(item, seletor)
                    except Exception as erro:
                        raise ValueError(f"Seletor inválido no campo “{nome}”: {seletor}") from erro
                if _passa_regras(registro, perfil.regras):
                    registros.append(registro)
                else:
                    descartados += 1

    colunas = ["coletado_em", "fonte", "termo_busca", *perfil.campos]
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)
    if ao_atualizar:
        if registros:
            ao_atualizar(f"Concluído: {len(registros)} registros salvos.")
        else:
            ao_atualizar(
                "Nenhum resultado passou pelos filtros; CSV vazio criado com os cabeçalhos."
            )
    return len(registros), descartados

