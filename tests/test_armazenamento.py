import csv
import tempfile
import unittest
from pathlib import Path

from helpers import produto

from coletor_hardware.armazenamento import acrescentar, chaves_gravadas
from coletor_hardware.modelos import COLUNAS


def ler(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as arq:
        return list(csv.DictReader(arq))


class ArmazenamentoTest(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self._pasta.cleanup)
        self.caminho = Path(self._pasta.name) / "dados" / "dataset.csv"

    def test_cria_pasta_arquivo_e_cabecalho(self):
        self.assertEqual(acrescentar(self.caminho, [produto()]), 1)
        with self.caminho.open(encoding="utf-8-sig", newline="") as arq:
            self.assertEqual(next(csv.reader(arq)), COLUNAS)

    def test_cabecalho_aparece_uma_vez_so(self):
        acrescentar(self.caminho, [produto()])
        acrescentar(self.caminho, [produto(url="https://www.kabum.com.br/produto/222")])
        self.assertEqual(len(ler(self.caminho)), 2)
        texto = self.caminho.read_text(encoding="utf-8-sig")
        self.assertEqual(texto.count("coletado_em"), 1)

    def test_lista_vazia_nao_cria_arquivo(self):
        self.assertEqual(acrescentar(self.caminho, []), 0)
        self.assertFalse(self.caminho.exists())

    def test_none_vira_campo_vazio(self):
        acrescentar(self.caminho, [produto(preco_avista=None, em_estoque=None)])
        linha = ler(self.caminho)[0]
        self.assertEqual(linha["preco_avista"], "")
        self.assertEqual(linha["em_estoque"], "")

    def test_chaves_gravadas(self):
        self.assertEqual(chaves_gravadas(self.caminho), set())
        item = produto()
        acrescentar(self.caminho, [item])
        self.assertEqual(chaves_gravadas(self.caminho), {item.chave})

    def test_cabecalho_diferente_e_erro(self):
        self.caminho.parent.mkdir(parents=True)
        self.caminho.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "colunas diferentes"):
            acrescentar(self.caminho, [produto()])
        with self.assertRaisesRegex(ValueError, "colunas diferentes"):
            chaves_gravadas(self.caminho)

    def test_arquivo_vazio_e_tratado_como_novo(self):
        self.caminho.parent.mkdir(parents=True)
        self.caminho.write_text("", encoding="utf-8")
        acrescentar(self.caminho, [produto()])
        self.assertEqual(len(ler(self.caminho)), 1)


if __name__ == "__main__":
    unittest.main()

