"""Audita los nombres de técnicas citados en los diálogos EBM: ¿la línea española usa el nombre definitivo del glosario?
Entrada: backups_juego/ebm (originales EN), traduccion/ebm (ES), docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv. Salida: docs/AUDITORIA_EBM_TECNICAS.csv (solo lectura de los EBM)."""
import csv, glob, os, re, sys, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'tools/ebm'))
import ebm

PRE = re.compile(r'^(Ultra |Max |EX )')


def base(s):
    s = PRE.sub('', re.sub(r'<[^>]*>', '', s).strip())
    return re.sub(r'\s*(\+{1,2}|\d+)$', '', s).strip()


def nrm(s):
    """minúsculas, sin tildes ni puntuación, sin posesivos: para comparar nombres."""
    s = re.sub(r"['’]s\b", '', re.sub(r'<[^>]*>', ' ', s))
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' ' + re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9]+", ' ', s)).strip() + ' '


def main():
    filas = list(csv.DictReader(open(RAIZ / 'docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv', encoding='utf-8-sig')))
    nombres = {}  # clave EN normalizada -> (EN, ES definitivo base, estado)
    for f in filas:
        en = base(f['Inglés'])
        if not en or len(en.split()) < 2 and len(en) < 9:
            continue
        if len(en.split()) < 2 and not re.search(r'[A-Z][a-z]+[a-z]', en):
            continue
        es = base(f['Español definitivo'])
        k = nrm(en)
        if len(k.strip()) >= 8 and k not in nombres and f['Estado'] != 'SIN TEXTO':
            nombres[k] = (en, es, f['Estado'])
    claves = sorted(nombres, key=len, reverse=True)
    pat = re.compile('|'.join(re.escape(k.strip()) for k in claves))
    out, tot, hits = [], 0, 0
    for p in sorted(glob.glob(str(RAIZ / 'traduccion/ebm/*.ebm'))):
        n = os.path.basename(p)
        ro, _ = ebm.parse(open(RAIZ / 'backups_juego/ebm' / n, 'rb').read())
        rt, _ = ebm.parse(open(p, 'rb').read())
        for i, (a, b) in enumerate(zip(ro, rt)):
            tot += 1
            en = a['texto_b'].decode('utf-8', 'replace'); es = b['texto_b'].decode('utf-8', 'replace')
            ne = nrm(en)
            visto = set()
            for m in pat.finditer(ne):
                k = ' ' + m.group(0) + ' '
                if k not in nombres or k in visto or not (ne[m.start() - 1:m.start()] == ' ' or m.start() == 0):
                    continue
                visto.add(k)
                en_n, es_n, est = nombres[k]
                ok = nrm(es_n) in nrm(es)
                hits += 1
                out.append([n, i, a['A'], a['B'], en_n, es_n, 'USA_EL_NOMBRE' if ok else 'DISTINTO', est, re.sub(r'\s+', ' ', en)[:160], re.sub(r'\s+', ' ', es)[:160]])
    with open(RAIZ / 'docs/AUDITORIA_EBM_TECNICAS.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Archivo', 'Registro', 'Voz', 'Nombre', 'Técnica EN', 'Español definitivo', 'Resultado', 'Estado glosario', 'Línea EN', 'Línea ES'])
        w.writerows(out)
    import collections
    print('registros', tot, '| menciones', hits, '|', dict(collections.Counter(x[6] for x in out)))


main()
