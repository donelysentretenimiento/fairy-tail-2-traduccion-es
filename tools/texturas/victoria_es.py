"""ea7dba9c (512x256) y f7892fda (1024x256): VICTORY! / New Record -> ¡VICTORIA! / Nuevo récord."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from PIL import Image
from estilo import *
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# (caja título, cap título, outline título, caja cinta, cap cinta, outline cinta)
CFG = {
 'ea7': ((95, 3, 420, 78), 53, 4, (48, 82, 252, 128), 22, 3),
 'f78': ((185, 8, 830, 150), 100, 8, (48, 160, 252, 210), 22, 3),
}
def blanco(img, box):
    x0, y0, x1, y1 = box; a = img[y0:y1, x0:x1]; m = (a[..., :3].min(axis=2) > 200) & (a[..., 3] > 240)
    ys, xs = np.nonzero(m); return x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1, m
def main(nombre, src, dst):
    tb, tcap, tol, cb, ccap, col = CFG[nombre]
    img = np.asarray(Image.open(src).convert('RGBA')).astype(float).copy(); orig = img.copy()
    # --- título
    grad, _ = perfil_relleno(orig, tb); bx0, by0, bx1, by1 = bbox_texto(orig, tb)
    base = by1 - 1
    # la base real es el borde inferior de la 'V' (primera letra): sin descendentes en VICTORY!
    borrar(img, tb)
    f = fuente('bahnschrift.ttf', 100, 'Bold'); cm = f.getbbox('I')[3] - f.getbbox('I')[1]
    tam = 100 * tcap / cm; f = fuente('bahnschrift.ttf', tam, 'Bold')
    txt = '¡VICTORIA!'; w = sum(f.getlength(c) for c in txt)
    if w > (bx1 - bx0) * 1.1: f = fuente('bahnschrift.ttf', tam * (bx1 - bx0) * 1.1 / w, 'Bold')
    dibujar(img, txt, f, grad, (bx0 + bx1) / 2, by1, outline=tol, sombra=0.7, cap_h=tcap)
    # --- cinta: borrar texto antiguo por inpainting y dibujar el nuevo
    x0, y0, x1, y1 = cb; wx0, wy0, wx1, wy1, wm = blanco(orig, cb)
    sub = orig[y0:y1, x0:x1]
    m = wm.astype(np.uint8)
    # el contorno negro del texto: píxeles muy oscuros dentro del cuadro del texto, junto al blanco
    dark = (sub[..., :3].max(axis=2) < 70) & (sub[..., 3] > 200)
    near = cv2.dilate(m, np.ones((2 * col + 3, 2 * col + 3), np.uint8)) > 0
    # sólo la parte del contorno que rodea el texto (zona del texto ampliada), no el borde oscuro de la cinta
    box = np.zeros_like(m); box[max(0, wy0 - y0 - col - 2):wy1 - y0 + col + 2, max(0, wx0 - x0 - col - 2):wx1 - x0 + col + 2] = 1
    mask = ((m > 0) | (dark & near)) & (box > 0)
    mask = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
    rgba = np.clip(sub, 0, 255).astype(np.uint8)
    inp = cv2.inpaint(rgba[..., :3], mask, 4, cv2.INPAINT_TELEA)
    ainp = cv2.inpaint(rgba[..., 3], mask, 4, cv2.INPAINT_TELEA)
    ainp = np.where((mask > 0) & (ainp < 110), 0, ainp); inp[(mask > 0) & (ainp == 0)] = 0   # restos semitransparentes sobre el fondo
    img[y0:y1, x0:x1, :3] = inp; img[y0:y1, x0:x1, 3] = ainp
    f = fuente('bahnschrift.ttf', 100, 'Bold'); cm = f.getbbox('I')[3] - f.getbbox('I')[1]
    tam = 100 * ccap / cm; txt = 'Nuevo récord'; f = fuente('bahnschrift.ttf', tam, 'Bold')
    w = sum(f.getlength(c) for c in txt); ancho = (wx1 - wx0) * 1.06
    if w > ancho: f = fuente('bahnschrift.ttf', tam * ancho / w, 'Bold')
    dibujar(img, txt, f, np.array([[255, 255, 255], [235, 235, 240], [190, 190, 200]], float), (wx0 + wx1) / 2, wy1, outline=col, sombra=0.5, cap_h=ccap)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(dst)
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
