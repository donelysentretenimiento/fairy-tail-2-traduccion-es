"""Indexa TODAS las fichas de la wiki ES que usan la plantilla Hechizos: título ES, Kanji, Romaji, Ingles. Sin pasar por la wiki inglesa."""
import json, os, sys, urllib.parse
from emparejar_es import ES, RAIZ, campo, get

SALIDA = RAIZ / 'pruebas/terminologia/wiki_es_hechizos.json'


def titulos():
    res, cont = [], {}
    while True:
        d = get(ES, action='query', list='embeddedin', eititle='Plantilla:Hechizos', eilimit=500, **cont)
        res += [x['title'] for x in d.get('query', {}).get('embeddedin', [])]
        if 'continue' not in d:
            return res
        cont = {'eicontinue': d['continue']['eicontinue']}


def main():
    out = {}
    ts = titulos()
    print(len(ts), 'fichas', flush=True)
    for i, t in enumerate(ts, 1):
        pw = get(ES, action='parse', page=t, prop='wikitext').get('parse', {}).get('wikitext', {}).get('*', '')
        out[t] = {'kanji': campo(pw, 'Kanji'), 'romaji': campo(pw, 'Romaji'), 'ingles': campo(pw, 'Ingles'),
                  'url': 'https://fairytail.fandom.com/es/wiki/' + urllib.parse.quote(t.replace(' ', '_'))}
        if i % 100 == 0:
            json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(i, flush=True)
    json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('fin', len(out), flush=True)


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
