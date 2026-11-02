"""Pasada 2: wiki EN (kanji/rōmaji/capítulo) -> busca el kanji en la wiki ES y verifica que la ficha ES lo trae en su campo kanji=."""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / 'pruebas/terminologia/wiki_cache.json'
SALIDA = RAIZ / 'pruebas/terminologia/wiki_es.json'
EN = 'https://fairytail.fandom.com/api.php'
ES = 'https://fairytail.fandom.com/es/api.php'
RUBY = re.compile(r'\{\{[Rr]uby\|([^|}]*)\|[^}]*\}\}')


CACHE = RAIZ / 'pruebas/terminologia/http_cache'
CACHE.mkdir(parents=True, exist_ok=True)


def get(base, **p):
    """Cada respuesta válida se guarda en disco: una petición ya hecha nunca se repite."""
    p['format'] = 'json'
    url = base + '?' + urllib.parse.urlencode(p)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + '.json')
    if f.exists():
        return json.load(open(f, encoding='utf-8'))
    r = urllib.request.Request(url, headers={'User-Agent': 'FT2-ES-terminologia/1.0'})
    for i in range(6):
        try:
            time.sleep(0.7)
            d = json.load(urllib.request.urlopen(r, timeout=30))
            json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
            return d
        except Exception:
            time.sleep(10 * (i + 1))
    return {}


def campo(w, n):
    m = re.search(r'\|\s*' + n + r'\s*=\s*([^\n]*)', w, re.I)
    if not m:
        return ''
    return re.split(r'\||<', RUBY.sub(r'\1', m.group(1)))[0].strip()


def kanji_es(pw):
    return campo(pw, 'kanji')


def main():
    cache = json.load(open(ENTRADA, encoding='utf-8'))
    out = json.load(open(SALIDA, encoding='utf-8')) if SALIDA.exists() else {}
    n = 0
    for nombre, v in cache.items():
        if nombre in out or not v['en_wiki'] or v['score'] < 0.8:
            continue
        w = get(EN, action='parse', page=v['en_wiki'], prop='wikitext').get('parse', {}).get('wikitext', {}).get('*', '')
        kanji, romaji = campo(w, 'kanji'), campo(w, r'r[oō]maji')
        caps = sorted(set(re.findall(r'Chapter (\d+)', w)), key=int)[:3]
        reg = {'en_wiki': v['en_wiki'], 'kanji': kanji, 'romaji': romaji, 'capitulos': caps, 'es_titulo': '', 'verificado_kanji': False, 'url_es': ''}
        if kanji:
            for t in [x['title'] for x in get(ES, action='query', list='search', srsearch=kanji, srlimit=4).get('query', {}).get('search', [])]:
                if '/' in t:
                    continue
                pw = get(ES, action='parse', page=t, prop='wikitext').get('parse', {}).get('wikitext', {}).get('*', '')
                if kanji_es(pw) == kanji:
                    reg.update(es_titulo=t, verificado_kanji=True, es_campo_ingles=campo(pw, 'Ingles'), es_campo_espanol=campo(pw, 'Espa[nñ]ol'), url_es='https://fairytail.fandom.com/es/wiki/' + urllib.parse.quote(t.replace(' ', '_')))
                    break
        out[nombre] = reg
        n += 1
        if n % 20 == 0:
            json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(n, flush=True)
    json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('fin', len(out), flush=True)


if __name__ == '__main__':
    bloqueo = RAIZ / 'pruebas/terminologia/recolector.lock'
    try:
        os.close(os.open(bloqueo, os.O_CREAT | os.O_EXCL))  # un único recolector a la vez
    except FileExistsError:
        sys.exit('Ya hay un recolector activo (borra recolector.lock si no es cierto).')
    try:
        main()
    finally:
        bloqueo.unlink(missing_ok=True)
