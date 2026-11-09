import csv
import json
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURE_KABUM

from coletor_hardware.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self._pasta.cleanup)
        self.pasta = Path(self._pasta.name)
        self.filtros = self.pasta / "filtros.json"
        self.saida = self.pasta / "data" / "dataset.csv"

    def escrever_filtros(self, **campos):
        base = {"termos_busca": ["rtx 4060"], "preco_max": 5000, "max_paginas": 1}
        self.filtros.write_text(json.dumps({**base, **campos}), encoding="utf-8")

    def rodar(self, *extra):
        return main(["--filtros", str(self.filtros), "--saida", str(self.saida), *extra])

    def test_modo_offline_gera_o_csv(self):
        self.escrever_filtros()
        self.assertEqual(self.rodar("--html", str(FIXTURE_KABUM)), 0)
        with self.saida.open(encoding="utf-8-sig", newline="") as arq:
            linhas = list(csv.DictReader(arq))
        self.assertEqual(len(linhas), 3)

    def test_filtros_invalidos_retorna_2(self):
        self.escrever_filtros(preco_maximo=10)
        self.assertEqual(self.rodar("--html", str(FIXTURE_KABUM)), 2)
        self.assertFalse(self.saida.exists())

    def test_arquivo_de_filtros_inexistente_retorna_2(self):
        self.assertEqual(self.rodar("--html", str(FIXTURE_KABUM)), 2)

    def test_html_inexistente_retorna_2(self):
        self.escrever_filtros()
        self.assertEqual(self.rodar("--html", str(self.pasta / "nao_existe.html")), 2)

    def test_leitor_sem_produtos_retorna_1(self):
        self.escrever_filtros()
        vazio = self.pasta / "vazio.html"
        vazio.write_text("<html><body>layout novo</body></html>", encoding="utf-8")
        self.assertEqual(self.rodar("--html", str(vazio)), 1)


if __name__ == "__main__":
    unittest.main()

