"""Traduce la insignia 'NEW' (naranja) de los títulos a 'NUEVO' sobre el PNG ya generado. Uso: insignia_es.py png caja(x0,y0,x1,y1 del texto NEW) escala"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from estilo import *
def main(png, box, k):
    img = np.asarray(Image.open(png).convert('RGBA')).astype(float).copy(); x0, y0, x1, y1 = box
    ring = img[y0 - int(6 * k):y1 + int(6 * k), x0 - int(14 * k):x0 - int(6 * k)]
    fondo = np.median(ring.reshape(-1, 4), axis=0); print('fondo', fondo)   # naranja liso de la insignia
    m = 4 * k
    xa, ya, xb, yb = int(x0 - m), int(y0 - m), int(x1 + m), int(y1 + m)
    img[ya:yb, xa:xb] = fondo
    f = fuente('bahnschrift.ttf', 100, 'Bold'); cm = f.getbbox('I')[3] - f.getbbox('I')[1]
    cap = (y1 - y0) * 1.0; f = fuente('bahnschrift.ttf', 100 * cap / cm, 'Bold')
    w = sum(f.getlength(c) for c in 'NUEVO'); ancho = (x1 - x0) * 1.12
    if w > ancho: f = fuente('bahnschrift.ttf', f.size * ancho / w, 'Bold')
    grad = np.array([[255, 240, 215], [255, 232, 190]], float)
    dibujar(img, 'NUEVO', f, grad, (x0 + x1) / 2, y1, outline=max(1, int(2 * k)), sombra=0.0, cap_h=cap, ocol=(225, 120, 0))
    # contorno naranja oscuro en lugar de negro: se recolorea el borde
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(png)
if __name__ == '__main__': main(sys.argv[1], [int(v) for v in sys.argv[2].split(',')], float(sys.argv[3]))
