"""38d7494f (1024x512) y 45e2be8d (2048x1024, misma maqueta x2): resultados de mejora en español."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from estilo import *

# (texto_es, caja del texto original en la textura 1024x512, altura de mayúscula original, contorno, peso/fuente)
LINEAS = [
 ("Mejora fallida...", (85, 28, 670, 92),   40, 5),
 ("Éxito",             (205, 130, 540, 205), 53, 6),
 ("Gran éxito",        (145, 235, 605, 315), 52, 6),
 ("¡Éxito total!",     (80, 345, 670, 430),  53, 6),
]

def base_y(img, box, capw):
    x0, y0, x1, y1 = box; bx0, by0, bx1, by1 = bbox_texto(img, box)
    sub = img[by0:by1, bx0:bx0 + max(8, int(capw * 0.7))]
    m = (sub[..., 3] > 200) & (sub[..., :3].max(axis=2) > 90)
    return by0 + np.nonzero(m.any(axis=1))[0].max() + 1

def main(src, dst, k):
    img = np.asarray(Image.open(src).convert('RGBA')).astype(float).copy()
    orig = img.copy()
    for txt, box, cap, ol in LINEAS:
        b = tuple(int(v * k) for v in box)
        grad, _ = perfil_relleno(orig, b)
        bx0, by0, bx1, by1 = bbox_texto(orig, b); cx = (bx0 + bx1) / 2; by = base_y(orig, b, cap * k)
        borrar(img, tuple(v for v in (b[0] - 6, b[1] - 6, b[2] + 6, b[3] + 6)))
        f = fuente('seguibl.ttf', 100); capmed = f.getbbox('E')[3] - f.getbbox('E')[1]
        tam = 100 * cap * k / capmed
        f = fuente('seguibl.ttf', tam)
        w = sum(f.getlength(c) for c in txt)
        if w > (bx1 - bx0) * 1.12: f = fuente('seguibl.ttf', tam * (bx1 - bx0) * 1.12 / w)
        dibujar(img, txt, f, grad, cx, by, outline=int(ol * k), sombra=0.6, cap_h=cap * k)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
