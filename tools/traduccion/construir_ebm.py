"""Construye los EBM traducidos a partir de un JSONL (solo líneas ok) y, con --instalar, los copia al juego (respaldo en backups_juego/ebm).
Uso: construir_ebm.py JSONL [--archivos MS01_120,...] [--instalar]"""
import json, os, sys, glob, shutil, re
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, R + '/tools/ebm'); sys.path.insert(0, R + '/tools/fuentes'); import ebm, g1n_build as g
SRC = r'C:\Juegos\FAIRY TAIL 2\MASTER\ENG\EventMessageData'; OUT = R + '/traduccion/ebm'; BK = R + '/backups_juego/ebm'
f = g.parse(open(R + '/traduccion/fuente/e876b7f0_es.g1n', 'rb').read()); TIENE = {chr(c) for c in range(65536) if f['tab'][c]} | {' '}
SUST = {'…': '...', '“': '"', '”': '"', '‘': "'", '’': "'", '«': '"', '»': '"', '\u00a0': ' ', '―': '—', '–': '-'}
def limpiar(t, falt):
    t = ''.join(SUST.get(c, c) for c in t)
    for c in t:
        if c not in TIENE: falt[c] = falt.get(c, 0) + 1
    return t
def main():
    jsonl = sys.argv[1]; solo = sys.argv[sys.argv.index('--archivos') + 1].split(',') if '--archivos' in sys.argv else None
    tr = {}
    for l in open(jsonl, encoding='utf-8'):
        r = json.loads(l)
        if r['ok'] and r['es']: tr[r['id']] = r['es']
    os.makedirs(OUT, exist_ok=True); os.makedirs(BK, exist_ok=True); falt = {}; n_arch = n_lin = 0
    for p in sorted(glob.glob(SRC + '/*.ebm')):
        nombre = os.path.basename(p)[len('EVENT_MESSAGE_'):-4]
        if solo and nombre not in solo: continue
        d = open(BK + '/' + os.path.basename(p), 'rb').read() if os.path.exists(BK + '/' + os.path.basename(p)) else open(p, 'rb').read()
        recs, end = ebm.parse(d); cola = d[end:]; cambios = 0
        for i, r in enumerate(recs):
            es = tr.get(f'{nombre}#{i}')
            if es and r['texto_b']:
                r['texto_b'] = limpiar(es, falt).encode('utf-8'); cambios += 1
        if not cambios: continue
        nuevo = ebm.build(recs, cola); open(OUT + '/' + os.path.basename(p), 'wb').write(nuevo); n_arch += 1; n_lin += cambios
        if '--instalar' in sys.argv:
            if not os.path.exists(BK + '/' + os.path.basename(p)): shutil.copy(p, BK + '/' + os.path.basename(p))
            shutil.copy(OUT + '/' + os.path.basename(p), p)
    print(f'{n_arch} archivos, {n_lin} líneas traducidas; caracteres sin glifo: {falt}')
main()
