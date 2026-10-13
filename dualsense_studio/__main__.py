import os
import sys

from dualsense_painel import plataforma


def run():
    if plataforma.LINUX and os.environ.get("DS_STUDIO_HOST") != "web":
        from .app import main
    else:
        from .web import main
    return main()


if __name__ == "__main__":
    sys.exit(run())
