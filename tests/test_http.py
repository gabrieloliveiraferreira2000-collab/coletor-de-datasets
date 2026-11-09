import unittest
from unittest import mock

import helpers  # noqa: F401  (silencia os logs durante os testes)
import requests

from coletor_hardware.http import Cliente

SITE = "https://loja.exemplo"


class RespostaFalsa:
    def __init__(self, status, texto=""):
        self.status_code = status
        self.text = texto


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.headers = {}
        self.chamadas = []

    def get(self, url, timeout=None):
        self.chamadas.append(url)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def cliente(respostas, **kwargs):
    sessao = SessaoFalsa(respostas)
    return Cliente(SITE, sessao=sessao, **kwargs), sessao


class BaixarTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("coletor_hardware.http.time.sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_devolve_o_html_quando_200(self):
        c, sessao = cliente([RespostaFalsa(200, "<html/>")])
        self.assertEqual(c.baixar(f"{SITE}/busca"), "<html/>")
        self.assertEqual(len(sessao.chamadas), 1)

    def test_erro_definitivo_nao_tenta_de_novo(self):
        c, sessao = cliente([RespostaFalsa(404)])
        self.assertIsNone(c.baixar(f"{SITE}/busca"))
        self.assertEqual(len(sessao.chamadas), 1)

    def test_erro_transitorio_tenta_de_novo(self):
        c, sessao = cliente([RespostaFalsa(503), RespostaFalsa(200, "ok")])
        self.assertEqual(c.baixar(f"{SITE}/busca"), "ok")
        self.assertEqual(len(sessao.chamadas), 2)
        self.sleep.assert_called_once()

    def test_desiste_depois_das_tentativas(self):
        erro = requests.ConnectionError("sem rede")
        c, sessao = cliente([erro, erro, erro], tentativas=3)
        self.assertIsNone(c.baixar(f"{SITE}/busca"))
        self.assertEqual(len(sessao.chamadas), 3)


class RobotsTest(unittest.TestCase):
    def test_respeita_disallow(self):
        robots = RespostaFalsa(200, "User-agent: *\nDisallow: /busca\n")
        c, _ = cliente([robots])
        self.assertFalse(c.pode_acessar(f"{SITE}/busca/rtx-4060"))
        self.assertTrue(c.pode_acessar(f"{SITE}/produto/1"))

    def test_le_o_robots_uma_vez_so(self):
        c, sessao = cliente([RespostaFalsa(200, "User-agent: *\nDisallow:\n")])
        c.pode_acessar(f"{SITE}/a")
        c.pode_acessar(f"{SITE}/b")
        self.assertEqual(len(sessao.chamadas), 1)

    def test_sem_robots_segue_em_frente(self):
        c, _ = cliente([RespostaFalsa(404)])
        self.assertTrue(c.pode_acessar(f"{SITE}/busca"))

    def test_erro_de_rede_no_robots_segue_em_frente(self):
        c, _ = cliente([requests.ConnectionError("sem rede")])
        self.assertTrue(c.pode_acessar(f"{SITE}/busca"))


if __name__ == "__main__":
    unittest.main()

