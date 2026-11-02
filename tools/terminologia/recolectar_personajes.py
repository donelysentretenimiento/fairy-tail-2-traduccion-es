"""Subpáginas «X/Magia y Habilidad» de la wiki ES (personajes Y enemigos): nombre español + kanji + personaje (nivel 3). Reutiliza caché y bloqueo de emparejar_es."""
import json, os, re, sys, urllib.parse
from emparejar_es import ES, RAIZ, get

SALIDA = RAIZ / 'pruebas/terminologia/wiki_personajes.json'
# '''[[Nombre]]''' (''kanji, romaji'')   |   '''Nombre''' (kanji, romaji)
PAT = re.compile(r"(?:'''\s*)?(?:\[\[(?:[^\]|]*\|)?([^\]]+)\]\]|(?<=')([^'\[\]\n]+?))\s*(?:''')?\s*\(\s*''?([^,()'\n]*[぀-ヿ一-鿿][^,()'\n]*),\s*([^)\n]*?)''?\s*\)")


def paginas():
    res, off = [], 0
    while True:
        d = get(ES, action='query', list='search', srsearch='Magia y Habilidad', srnamespace=0, srlimit=50, sroffset=off)
        lote = [x['title'] for x in d.get('query', {}).get('search', [])]
        res += [t for t in lote if t.endswith('/Magia y Habilidad')]
        if 'continue' not in d or not lote:
            return sorted(set(res))
        off = d['continue']['sroffset']


def main():
    out = {}
    pags = paginas()
    print(len(pags), 'páginas', flush=True)
    for t in pags:
        w = get(ES, action='parse', page=t, prop='wikitext').get('parse', {}).get('wikitext', {}).get('*', '')
        for m in PAT.finditer(w):
            out.setdefault(m.group(3).strip(), []).append({'es': (m.group(1) or m.group(2)).strip(), 'romaji': m.group(4).strip("' "), 'personaje': t.split('/')[0],
                                                          'url': 'https://fairytail.fandom.com/es/wiki/' + urllib.parse.quote(t.replace(' ', '_'))})
    json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('fin', len(out), 'kanji distintos', flush=True)


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
