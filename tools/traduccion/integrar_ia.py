"""Integra en el agregado los textos traducidos por la IA local (solo los válidos), normaliza caracteres sin glifo,
valida marcadores y escribe traduccion/candidato_ia/message.json (+ .e con gust_enc). Uso: integrar_ia.py"""
import json, re, sys, os, subprocess, collections
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, R + '/tools/fuentes'); import g1n_build as g
MARCA = re.compile(r"<[^>]*>|%[0-9]*[sd]")
f = g.parse(open(R + '/traduccion/fuente/e876b7f0_es.g1n', 'rb').read())
TIENE = {chr(c) for c in range(65536) if f['tab'][c] != 0} | {'\n', ' '}
SUST = {'…': '...', '—': ' - ', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '«': '"', '»': '"', 'ú': 'ú', ' ': ' ', '×': 'x', '❤': '♥', '【': '[', '】': ']', 'µ': 'u', '　': ' ', '↑': '+', '↓': '-'}  # ↑/↓ no tienen glifo en la fuente del juego
base = json.load(open(R + '/traduccion/candidato_menu/message.json', encoding='utf-8-sig'))
by = {r['NAME_LABEL']: r for r in base['message_message']}
menu = {r['NAME_LABEL'] for r in json.load(open(R + '/traduccion/candidato_menu/message.json', encoding='utf-8-sig'))['message_message']}  # todos; el menú ya está dentro
ia = {}
import glob
for fn in sorted(glob.glob(R + '/pruebas/traduccion_ia/ortenzya_*.jsonl')):
    if '--sin-menu' in sys.argv and 'menu_pendiente' in fn: continue
    for l in open(fn, encoding='utf-8'):
        r = json.loads(l)
        if r['ok']: ia[r['id']] = r['es']
omitidos = []; falt = collections.Counter(); cambiados = 0; sin_glifo = collections.Counter()
for k, es in ia.items():
    if k not in by or by[k]['MESSAGE'] != by[k].get('_en', by[k]['MESSAGE']): pass
    if k not in by: continue
    if len(by[k]['MESSAGE']) > 900 and k.startswith('STR_MENU_DEFINE'): omitidos.append(k); continue   # licencias (texto legal; una de ellas cierra el juego); los glosarios STR_LIBRARY_* largos sí arrancan (probado)   # licencias largas: la versión traducida cierra el juego (STR_MENU_DEFINE_451)
    if MARCA.findall(es) != MARCA.findall(by[k]['MESSAGE']): falt['marcadores'] += 1; continue
    t = ''.join(SUST.get(c, c) for c in es)
    for c in t:
        if c not in TIENE: sin_glifo[c] += 1
    by[k]['MESSAGE'] = t; cambiados += 1
# restos que seguían en inglés (tools/terminologia/restos_ingles.py): ID -> español; exige marcadores idénticos
_ri = R + '/traduccion/restos_ingles.json'
if os.path.exists(_ri):
    for k, v in json.load(open(_ri, encoding='utf-8')).items():
        if k in by and MARCA.findall(v) == MARCA.findall(by[k]['MESSAGE']): by[k]['MESSAGE'] = ''.join(SUST.get(c, c) for c in v)
# terminología canónica por ID (docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv); nunca reemplazos globales
_ov = R + '/traduccion/terminologia_overrides.json'
if os.path.exists(_ov):
    for k, v in json.load(open(_ov, encoding='utf-8')).items():
        if k in by and MARCA.findall(v) == MARCA.findall(by[k]['MESSAGE']): by[k]['MESSAGE'] = ''.join(SUST.get(c, c) for c in v)
# cambios de una frase concreta dentro de un mensaje (ID, viejo, nuevo): terminología en textos largos; idempotente y sin tocar marcadores
_tx = R + '/traduccion/terminologia_textos.json'
if os.path.exists(_tx):
    for k, viejo, nuevo in json.load(open(_tx, encoding='utf-8')):
        if k in by and viejo in by[k]['MESSAGE']: by[k]['MESSAGE'] = by[k]['MESSAGE'].replace(viejo, nuevo)
# correcciones manuales (máxima prioridad): etiquetas que no caben en su cuadro
for k, v in json.load(open(R + '/traduccion/correcciones.json', encoding='utf-8')).items():
    if k in by: by[k]['MESSAGE'] = v
os.makedirs(R + '/traduccion/candidato_ia', exist_ok=True)
p = R + '/traduccion/candidato_ia/message.json'
open(p, 'wb').write(b'\xef\xbb\xbf' + json.dumps(base, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
print('omitidos (>900 car.):', omitidos); print('integrados', cambiados, 'de', len(ia), '| rechazados', dict(falt), '| caracteres sin glifo', dict(sin_glifo.most_common(15)))
subprocess.run([R + '/tools/gust_tools/gust_enc.exe', '-FT', p], check=True, capture_output=True, cwd=R + '/traduccion/candidato_ia')
print('escrito', os.path.getsize(p + '.e'), 'bytes .e')
