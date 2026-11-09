import json
import tempfile
import unittest
from pathlib import Path

from helpers import produto

from coletor_hardware.filtros import Filtros, FiltrosInvalidos, motivo_rejeicao


def filtros(**campos) -> Filtros:
    return Filtros(**{"termos_busca": ["rtx 4060"], **campos})


class MotivoRejeicaoTest(unittest.TestCase):
    def test_aceita_produto_dentro_dos_filtros(self):
        self.assertIsNone(motivo_rejeicao(produto(), filtros(preco_max=5000)))

    def test_rejeicoes(self):
        casos = [
            ("sem preço", produto(preco_avista=None), filtros()),
            ("fora da faixa de preço", produto(preco_avista=9000.0), filtros(preco_max=5000)),
            ("fora da faixa de preço", produto(preco_avista=100.0), filtros(preco_min=500)),
            ("sem estoque confirmado", produto(em_estoque=False), filtros()),
            ("sem estoque confirmado", produto(em_estoque=None), filtros()),
            (
                "marca fora da lista",
                produto(marca="MSI", nome="Placa de Vídeo RTX 4060 MSI Ventus"),
                filtros(marcas=["asus"]),
            ),
            ("falta palavra obrigatória", produto(), filtros(palavras_obrigatorias=["super"])),
            (
                "tem palavra proibida",
                produto(nome="Notebook Gamer RTX 4060"),
                filtros(palavras_proibidas=["notebook"]),
            ),
        ]
        for esperado, item, regras in casos:
            with self.subTest(esperado=esperado, nome=item.nome):
                self.assertEqual(motivo_rejeicao(item, regras), esperado)

    def test_faixa_de_preco_inclui_os_extremos(self):
        regras = filtros(preco_min=1000, preco_max=5000)
        self.assertIsNone(motivo_rejeicao(produto(preco_avista=1000.0), regras))
        self.assertIsNone(motivo_rejeicao(produto(preco_avista=5000.0), regras))

    def test_sem_filtro_de_estoque_aceita_estoque_desconhecido(self):
        regras = filtros(somente_em_estoque=False)
        self.assertIsNone(motivo_rejeicao(produto(em_estoque=None), regras))

    def test_marca_tambem_vale_quando_esta_so_no_nome(self):
        item = produto(marca="", nome="Placa de Vídeo ASUS RTX 4060")
        self.assertIsNone(motivo_rejeicao(item, filtros(marcas=["asus"])))

    def test_ignora_maiusculas_e_acentos(self):
        regras = filtros(palavras_obrigatorias=["VIDEO"], palavras_proibidas=["NOTEBOOK"])
        self.assertIsNone(motivo_rejeicao(produto(nome="Placa de Vídeo RTX 4060"), regras))


class FiltrosTest(unittest.TestCase):
    def test_carrega_de_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "filtros.json"
            caminho.write_text(
                json.dumps({"termos_busca": ["ryzen 5"], "preco_max": 1500, "marcas": ["amd"]}),
                encoding="utf-8",
            )
            carregado = Filtros.de_arquivo(caminho)
        self.assertEqual(carregado.termos_busca, ["ryzen 5"])
        self.assertEqual(carregado.preco_max, 1500)
        self.assertEqual(carregado.marcas, ["amd"])
        self.assertTrue(carregado.somente_em_estoque)

    def test_chave_desconhecida_e_erro(self):
        with self.assertRaisesRegex(FiltrosInvalidos, "preco_maximo"):
            Filtros.de_dict({"termos_busca": ["x"], "preco_maximo": 10})

    def test_termos_de_busca_e_obrigatorio(self):
        with self.assertRaises(FiltrosInvalidos):
            Filtros.de_dict({"preco_max": 10})
        with self.assertRaises(FiltrosInvalidos):
            Filtros(termos_busca=[])
        with self.assertRaises(FiltrosInvalidos):
            Filtros(termos_busca=["  "])

    def test_faixa_de_preco_incoerente(self):
        with self.assertRaises(FiltrosInvalidos):
            filtros(preco_min=500, preco_max=100)

    def test_tipos_invalidos(self):
        invalidos = [
            {"preco_max": "5000"},
            {"preco_min": -1},
            {"somente_em_estoque": "sim"},
            {"max_paginas": 0},
            {"itens_por_pagina": 2.5},
            {"marcas": "asus"},
        ]
        for campos in invalidos:
            with self.subTest(campos=campos), self.assertRaises(FiltrosInvalidos):
                filtros(**campos)

    def test_textos_vazios_nas_listas_sao_ignorados(self):
        regras = filtros(palavras_proibidas=["", "  ", "usado"])
        self.assertEqual(regras.palavras_proibidas, ["usado"])

    def test_json_invalido(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "filtros.json"
            caminho.write_text("{ isso não é json", encoding="utf-8")
            with self.assertRaisesRegex(FiltrosInvalidos, "JSON inválido"):
                Filtros.de_arquivo(caminho)

    def test_arquivo_inexistente(self):
        with self.assertRaisesRegex(FiltrosInvalidos, "não encontrado"):
            Filtros.de_arquivo("nao_existe.json")

    def test_json_que_nao_e_objeto(self):
        with self.assertRaises(FiltrosInvalidos):
            Filtros.de_dict(["termos_busca"])


if __name__ == "__main__":
    unittest.main()

