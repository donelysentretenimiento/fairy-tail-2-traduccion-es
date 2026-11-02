"""Añade 'TRADUCIDO POR DONELYS ENTRETENIMIENTO' bajo el logo FAIRY TAIL 2 (dentro de su halo), con los colores del logo:
relleno oscuro->rojo->naranja (llama), contorno dorado (215,187,29) y borde negro exterior. Uso: credito_logo.py png cx base cap contorno"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from estilo import *
TXT = 'TRADUCIDO POR DONELYS ENTRETENIMIENTO'
def main(png, cx, base, cap, ol):
    img = np.asarray(Image.open(png).convert('RGBA')).astype(float).copy()
    f = fuente('impact.ttf', 100); cm = f.getbbox('I')[3] - f.getbbox('I')[1]; f = fuente('impact.ttf', 100 * cap / cm)
    grad = np.array([[45, 5, 5], [150, 20, 10], [235, 90, 15], [255, 150, 30]], float)
    grad = np.stack([np.interp(np.linspace(0, 1, 64), np.linspace(0, 1, 4), grad[:, c]) for c in range(3)], axis=1)
    dibujar(img, TXT, f, grad, cx, base, outline=ol + max(1, ol // 2), cap_h=cap, track=cap * 0.06, ocol=(0, 0, 0))       # borde exterior negro
    dibujar(img, TXT, f, grad, cx, base, outline=ol, cap_h=cap, track=cap * 0.06, ocol=(215, 187, 29))                   # contorno dorado + relleno
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(png)
if __name__ == '__main__': main(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]))
