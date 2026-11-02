"""Extrae como PNG las texturas localizadas aún sin traducir (según root.texture.enUS.lang) y genera una hoja de contacto.
Salida: pruebas/texturas_candidatas/<ktid>/NNN.png y hoja_<n>.png. Solo lee los FDATA ORIGINALES."""
import os, struct, subprocess, sys, zlib, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fuentes'))
from fdata_sustituir import lista_bytes
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
R = Path(__file__).resolve().parents[2]
TEXCONV = R / 'tools/externas/DirectXTex/_out/bin/texconv.exe'; GUST = R / 'tools/fuentes/gust_g1t.exe'
HECHAS = {0xb55a1a66, 0xa84ea528, 0xea7dba9c, 0xf7892fda, 0x13cbe5db, 0x06c0709d, 0x8cb9ff30, 0x99c5746e, 0x38d7494f, 0x45e2be8d}
OUT = R / 'pruebas/texturas_candidatas'


def main():
    lang = open(R / 'backups_juego/root.texture.enUS.lang.ORIGINAL', 'rb').read()
    objetivo = {struct.unpack_from('<I', lang, i * 12)[0] for i in range(len(lang) // 12)} - HECHAS
    OUT.mkdir(parents=True, exist_ok=True)
    hechas = []
    for k in sorted(objetivo):
        idh = f'{k:08x}'; src = R / f'pruebas/fuentes/enUS/fdata_out/Root/g1t/{idh}.g1t'
        if not src.exists():
            print('sin volcado', idh); continue
        d = OUT / idh; d.mkdir(exist_ok=True)
        (OUT / f'{idh}.g1t').write_bytes(src.read_bytes())   # volcado por fdata_dump (ya descomprimido)
        subprocess.run([str(GUST), str(OUT / f'{idh}.g1t')], capture_output=True, cwd=str(OUT))
        for dds in sorted(d.glob('*.dds')):
            subprocess.run([str(TEXCONV), '-nologo', '-y', '-ft', 'png', '-o', str(d), str(dds)], capture_output=True)
        hechas.append(idh)
    print('extraídas', len(hechas), hechas)
    pngs = [(i, sorted((OUT / i).glob('*.png'))) for i in hechas]
    celdas = [(i, p) for i, ps in pngs for p in ps]
    for hoja in range(0, len(celdas), 6):
        sheet = Image.new('RGB', (1500, 2 * 400), '#202020'); dr = ImageDraw.Draw(sheet)
        for j, (i, p) in enumerate(celdas[hoja:hoja + 6]):
            im = Image.open(p).convert('RGBA'); bg = Image.new('RGBA', im.size, (60, 60, 60, 255)); bg.alpha_composite(im); bg.thumbnail((480, 360))
            x, y = (j % 3) * 500 + 10, (j // 3) * 400 + 30
            sheet.paste(bg.convert('RGB'), (x, y)); dr.text((x, y - 20), f'{i}/{p.stem} {im.size}', fill='white')
        sheet.save(OUT / f'hoja_{hoja // 6 + 1}.png')
    print('hojas', (len(celdas) + 5) // 6)


main()
