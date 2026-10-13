from dualsense_painel import audio, charge_light, profiles
from dualsense_painel.protocol import MODES_BY_KEY

LOW_BATTERY = (0, 10, 15, 20, 25, 30)
IDLE_OFF = (0, 5, 10, 15, 30)
STATUS = {"Charging": "charging", "Discharging": "discharging", "Full": "full", "Not charging": "discharging"}


def _int(value, low, high, default):
    try:
        return max(low, min(high, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _color(value, default):
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return [_int(c, 0, 255, 0) for c in value]
    return list(default)


class Bridge:
    def __init__(self, session, emit, save_report=None, audio_backend=audio):
        self.session = session
        self.cfg = session.cfg
        self.emit = emit
        self.save_report = save_report
        self.audio = audio_backend
        self.mic = None
        self.audio_available = False

    def snapshot(self):
        s = self.session
        c = self.cfg
        return {
            "type": "state",
            "connected": s.connected,
            "model": s.model or "DualSense",
            "connection": s.connection,
            "canDisconnect": s.pode_desligar_bluetooth,
            "battery": {"percent": s.battery_pct, "status": STATUS.get(s.battery_status)},
            "charging": s.charging_mode,
            "audio": {"available": self.audio_available and s.connection == "usb"},
            "settings": {
                "color": list(c["color"]),
                "intensity": c["intensity"],
                "playerLeds": c["player_leds"],
                "ledBrightness": c["led_brightness"],
                "micLed": c["mic_led"],
                "autoCharge": c["auto_charge"],
                "lightbarMode": c["lightbar_mode"],
                "shortcut": c["shortcut"],
                "lowBattery": c["low_battery"],
                "idleOff": c["idle_off"],
                "profiles": profiles.summary(c),
                "chargeGlow": c["charge_glow"],
                "chargeLight": {
                    "color": list(c["charge_color"]),
                    "style": c["charge_style"],
                    "period": c["charge_period"],
                    "intensity": c["charge_intensity"],
                    "full": c["charge_full"],
                },
                "triggers": {side: {"mode": t["mode"], "params": {**MODES_BY_KEY[t["mode"]].defaults(),
                                                                    **t.get("params", {})}}
                             for side, t in c["triggers"].items()},
            },
        }

    def publish(self):
        self.emit(self.snapshot())

    def publish_input(self, data):
        if not data:
            return
        self.emit({
            "type": "input",
            "sticks": data["sticks"],
            "triggers": data["triggers"],
            "buttons": data["buttons"],
            "touch": data["touch"],
            "gyro": data["gyro"],
            "accel": data["accel"],
            "headphones": data["headphones"],
            "hz": self.session.report_hz,
        })

    def publish_info(self):
        info = self.session.info or {}
        self.emit({"type": "info", **{k: info.get(k) for k in
                                      ("model", "connection", "firmware", "hardware", "update", "build", "mac",
                                       "serial", "board", "color", "colorPt", "colorHex", "colorCode")}})

    def publish_history(self):
        h = self.session.history
        self.emit({"type": "history", "points": h.as_list(), "estimate": h.estimate()})

    def refresh_audio(self, publish=True):
        try:
            devices = self.audio.find_devices()
        except Exception:
            devices = {}
        available = bool(devices.get("sink"))
        if available != self.audio_available:
            self.audio_available = available
            if publish:
                self.publish()

    def stop_mic(self):
        if self.mic:
            self.mic.stop()
            self.mic = None

    def handle(self, message):
        if not isinstance(message, dict):
            return
        kind = message.get("type")
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        handler = getattr(self, "_cmd_" + str(kind), None)
        if handler:
            handler(payload)

    def _changed(self):
        self.session.settings_changed()
        self.publish()

    def _cmd_ready(self, _p):
        self.refresh_audio(publish=False)
        self.publish()
        self.publish_info()
        self.publish_history()

    def _cmd_setLightbar(self, p):
        if "color" in p:
            self.cfg["color"] = _color(p["color"], self.cfg["color"])
        if "intensity" in p:
            self.cfg["intensity"] = _int(p["intensity"], 0, 100, self.cfg["intensity"])
        self._changed()

    def _cmd_setPlayerLeds(self, p):
        if "mask" in p:
            self.cfg["player_leds"] = _int(p["mask"], 0, 31, self.cfg["player_leds"])
        if "brightness" in p:
            self.cfg["led_brightness"] = _int(p["brightness"], 0, 2, self.cfg["led_brightness"])
        self._changed()

    def _cmd_setMicLed(self, p):
        self.cfg["mic_led"] = _int(p.get("mode"), 0, 2, self.cfg["mic_led"])
        self._changed()

    def _cmd_setTrigger(self, p):
        side = p.get("side")
        mode = MODES_BY_KEY.get(p.get("mode"))
        if side not in ("l2", "r2") or not mode:
            return
        raw = p.get("params") if isinstance(p.get("params"), dict) else {}
        params = {}
        for spec in mode.params:
            params[spec.key] = _int(raw.get(spec.key, spec.default), spec.low, spec.high, spec.default)
        self.cfg["triggers"][side] = {"mode": mode.key, "params": params}
        self._changed()

    def _cmd_testRumble(self, _p):
        self.session.test_rumble()

    def _cmd_rumble(self, p):
        self.session.rumble(_int(p.get("left"), 0, 255, 0), _int(p.get("right"), 0, 255, 0),
                            _int(p.get("ms"), 50, 5000, 500))

    def _cmd_setLightbarMode(self, p):
        if p.get("mode") in ("fixed", "battery"):
            self.cfg["lightbar_mode"] = p["mode"]
            self._changed()

    def _cmd_setShortcut(self, p):
        self.cfg["shortcut"] = bool(p.get("on"))
        self._changed()

    def _cmd_setLowBattery(self, p):
        value = _int(p.get("threshold"), 0, 30, self.cfg["low_battery"])
        self.cfg["low_battery"] = min(LOW_BATTERY, key=lambda v: abs(v - value))
        self._changed()

    def _cmd_setIdleOff(self, p):
        value = _int(p.get("minutes"), 0, 30, self.cfg["idle_off"])
        self.cfg["idle_off"] = min(IDLE_OFF, key=lambda v: abs(v - value))
        self._changed()

    def _cmd_disconnectBluetooth(self, _p):
        self.session.disconnect_bluetooth()

    def _cmd_saveProfile(self, p):
        name = profiles.save(self.cfg, p.get("name"))
        if name:
            self._changed()
            self.emit({"type": "toast", "text": f"Perfil \"{name}\" salvo"})
        else:
            self.emit({"type": "toast", "text": "Não deu para salvar o perfil"})

    def _cmd_applyProfile(self, p):
        if profiles.apply(self.cfg, p.get("name")):
            self._changed()
            self.emit({"type": "toast", "text": f"Perfil \"{p.get('name')}\" aplicado"})

    def _cmd_deleteProfile(self, p):
        if profiles.delete(self.cfg, p.get("name")):
            self._changed()

    def _cmd_audioTone(self, p):
        target = p.get("target")
        if target not in (self.audio.SPEAKER, self.audio.HEADPHONES):
            return
        if not self.audio.play_tone(target):
            self.emit({"type": "toast", "text": "Áudio do controle não encontrado. Ele precisa estar no cabo USB."})

    def _cmd_micStart(self, _p):
        if self.mic:
            return
        self.mic = self.audio.MicMeter(lambda level: self.emit({"type": "micLevel", "level": round(level, 3)}))
        if not self.mic.start():
            self.mic = None
            self.emit({"type": "toast", "text": "Microfone do controle não encontrado"})

    def _cmd_micStop(self, _p):
        self.stop_mic()

    def _cmd_saveReport(self, p):
        content = p.get("content")
        if not isinstance(content, str) or not content.strip() or not self.save_report:
            return
        name = str(p.get("filename") or "relatorio-dualsense.md")
        self.save_report(name, content)

    def _cmd_requestInfo(self, _p):
        self.publish_info()

    def _cmd_requestHistory(self, _p):
        self.publish_history()

    def _cmd_setCharging(self, p):
        self.session.set_charging(bool(p.get("on")), announce=False)
        self.publish()

    def _cmd_setChargeGlow(self, p):
        self.cfg["charge_glow"] = bool(p.get("on"))
        self._changed()

    def _cmd_setAutoCharge(self, p):
        self.cfg["auto_charge"] = bool(p.get("on"))
        self._changed()

    def _cmd_setChargeLight(self, p):
        c = self.cfg
        if "color" in p:
            c["charge_color"] = _color(p["color"], c["charge_color"])
        if p.get("style") in charge_light.STYLES:
            c["charge_style"] = p["style"]
        if "period" in p:
            try:
                c["charge_period"] = max(1.0, min(10.0, round(float(p["period"]) * 2) / 2))
            except (TypeError, ValueError):
                pass
        if "intensity" in p:
            c["charge_intensity"] = _int(p["intensity"], 5, 100, c["charge_intensity"])
        if p.get("full") in charge_light.FULL_ACTIONS:
            c["charge_full"] = p["full"]
        if "glow" in p:
            c["charge_glow"] = bool(p["glow"])
        self._changed()
