"""Traduce los mensajes que siguen idénticos al inglés y SÍ son traducibles. Salida: traduccion/restos_ingles.json {ID: español}
(aplicado por tools/traduccion/integrar_ia.py; exige marcadores idénticos). Fuera de alcance a propósito: créditos, nombres de personajes,
técnicas conservadas (glosario), licencias legales y términos gráficos (MSAA, TAA, Bloom…).
Usa el japonés del juego como contexto; propuestas del modelo marcadas como localización propia en docs/AUDITORIA_RESTOS_INGLES.csv."""
import csv, json, re, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODELO = 'hf.co/llmfan46/gemma-4-Ortenzya-The-Creative-Wordsmith-31B-it-uncensored-heretic-GGUF:Q4_K_M'
M = re.compile(r'<[^>]*>|%[sd]')


def cargar(p):
    return {e['NAME_LABEL']: e['MESSAGE'] for e in json.load(open(p, encoding='utf-8-sig'))['message_message']}


# (prefijo, texto inglés exacto) -> español. Criterio: la wiki ES / coherencia con el resto del juego.
MANUAL = {
    ('STR_LIBRARY_GLOSSARY_TITLE', 'Akane Beach'): 'Playa Akane',
    ('STR_LIBRARY_GLOSSARY_TITLE', 'Tartaros'): 'Tártaros',
    ('STR_EXTRA_BGM', 'Tartaros'): 'Tártaros',
    ('STR_EXTRA_BGM', 'Grand Magic Games'): 'Grandes Juegos Mágicos',
    ('STR_EVENT_TITLE_NAME', 'Natsu vs. Zeref'): 'Natsu contra Zeref',
    ('STR_EVENT_TITLE_NAME', 'Atelier Lucy 1'): 'Taller de Lucy 1', ('STR_EVENT_TITLE_NAME', 'Atelier Lucy 2'): 'Taller de Lucy 2',
    ('STR_EVENT_TITLE_NAME', 'Atelier Lucy 3'): 'Taller de Lucy 3', ('STR_EVENT_TITLE_NAME', 'Atelier Lucy 4'): 'Taller de Lucy 4',
    ('STR_LIBRARY_HELP_TITLE', 'Atelier: BGM'): 'Taller: BGM',
    ('STR_TEROP_NICKNAME', '12 Golden Keys of the Zodiac: Maiden'): '12 Llaves Doradas del Zodiaco: Virgo',
    ('STR_TEROP_NICKNAME', '12 Golden Keys of the Zodiac: Lion'): '12 Llaves Doradas del Zodiaco: Leo',
    ('STR_TEROP_NICKNAME', '12 Golden Keys of the Zodiac: Scorpion'): '12 Llaves Doradas del Zodiaco: Escorpio',
    ('STR_TEROP_NICKNAME', 'Canis Minor'): 'Canis Minor',
    ('STR_TEROP_NICKNAME', 'Spriggan 12: Nation Destroyer'): 'Spriggan 12: Destructor de Naciones',
    ('STR_TEROP_NICKNAME', 'Spriggan 12: Desert King'): 'Spriggan 12: Rey del Desierto',
    ('STR_TEROP_NICKNAME', 'Spriggan 12: Judge'): 'Spriggan 12: Juez',
    ('STR_TEROP_NICKNAME', 'Spriggan 12: Warrior Queen'): 'Spriggan 12: Reina Guerrera',
    ('STR_TEROP_NICKNAME', 'Spriggan 12: Assassin'): 'Spriggan 12: Asesino',
    ('STR_MONSTER_NAME', 'Imp'): 'Diablillo', ('STR_MONSTER_NAME', 'Golem'): 'Gólem',
    ('STR_MONSTER_NAME', 'Dragon King Acnologia'): 'Rey Dragón Acnologia',
    ('STR_MONSTER_NAME', 'Grim Reaper: Bloodman'): 'Segador: Bloodman',
    ('STR_MONSTER_NAME', 'Wizard King: August'): 'Rey Mago: August',
    ('STR_MONSTER_NAME', 'Scarlet Despair: Irene Belserion'): 'Desesperación Escarlata: Irene Belserion',
    ('STR_MONSTER_NAME', 'Assault Mode: Wall Eehto'): 'Modo Asalto: Wall Eehto',
    ('STR_MONSTER_NAME', 'Nine Demon Gates: Kyoka'): 'Nueve Puertas Demoníacas: Kyoka',
    ('STR_COSTUME', 'Fairy School'): 'Escuela de Fairy',
    ('STR_QUEST_CHARA_TITLE', 'Fairy Pop Idol'): 'Ídolo Pop de Fairy',
    ('STR_ITEM_NAME', 'Zenith of Fire Dragon'): 'Cénit del Dragón de Fuego',
    ('STR_OPTION_DEFINE', 'STORY'): 'HISTORIA', ('STR_OPTION_DEFINE', 'BALANCED'): 'EQUILIBRADO', ('STR_OPTION_DEFINE', 'HARD'): 'DIFÍCIL',
    ('STR_SKILL_TREE_ORIGIN_NAME', 'ATK + <NUM0>%'): 'ATQ + <NUM0>%', ('STR_SKILL_TREE_ORIGIN_NAME', 'DEF + <NUM0>%'): 'DEF + <NUM0>%',
    ('STR_SKILL_TREE_ORIGIN_NAME', 'SPD + <NUM0>%'): 'VEL + <NUM0>%',
}


# Correcciones a la salida del modelo (copió el efecto japonés como nombre o dejó «Lv»)
AJUSTE_MODELO = {
    'Tip of the Storm': 'Punta de la Tormenta', 'Tip of the Whirlwind': 'Punta del Torbellino', 'Tip of the Blackwind': 'Punta del Viento Negro',
    'Tip of the Fierce Wind': 'Punta del Viento Feroz', 'Tip of the Tempest': 'Punta de la Tempestad', 'Whiteout': 'Ventisca',
    'Separating Ice Flame': 'Llama de Hielo Separadora', 'Repelling Ice Flame': 'Llama de Hielo Repulsora', 'Interfering Ice Flame': 'Llama de Hielo Interferente',
    'Mixed Ice Flame': 'Llama de Hielo Mixta', 'Intermingling Ice Flame': 'Llama de Hielo Entrelazada', 'Penetrating Ice Flame': 'Llama de Hielo Penetrante',
    'Fusing Ice Flame': 'Llama de Hielo Fusionada', 'Dragon Slayer': 'Cazador de Wyverns', 'Golem Slayer': 'Cazador de Gólems',
}


def llamar(sistema, usuario):
    cuerpo = {'model': MODELO, 'stream': False, 'think': False, 'format': 'json', 'options': {'temperature': 0.2, 'num_ctx': 8192},
              'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}]}
    r = urllib.request.Request('http://localhost:11434/api/chat', json.dumps(cuerpo).encode(), {'Content-Type': 'application/json'})
    return json.loads(json.load(urllib.request.urlopen(r, timeout=900))['message']['content'])


def main():
    en = cargar(RAIZ / 'pruebas/gust_enc/06_decode_message/message.json'); es = cargar(RAIZ / 'traduccion/candidato_ia/message.json')
    jp = cargar(RAIZ / 'pruebas/terminologia/jpn/message.json')
    out = {}; filas = []
    for k, v in en.items():
        pref = re.sub(r'_\d+$', '', k)
        t = MANUAL.get((pref, v.strip()))
        if t and es[k] == en[k] and M.findall(t) == M.findall(v):
            out[k] = t; filas.append([k, v, t, 'manual'])
    # efectos de objeto: modelo con japonés
    pend = {}
    for k, v in en.items():
        if k.startswith('STR_ITEM_EFFECT') and es[k] == en[k] and re.search(r'[A-Za-z]{3,}', v) and not M.findall(v):
            pend.setdefault(v.strip(), []).append(k)
    ej = ['Tuning Heart XXL → Corazón de Afinación XXL', 'Swing of the Giants XL → Columpio de Gigantes XL', 'Pure Prayer L → Oración Pura L',
          'Four-Color Feather S → Pluma de Cuatro Colores S', 'Lightbringer S → Portador de Luz S', "Guardian's Curse → Maldición del Guardián", 'HP +10 → PV +10']
    sistema = ('Eres traductor de FAIRY TAIL al español de España. Traduces NOMBRES de efectos de objetos de un videojuego (etiquetas cortas). Reglas: '
               'conserva los sufijos de nivel (S, M, L, XL, XXL) y los números; estadísticas: ATK→ATQ, DEF→DEF, SPD→VEL, HP→PV; '
               '«X Slayer» (JP 特攻 = daño extra contra X) → «Cazador de X» en plural natural; «Up» → «↑» no, usa «+»: «ATQ + S»; '
               'mantén los nombres propios; usa el japonés solo como pista de significado; conserva tildes y ñ; brevedad. Ejemplos del estilo ya usado:\n'
               + '\n'.join(ej) + '\nResponde SOLO JSON: {"items":[{"en":"...","es":"..."}]}')
    cache_f = RAIZ / 'pruebas/terminologia/restos_modelo.json'
    cache = json.load(open(cache_f, encoding='utf-8')) if cache_f.exists() else {}
    lista = sorted(x for x in pend if x not in cache)
    for i in range(0, len(lista), 20):
        lote = lista[i:i + 20]
        usuario = json.dumps([{'en': x, 'jp': jp[pend[x][0]][:30]} for x in lote], ensure_ascii=False)
        for it in llamar(sistema, usuario).get('items', []):
            if it.get('en') in pend and it.get('es'):
                cache[it['en']] = it['es'].strip()
        json.dump(cache, open(cache_f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(i + len(lote), '/', len(lista), flush=True)
    for x, ks in pend.items():
        if x in cache:
            for k in ks:
                out[k] = cache[x]; filas.append([k, x, cache[x], 'modelo'])
    for k in list(out):
        if en[k].strip() in AJUSTE_MODELO and not M.findall(en[k]):
            out[k] = AJUSTE_MODELO[en[k].strip()]
    json.dump(out, open(RAIZ / 'traduccion/restos_ingles.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(RAIZ / 'docs/AUDITORIA_RESTOS_INGLES.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['ID', 'Inglés', 'Español', 'Origen']); w.writerows(filas)
    print('restos traducidos', len(out))


main()
