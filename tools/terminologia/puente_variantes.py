"""Para los nombres aún en inglés: prueba variantes (Thunder->Lightning, Dragon->Dragon's...) en la wiki EN SOLO para obtener el kanji.
El nombre español sale luego del índice de la wiki ES (wiki_es_hechizos.json) por kanji exacto. Caché y bloqueo compartidos."""
import csv, difflib, json, os, re, sys
from emparejar_es import EN, RAIZ, campo, get

T = RAIZ / 'pruebas/terminologia'
SALIDA = T / 'wiki_puente2.json'
SINON = [('Thunder', 'Lightning'), ('Heavenward', "Heaven's"), ('Iron', 'Steel')]


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def variantes(n):
    n = re.sub(r'\s*(Ultra|Max|EX)$', '', n).strip()
    vs = {n}
    for a, b in SINON:
        vs |= {v.replace(a, b) for v in list(vs)}
    for v in list(vs):
        vs.add(re.sub(r'\b(Dragon|Devil|God|Demon|Giant) ', r"\1's ", v, count=1))
        vs.add(re.sub(r'\b(Dragon|Devil|God|Demon|Giant) ', r"\1's ", v.replace('-', ' '), count=1))
    return sorted(vs)


def main():
    pend = {re.sub(r'\s*(\+{1,2}|\d+)$', '', x['Inglés'].strip()) for x in csv.DictReader(open(RAIZ / 'docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv', encoding='utf-8-sig'))
            if x['Decisión'].startswith('Pendiente')}
    out = json.load(open(SALIDA, encoding='utf-8')) if SALIDA.exists() else {}
    for i, n in enumerate(sorted(pend), 1):
        if n in out:
            continue
        mejor = None
        for v in variantes(n):
            for h in get(EN, action='query', list='search', srsearch=v, srlimit=3, srnamespace=0).get('query', {}).get('search', []):
                s = difflib.SequenceMatcher(None, norm(v), norm(h['title'])).ratio()
                if s >= 0.88 and (not mejor or s > mejor[0]):
                    mejor = (s, h['title'], v)
        reg = {'titulo_en': '', 'kanji': '', 'variante': '', 'score': 0}
        if mejor:
            w = get(EN, action='parse', page=mejor[1], prop='wikitext').get('parse', {}).get('wikitext', {}).get('*', '')
            reg = {'titulo_en': mejor[1], 'kanji': campo(w, 'kanji'), 'variante': mejor[2], 'score': round(mejor[0], 3)}
        out[n] = reg
        if i % 20 == 0:
            json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(i, flush=True)
    json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('fin', len(out), 'con kanji', sum(1 for v in out.values() if v['kanji']), flush=True)


if __name__ == '__main__':
    bloqueo = RAIZ / 'pruebas/terminologia/recolector.lock'
    try:
        os.close(os.open(bloqueo, os.O_CREAT | os.O_EXCL))
    except FileExistsError:
        sys.exit('Ya hay un recolector activo.')
    try:
        main()
    finally:
        bloqueo.unlink(missing_ok=True)
