import unittest

from helpers import FIXTURE_KABUM

from coletor_hardware.lojas import kabum

AGORA = "2026-11-08T12:00:00"


def bruto(**campos) -> dict:
    return {"name": "Placa de Vídeo X", "price": 100, "available": True, **campos}


class UrlBuscaTest(unittest.TestCase):
    def test_monta_a_url(self):
        self.assertEqual(
            kabum.url_busca("rtx 4060", 2, 20),
            "https://www.kabum.com.br/busca/rtx-4060?page_number=2&page_size=20",
        )

    def test_codifica_acentos(self):
        self.assertIn("v%C3%ADdeo", kabum.url_busca("placa de vídeo", 1, 20))


class ExtrairProdutosTest(unittest.TestCase):
    def setUp(self):
        self.html = FIXTURE_KABUM.read_text(encoding="utf-8")

    def test_acha_todos_os_produtos_da_pagina(self):
        brutos = kabum.extrair_produtos(self.html)
        self.assertEqual(len(brutos), 7)

    def test_nao_confunde_metadados_com_produto(self):
        nomes = [item["name"] for item in kabum.extrair_produtos(self.html)]
        self.assertNotIn("busca", nomes)

    def test_pagina_sem_next_data(self):
        self.assertEqual(kabum.extrair_produtos("<html><body>oi</body></html>"), [])

    def test_json_quebrado(self):
        html = '<script id="__NEXT_DATA__" type="application/json">{ quebrado</script>'
        self.assertEqual(kabum.extrair_produtos(html), [])


class NormalizarTest(unittest.TestCase):
    def test_preco_pix_vira_avista_e_o_normal_fica_no_cartao(self):
        item = kabum.normalizar(bruto(price=2599.99, priceWithDiscount=2339.99), "rtx", AGORA)
        self.assertEqual(item.preco_avista, 2339.99)
        self.assertEqual(item.preco_cartao, 2599.99)

    def test_sem_preco_pix_o_avista_e_o_preco_normal(self):
        item = kabum.normalizar(bruto(price=2699.9, priceWithDiscount=None), "rtx", AGORA)
        self.assertEqual(item.preco_avista, 2699.9)
        self.assertEqual(item.preco_cartao, 2699.9)

    def test_preco_em_texto_no_formato_brasileiro(self):
        item = kabum.normalizar(bruto(price="R$ 2.699,90"), "rtx", AGORA)
        self.assertEqual(item.preco_cartao, 2699.9)

    def test_precos_invalidos_viram_none(self):
        for invalido in ["abc", "", 0, -5, float("nan"), float("inf"), True, None]:
            with self.subTest(preco=invalido):
                item = kabum.normalizar(bruto(price=invalido), "rtx", AGORA)
                self.assertIsNone(item.preco_avista)
                self.assertIsNone(item.preco_cartao)

    def test_marca_como_dict_ou_como_texto(self):
        com_dict = kabum.normalizar(bruto(manufacturer={"name": "ASUS"}), "rtx", AGORA)
        com_texto = kabum.normalizar(bruto(manufacturer="PNY"), "rtx", AGORA)
        sem_marca = kabum.normalizar(bruto(), "rtx", AGORA)
        self.assertEqual(com_dict.marca, "ASUS")
        self.assertEqual(com_texto.marca, "PNY")
        self.assertEqual(sem_marca.marca, "")

    def test_url_pelo_codigo_ou_relativa(self):
        pelo_codigo = kabum.normalizar(bruto(code=111), "rtx", AGORA)
        relativa = kabum.normalizar(bruto(link="/produto/222"), "rtx", AGORA)
        self.assertEqual(pelo_codigo.url, "https://www.kabum.com.br/produto/111")
        self.assertEqual(relativa.url, "https://www.kabum.com.br/produto/222")

    def test_disponibilidade_desconhecida_fica_none(self):
        sem_campo = bruto()
        del sem_campo["available"]
        self.assertIsNone(kabum.normalizar(sem_campo, "rtx", AGORA).em_estoque)
        self.assertFalse(kabum.normalizar(bruto(available=False), "rtx", AGORA).em_estoque)

    def test_item_sem_nome_e_ignorado(self):
        self.assertIsNone(kabum.normalizar(bruto(name="  "), "rtx", AGORA))


if __name__ == "__main__":
    unittest.main()

