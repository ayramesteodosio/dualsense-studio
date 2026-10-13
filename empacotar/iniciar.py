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


def registro():
    if sys.stdout is not None and sys.stderr is not None:
        return
    from dualsense_painel import plataforma
    pasta = plataforma.data_dir()
    os.makedirs(pasta, exist_ok=True)
    arquivo = open(os.path.join(pasta, "registro-studio.txt"), "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or arquivo
    sys.stderr = sys.stderr or arquivo


registro()
desbloquear()

from dualsense_studio.__main__ import run

sys.exit(run())
