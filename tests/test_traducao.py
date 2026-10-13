import glob
import importlib.util
import os
import unittest

import dualsense_painel

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAINEL = os.path.dirname(os.path.dirname(os.path.abspath(dualsense_painel.__file__)))


class TraducaoTest(unittest.TestCase):
    def test_todo_texto_tem_traducao(self):
        caminho = os.path.join(PAINEL, "tests", "verificar_traducao.py")
        if not os.path.exists(caminho):
            self.skipTest("verificador do painel indisponível")
        spec = importlib.util.spec_from_file_location("verificar_traducao", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        arquivos = glob.glob(os.path.join(RAIZ, "dualsense_studio", "*.py"))
        dados = modulo.traducoes(os.path.join(RAIZ, "dualsense_studio", "traducoes"),
                                 os.path.join(PAINEL, "dualsense_painel", "traducoes"))
        self.assertEqual(modulo.problemas(arquivos, dados), [])
