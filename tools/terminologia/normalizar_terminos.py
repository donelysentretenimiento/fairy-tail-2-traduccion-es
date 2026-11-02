"""Unifica términos de combate repetidos en muchos mensajes, SOLO en IDs cuyo inglés contiene el término (nunca global ciego).
Genera traduccion/terminologia_textos.json = [[ID, viejo, nuevo], ...], aplicado por tools/traduccion/integrar_ia.py.
Formas fijadas: Link Attack -> «Ataque enlazado»; Fairy Rank -> «Rango de Fairy»; Break (sustantivo) -> «Ruptura» (se deja «romper» verbo)."""
import json, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def cargar(p):
    return {e['NAME_LABEL']: e['MESSAGE'] for e in json.load(open(p, encoding='utf-8-sig'))['message_message']}


def mayus(modelo, nuevo):
    return nuevo.upper() if modelo.isupper() else (nuevo[0].upper() + nuevo[1:] if modelo[0].isupper() else nuevo)


REGLAS = [  # (patrón en el inglés, patrón en el español actual, forma nueva en minúsculas)
    (r'link attack', r'ataques? (?:combinados?|en cadena|de enlace|encadenados?|vinculados?|enlazados?)',
     lambda m: ('ataques enlazados' if m.group(0).lower().startswith('ataques') else 'ataque enlazado')),
    (r'fairy rank', r'rango (?:de hada|de fairy tail|fairy|de fairy)(?!\s*tail)', lambda m: 'rango de Fairy'),
    (r'\bbreak\b', r'\brotura\b', lambda m: 'ruptura'),
]
FIJOS = [  # las 3 cadenas con «Bane» ya acordadas
    ["STR_FIELDMAP_TWEET_MAIN02_019", "Partículas de Bane", "Partículas Bane"],
    ["STR_FIELDMAP_TWEET_MAIN01_078", "Partículas de Plaga", "Partículas Bane"],
    ["STR_EVENT_TITLE_NAME_066", "Partículas de Bane", "Partículas Bane"],
]


def main():
    en = cargar(RAIZ / 'pruebas/gust_enc/06_decode_message/message.json')
    es = cargar(RAIZ / 'pruebas/terminologia/antes/message.json')  # base sin overrides: el resultado no depende de ejecuciones previas
    out = list(FIJOS); n = 0
    for k, v in en.items():
        if k.startswith(('STR_ACTION_NAME', 'STR_TEAMSKILL_NAME', 'STR_SKILL_TREE_ORIGIN_NAME')):
            continue  # los nombres de técnica van por glosario.py
        for pen, pes, f in REGLAS:
            if not re.search(pen, v, re.I):
                continue
            for m in re.finditer(pes, es[k], re.I):
                nuevo = mayus(m.group(0), f(m))
                if nuevo != m.group(0):
                    out.append([k, m.group(0), nuevo]); n += 1
    # quitar duplicados exactos conservando orden
    vistos, final = set(), []
    for x in out:
        t = tuple(x)
        if t not in vistos:
            vistos.add(t); final.append(x)
    json.dump(final, open(RAIZ / 'traduccion/terminologia_textos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('entradas', len(final), '(', n, 'de normalización)')


main()
