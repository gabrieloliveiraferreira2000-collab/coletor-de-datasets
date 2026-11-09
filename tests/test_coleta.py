import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from helpers import FIXTURE_KABUM

from coletor_hardware.coleta import ARQUIVO_DEBUG, coletar
from coletor_hardware.filtros import Filtros
from coletor_hardware.lojas import kabum

AGORA = "2026-11-08T12:00:00"


class FonteFalsa:
    def __init__(self, html, bloqueia=False):
        self.html = html
        self.bloqueia = bloqueia
        self.urls = []

    def pode_acessar(self, url):
        return not self.bloqueia

    def baixar(self, url):
        self.urls.append(url)
        return self.html

    def esperar(self):
        return None


def filtros(**campos) -> Filtros:
    base = {
        "termos_busca": ["rtx 4060"],
        "preco_max": 5000,
        "palavras_proibidas": ["notebook"],
        "max_paginas": 1,
    }
    return Filtros(**{**base, **campos})


class ColetaTest(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self._pasta.cleanup)
        self.pasta = Path(self._pasta.name)
        self.saida = self.pasta / "dataset.csv"
        self.html = FIXTURE_KABUM.read_text(encoding="utf-8")

    def linhas(self):
        with self.saida.open(encoding="utf-8-sig", newline="") as arq:
            return list(csv.DictReader(arq))

    def test_grava_so_o_que_passa_nos_filtros(self):
        resumo = coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora=AGORA)
        self.assertEqual(resumo.gravados, 3)
        self.assertEqual(
            resumo.descartes,
            Counter({"fora da faixa de preço": 2, "sem preço": 1, "sem estoque confirmado": 1}),
        )
        codigos = sorted(linha["url"].rsplit("/", 1)[1] for linha in self.linhas())
        self.assertEqual(codigos, ["111", "222", "777"])

    def test_dados_gravados_sao_os_da_pagina(self):
        coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora=AGORA)
        asus = next(linha for linha in self.linhas() if linha["marca"] == "ASUS")
        self.assertEqual(asus["preco_avista"], "2339.99")
        self.assertEqual(asus["preco_cartao"], "2599.99")
        self.assertEqual(asus["loja"], "kabum")
        self.assertEqual(asus["coletado_em"], AGORA)

    def test_filtro_de_marca_reduz_o_resultado(self):
        resumo = coletar(
            filtros(marcas=["asus"]), kabum, FonteFalsa(self.html), self.saida, agora=AGORA
        )
        self.assertEqual(resumo.gravados, 1)

    def test_segunda_execucao_no_mesmo_dia_nao_duplica(self):
        coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora=AGORA)
        segunda = coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora=AGORA)
        self.assertEqual(segunda.gravados, 0)
        self.assertEqual(len(self.linhas()), 3)

    def test_outro_dia_grava_de_novo_para_formar_o_historico(self):
        coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora=AGORA)
        coletar(filtros(), kabum, FonteFalsa(self.html), self.saida, agora="2026-11-09T12:00:00")
        self.assertEqual(len(self.linhas()), 6)

    def test_pagina_repetida_encerra_a_busca_do_termo(self):
        fonte = FonteFalsa(self.html)
        coletar(filtros(max_paginas=5), kabum, fonte, self.saida, agora=AGORA)
        self.assertEqual(len(fonte.urls), 2)

    def test_pagina_sem_produtos_salva_html_para_depuracao(self):
        fonte = FonteFalsa("<html><body>mudou tudo</body></html>")
        resumo = coletar(
            filtros(), kabum, fonte, self.saida, pasta_debug=self.pasta / "dbg", agora=AGORA
        )
        self.assertEqual(resumo.paginas_sem_produtos, 1)
        self.assertEqual(resumo.gravados, 0)
        self.assertTrue((self.pasta / "dbg" / ARQUIVO_DEBUG).exists())
        self.assertFalse(self.saida.exists())

    def test_robots_bloqueando_nao_baixa_nada(self):
        fonte = FonteFalsa(self.html, bloqueia=True)
        resumo = coletar(filtros(), kabum, fonte, self.saida, agora=AGORA)
        self.assertEqual(resumo.bloqueios_robots, 1)
        self.assertEqual(fonte.urls, [])

    def test_falha_de_download_e_contada(self):
        resumo = coletar(filtros(), kabum, FonteFalsa(None), self.saida, agora=AGORA)
        self.assertEqual(resumo.falhas_download, 1)
        self.assertEqual(resumo.gravados, 0)


if __name__ == "__main__":
    unittest.main()

