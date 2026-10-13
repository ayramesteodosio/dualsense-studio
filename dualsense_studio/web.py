import json
import os
import pathlib
import sys
import threading
import time

import webview

from dualsense_painel import atualizacao, config, idioma, plataforma, segundo_plano
from dualsense_painel.idioma import _
from dualsense_painel.loop import ThreadLoop
from dualsense_painel.session import Listener, Session

from .bridge import Bridge
from .versao import VERSAO

USER_AGENT = "Mozilla/5.0 DualSenseStudio"


def recurso(*partes):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *partes)


def ui_path():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ui = os.path.join(base, "ui")
    foto = ("index-foto.html", "dualsense-base.png", "dualsense-lightbar.png")
    name = foto[0] if all(os.path.exists(os.path.join(ui, f)) for f in foto) else "index.html"
    return os.environ.get("DS_STUDIO_UI") or os.path.join(ui, name)


class Api:
    def __init__(self, host):
        self._host = host

    def send(self, message):
        self._host.receive(message)


class Host(Listener):
    def __init__(self):
        self.loop = ThreadLoop()
        self.window = None
        self.ready = False
        self.session = Session(config.load(), self, loop=self.loop)
        self.bridge = Bridge(self.session, self.emit, save_report=self.save_report, ao_instalar=self.instalar_versao,
                             ao_sair=self.sair)
        self.saindo = False
        self.icone = None
        self._avisou_fundo = False

    def emit(self, message):
        if not self.ready or not self.window:
            return
        script = f"window.dsReceive && window.dsReceive({json.dumps(message)});"
        try:
            run = getattr(self.window, "run_js", None)
            (run or self.window.evaluate_js)(script)
        except Exception:
            pass

    def receive(self, raw):
        try:
            message = json.loads(raw)
        except (TypeError, ValueError):
            return
        if isinstance(message, dict) and message.get("type") == "ready":
            self.ready = True
        self.loop.idle_add(self._handle, message)

    def _handle(self, message):
        self.bridge.handle(message)
        return False

    def status_changed(self):
        self.bridge.publish()

    def mode_changed(self):
        if self.ready:
            self.bridge.refresh_audio()
        self.bridge.publish()

    def input(self, data):
        self.bridge.publish_input(data)

    def info_changed(self):
        self.bridge.publish_info()

    def history_changed(self):
        self.bridge.publish_history()

    def toast(self, text):
        self.emit({"type": "toast", "text": text})

    def charged(self):
        self.toast(_("Controle carregado. Pode tirar do cabo ou voltar ao modo normal."))

    def low_battery(self, pct):
        self.toast(_("Bateria do controle baixa: {pct}%").format(pct=pct))

    def save_report(self, name, content):
        def ask():
            try:
                result = self.window.create_file_dialog(webview.SAVE_DIALOG, save_filename=os.path.basename(name))
            except Exception:
                result = None
            path = result[0] if isinstance(result, (list, tuple)) and result else result
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.toast(_("Relatório salvo em {path}").format(path=path))
            except OSError as e:
                self.toast(_("Não consegui salvar: {erro}").format(erro=e.strerror))
        threading.Thread(target=ask, daemon=True).start()

    def start(self):
        self.loop.start()
        self.loop.idle_add(lambda: self.session.start() and False)
        self.loop.timeout_add(5000, self._checar_versao)
        self.loop.timeout_add_seconds(24 * 3600, self._checar_versao, True)

    def _checar_versao(self, repetir=False):
        atualizacao.verificar("dualsense-studio", VERSAO, self._nova_versao)
        return repetir

    def _nova_versao(self, tag, url):
        if url == getattr(self, "_url_versao", None):
            return
        self._url_versao = url
        self.loop.idle_add(self.bridge.anunciar_versao, tag, url)

    def instalar_versao(self, caminho):
        if not atualizacao.instalar("dualsense-studio", caminho):
            return False
        reserva = threading.Timer(6, os._exit, (0,))
        reserva.daemon = True
        reserva.start()
        threading.Timer(0.8, self.sair).start()
        return True

    def _fechar(self):
        if not self.window.events.shown.is_set():
            self.shutdown()
            try:
                self.window.gui.destroy_window(self.window.uid)
            except Exception:
                pass
            time.sleep(0.5)
            os._exit(0)
        try:
            self.window.destroy()
        except Exception:
            self.shutdown()
            os._exit(0)

    def ao_fechar(self):
        fica = self.session.cfg["segundo_plano"] or (self.session.charging_mode and self.session.connected)
        if fica and not self.saindo:
            threading.Thread(target=self.window.hide, daemon=True).start()
            self._avisar_fundo()
            return False
        self.shutdown()
        return None

    def _avisar_fundo(self):
        if self.icone and not self._avisou_fundo:
            self._avisou_fundo = True
            try:
                self.icone.notify(_("Ele segue no ícone perto do relógio. Para fechar de vez, use Sair."),
                                  _("O Studio continua rodando"))
            except Exception:
                pass

    def bandeja(self):
        if plataforma.LINUX:
            return
        try:
            import pystray
            from PIL import Image
            imagem = Image.open(recurso("icones", "dualsense-studio.png"))
        except Exception:
            return

        def alternar_carga():
            self.loop.idle_add(lambda: self.session.set_charging(not self.session.charging_mode) or False)

        menu = pystray.Menu(
            pystray.MenuItem(lambda _i: _("Abrir o Studio"), lambda: self.comando_canal("mostrar"), default=True),
            pystray.MenuItem(lambda _i: _("Voltar ao modo normal") if self.session.charging_mode
                             else _("Entrar no modo carregar"), alternar_carga),
            pystray.MenuItem(lambda _i: _("Sair"), lambda: self.sair()))
        try:
            self.icone = pystray.Icon("dualsense-studio", imagem, "DualSense Studio", menu)
            self.icone.run_detached()
        except Exception:
            self.icone = None

    def comando_canal(self, comando):
        if comando == "mostrar":
            self.window.hidden = False
            try:
                self.window.gui.show(self.window.uid)
            except Exception:
                self.window.show()
        else:
            self.sair()

    def sair(self):
        self.saindo = True
        if self.icone:
            try:
                self.icone.stop()
            except Exception:
                pass
        threading.Thread(target=self._fechar, daemon=True).start()

    def shutdown(self):
        if getattr(self, "_desligado", False):
            return
        self._desligado = True
        self.ready = False
        try:
            self.loop.call_sync(self._shutdown)
        finally:
            self.loop.stop()

    def _shutdown(self):
        self.bridge.stop_mic()
        self.session.cleanup()


def main():
    idioma.carregar(os.path.join(os.path.dirname(os.path.abspath(__file__)), "traducoes"))
    idioma.definir(config.load()["idioma"])
    if segundo_plano.FLAG_SAIR in sys.argv:
        segundo_plano.enviar("dualsense-studio", "sair")
        return 0
    escondido = segundo_plano.FLAG in sys.argv
    estado, lock = segundo_plano.obter_controle("dualsense-studio", escondido=escondido)
    if estado == "mostrado" or (estado != "livre" and escondido):
        return 0
    if lock is None:
        webview.create_window("DualSense Studio", html=(
            "<body style='font:15px system-ui;background:#0b0e18;color:#e6e8ef;display:grid;place-items:center;"
            "height:100vh;margin:0'><div style='text-align:center'><h2>{}</h2><p>{}</p></div></body>").format(
            _("O controle já está sendo usado"),
            _("Não consegui assumir o controle. Feche o outro app do DualSense e tente de novo.")),
            width=480, height=240)
        webview.start()
        return 1
    host = Host()
    url = pathlib.Path(ui_path()).resolve().as_uri()
    window = webview.create_window("DualSense Studio", url=url, js_api=Api(host), width=1180, height=760,
                                   min_size=(960, 640), background_color="#05070f", hidden=escondido)
    host.window = window
    window.events.closing += host.ao_fechar
    segundo_plano.Canal("dualsense-studio", lock, host.comando_canal)
    host.bandeja()
    webview.start(host.start, debug=bool(os.environ.get("DS_DEVTOOLS")),
                  user_agent=USER_AGENT + (" DSLang/en" if idioma.atual() == "en" else ""))
    return 0
