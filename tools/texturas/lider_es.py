"""13cbe5db/001 (512x256): LEADER / SUPPORT -> LÍDER / APOYO (texto amarillo plano con contorno negro; iconos intactos)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from estilo import *
LINEAS = [("LÍDER", (56, 0, 275, 64), 36), ("APOYO", (78, 66, 335, 128), 36)]
def main(src, dst, k=1.0):
    img = np.asarray(Image.open(src).convert('RGBA')).astype(float).copy(); orig = img.copy()
    for txt, box, cap in LINEAS:
        box = tuple(int(v * k) for v in box); cap = cap * k
        grad, _ = perfil_relleno(orig, box); bx0, by0, bx1, by1 = bbox_texto(orig, box)
        borrar(img, box)
        f = fuente('bahnschrift.ttf', 100, 'Bold'); cm = f.getbbox('I')[3] - f.getbbox('I')[1]
        f = fuente('bahnschrift.ttf', 100 * cap / cm, 'Bold'); w = sum(f.getlength(c) for c in txt)
        dibujar(img, txt, f, grad, bx0 + w / 2, by1, outline=max(2, int(6 * k)), sombra=0.0, cap_h=cap, track=2 * k)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(dst)
main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
