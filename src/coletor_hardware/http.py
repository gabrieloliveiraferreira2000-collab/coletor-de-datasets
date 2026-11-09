"""Acesso às páginas: educado com o site (robots.txt, pausas, novas tentativas)."""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from urllib import robotparser

import requests

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; coletor-hardware-br/0.1; projeto academico)"
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


class Cliente:
    """Baixa páginas respeitando o robots.txt e espalhando as requisições no tempo."""

    def __init__(
        self,
        site: str,
        pausa: tuple[float, float] = (2.0, 4.0),
        tentativas: int = 3,
        timeout: float = 20.0,
        sessao: requests.Session | None = None,
    ) -> None:
        self.site = site.rstrip("/")
        self.pausa = pausa
        self.tentativas = tentativas
        self.timeout = timeout
        self.sessao = sessao or requests.Session()
        self.sessao.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
        self._robots: robotparser.RobotFileParser | None = None
        self._robots_lido = False

    def _ler_robots(self) -> None:
        if self._robots_lido:
            return
        self._robots_lido = True
        try:
            resposta = self.sessao.get(f"{self.site}/robots.txt", timeout=self.timeout)
        except requests.RequestException as erro:
            log.warning("Não consegui ler o robots.txt (%s); seguindo sem essa checagem.", erro)
            return
        if resposta.status_code != 200:
            log.warning(
                "robots.txt respondeu HTTP %s; seguindo sem essa checagem.", resposta.status_code
            )
            return
        regras = robotparser.RobotFileParser()
        regras.parse(resposta.text.splitlines())
        self._robots = regras

    def pode_acessar(self, url: str) -> bool:
        self._ler_robots()
        return True if self._robots is None else self._robots.can_fetch(USER_AGENT, url)

    def baixar(self, url: str) -> str | None:
        """Devolve o HTML da página ou ``None`` se não foi possível baixar."""
        for tentativa in range(1, self.tentativas + 1):
            try:
                resposta = self.sessao.get(url, timeout=self.timeout)
            except requests.RequestException as erro:
                log.warning("Erro de rede em %s: %s", url, erro)
            else:
                if resposta.status_code == 200:
                    return resposta.text
                log.warning("HTTP %s em %s", resposta.status_code, url)
                if resposta.status_code not in STATUS_TRANSITORIOS:
                    return None
            if tentativa < self.tentativas:
                time.sleep(3 * tentativa)
        return None

    def esperar(self) -> None:
        time.sleep(random.uniform(*self.pausa))


class ClienteLocal:
    """Lê uma página já salva no disco (modo offline), com a mesma interface do Cliente."""

    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)

    def pode_acessar(self, url: str) -> bool:
        return True

    def baixar(self, url: str) -> str | None:
        return self.caminho.read_text(encoding="utf-8")

    def esperar(self) -> None:
        return None

