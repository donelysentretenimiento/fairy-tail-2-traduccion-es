"""Texto estilizado (degradado + contorno negro + sombra) para sustituir rótulos de texturas del juego."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
W = 'C:/Windows/Fonts/'

def fuente(nombre, tam, variacion=None):
    f = ImageFont.truetype(W + nombre, int(tam))
    if variacion: f.set_variation_by_name(variacion)
    return f

def perfil_relleno(img, box, n=64):
    """Degradado vertical del texto original: color medio por fila de los píxeles de relleno (opacos, no negros)."""
    x0, y0, x1, y1 = box; a = img[y0:y1, x0:x1].astype(float)
    fill = (a[..., 3] > 240) & (a[..., :3].max(axis=2) > 90)
    ys = np.nonzero(fill.any(axis=1))[0]; top, bot = ys.min(), ys.max()
    rows = []
    for y in range(top, bot + 1):
        m = fill[y]
        rows.append(a[y][m][:, :3].mean(axis=0) if m.any() else rows[-1])
    rows = np.array(rows); t = np.linspace(0, 1, len(rows)); tt = np.linspace(0, 1, n)
    return np.stack([np.interp(tt, t, rows[:, c]) for c in range(3)], axis=1), (top, bot)

def bbox_texto(img, box):
    x0, y0, x1, y1 = box; a = img[y0:y1, x0:x1]
    m = (a[..., 3] > 200) & (a[..., :3].max(axis=2) > 90)
    ys, xs = np.nonzero(m); return x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1

def dibujar(img, texto, fnt, grad, centro_x, base_y, outline=6, sombra=0.0, track=0.0, relleno_blanco=False, cap_h=None, ocol=(0, 0, 0)):
    """Compone `texto` sobre img (RGBA float) centrado en centro_x con la base en base_y."""
    adv = [fnt.getlength(c) for c in texto]; w = int(sum(adv) + track * (len(texto) - 1)) + 4 * outline + 8
    h = int(fnt.size * 2) + 4 * outline
    BL = int(fnt.size * 1.2)  # fila de la línea base dentro de la máscara
    mask = Image.new('L', (w, h), 0); d = ImageDraw.Draw(mask); x = 2 * outline + 4
    for c, a in zip(texto, adv): d.text((x, BL), c, font=fnt, fill=255, anchor='ls'); x += a + track
    m = np.asarray(mask).astype(float) / 255
    ink = np.nonzero(m.max(axis=1) > 0.5)[0]; inx = np.nonzero(m.max(axis=0) > 0.5)[0]
    bot = BL; top = BL - (cap_h if cap_h else (BL - ink.min()))
    # contorno
    dist = ndimage.distance_transform_edt(m < 0.5)
    stroke = np.clip(outline + 0.5 - dist, 0, 1)
    shadow = ndimage.gaussian_filter(stroke, sigma=max(1, outline * 0.8)) * sombra
    # degradado vertical sobre la altura de tinta
    ty = np.clip((np.arange(h) - top) / max(1, bot - top - 1), 0, 1)
    gi = (ty * (len(grad) - 1)).round().astype(int)
    col = grad[gi][:, None, :] * np.ones((1, w, 1))
    if relleno_blanco: col = np.ones((h, w, 3)) * 245
    ox = int(round(centro_x - (inx.min() + inx.max()) / 2)); oy = int(round(base_y - BL))
    H, Wd = img.shape[:2]
    y0, y1 = max(0, oy), min(H, oy + h); x0, x1 = max(0, ox), min(Wd, ox + w)
    sy, sx = slice(y0 - oy, y1 - oy), slice(x0 - ox, x1 - ox)
    reg = img[y0:y1, x0:x1]
    # sombra → contorno → relleno (composición "over")
    def over(reg, rgb, alpha):
        a = alpha[..., None]; oa = reg[..., 3:4] / 255
        na = a + oa * (1 - a)
        reg[..., :3] = np.where(na > 0, (rgb * a + reg[..., :3] * oa * (1 - a)) / np.maximum(na, 1e-6), 0)
        reg[..., 3:4] = na * 255
    if sombra: over(reg, np.zeros_like(reg[..., :3]), shadow[sy, sx])
    over(reg, np.zeros_like(reg[..., :3]) + np.array(ocol, float), stroke[sy, sx] * 0.97)
    over(reg, col[sy, sx], m[sy, sx])
    img[y0:y1, x0:x1] = reg

def borrar(img, box):
    x0, y0, x1, y1 = box; img[y0:y1, x0:x1] = 0

def rellenar_cinta(img, box, izq, der):
    """Rellena `box` (texto sobre fondo liso) interpolando horizontalmente entre las columnas izq y der, por fila."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        a = img[y, izq].astype(float); b = img[y, der].astype(float)
        t = np.linspace(0, 1, x1 - x0)[:, None]
        img[y, x0:x1] = (a * (1 - t) + b * t)
