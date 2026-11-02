"""Localización PROPIA (marcada como tal) de los nombres de técnica sin ficha en la wiki ES. Salida independiente: pruebas/terminologia/localizacion_propia.jsonl
(no toca ningún JSONL de Ortenzya). Usa el japonés del juego y pares ya documentados como ejemplos."""
import csv, json, re, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
T = RAIZ / 'pruebas/terminologia'
SALIDA = T / 'localizacion_propia.jsonl'
MODELO = 'hf.co/llmfan46/gemma-4-Ortenzya-The-Creative-Wordsmith-31B-it-uncensored-heretic-GGUF:Q4_K_M'
PRE = re.compile(r'^(Ultra |Max |EX )')


def base(en):
    s = re.sub(r'<[^>]*>', '', en).strip()
    s = PRE.sub('', s)
    return re.sub(r'\s*(\+{1,2}|\d+)$', '', s).strip()


def llamar(sistema, usuario):
    cuerpo = {'model': MODELO, 'stream': False, 'think': False, 'format': 'json', 'options': {'temperature': 0.2, 'num_ctx': 8192},
              'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}]}
    r = urllib.request.Request('http://localhost:11434/api/chat', json.dumps(cuerpo).encode(), {'Content-Type': 'application/json'})
    return json.loads(json.load(urllib.request.urlopen(r, timeout=900))['message']['content'])


def main():
    filas = list(csv.DictReader(open(RAIZ / 'docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv', encoding='utf-8-sig')))
    ejemplos = {}
    for f in filas:
        if f['Estado'] == 'DOCUMENTADO POR LA COMUNIDAD' and not re.search(r'[+＋]', f['Inglés']):
            ejemplos[f['Inglés']] = f['Español definitivo']
    ej = '\n'.join(f'- {en} → {es}' for en, es in list(ejemplos.items())[:45])
    pend = {}
    for f in filas:
        if f['Estado'] == 'PENDIENTE DE IDENTIFICACIÓN' and base(f['Inglés']):
            pend.setdefault(base(f['Inglés']), f['Japonés (juego)'])
    hechos = set()
    if SALIDA.exists():
        hechos = {json.loads(l)['en'] for l in open(SALIDA, encoding='utf-8')}
    cola = [(en, jp) for en, jp in sorted(pend.items()) if en not in hechos]
    print(len(pend), 'únicos;', len(cola), 'por hacer', flush=True)
    sistema = ('Eres traductor de FAIRY TAIL al español de España. Traduces NOMBRES DE TÉCNICAS de un videojuego. Reglas: '
               '1) Sigue el patrón de la wiki española: «Rugido del Dragón de Fuego», «Puño de Hierro del Dragón del Rayo», «Espada del Dragón de Acero». '
               '2) Conserva tal cual los nombres propios o técnicos que la serie mantiene en inglés/francés/latín (Ice Make, Satan Soul, Urano Metria, Etoile Fleuve, Regulus, Take Over, Unison Raid, Dragon Slayer, Lucy Kick). '
               '3) No inventes lore; si el nombre es una palabra común, tradúcela de forma natural y breve. 4) Usa el japonés como referencia de significado. '
               '5) Conserva tildes y ñ. 6) Máximo ~1,6 veces la longitud del original. Ejemplos ya documentados:\n' + ej +
               '\nResponde SOLO JSON: {"items":[{"en":"...","es":"...","nota":"motivo breve o CONSERVADO"}]}')
    for i in range(0, len(cola), 20):
        lote = cola[i:i + 20]
        usuario = json.dumps([{'en': en, 'jp': jp} for en, jp in lote], ensure_ascii=False)
        res = llamar(sistema, usuario).get('items', [])
        with open(SALIDA, 'a', encoding='utf-8') as f:
            for x in res:
                if x.get('en') in dict(lote) and x.get('es'):
                    f.write(json.dumps(x, ensure_ascii=False) + '\n')
        print(i + len(lote), flush=True)
    print('fin', flush=True)


main()
