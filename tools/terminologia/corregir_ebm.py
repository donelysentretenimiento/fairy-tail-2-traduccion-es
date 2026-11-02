"""Aplica traduccion/ebm_correcciones.json (archivo, registro, texto viejo, texto nuevo) a traduccion/ebm/*.ebm.
Idempotente; ejecutar SIEMPRE después de tools/traduccion/construir_ebm.py (que regenera esos archivos). Solo cambia el texto del registro
indicado; conserva marcadores, cabeceras y la cola del archivo. Aborta si el texto viejo no está (ni el nuevo)."""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'tools/ebm'))
import ebm


def main():
    cambios = json.load(open(RAIZ / 'traduccion/ebm_correcciones.json', encoding='utf-8'))
    por_archivo = {}
    for f, i, viejo, nuevo in cambios:
        por_archivo.setdefault(f, []).append((i, viejo, nuevo))
    hechos = ya = 0
    for f, lista in por_archivo.items():
        p = RAIZ / f'traduccion/ebm/EVENT_MESSAGE_{f}.ebm'
        d = open(p, 'rb').read()
        recs, fin = ebm.parse(d)
        cola = d[fin:]
        for i, viejo, nuevo in lista:
            t = recs[i]['texto_b'].decode('utf-8')
            if viejo in t:
                recs[i]['texto_b'] = t.replace(viejo, nuevo).encode('utf-8'); hechos += 1
            elif nuevo in t:
                ya += 1
            else:
                sys.exit(f'{f}#{i}: no aparece «{viejo}» ni «{nuevo}» en «{t[:90]}»')
        nuevo_b = ebm.build(recs, cola)
        ebm.parse(nuevo_b)  # comprobación de que sigue siendo válido
        open(p, 'wb').write(nuevo_b)
    print('correcciones aplicadas', hechos, '| ya aplicadas', ya)


main()
