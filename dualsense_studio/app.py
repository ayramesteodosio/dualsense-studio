import json
import os
import signal
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2

from dualsense_painel import config
from dualsense_painel.session import Session, acquire_lock

from .bridge import Bridge

APP_ID = "com.ayrames.DualSenseStudio"
UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
FOTO = ("index-foto.html", "dualsense-base.png", "dualsense-lightbar.png")
UI = os.environ.get("DS_STUDIO_UI") or os.path.join(
    UI_DIR, FOTO[0] if all(os.path.exists(os.path.join(UI_DIR, f)) for f in FOTO) else "index.html")


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="DualSense Studio")
        self.app = app
        self.set_default_size(1180, 760)
        self.set_size_request(960, 640)
        self.set_icon_name(APP_ID)

        manager = WebKit2.UserContentManager()
        manager.connect("script-message-received::ds", self._on_message)
        manager.register_script_message_handler("ds")
        self.view = WebKit2.WebView.new_with_user_content_manager(manager)
        self.view.get_settings().set_enable_developer_extras(bool(os.environ.get("DS_DEVTOOLS")))
        self.view.set_background_color(Gdk.RGBA(0.02, 0.03, 0.06, 1))
        if not os.environ.get("DS_DEVTOOLS"):
            self.view.connect("context-menu", lambda *_: True)
        self.add(self.view)

        self.session = Session(config.load(), self)
        self.bridge = Bridge(self.session, self._emit, save_report=self._save_report)
        self._ready = False

        self.view.load_uri(GLib.filename_to_uri(UI))
        self.connect("delete-event", self._on_close)
        self.show_all()
        self.session.start()

    def _emit(self, message):
        if not self._ready:
            return
        script = f"window.dsReceive && window.dsReceive({json.dumps(message)});"
        self.view.run_javascript(script, None, None, None)

    def _on_message(self, _manager, result):
        try:
            message = json.loads(result.get_js_value().to_string())
        except (ValueError, TypeError):
            return
        if isinstance(message, dict) and message.get("type") == "ready":
            self._ready = True
        self.bridge.handle(message)

    def status_changed(self):
        self.bridge.publish()

    def mode_changed(self):
        if self._ready:
            self.bridge.refresh_audio()
        self.bridge.publish()

    def input(self, data):
        self.bridge.publish_input(data)

    def info_changed(self):
        self.bridge.publish_info()

    def history_changed(self):
        self.bridge.publish_history()

    def low_battery(self, pct):
        n = Gio.Notification.new("Bateria do controle baixa")
        n.set_body(f"O DualSense está com {pct}%. Hora de ligar no cabo.")
        self.app.send_notification("bateria-baixa", n)

    def _save_report(self, name, content):
        dialog = Gtk.FileChooserNative.new("Salvar relatório", self, Gtk.FileChooserAction.SAVE,
                                           "Salvar", "Cancelar")
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(os.path.basename(name))
        docs = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
        if docs:
            dialog.set_current_folder(docs)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.toast(f"Relatório salvo em {path}")
            except OSError as e:
                self.toast(f"Não consegui salvar: {e.strerror}")
        dialog.destroy()

    def toast(self, text):
        self._emit({"type": "toast", "text": text})

    def charged(self):
        n = Gio.Notification.new("Controle carregado")
        n.set_body("Pode tirar do cabo ou voltar ao modo normal.")
        self.app.send_notification("carregado", n)

    def _on_close(self, *_args):
        if self.session.charging_mode and self.session.connected:
            self.hide()
            self.app.hold_in_background()
            return True
        self.bridge.stop_mic()
        self.session.cleanup()
        return False


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self._held = False
        self._lock = None

    def _busy(self):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE,
                                   text="O controle já está sendo usado")
        dialog.format_secondary_text("O Painel do DualSense está aberto. Feche ele para usar o Studio.")
        self.add_window(dialog)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.show()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self._on_signal)

    def _on_signal(self):
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_shutdown(self):
        if self.window:
            self.window.bridge.stop_mic()
            self.window.session.cleanup()
        Gtk.Application.do_shutdown(self)

    def do_activate(self):
        if not self.window and not self._lock:
            self._lock = acquire_lock()
            if self._lock is None:
                self._busy()
                return
        if not self.window:
            self.window = Window(self)
        if self._held:
            self.release()
            self._held = False
        self.window.show()
        self.window.present()

    def hold_in_background(self):
        if not self._held:
            self.hold()
            self._held = True
            n = Gio.Notification.new("Modo carregar continua ligado")
            n.set_body("Abra o DualSense Studio de novo para voltar ao modo normal.")
            self.send_notification("segundo-plano", n)


def main():
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("DualSense Studio")
    return App().run(sys.argv)
