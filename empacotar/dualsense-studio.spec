import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
PAINEL = os.environ.get("DUALSENSE_PAINEL") or os.path.join(ROOT, "..", "dualsense-painel")
ICON = os.path.join(ROOT, "empacotar", "icones", "dualsense-studio.ico" if sys.platform.startswith("win") else "dualsense-studio.icns")

a = Analysis(
    [os.path.join(ROOT, "empacotar", "iniciar.py")],
    pathex=[ROOT, PAINEL],
    datas=[(os.path.join(ROOT, "ui", f), "ui") for f in ("index.html", "index-foto.html", "dualsense-base.png",
                                                          "dualsense-lightbar.png")
           if os.path.exists(os.path.join(ROOT, "ui", f))],
    hiddenimports=["dualsense_studio.web", "dualsense_painel.backends.hidapi_backend",
                   "dualsense_painel.backends.hidhide", "dualsense_painel.audio_portable", "hid"],
    excludes=([] if sys.platform.startswith("linux") else ["gi"]) + ["dualsense_studio.app", "dualsense_painel.app",
                                                                    "dualsense_painel.telas", "pkg_resources",
                                                                    "setuptools"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="DualSense Studio", console=False,
          icon=ICON if os.path.exists(ICON) else None)
coll = COLLECT(exe, a.binaries, a.datas, name="DualSense Studio")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="DualSense Studio.app", icon=ICON if os.path.exists(ICON) else None,
                 bundle_identifier="com.ayrames.DualSenseStudio",
                 info_plist={"NSHighResolutionCapable": True,
                             "NSMicrophoneUsageDescription": "Medir o microfone do controle no teste de áudio."})
