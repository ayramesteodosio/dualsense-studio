import json
import os
import pathlib
import sys
import threading

import webview

from dualsense_painel import atualizacao, config
from dualsense_painel.loop import ThreadLoop
from dualsense_painel.session import Listener, Session, acquire_lock

from .bridge import Bridge
from .versao import VERSAO

USER_AGENT = "Mozilla/5.0 DualSenseStudio"


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
        self.bridge = Bridge(self.session, self.emit, save_report=self.save_report, ao_instalar=self.instalar_versao)

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
        self.toast("Controle carregado. Pode tirar do cabo ou voltar ao modo normal.")

    def low_battery(self, pct):
        self.toast(f"Bateria do controle baixa: {pct}%")

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
                self.toast(f"Relatório salvo em {path}")
            except OSError as e:
                self.toast(f"Não consegui salvar: {e.strerror}")
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
        threading.Timer(0.8, self._fechar).start()
        return True

    def _fechar(self):
        try:
            self.window.destroy()
        except Exception:
            os._exit(0)

    def shutdown(self):
        self.ready = False
        try:
            self.loop.call_sync(self._shutdown)
        finally:
            self.loop.stop()

    def _shutdown(self):
        self.bridge.stop_mic()
        self.session.cleanup()


def main():
    lock = acquire_lock()
    if lock is None:
        webview.create_window("DualSense Studio", html=(
            "<body style='font:15px system-ui;background:#0b0e18;color:#e6e8ef;display:grid;place-items:center;"
            "height:100vh;margin:0'><div style='text-align:center'><h2>O controle já está sendo usado</h2>"
            "<p>Feche o outro app do DualSense para usar o Studio.</p></div></body>"), width=480, height=240)
        webview.start()
        return 1
    host = Host()
    url = pathlib.Path(ui_path()).resolve().as_uri()
    window = webview.create_window("DualSense Studio", url=url, js_api=Api(host), width=1180, height=760,
                                   min_size=(960, 640), background_color="#05070f")
    host.window = window
    window.events.closing += host.shutdown
    webview.start(host.start, debug=bool(os.environ.get("DS_DEVTOOLS")), user_agent=USER_AGENT)
    return 0
