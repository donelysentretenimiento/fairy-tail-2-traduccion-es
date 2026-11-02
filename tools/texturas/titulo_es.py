"""Traduce las etiquetas del menú de título (b55a1a66 4096x2048 y a84ea528 2048x2048) a español.
Borra cada etiqueta inglesa y dibuja la española con Bahnschrift (estilo DIN del original), con el mismo brillo:
resplandor naranja (opción seleccionada) o sombra negra (normal). Uso: titulo_es.py in.png out.png [--k 1|0.5]"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
FONT = r'C:\Windows\Fonts\bahnschrift.ttf'
PESO = 'SemiBold'
# perfil medido del original: alfa del resplandor según la distancia (px) al trazo
PERFIL = {'o': ([0, 4, 6, 8, 10, 14, 18, 26, 34], [150, 118, 107, 94, 79, 55, 37, 15, 0]),
          'w': ([0, 4, 6, 8, 10, 12, 14, 18], [240, 230, 219, 136, 55, 20, 5, 0])}
# (texto_es, estilo, caja a limpiar [x0,y0,x1,y1] en la textura de 4096x2048)
ITEMS = [
 ("CONTINUAR",        "o", (2830, 900, 3440, 1015)),
 ("SALIR DEL JUEGO",  "o", (2790, 1045, 3480, 1165)),
 ("IMPORTAR DATOS",   "o", (20, 1115, 1000, 1245)),
 ("LICENCIA",         "o", (1280, 1115, 1700, 1245)),
 ("OPCIONES",         "o", (290, 1275, 720, 1390)),
 ("CARGAR PARTIDA",   "o", (2090, 1190, 2920, 1305)),
 ("NUEVA PARTIDA",    "o", (3150, 1190, 3860, 1305)),
 ("CONTINUAR",        "w", (2270, 1505, 2740, 1580)),
 ("SALIR DEL JUEGO",  "w", (3190, 1505, 3830, 1580)),
 ("IMPORTAR DATOS",   "w", (40, 1575, 960, 1662)),
 ("LICENCIA",         "w", (1290, 1575, 1680, 1662)),
 ("CARGAR PARTIDA",   "w", (2110, 1650, 2890, 1725)),
 ("NUEVA PARTIDA",    "w", (3170, 1650, 3840, 1725)),
 ("OPCIONES",         "w", (320, 1738, 680, 1805)),
 ("PULSA UN BOTÓN",   "o", (2740, 30, 3530, 125)),
]
# Maqueta de 2048x2048 (a84ea528): cajas en píxeles propios (k=1 con estas coordenadas), cap 22 px
def _b(cx, y0, y1, w): return (cx - w // 2 - 30, max(0, y0 - 30), cx + w // 2 + 30, y1 + 30)
ITEMS_A84 = [
 ("CONTINUAR", "o", _b(250, 690, 712, 152)), ("SALIR DEL JUEGO", "o", _b(752, 690, 712, 165)),
 ("IMPORTAR DATOS", "o", _b(1254, 690, 712, 290)), ("LICENCIA", "o", _b(1757, 690, 712, 126)),
 ("CARGAR PARTIDA", "o", _b(250, 764, 786, 174)), ("NUEVA PARTIDA", "o", _b(752, 764, 786, 162)),
 ("OPCIONES", "o", _b(1254, 764, 786, 130)),
 ("CONTINUAR", "w", _b(250, 912, 934, 152)), ("SALIR DEL JUEGO", "w", _b(752, 912, 934, 165)),
 ("IMPORTAR DATOS", "w", _b(1254, 912, 934, 290)), ("LICENCIA", "w", _b(1757, 912, 934, 126)),
 ("CARGAR PARTIDA", "w", _b(250, 986, 1008, 174)), ("NUEVA PARTIDA", "w", _b(752, 986, 1008, 162)),
 ("OPCIONES", "w", _b(1254, 986, 1008, 130)),
 ("PULSA UN BOTÓN", "o", _b(1567, 26, 50, 335)), ("PULSA UN BOTÓN", "o", _b(1567, 104, 128, 335)),
]
CAL_A84 = _b(1254, 912, 934, 290)

def font_for_cap(H):
    f = ImageFont.truetype(FONT, 100); f.set_variation_by_name(PESO)
    cap = f.getbbox('I')[3] - f.getbbox('I')[1]
    s = round(100 * H / cap)
    f = ImageFont.truetype(FONT, s); f.set_variation_by_name(PESO); return f
def draw_text(txt, f, track):
    w = int(sum(f.getlength(c) for c in txt) + track * len(txt)) + 8
    m = Image.new('L', (w, f.size * 2), 0); d = ImageDraw.Draw(m); x = 4
    for c in txt: d.text((x, f.size // 2), c, font=f, fill=255); x += f.getlength(c) + track
    return np.asarray(m)
def main(src, dst, k):
    im = np.asarray(Image.open(src).convert('RGBA')).copy().astype(float)
    base = im.copy()
    bright = (base[..., :3].min(axis=2) > 190) & (base[..., 3] > 200)
    # calibración con IMPORT SAVE DATA blanco (referencia de tamaño y tracking)
    a84 = '--a84' in sys.argv
    items = ITEMS_A84 if a84 else ITEMS; kk = 1.0 if a84 else k
    x0, y0, x1, y1 = CAL_A84 if a84 else [round(v * k) for v in (40, 1575, 960, 1662)]
    ys, xs = np.nonzero(bright[y0:y1, x0:x1]); H = ys.max() - ys.min() + 1; W = xs.max() - xs.min() + 1
    f = font_for_cap(H); n = len("IMPORT SAVE DATA")
    adv = sum(f.getlength(c) for c in "IMPORT SAVE DATA"); track = (W - adv) / (n - 1)
    out = im.copy()
    k = 0.5 if a84 else k
    for txt, st, box in items:
        x0, y0, x1, y1 = [round(v * kk) for v in box]
        ys, xs = np.nonzero(bright[y0:y1, x0:x1])
        if len(ys) == 0: print('sin texto en', txt, box); continue
        cx = x0 + (xs.min() + xs.max()) / 2; bot = y0 + ys.max() + 1
        # colores medidos del original
        txtcol = base[y0:y1, x0:x1][bright[y0:y1, x0:x1]][:, :3].mean(axis=0)
        ring = ndimage.binary_dilation(bright[y0:y1, x0:x1], iterations=int(10 * k)) & ~ndimage.binary_dilation(bright[y0:y1, x0:x1], iterations=int(3 * k)) & (base[y0:y1, x0:x1, 3] > 40)
        glowcol = base[y0:y1, x0:x1][ring][:, :3].mean(axis=0) if ring.any() else np.array([200, 80, 30.])
        mask = draw_text(txt, f, track).astype(float) / 255
        mh, mw = mask.shape
        ink = np.nonzero(mask.max(axis=1) > 0.5)[0]; ink_x = np.nonzero(mask.max(axis=0) > 0.5)[0]
        top = ink.min(); bottom = ink.max() + 1; lx = (ink_x.min() + ink_x.max()) / 2
        ox = int(round(cx - lx)); oy = int(round(bot - bottom))
        layer = np.zeros((out.shape[0], out.shape[1]))
        yy0 = max(0, oy); yy1 = min(out.shape[0], oy + mh); xx0 = max(0, ox); xx1 = min(out.shape[1], ox + mw)
        layer[yy0:yy1, xx0:xx1] = mask[yy0 - oy:yy1 - oy, xx0 - ox:xx1 - ox]
        mg = int(36 * k)
        sx0 = max(0, min(x0, ox + ink_x.min() - mg)); sx1 = max(x1, ox + ink_x.max() + 1 + mg)
        sy0 = max(0, min(y0, oy + top - mg)); sy1 = max(y1, oy + bottom + mg)
        out[sy0:sy1, sx0:sx1] = 0
        sub = (slice(sy0, sy1), slice(sx0, sx1))
        L = layer[sub]
        dist = ndimage.distance_transform_edt(L < 0.5) / k
        px, py = PERFIL[st]
        galpha = np.interp(dist, px, py) / 255
        gcol = glowcol if st == 'o' else np.array([0., 0., 0.])
        region = out[sub]
        region[..., :3] = gcol; region[..., 3] = galpha * 255
        ta = L[..., None]; region[..., :3] = region[..., :3] * (1 - ta) + txtcol * ta
        region[..., 3] = np.maximum(region[..., 3], L * 255)
        out[sub] = region
        print(f"{txt:16s} {st} cap={H} cx={cx:.0f} base={bot} ancho={(ink_x.max()-ink_x.min()):d}")
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA').save(dst)
if __name__ == '__main__':
    k = float(sys.argv[sys.argv.index('--k') + 1]) if '--k' in sys.argv else 1.0
    main(sys.argv[1], sys.argv[2], k)
