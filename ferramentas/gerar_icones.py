import io
import os
import sys

import cairosvg
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SVG = os.path.join(ROOT, "dados", "com.ayrames.DualSenseStudio.svg")
OUT = os.path.join(ROOT, "empacotar", "icones")


def render(size):
    png = cairosvg.svg2png(url=SVG, output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    big = render(1024)
    big.save(os.path.join(OUT, "dualsense-studio.png"))
    big.save(os.path.join(OUT, "dualsense-studio.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                              (128, 128), (256, 256)])
    big.save(os.path.join(OUT, "dualsense-studio.icns"))
    print("ícones em", OUT)


if __name__ == "__main__":
    sys.exit(main())
