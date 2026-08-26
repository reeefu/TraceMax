#!/usr/bin/env python3
"""Generate icon files from newlogo.png for PyInstaller builds.

Creates:
  - src/assets/tracemax.ico  (Windows: multi-size ICO)
  - src/assets/tracemax.png  (Linux: 256x256 PNG)
"""

from PIL import Image
import os

SRC_IMG = os.path.join('src', 'assets', 'newlogo.png')
OUT_ICO = os.path.join('src', 'assets', 'tracemax.ico')
OUT_PNG = os.path.join('src', 'assets', 'tracemax.png')

img = Image.open(SRC_IMG).convert('RGBA')

# Windows ICO: embed multiple sizes
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_images = [img.resize(s, Image.LANCZOS) for s in sizes]
ico_images[0].save(OUT_ICO, format='ICO', sizes=sizes, append_images=ico_images[1:])
print(f'Created {OUT_ICO}')

# Linux PNG: 256x256
img.resize((256, 256), Image.LANCZOS).save(OUT_PNG, format='PNG')
print(f'Created {OUT_PNG}')
