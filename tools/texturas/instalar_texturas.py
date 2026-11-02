"""Reconstruye G1T con PNG traducidos, los inserta en los FDATA (crudos, CRC32 ok) y actualiza root.texture.enUS.lang.
Parte SIEMPRE de los originales (backups_juego/*.ORIGINAL), así es idempotente. Escribe en traduccion/texturas/.
Uso: instalar_texturas.py [--instalar]   (con --instalar copia al juego)"""
import os, sys, shutil, subprocess, struct, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fuentes'))
from fdata_sustituir import sustituir, actualizar_lang, lista_bytes
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TEXCONV = R + '/tools/externas/DirectXTex/_out/bin/texconv.exe'; GUST = R + '/tools/fuentes/gust_g1t.exe'
GAME = 'C:/Juegos/FAIRY TAIL 2/Motor'; BK = R + '/backups_juego'; OUT = R + '/traduccion/texturas'
# ktid -> {subtextura: png}
CAMBIOS = {
 0xb55a1a66: {'000': R + '/pruebas/tex_trabajo/b55_es.png'},
 0xa84ea528: {'000': R + '/pruebas/tex_trabajo/a84_es.png'},
 0xea7dba9c: {'000': R + '/pruebas/tex_trabajo/ea7_es.png'},
 0xf7892fda: {'000': R + '/pruebas/tex_trabajo/f78_es.png'},
 0x13cbe5db: {'000': R + '/pruebas/tex_trabajo/c13_es.png', '001': R + '/pruebas/tex_trabajo/ls_es.png'},
 0x06c0709d: {'000': R + '/pruebas/tex_trabajo/a06_es.png', '001': R + '/pruebas/tex_trabajo/ls06_es.png'},
 0x8cb9ff30: {'000': R + '/pruebas/tex_trabajo/cr_es.png'},
 0x99c5746e: {'000': R + '/pruebas/tex_trabajo/c99_es.png'},
 0x38d7494f: {'000': R + '/pruebas/tex_trabajo/38d_es.png'},
 0x45e2be8d: {'000': R + '/pruebas/tex_trabajo/45e_es.png'},
}
EXTRA = [R + '/pruebas/tex_trabajo/extra.json']   # opcional: más cambios {"ktid_hex": {"000": "ruta.png"}}
FDATAS = ['0a12caf9', 'b766cb46', 'cdce5e37', 'f3ab3808']

def dir_g1t(idh):
    for d in (R + f'/pruebas/fuentes/enUS/fdata_out/Root/g1t/{idh}', R + f'/pruebas/texturas_extra/enUS/{idh}', R + f'/pruebas/texturas_candidatas/{idh}'):
        if os.path.isdir(d): return d

def mips(dds):
    return struct.unpack_from('<I', open(dds, 'rb').read(32), 28)[0]

def construir_g1t(k, subs):
    idh = f'{k:08x}'; src = dir_g1t(idh); w = f'{OUT}/trabajo/{idh}'
    if os.path.isdir(w): shutil.rmtree(w)
    shutil.copytree(src, w)
    for sub, png in subs.items():
        orig = f'{src}/{sub}.dds'; m = mips(orig)
        subprocess.run([TEXCONV, '-nologo', '-y', '-f', 'BC7_UNORM', '-m', str(m), '-dx10', '-o', w, png], check=True, capture_output=True)
        os.replace(f'{w}/{os.path.splitext(os.path.basename(png))[0]}.dds', f'{w}/{sub}.dds')
    subprocess.run([GUST, w], check=True, capture_output=True)
    return open(f'{w}.g1t', 'rb').read()

def main():
    cambios = dict(CAMBIOS)
    for e in EXTRA:
        if os.path.exists(e):
            for kk, v in json.load(open(e)).items(): cambios.setdefault(int(kk, 16), {}).update(v)
    os.makedirs(OUT + '/trabajo', exist_ok=True)
    lang = open(BK + '/root.texture.enUS.lang.ORIGINAL', 'rb').read()
    for fd in FDATAS:
        orig = open(f'{BK}/0x{fd}.enUS.fdata.ORIGINAL', 'rb').read(); f = orig; todos = {}
        _, ents = lista_bytes(f); presentes = {e['name'] for e in ents}
        for k, subs in cambios.items():
            if k in presentes:
                f, recs = sustituir(f, k, construir_g1t(k, subs)); print(fd, 'sustituye', f'{k:08x}', list(subs))
                todos = recs
        if todos:
            open(f'{OUT}/0x{fd}.fdata', 'wb').write(f); lang = actualizar_lang(lang, todos)
            if '--instalar' in sys.argv: shutil.copy(f'{OUT}/0x{fd}.fdata', f'{GAME}/enUS/0x{fd}.fdata')
    open(f'{OUT}/root.texture.enUS.lang', 'wb').write(lang)
    if '--instalar' in sys.argv: shutil.copy(f'{OUT}/root.texture.enUS.lang', f'{GAME}/root.texture.enUS.lang')
main()
