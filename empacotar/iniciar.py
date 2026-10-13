import os
import sys


def desbloquear():
    base = getattr(sys, "_MEIPASS", None)
    if not base or not sys.platform.startswith("win"):
        return
    for raiz, _pastas, arquivos in os.walk(base):
        for nome in arquivos:
            if nome.lower().endswith((".dll", ".exe", ".pyd")):
                try:
                    os.remove(os.path.join(raiz, nome) + ":Zone.Identifier")
                except OSError:
                    pass


desbloquear()

from dualsense_studio.__main__ import run

sys.exit(run())
