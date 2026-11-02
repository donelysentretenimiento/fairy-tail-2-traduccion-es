"""Hoja de efectos de combate (dfd3bf79 2048x2048 y d2c84a3b 1024x1024): LINK ATTACK, BREAK, RESIST, WEAK, CURED, MISS, NO EFFECT, DAMAGE, NEXT,
FAIRY RANK, FAIRY RANK UP! -> español. UNISON RAID, COMBO, UnisonRaid y los dígitos se dejan (nombre conservado / sin texto).
Cajas definidas sobre 2048 (la de 1024 es la mitad). Uso: efectos_combate_es.py debug|hacer"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from estilo import perfil_relleno, bbox_texto, borrar, W
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = {'dfd': R + '/pruebas/texturas_candidatas/dfd3bf79/000.png', 'd2c': R + '/pruebas/texturas_candidatas/d2c84a3b/000.png'}
# nombre: (caja en 2048 x0,y0,x1,y1, texto español)
ETIQ = {
 'link':   ((250, 50, 1740, 390), 'ATAQUE ENLAZADO'),
 'break1': ((30, 900, 700, 1115), 'RUPTURA'),
 'break2': ((45, 1175, 690, 1360), 'RUPTURA'),
 'blur':   ((735, 880, 1478, 1145), 'RUPTURA'),
 'cured':  ((1520, 880, 1825, 985), 'CURADO'),
 'miss':   ((1555, 978, 1790, 1085), 'FALLO'),
 'noeff':  ((1478, 1080, 1885, 1175), 'SIN EFECTO'),
 'resist': ((780, 1146, 1092, 1237), 'RESISTE'),
 'weak':   ((1200, 1180, 1475, 1275), 'DÉBIL'),
 'damage': ((815, 1312, 990, 1372), 'DAÑO'),
 'next':   ((1860, 1302, 1978, 1364), 'SIG.'),
 'frank':  ((1620, 1180, 1790, 1248), None),
 'rankup': ((0, 1385, 1600, 1700), '¡RANGO DE FAIRY AUMENTADO!'),
}
PADV = 0; PADH = 0  # margen extra de la máscara (para halos)
# 1024 no es una escala exacta de 2048 en estas dos etiquetas: cajas medidas directamente (coordenadas de 1024)
CAJAS_D2C = {'frank': (812, 598, 882, 631), 'next': (938, 662, 996, 688)}
FUENTES = {'negra': 'ariblk.ttf', 'bold': 'arialbd.ttf', 'boldital': 'arialbi.ttf'}


def debug():
    for k, p in SRC.items():
        im = Image.open(p).convert('RGBA'); s = im.size[0] / 2048
        bg = Image.new('RGBA', im.size, (70, 70, 70, 255)); bg.alpha_composite(im); d = ImageDraw.Draw(bg)
        for n, (b, _) in ETIQ.items():
            d.rectangle([int(v * s) for v in b], outline=(255, 0, 255, 255), width=2); d.text((int(b[0] * s) + 3, int(b[1] * s) + 3), n, fill=(255, 255, 0, 255))
        bg.convert('RGB').save(R + f'/pruebas/texturas_candidatas/debug_{k}.png')


def mascara(txt, fuente, cap_h, max_w, shear=0.0, track=0.0):
    """Máscara 0..1 del texto con altura de mayúscula cap_h (reducida si supera max_w). Devuelve (mask, (ink_x0, ink_x1), línea base)."""
    f = ImageFont.truetype(W + FUENTES[fuente], 100); hb = f.getbbox('H'); tam = 100 * cap_h / (hb[3] - hb[1])
    for _ in range(60):
        f = ImageFont.truetype(W + FUENTES[fuente], max(6, int(round(tam)))); adv = [f.getlength(c) for c in txt]
        w = sum(adv) + track * (len(txt) - 1)
        if w <= max_w:
            break
        tam *= 0.97
    H = int(f.size * 2.2) + 2 * PADV; BL = int(f.size * 1.4) + PADV; pad = int(f.size * 0.6) + 8 + PADH
    m = Image.new('L', (int(w) + 2 * pad, H), 0); d = ImageDraw.Draw(m); x = pad
    for c, a in zip(txt, adv):
        d.text((x, BL), c, font=f, fill=255, anchor='ls'); x += a + track
    if shear:
        m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * BL, 0, 1, 0), resample=Image.BICUBIC)
    a = np.asarray(m).astype(float) / 255; xs = np.nonzero(a.max(axis=0) > 0.5)[0]
    return a, (xs.min(), xs.max()), BL


def over(reg, rgb, alpha):
    a = alpha[..., None]; oa = reg[..., 3:4] / 255; na = a + oa * (1 - a)
    reg[..., :3] = np.where(na > 0, (rgb * a + reg[..., :3] * oa * (1 - a)) / np.maximum(na, 1e-6), 0); reg[..., 3:4] = na * 255


def rotulo(img, txt, cx, base_y, cap_h, max_w, fuente='bold', shear=0.0, grad=None, color=(255, 255, 255), outline=6, ocol=(0, 0, 0),
           sombra=0.0, glow=None, track=0.0):
    """Texto centrado en cx con la línea base en base_y. grad: array (n,3) vertical; glow: (color, sigma, intensidad)."""
    m, (x0, x1), BL = mascara(txt, fuente, cap_h, max_w, shear, track)
    h, w = m.shape; ox = int(round(cx - (x0 + x1) / 2)); oy = int(round(base_y - BL))
    dist = ndimage.distance_transform_edt(m < 0.5); stroke = np.clip(outline + 0.5 - dist, 0, 1) if outline else np.zeros_like(m)
    top = BL - cap_h; ty = np.clip((np.arange(h) - top) / max(1, cap_h - 1), 0, 1)
    if grad is not None:
        gi = (ty * (len(grad) - 1)).round().astype(int); col = grad[gi][:, None, :] * np.ones((1, w, 1))
    else:
        col = np.ones((h, w, 3)) * np.array(color, float)
    H, Wd = img.shape[:2]; y0, y1 = max(0, oy), min(H, oy + h); xa, xb = max(0, ox), min(Wd, ox + w)
    sy, sx = slice(y0 - oy, y1 - oy), slice(xa - ox, xb - ox); reg = img[y0:y1, xa:xb]
    if glow:
        gc, sg, inten = glow; base = np.clip(stroke + m, 0, 1)
        g = np.clip(ndimage.gaussian_filter(base, sigma=sg) * inten, 0, 1) ** 1.3
        over(reg, np.zeros_like(reg[..., :3]) + np.array(gc, float), g[sy, sx] * 0.92)
        g2 = np.clip(ndimage.gaussian_filter(base, sigma=sg * 0.3) * 1.3, 0, 1)
        over(reg, np.zeros_like(reg[..., :3]) + np.array((255, 190, 0), float), g2[sy, sx] * 0.55)
    if sombra:
        sh = ndimage.gaussian_filter(np.clip(stroke + m, 0, 1), sigma=max(1, outline * 0.8)) * sombra
        over(reg, np.zeros_like(reg[..., :3]), sh[sy, sx])
    if outline:
        over(reg, np.zeros_like(reg[..., :3]) + np.array(ocol, float), stroke[sy, sx] * 0.97)
    over(reg, col[sy, sx], m[sy, sx]); img[y0:y1, xa:xb] = reg


def zoom_blur(a, fuerza=0.12, pasos=22):
    """Estela radial sobre una máscara 0..1 (aproxima el BREAK difuminado original)."""
    h, w = a.shape; out = np.zeros_like(a); cy, cx = h / 2, w / 2
    for i in range(pasos):
        s = 1 + fuerza * i / pasos
        out += ndimage.affine_transform(a, [1 / s, 1 / s], offset=[cy - cy / s, cx - cx / s], order=1)
    return np.clip(out / pasos * 1.9, 0, 1)


def hacer(clave):
    img = np.asarray(Image.open(SRC[clave]).convert('RGBA')).astype(float).copy(); orig = img.copy(); S = img.shape[0] / 2048
    B = {n: tuple(int(round(v * S)) for v in b) for n, (b, _) in ETIQ.items()}
    if clave == 'd2c':
        B.update(CAJAS_D2C)
    T = {n: t for n, (_, t) in ETIQ.items()}

    def med(n):
        try:
            bb = bbox_texto(orig, B[n])
        except ValueError:  # texto semitransparente (FAIRY RANK): umbral de alfa más bajo
            x0, y0, x1, y1 = B[n]; a = orig[y0:y1, x0:x1]; ys, xs = np.nonzero((a[..., 3] > 90) & (a[..., :3].max(axis=2) > 90))
            bb = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
        return bb, (bb[3] - bb[1]), (bb[0] + bb[2]) / 2

    def gr(n):
        return perfil_relleno(orig, B[n])[0]

    bb, ch, cx = med('link'); borrar(img, B['link']); global PADV, PADH; PADV = PADH = int(110 * S)
    rotulo(img, T['link'], cx, bb[3], ch, (bb[2] - bb[0]) * 1.08, 'negra', 0.2, color=(255, 255, 255), outline=max(2, int(7 * S)), ocol=(150, 100, 0),
           glow=((255, 120, 0), 20 * S, 1.7))
    PADV = PADH = 0
    bb, ch, cx = med('break1'); g = gr('break1'); borrar(img, B['break1'])
    rotulo(img, T['break1'], cx, bb[3], ch, (bb[2] - bb[0]) * 1.04, 'negra', 0.2, grad=g, outline=max(2, int(13 * S)), ocol=(16, 10, 30), sombra=0.5)
    bb, ch, cx = med('break2'); borrar(img, B['break2'])
    rotulo(img, T['break2'], cx, bb[3], ch, (bb[2] - bb[0]) * 1.04, 'negra', 0.2, color=(255, 255, 255), outline=0, sombra=0.35)
    x0, y0, x1, y1 = B['blur']; bw, bh = x1 - x0, y1 - y0
    tmp = np.zeros((bh, bw, 4)); rotulo(tmp, T['blur'], bw / 2, bh * 0.70, int(bh * 0.40), bw * 0.66, 'negra', 0.2, color=(255, 255, 255), outline=0)
    a = tmp[..., 3] / 255; v = np.clip(zoom_blur(a) * 0.9 + ndimage.gaussian_filter(a, 3 * S) * 0.6, 0, 1)
    ng = ndimage.gaussian_filter(np.random.default_rng(4).random(a.shape), 1.2 * S); v = np.clip(v * (0.85 + 0.3 * ng), 0, 1)
    img[y0:y1, x0:x1, :3] = v[..., None] * 255
    esp = {'cured': ((0, 40, 0), 7), 'miss': ((20, 20, 30), 7), 'noeff': ((20, 20, 30), 7), 'resist': ((20, 0, 40), 7), 'weak': ((40, 20, 0), 7), 'next': ((20, 40, 0), 4)}
    for n, (oc, ol) in esp.items():
        bb, ch, cx = med(n); g = gr(n); borrar(img, B[n])
        rotulo(img, T[n], cx, bb[3], ch, (bb[2] - bb[0]) * (1.12 if n in ('weak', 'resist') else 1.0), 'bold', 0.0, grad=g,
               outline=max(1, int(ol * S)), ocol=oc, sombra=0.5)
    bb, ch, cx = med('damage'); borrar(img, B['damage'])
    rotulo(img, T['damage'], cx, bb[3], ch, (bb[2] - bb[0]) * 1.0, 'boldital', 0.0, color=(255, 255, 255), outline=max(1, int(4 * S)), ocol=(0, 0, 0), sombra=0.4)
    bb, ch, cx = med('frank'); borrar(img, B['frank']); ch1 = int(ch * 0.4); xl = bb[0]
    rotulo(img, 'RANGO', xl + 40 * S, bb[1] + ch1 + 2 * S, ch1, (bb[2] - bb[0]) * 0.8, 'bold', 0.0, color=(255, 255, 255), outline=max(1, int(3 * S)), sombra=0.3)
    rotulo(img, 'FAIRY', xl + 75 * S, bb[3] - 2 * S, ch1, (bb[2] - bb[0]) * 0.8, 'bold', 0.0, color=(255, 255, 255), outline=max(1, int(3 * S)), sombra=0.3)
    bb, ch, cx = med('rankup'); borrar(img, B['rankup']); maxw = (img.shape[1] - 2 * bb[0]) * 0.97
    _, (xi0, xi1), _ = mascara(T['rankup'], 'bold', ch, maxw)
    rotulo(img, T['rankup'], bb[0] + (xi1 - xi0) / 2, bb[3], ch, maxw, 'bold', 0.0, color=(255, 255, 255), outline=0, sombra=0.9)
    out = R + f'/pruebas/tex_trabajo/efectos_{clave}_es.png'
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(out); print('guardado', out)


if __name__ == '__main__':
    if sys.argv[1] == 'debug':
        debug()
    else:
        for c in SRC:
            hacer(c)
