"""Busca cada nombre inglés de técnica en la wiki inglesa de Fairy Tail y obtiene el enlace de idioma (langlinks) a la wiki española.
Resultado: pruebas/terminologia/wiki_cache.json  {nombre_ingles_limpio: {...}}  — trazable por URL. Solo lectura de la API pública de MediaWiki."""
import json, re, sys, time, urllib.request, urllib.parse, difflib, os
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = R + '/pruebas/terminologia/wiki_cache.json'
def api(base, **p):
    p['format'] = 'json'; u = base + '?' + urllib.parse.urlencode(p)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'FT2ES-terminologia/1.0 (traduccion no comercial)'}), timeout=30) as x: return json.loads(x.read())
        except Exception as e: time.sleep(1.5)
    return {}
def norm(s): return re.sub(r"[^a-z0-9 ]", '', re.sub(r"'s\b", 's', s.lower())).strip()
def limpiar(n):
    n = re.sub(r'\s*\+$', '', n.strip()); n = re.sub(r'\s*(Ultra|Max|EX|Ex)\s*$', '', n).strip(); n = re.sub(r'\s*\d+$', '', n).strip(); return n
def main():
    src = {r['NAME_LABEL']: r['MESSAGE'] for r in json.load(open(R + '/pruebas/gust_enc/06_decode_message/message.json', encoding='utf-8-sig'))['message_message']}
    nombres = sorted({limpiar(v) for k, v in src.items() if re.match(r'STR_(ACTION_NAME|TEAMSKILL_NAME|SKILL_TREE_ORIGIN_NAME|MIX_DEFINE)', k) and v.strip() and not re.match(r'(Normal Attack|Unison Raid$)', limpiar(v))})
    cache = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    print(len(nombres), 'nombres únicos limpios;', len(cache), 'ya en caché', flush=True)
    for i, n in enumerate(nombres):
        if n in cache: continue
        q = api('https://fairytail.fandom.com/api.php', action='query', list='search', srsearch=n, srlimit=6, srnamespace=0)
        cand = [h['title'] for h in q.get('query', {}).get('search', [])]
        best = max(cand, key=lambda t: difflib.SequenceMatcher(None, norm(t), norm(n)).ratio(), default=None)
        score = difflib.SequenceMatcher(None, norm(best), norm(n)).ratio() if best else 0
        es = None
        if best and score >= 0.8:
            l = api('https://fairytail.fandom.com/api.php', action='query', prop='langlinks', titles=best, lllang='es', lllimit=5)
            for pg in l.get('query', {}).get('pages', {}).values():
                for ll in pg.get('langlinks', []): es = ll.get('*') or ll.get('title')
        cache[n] = dict(en_wiki=best, score=round(score, 3), es_wiki=es, url_en=('https://fairytail.fandom.com/wiki/' + urllib.parse.quote(best.replace(' ', '_'))) if best else None,
                        url_es=('https://fairytail.fandom.com/es/wiki/' + urllib.parse.quote(es.replace(' ', '_'))) if es else None, candidatos=cand[:4])
        if i % 25 == 0: json.dump(cache, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(i, '/', len(nombres), flush=True)
        time.sleep(0.25)
    json.dump(cache, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print('fin', len(cache))
main()
