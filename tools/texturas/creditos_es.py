"""8cb9ff30 (4096x2048) y 99c5746e (8192x4096, x2): títulos de capítulo / 'Original Story by' / etiquetas 'Ch.' en español.
Texto blanco DIN con halo blanco tenue (perfil medido). Cada línea se alinea al centro de la inglesa, misma línea base, y se
reduce para no superar el ancho máximo de la línea inglesa/francesa."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
F = 'C:/Windows/Fonts/bahnschrift.ttf'
IZQ = ["Historia original de", None, "Orgullo de asesino", None, "El vínculo roto", "El hijo del emperador", "El Rey Dragón", "Padre e hijo", "Llave a lo desconocido", "Prólogo"]
DER = ["Emperador Spriggan", "Comienza la guerra", "Batalla por Hargeon", "Cuenta atrás al inframundo", "Profundidades oscuras", "¿Dragón o demonio?",
       "El Libro de E.N.D.", "¡El campeón del «Dulce verano»!", "¡Investigando los Cuentos Dorados!"]
PEQ = {(1918, 1488): "Cap. 11", (2444, 1488): "Cap. extra 1", (1842, 1590): "Cap. extra 3", (2444, 1590): "Cap. extra 4", (3046, 1536): "Cap. extra 2", (3056, 1638): "Capítulo 16"}
CHN = [f"Cap. {i}" for i in range(1, 11)]
PERFIL = ([0, 4, 6, 8, 12, 16, 24, 32], [60, 26, 23, 19, 11, 6, 1, 0])
def lineas(a, k):
    m = (a[..., 3] > 200) & (a[..., :3].min(axis=2) > 200)
    d = ndimage.binary_dilation(m, structure=np.ones((5, int(100 * k)))); lab, n = ndimage.label(d); L = []
    for s in ndimage.find_objects(lab):
        ys, xs = np.nonzero(m[s])
        if len(ys) < 120 * k * k: continue
        L.append([s[1].start + xs.min(), s[0].start + ys.min(), s[1].start + xs.max() + 1, s[0].start + ys.max() + 1])
    return [r for r in L if (r[2] - r[0]) > 60 * k]
def clasificar(L, k):
    izq = sorted([r for r in L if r[0] < 1600 * k and r[2] < 1650 * k and r[1] < 1650 * k], key=lambda r: r[1])
    chn = sorted([r for r in L if r[0] > 3500 * k], key=lambda r: r[1])
    resto = [r for r in L if r not in izq and r not in chn]
    peq = [r for r in resto if (r[3] - r[1]) < 55 * k and r[1] > 1400 * k and r[0] < 3500 * k]
    der = sorted([r for r in resto if r not in peq and (r[3] - r[1]) > 60 * k], key=lambda r: r[1])
    return izq, der, peq, chn
def main(src, fr, dst, k):
    a = np.asarray(Image.open(src).convert('RGBA')).astype(float).copy(); orig = a.copy(); mk = (orig[..., 3] > 200) & (orig[..., :3].min(axis=2) > 200)
    Le = lineas(orig.astype(np.uint8), k); Lf = lineas(np.asarray(Image.open(fr).convert('RGBA')), k)
    izq, der, peq, chn = clasificar(Le, k); fizq, fder, fpeq, fchn = clasificar(Lf, k)
    print('izq', len(izq), 'der', len(der), 'peq', len(peq), 'chn', len(chn), '| fr', len(fizq), len(fder), len(fpeq), len(fchn))
    trabajo = []
    for L, FL, T in ((izq, fizq, IZQ), (der, fder, DER), (chn, fchn, CHN)):
        for i, r in enumerate(L):
            if i < len(T) and T[i]: trabajo.append((r, FL[i] if i < len(FL) else r, T[i]))
    for r in peq:
        key = min(PEQ, key=lambda p: abs(p[0] * k - r[0]) + abs(p[1] * k - r[1]))
        trabajo.append((r, r, PEQ[key]))
    f100 = ImageFont.truetype(F, 100); f100.set_variation_by_name('Bold'); capf = f100.getbbox('E')[3] - f100.getbbox('E')[1]
    for r, rf, txt in trabajo:
        sub = mk[r[1]:r[3], r[0]:r[0] + int(0.55 * (r[3] - r[1]))]; ys = np.nonzero(sub.any(axis=1))[0]
        cap = ys.max() - ys.min() + 1; base = r[1] + ys.max() + 1; cx = (r[0] + r[2]) / 2
        maxw = max(r[2] - r[0], rf[2] - rf[0]) * 1.03
        f = ImageFont.truetype(F, 100 * cap / capf); f.set_variation_by_name('Bold'); w = f.getlength(txt)
        if w > maxw: f = ImageFont.truetype(F, f.size * maxw / w); f.set_variation_by_name('Bold'); w = f.getlength(txt)
        mg = int(34 * k); x0 = max(0, int(min(r[0], rf[0]) - mg)); x1 = int(max(r[2], rf[2], cx + w / 2) + mg); y0 = max(0, r[1] - mg); y1 = r[3] + mg
        a[y0:y1, x0:x1] = 0
        m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).text((cx - x0 - w / 2, base - y0), txt, font=f, fill=255, anchor='ls')
        ml = np.asarray(m).astype(float) / 255; dist = ndimage.distance_transform_edt(ml < 0.5) / k
        al = np.interp(dist, *PERFIL) / 255; reg = a[y0:y1, x0:x1]
        reg[..., :3] = 255; reg[..., 3] = np.maximum(al * 255, ml * 255); a[y0:y1, x0:x1] = reg
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(dst); print(len(trabajo), 'líneas escritas')
if __name__ == '__main__': main(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]))
