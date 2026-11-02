"""Glosario canónico + overrides por ID, con el JAPONÉS del propio juego (MASTER/JPN) como prueba de identidad.
A) kanji del juego == campo Kanji de UNA ficha de la wiki ES (cruce_jp.json)  -> DOCUMENTADO POR LA COMUNIDAD.
B) correcciones previas sin kanji idéntico, revisadas a mano (REVISADAS_A_MANO) -> también marcadas, con la salvedad.
Nada es CONFIRMADO POR EDICIÓN ESPAÑOLA sin evidencia de Norma/doblaje. Los huecos vacíos nunca se tocan."""
import csv, json, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
T = RAIZ / 'pruebas/terminologia'
NOMBRES = ('STR_ACTION_NAME', 'STR_TEAMSKILL_NAME', 'STR_SKILL_TREE_ORIGIN_NAME')
TIPO = {'STR_ACTION_NAME': 'Ataque/habilidad', 'STR_TEAMSKILL_NAME': 'Cooperativo', 'STR_SKILL_TREE_ORIGIN_NAME': 'Árbol de habilidades'}
PRE = re.compile(r'^(Ultra |Max |EX )')
# Ajustes manuales tras auditar los diálogos EBM (coherencia menú/diálogo y fuentes)
AJUSTES = {
    'grandchariot': ('Grand Chariot', 'NOMBRE CONSERVADO (pendiente de verificación)', 'nombre propio de la magia de Jellal (dossier); los diálogos lo conservan'),
    'eternalflare': ('Eternal Flare', 'NOMBRE CONSERVADO (pendiente de verificación)', 'la wiki ES lo mantiene en inglés; los diálogos lo conservan'),
    'baneparticles': ('Partículas Bane', 'DOCUMENTADO POR LA COMUNIDAD', 'forma del glosario del juego (STR_LIBRARY_GLOSSARY_TITLE_049) y de la wiki ES'),
}
# Sin apoyo en el japonés del juego (ficha sin kanji, o kanji de otra técnica): se retiran
RETIRAR = {'sandwave', 'waterblast', 'crush'}
# El título de la ficha ES no es un nombre de técnica fiable: «Misión de Agua» para 水割り (mizuwari = whisky aguado)
NO_FIABLE = {'mizuwari', 'moonflash'}  # moonflash: la ficha dice «Luna del Destello» (orden alterado); el dossier propone «Destello Lunar», pendiente de confirmar
# Revisadas a mano: el kanji de la ficha difiere del juego solo en variante/puntuación/kana, o la ficha lleva la misma lectura
REVISADAS_A_MANO = {'crimsonlotusexplodingflameblade': 'kanji simplificado 红莲 vs 紅蓮 (misma técnica, Natsu)',
                    'lightningfiredragonmode': '雷炎竜 = Lightning Flame Dragon Mode', 'firedragonkingmode': '炎竜王 = Fire Dragon King Mode',
                    'winggodsword': '', 'windgodsword': '風神の剣 (Erza, guía Gamecap)', 'nakagamistarlight': 'ficha usa 中一神 (errata) por 天一神',
                    'icedevilzerolongsword': 'solo difiere la puntuación ・', 'icedevilzerodestructionbow': 'solo difiere la puntuación ・',
                    'karmademonironspiral': '鉄螺旋 vs 鉄螺線形 (Gajeel)', 'wingsoflove': 'ficha añade signos !!!! (Juvia)',
                    'painrelievingperfume': 'ficha en kana, misma lectura パルファム', 'historiaofthedead': '屍のヒストリア (Neinhart)'}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


# Se conservan en inglés: la wiki ES los mantiene como nombre propio/técnico (Wendy, Mirajane, Lucy, Gildarts) o son términos de estado genéricos sin ficha
DEJAR = {norm(x) for x in ['Arms', 'Armor', 'Vernier', 'Heal', 'Raise', 'Revive', 'Vigor', 'Triage', 'Iron', 'Steel', 'Concentrate', 'Scratch', 'Lariat', 'Tackle',
                           'Earth Wave', 'Eternal Flare', 'Darkness Stream', 'Evil Explosion', 'Evil Shower', 'Evil Orb', 'Soul Extinction', 'Suppression Arts',
                           'Water Heal', 'Water Make: Blood', 'Ice-Make', 'Ice Cannon']}
# Correcciones a la propuesta del modelo, cada una con su motivo
LOC_MANUAL = {norm(k): v for k, v in {
    'Fire Dragon Flame Elbow': ('Codo del Dragón de Fuego', 'wiki ES, Natsu: 火竜の炎肘'),
    'Fire Dragon Sword Horn': ('Espada Cuerno del Dragón de Fuego', 'wiki ES, Natsu: 火竜の剣角'),
    'Crimson Lotus: Phoenix Blade': ('Loto Carmesí: Espada del Fénix', 'wiki ES, Natsu'),
    'Crimson-Black Twin Blades': ('Espadas Gemelas Negra y Roja', 'wiki ES, Erza: 紅黒の双刃'),
    'Ice-Make: Ice Hammer': ('Ice-Make: Martillo', 'wiki ES, Gray: Ice Make: Martillo'),
    'Ice-Make: Ice Geyser': ('Ice-Make: Géiser', 'wiki ES, Gray: Ice Make: Géiser'),
    'Ice-Make: Silver': ('Ice-Make: Silver', 'wiki ES conserva Silver'),
    'Ice Devil: Zero Destruction Bow': ('Arco de Destrucción del Demonio de Hielo', 'wiki ES, Gray'),
    'Ice Devil: Zero Long Sword': ('Espada Larga del Demonio de Hielo', 'wiki ES, Gray'),
    'Ice Devil: Zero Destruction Fist': ('Puño de Destrucción del Demonio de Hielo', 'por analogía con Arco de Destrucción (sin ficha)'),
    'Double Lucy Kick': ('Doble Lucy Kick', 'Lucy Kick se conserva (dossier)'),
    'Moon Flash': ('Destello Lunar', 'dossier: 月閃 «Destello Lunar», pendiente de confirmar'),
    'Rampant Demonic Blade': ('Hoja Demoníaca Desbocada', 'coherente con la traducción previa del ID 0447; el modelo omitió la tilde'),
    'Summon Capricorn': ('Invocar a Capricornio', 'coherente con «Invocar al Rey Espíritu Celestial»'),
    'Summon Loki': ('Invocar a Loke', 'Loke, nombre en España'),
    'Summon Scorpio': ('Invocar a Escorpio', 'coherente con Invocar a Capricornio'),
    'Summon Nikora': ('Invocar a Nikora', 'coherente con las demás invocaciones'),
    'Summon Celestial Spirit King': ('Invocar al Rey Espíritu Celestial', 'coherente con IDs ya traducidos'),
    'Water Cane': ('Vara de Agua', 'localización propia (Juvia); la wiki conserva el inglés'),
    'Water Slicer': ('Cuchilla de Agua', 'localización propia (Juvia); la wiki conserva el inglés'),
    'Water Cyclone': ('Ciclón de Agua', 'localización propia (Juvia); la wiki conserva el inglés'),
}.items()}


def partes(en):
    s = re.sub(r'<[^>]*>', '', en).strip()
    pre = PRE.match(s); pre = pre.group(1) if pre else ''
    s = s[len(pre):]
    suf = re.search(r'(\s*\+{1,2}|\s+\d+)$', s); suf = suf.group(1) if suf else ''
    return pre, s[:len(s) - len(suf)].strip(), suf


def main():
    inv = list(csv.DictReader(open(T / 'inventario.csv', encoding='utf-8-sig')))
    cruce = json.load(open(T / 'cruce_jp.json', encoding='utf-8'))
    prev_f = RAIZ / 'traduccion/terminologia_overrides.json'
    previos = json.load(open(T / 'antes/overrides_92.json', encoding='utf-8'))  # semilla fija: las 92 correcciones de la pasada anterior
    filas, over, conflictos = [], {}, []
    lf = T / 'localizacion_propia.jsonl'
    loc = {norm(x['en']): x for x in (json.loads(l) for l in open(lf, encoding='utf-8'))} if lf.exists() else {}
    for r in inv:
        if r['Prefijo'] not in NOMBRES:
            continue
        k = r['ID']; pre, base, suf = partes(r['Ingles'])
        c = cruce.get(k, {})
        actual = r['EspanolActual']; definitivo = actual
        sin_traducir = actual.strip() == r['Ingles'].strip()
        estado, decision, ev, fuente, origen, titulo = 'PENDIENTE DE IDENTIFICACIÓN', 'Pendiente', '', '', 'Sin traducir' if sin_traducir else 'Ortenzya', ''
        personaje = ', '.join(c.get('personajes', []))
        if not base:
            decision, estado, origen = 'Ranura vacía del juego (sin texto): no se toca', 'SIN TEXTO', 'Juego'
        else:
            nb = norm(base)
            if c.get('estado') == 'ficha_unica' and nb not in RETIRAR and nb not in NO_FIABLE:
                f = c['fichas'][0]; titulo = f['titulo']
                prueba = f"kanji del juego {c['jp_base']} idéntico al campo Kanji de la ficha"
                fuente, ev = f['url'], f"Wiki ES (nivel 3, no oficial): {f['url']}; {prueba}; rōmaji {f['romaji']}; ficha EN «{f['ingles']}»"
            elif nb in REVISADAS_A_MANO and previos.get(k):
                titulo = re.sub(r'^(Ultra |Max |EX )', '', re.sub(r'\s*(\+{1,2}|\d+)$', '', previos[k])).strip()
                prueba = 'revisada a mano: ' + REVISADAS_A_MANO[nb]
                ev = f"Wiki ES (nivel 3): título «{titulo}»; kanji del juego {c.get('jp_base', '')}; {prueba}"
            if titulo:
                # (':' in base) == (':' in titulo): el título no puede añadir ni perder un prefijo («Heaven's Wheel: …», «Ice Make Unlimited: …»)
                ok = ('(' not in titulo and '/' not in titulo and norm(titulo) != nb and len(titulo) <= max(len(base) * 1.7 + 6, 18)
                      and (':' in base) == (':' in titulo))
                if ok:
                    definitivo = pre + titulo + suf
                    estado = 'DOCUMENTADO POR LA COMUNIDAD'
                    origen = 'Wiki ES'
                    decision = 'Override por ID' if definitivo != actual else 'Coincide con la wiki ES'
                    if definitivo != actual:
                        over[k] = definitivo
                        if not sin_traducir:
                            conflictos.append((k, r['Ingles'].strip(), actual, definitivo, fuente or ev))
                else:
                    decision = f'Ficha descartada (nombre no válido o demasiado largo para la caja): {titulo}'
            elif nb in NO_FIABLE:
                decision = 'Ficha ES descartada: su título no es un nombre de técnica fiable (ver CONFLICTOS)'
            elif nb in RETIRAR:
                decision = 'Retirada: la ficha no tiene apoyo en el japonés del juego'
            # si la ficha se descartó (título igual al inglés, prefijo distinto…) y la fila sigue en inglés, se prueba la localización propia
            if estado.startswith('PENDIENTE') and sin_traducir and nb in loc and '<' not in r['Ingles']:
                es, motivo = LOC_MANUAL.get(nb, (loc[nb]['es'].strip(), loc[nb].get('nota', '')))
                origen = 'Criterio propio'
                if nb in DEJAR or norm(es) == nb or ('CONSERVAD' in motivo.upper() and nb not in LOC_MANUAL):
                    estado, decision = 'NOMBRE CONSERVADO (pendiente de verificación)', 'Se conserva el original'
                elif len(es) > max(len(base) * 1.8 + 6, 18) or ((':' in base) != (':' in es) and nb not in LOC_MANUAL):
                    decision = f'Localización descartada (longitud o prefijo): {es}'
                else:
                    definitivo = pre + es + suf
                    over[k] = definitivo
                    estado = 'LOCALIZACIÓN PROPIA (Ortenzya + japonés del juego; sin fuente española)'
                    decision = 'Override por ID (localización propia)'
                    ev = f"Sin ficha ES con kanji idéntico; japonés {c.get('jp_base', '')}; criterio: {motivo}"
            elif not sin_traducir and estado.startswith('PENDIENTE'):
                estado, decision = 'LOCALIZACIÓN PROPIA (Ortenzya, sin revisar ni fuente)', 'Sin cambios'
        if base and norm(base) in AJUSTES:  # ajustes de la auditoría EBM: el menú debe coincidir con los diálogos y con las fuentes
            aj, estado_aj, motivo_aj = AJUSTES[norm(base)]
            definitivo = pre + aj + suf
            if definitivo != actual:
                over[k] = definitivo
            else:
                over.pop(k, None)
            estado, origen, decision = estado_aj, 'Criterio propio / Wiki ES', 'Ajuste por auditoría EBM: ' + motivo_aj
        filas.append([k, r['Prefijo'].lower() + '.json', personaje, r['Ingles'].strip(), c.get('jp', ''), actual, definitivo, '', TIPO[r['Prefijo']],
                      origen, fuente, '', ev, estado, decision, 1])
    with open(RAIZ / 'docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ID', 'Archivo', 'Personaje', 'Inglés', 'Japonés (juego)', 'Español actual', 'Español definitivo', 'Variantes', 'Tipo', 'Origen', 'Fuente principal',
                    'Fuente secundaria', 'Evidencia', 'Estado', 'Decisión', 'Apariciones'])
        w.writerows(filas)
    json.dump(over, open(prev_f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(conflictos, open(T / 'conflictos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import collections
    print('filas', len(filas), '| overrides', len(over), '| conflictos', len(conflictos), '|', dict(collections.Counter(x[13] for x in filas)))


main()
