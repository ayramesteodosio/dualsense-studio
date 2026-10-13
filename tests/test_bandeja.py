import sys
import types
import unittest
from unittest import mock


class BandejaTest(unittest.TestCase):
    def test_menu_da_bandeja(self):
        criados = {}
        pystray = types.ModuleType("pystray")

        class Item:
            def __init__(self, texto, acao, default=False):
                self.texto, self.acao, self.default = texto, acao, default

        class Icone:
            def __init__(self, nome, imagem, titulo, menu):
                criados["icone"] = self
                self.menu = menu
                self.parado = False

            def run_detached(self):
                criados["rodando"] = True

            def stop(self):
                self.parado = True

        pystray.MenuItem = Item
        pystray.Menu = lambda *itens: list(itens)
        pystray.Icon = Icone
        pil = types.ModuleType("PIL")
        pil.Image = types.SimpleNamespace(open=lambda caminho: caminho)
        webview = types.ModuleType("webview")
        with mock.patch.dict(sys.modules, {"pystray": pystray, "PIL": pil, "webview": webview}):
            sys.modules.pop("dualsense_studio.web", None)
            from dualsense_studio import web
            from dualsense_painel import plataforma
            host = web.Host.__new__(web.Host)
            host.icone, host.saindo = None, False
            host.session = types.SimpleNamespace(charging_mode=False)
            chamadas = []
            host.comando_canal = lambda c: chamadas.append(c)
            host.sair = lambda: chamadas.append("sair")
            host.loop = types.SimpleNamespace(idle_add=lambda f: chamadas.append("alternar"))
            with mock.patch.object(plataforma, "LINUX", False):
                web.Host.bandeja(host)
            sys.modules.pop("dualsense_studio.web", None)
        self.assertTrue(criados.get("rodando"))
        abrir, carga, sair = host.icone.menu
        self.assertTrue(abrir.default)
        self.assertEqual(carga.texto(None), "Entrar no modo carregar")
        host.session.charging_mode = True
        self.assertEqual(carga.texto(None), "Voltar ao modo normal")
        abrir.acao()
        carga.acao()
        sair.acao()
        self.assertEqual(chamadas, ["mostrar", "alternar", "sair"])
