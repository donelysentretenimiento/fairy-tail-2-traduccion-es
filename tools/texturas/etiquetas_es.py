"""Atlas de etiquetas del menú (06c0709d 2048x2048 y 13cbe5db/000 4096x4096): sustituye cada etiqueta inglesa por la española.
Se detectan las líneas, se borran y se escribe el texto español alineado a la izquierda en la misma línea base,
sin superar el ancho máximo de la etiqueta inglesa/francesa (las celdas del juego se dimensionan para el idioma más largo)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
F = 'C:/Windows/Fonts/georgiab.ttf'
IZQ_A06 = ["Arena de combate", "Audio", "Cambiar vestuario", "Diario de Fairy Tail", "Registro de eventos", "Magia extrema", "Detalles",
           "Objetos", "Cargar", "Recuerdos", "Vídeos", "Opciones", "Misiones", "Descansar", "Tienda", "Orígenes mágicos", "Sistema", "Enciclopedia del mundo"]
DER_A06 = ["Taller de Lucy", "Personajes", "Base de datos", "Enemigos", "Extras", "Ayuda", "Objetos", "Lácrima", "Menú principal", "Modelos",
           "Novela de Lucy", "Tienda de Plue", "Equipo de reserva", "Guardar", "Habilidades", "Personaje de apoyo", "Equipo"]
LAYOUT = {'a06': (IZQ_A06, DER_A06), 'c13': (DER_A06, IZQ_A06[1:])}   # en 13cbe5db las columnas van intercambiadas y no hay 'Arena'
def lineas(a, k):
    m = (a[..., 3] > 200) & (a[..., :3].min(axis=2) > 170)
    d = ndimage.binary_dilation(m, structure=np.ones((3, int(36 * k))))
    lab, n = ndimage.label(d); out = []
    for s in ndimage.find_objects(lab):
        ys, xs = np.nonzero(m[s])
        if len(ys) < 60: continue
        out.append([s[1].start + xs.min(), s[0].start + ys.min(), s[1].start + xs.max() + 1, s[0].start + ys.max() + 1])
    hs = [r[3] - r[1] for r in out]; mh = max(hs)
    out = [r for r in out if (r[3] - r[1]) > 0.45 * mh and (r[2] - r[0]) > 20 * k]
    xs = sorted(set(round(r[0] / (300 * k)) for r in out)); cols = {}
    for r in out: cols.setdefault(round(r[0] / (300 * k)), []).append(r)
    ks = sorted(cols); return [sorted(cols[c], key=lambda r: r[1]) for c in ks]
def main(tag, k, src, fr, dst):
    a = np.asarray(Image.open(src).convert('RGBA')).copy().astype(float); orig = a.copy()
    afr = np.asarray(Image.open(fr).convert('RGBA'))
    cols_en = lineas(orig.astype(np.uint8), k); cols_fr = lineas(afr, k)
    textos = LAYOUT[tag]
    assert len(cols_en) == 2 and [len(c) for c in cols_en] == [len(t) for t in textos], ([len(c) for c in cols_en], [len(t) for t in textos])
    for ci, (col, txts) in enumerate(zip(cols_en, textos)):
        # primera letra: alto de mayúscula y base uniforme de la columna
        caps, bots = [], []
        mk = (orig[..., 3] > 200) & (orig[..., :3].min(axis=2) > 170)
        for r in col:
            sub = mk[r[1]:r[3], r[0]:r[0] + int(0.62 * (r[3] - r[1]))]
            ys = np.nonzero(sub.any(axis=1))[0]; caps.append(ys.max() - ys.min() + 1); bots.append(r[1] + ys.max() + 1)
        cap = float(np.median(caps)); pitch = np.median(np.diff([r[1] for r in col])); b0 = np.median([b - i * pitch for i, b in enumerate(bots)])
        f0 = ImageFont.truetype(F, 100); capf = f0.getbbox('E')[3] - f0.getbbox('E')[1]; size0 = 100 * cap / capf
        for i, (r, txt) in enumerate(zip(col, txts)):
            fr_w = (cols_fr[ci][i][2] - cols_fr[ci][i][0]) if len(cols_fr) > ci and i < len(cols_fr[ci]) else 0
            maxw = max(r[2] - r[0], fr_w) * 1.02
            f = ImageFont.truetype(F, size0 * 0.95); w = f.getlength(txt)
            if w > maxw * 1.8: f = ImageFont.truetype(F, size0 * 0.95 * maxw * 1.8 / w); w = f.getlength(txt)
            mg = int(14 * k); y0 = max(0, r[1] - mg); y1 = r[3] + mg; x0 = max(0, r[0] - mg); x1 = max(r[2], int(r[0] + w)) + mg
            a[y0:y1, x0:x1] = 0
            H = y1 - y0 + 2 * mg; Wd = x1 - x0 + mg
            m = Image.new('L', (x1 - x0, y1 - y0), 0); d = ImageDraw.Draw(m)
            d.text((r[0] - x0, round(b0 + i * pitch) - y0), txt, font=f, fill=255, anchor='ls')
            ml = np.asarray(m).astype(float) / 255
            sh = ndimage.gaussian_filter(np.pad(ml, 0), sigma=3.2 * k) * 1.6; sh = np.clip(np.roll(sh, int(2 * k), axis=0), 0, 0.85)
            reg = a[y0:y1, x0:x1]
            reg[..., 3] = np.maximum(sh * 255, ml * 255)
            reg[..., :3] = 255 * ml[..., None] + 0 * (1 - ml[..., None])
            a[y0:y1, x0:x1] = reg
        print(tag, 'col', ci, len(col), 'lineas; cap', cap, 'pitch', pitch)
    if tag == 'c13':   # etiqueta 'Arena' suelta, a mitad de tamaño, en (13,2641)-(131,2672)
        r = [13, 2641, 131, 2672]; f = ImageFont.truetype(F, size0 * 0.95 / 2); txt = 'Arena de combate'; mg = 14
        x0, y0, x1, y1 = 0, r[1] - mg, r[0] + int(f.getlength(txt)) + 2 * mg, r[3] + mg
        a[y0:y1, x0:x1] = 0
        m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).text((r[0] - x0, r[3] - y0), txt, font=f, fill=255, anchor='ls')
        ml = np.asarray(m).astype(float) / 255; sh = np.clip(np.roll(ndimage.gaussian_filter(ml, sigma=4) * 1.6, 3, axis=0), 0, 0.85)
        reg = a[y0:y1, x0:x1]; reg[..., 3] = np.maximum(sh * 255, ml * 255); reg[..., :3] = 255 * ml[..., None]; a[y0:y1, x0:x1] = reg
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(dst)
if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
