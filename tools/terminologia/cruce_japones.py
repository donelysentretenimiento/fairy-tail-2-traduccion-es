"""Cruce por ID usando el japonés del propio juego (MASTER/JPN message.json) contra el campo Kanji de las fichas ES.
Identidad = kanji idéntico; el inglés solo sirve de comprobación secundaria. Escribe pruebas/terminologia/cruce_jp.json."""
import csv, difflib, json, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
T = RAIZ / 'pruebas/terminologia'
NOMBRES = ('STR_ACTION_NAME', 'STR_TEAMSKILL_NAME', 'STR_SKILL_TREE_ORIGIN_NAME')


def kn(s):
    """Normaliza kanji: sin espacios ni marcadores de nivel (＋ + ++ números finales) ni etiquetas."""
    s = re.sub(r'<RB>(.*?)<>.*?<RE>', r'\1', s)  # ruby del juego: nos quedamos con la base
    s = re.sub(r'<[^>]*>', '', s)
    s = re.sub(r"[\s　']", '', s)  # espacios y comillas de cursiva de la wiki
    s = re.sub(r'(Ultra|Max|EX)$', '', s)
    return re.sub(r'([＋+]+|[0-9０-９]+)$', '', s)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def cargar(p):
    return {e['NAME_LABEL']: e['MESSAGE'] for e in json.load(open(p, encoding='utf-8-sig'))['message_message']}


def main():
    jp = cargar(T / 'jpn/message.json')
    en = cargar(RAIZ / 'pruebas/gust_enc/06_decode_message/message.json')
    es = cargar(RAIZ / 'traduccion/candidato_ia/message.json')
    idx = json.load(open(T / 'wiki_es_hechizos.json', encoding='utf-8'))
    pers = json.load(open(T / 'wiki_personajes.json', encoding='utf-8'))
    por_kanji = {}
    for t, f in idx.items():
        if f['kanji'] and '/' not in t and '(' not in t:
            por_kanji.setdefault(kn(f['kanji']), []).append((t, f))
    manuales = json.load(open(Path(__file__).with_name('fichas_manuales.json'), encoding='utf-8'))  # fichas fuera de la plantilla Hechizos, con fuente
    for kj, m in manuales.items():
        por_kanji.setdefault(kn(kj), []).append((m['titulo'], {'url': m['url'], 'ingles': m['ingles'], 'romaji': m['romaji']}))
    out = {}
    for k, v in jp.items():
        pref = re.sub(r'_\d+$', '', k)
        if pref not in NOMBRES:
            continue
        j = kn(v)
        r = {'jp': v, 'jp_base': j, 'en': en.get(k, ''), 'es_actual': es.get(k, ''), 'fichas': [], 'estado': 'sin_japones' if not j else 'sin_ficha'}
        if j:
            cand = por_kanji.get(j, [])
            r['fichas'] = [{'titulo': t, 'url': f['url'], 'ingles': f['ingles'], 'romaji': f['romaji']} for t, f in cand]
            if len(cand) == 1:
                r['estado'] = 'ficha_unica'
            elif len(cand) > 1:
                r['estado'] = 'ficha_ambigua'
            r['personajes'] = sorted({x['personaje'] for x in pers.get(j, [])})
        out[k] = r
    json.dump(out, open(T / 'cruce_jp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import collections
    print(collections.Counter(r['estado'] for r in out.values()))


main()
