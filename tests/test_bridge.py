import unittest

from dualsense_painel import config
from dualsense_studio.bridge import Bridge


class FakeHistory:
    def as_list(self):
        return [[1000, 50, "Charging"]]

    def estimate(self):
        return {"kind": "full", "minutes": 30}


class FakeAudio:
    SPEAKER = "speaker"
    HEADPHONES = "headphones"

    def __init__(self):
        self.played = []

    def find_devices(self):
        return {"sink": "dualsense-sink", "source": "dualsense-mic"}

    def play_tone(self, target):
        self.played.append(target)
        return True


class FakeSession:
    def __init__(self):
        self.info = {"model": "DualSense", "firmware": "0x0110002a", "mac": "AB:CD:EF:12:34:56"}
        self.history = FakeHistory()
        self.report_hz = 250
        self.cfg = config.load("/nonexistent/config.json")
        self.connected = True
        self.model = "DualSense"
        self.connection = "usb"
        self.pode_desligar_bluetooth = True
        self.battery_pct = 40
        self.battery_status = "Charging"
        self.charging_mode = False
        self.calls = []

    def settings_changed(self):
        self.calls.append("changed")

    def set_charging(self, on, announce=True):
        self.charging_mode = on
        self.calls.append(("charging", on))

    def test_rumble(self):
        self.calls.append("rumble")

    def rumble(self, left, right, ms):
        self.calls.append(("rumble", left, right, ms))

    def disconnect_bluetooth(self):
        self.calls.append("disconnect")


class Base(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.sent = []
        self.saved = []
        self.audio = FakeAudio()
        self.bridge = Bridge(self.session, self.sent.append,
                             save_report=lambda n, c: self.saved.append((n, c)), audio_backend=self.audio)



class BridgeTest(Base):
    def test_ready_publishes_full_snapshot(self):
        self.bridge.handle({"type": "ready"})
        state = self.sent[0]
        self.assertEqual(state["type"], "state")
        self.assertEqual(state["battery"], {"percent": 40, "status": "charging"})
        self.assertEqual(state["settings"]["chargeLight"]["style"], "breathe")
        self.assertEqual(state["settings"]["triggers"]["l2"]["mode"], "off")

    def test_lightbar_is_clamped(self):
        self.bridge.handle({"type": "setLightbar", "payload": {"color": [300, -5, 10.6], "intensity": 140}})
        self.assertEqual(self.session.cfg["color"], [255, 0, 11])
        self.assertEqual(self.session.cfg["intensity"], 100)
        self.assertIn("changed", self.session.calls)

    def test_trigger_params_are_validated(self):
        self.bridge.handle({"type": "setTrigger", "payload": {
            "side": "r2", "mode": "weapon", "params": {"start": 99, "strength": "x"}}})
        self.assertEqual(self.session.cfg["triggers"]["r2"],
                         {"mode": "weapon", "params": {"start": 7, "end": 6, "strength": 8}})

    def test_unknown_trigger_mode_is_ignored(self):
        before = dict(self.session.cfg["triggers"]["l2"])
        self.bridge.handle({"type": "setTrigger", "payload": {"side": "l2", "mode": "laser"}})
        self.assertEqual(self.session.cfg["triggers"]["l2"], before)

    def test_charge_light_partial_update(self):
        self.bridge.handle({"type": "setChargeLight", "payload": {"period": 7.3, "style": "blink",
                                                                  "full": "green", "color": [0, 0, 255]}})
        c = self.session.cfg
        self.assertEqual((c["charge_period"], c["charge_style"], c["charge_full"], c["charge_color"]),
                         (7.5, "blink", "green", [0, 0, 255]))

    def test_charging_and_rumble(self):
        self.bridge.handle({"type": "setCharging", "payload": {"on": True}})
        self.bridge.handle({"type": "testRumble"})
        self.assertEqual(self.session.calls, [("charging", True), "rumble"])
        self.assertTrue(self.sent[-1]["charging"])

    def test_garbage_is_ignored(self):
        for msg in (None, "x", {"type": "nada"}, {"type": "setMicLed", "payload": "x"}):
            self.bridge.handle(msg)


class NewCommandsTest(Base):
    def test_ready_sends_info_history_and_audio(self):
        self.bridge.handle({"type": "ready"})
        kinds = [m["type"] for m in self.sent]
        self.assertEqual(kinds, ["state", "info", "history"])
        self.assertTrue(self.sent[0]["audio"]["available"])
        self.assertEqual(self.sent[1]["firmware"], "0x0110002a")
        self.assertEqual(self.sent[2]["estimate"]["minutes"], 30)

    def test_settings_snap_to_allowed_values(self):
        self.bridge.handle({"type": "setLowBattery", "payload": {"threshold": 17}})
        self.bridge.handle({"type": "setIdleOff", "payload": {"minutes": 12}})
        self.bridge.handle({"type": "setLightbarMode", "payload": {"mode": "battery"}})
        self.bridge.handle({"type": "setShortcut", "payload": {"on": False}})
        c = self.session.cfg
        self.assertEqual((c["low_battery"], c["idle_off"], c["lightbar_mode"], c["shortcut"]),
                         (15, 10, "battery", False))

    def test_profiles_roundtrip(self):
        self.bridge.handle({"type": "setLightbar", "payload": {"color": [1, 2, 3]}})
        self.bridge.handle({"type": "saveProfile", "payload": {"name": "FPS"}})
        self.bridge.handle({"type": "setLightbar", "payload": {"color": [9, 9, 9]}})
        self.bridge.handle({"type": "applyProfile", "payload": {"name": "FPS"}})
        self.assertEqual(self.session.cfg["color"], [1, 2, 3])
        state = [m for m in self.sent if m["type"] == "state"][-1]
        self.assertEqual(state["settings"]["profiles"][0]["name"], "FPS")
        self.bridge.handle({"type": "deleteProfile", "payload": {"name": "FPS"}})
        self.assertEqual(self.session.cfg["profiles"], {})

    def test_rumble_audio_report(self):
        self.bridge.handle({"type": "rumble", "payload": {"left": 300, "right": 10, "ms": 99999}})
        self.bridge.handle({"type": "audioTone", "payload": {"target": "speaker"}})
        self.bridge.handle({"type": "audioTone", "payload": {"target": "lua"}})
        self.bridge.handle({"type": "saveReport", "payload": {"filename": "r.md", "content": "# ok"}})
        self.bridge.handle({"type": "saveReport", "payload": {"content": "   "}})
        self.assertIn(("rumble", 255, 10, 5000), self.session.calls)
        self.assertEqual(self.audio.played, ["speaker"])
        self.assertEqual(self.saved, [("r.md", "# ok")])

    def test_input_message_shape(self):
        data = {"sticks": {"lx": 1, "ly": 2, "rx": 3, "ry": 4}, "triggers": {"l2": 5, "r2": 6},
                "buttons": {"cross": True}, "touch": [], "gyro": [0, 0, 0], "accel": [0, 1, 0],
                "headphones": False, "battery": (50, "Charging"), "timestamp": 1}
        self.bridge.publish_input(data)
        msg = self.sent[-1]
        self.assertEqual(msg["type"], "input")
        self.assertEqual(msg["hz"], 250)
        self.assertNotIn("battery", msg)


if __name__ == "__main__":
    unittest.main()
