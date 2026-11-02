"""Inventario por ID de la terminología de combate: inglés original + español actual + clave limpia."""
import json, re, csv, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ORIG = RAIZ / 'pruebas/gust_enc/06_decode_message/message.json'
ACT = RAIZ / 'traduccion/candidato_ia/message.json'
PREFIJOS = ['STR_ACTION_NAME', 'STR_ACTION_COMMENT', 'STR_TEAMSKILL_NAME', 'STR_TEAMSKILL_TEXT', 'STR_MIX_DEFINE', 'STR_MIX_RECALL_DEFINE',
            'STR_MIX_SKILL_DESC', 'STR_MIX_TREE', 'STR_MIX_TREE_DESC', 'STR_MIX_TUTORIAL', 'STR_SKILL_TREE_ORIGIN_NAME', 'STR_SKILL_TREE_ORIGIN_TEXT',
            'STR_SKILL_TREE_TEXT', 'STR_SKILL_TREE_TUTORIAL', 'STR_SKILL_RANGE', 'STR_SKILL_TARGET', 'STR_BUFF_NAME', 'STR_BUFF_TEXT',
            'STR_BATTLE_DEFINE', 'STR_BATTLE_TUTORIAL', 'STR_TUTO_TEXT', 'STR_TUTO_TITLE', 'STR_LIBRARY_GLOSSARY', 'STR_LIBRARY_GLOSSARY_TITLE']


def cargar(p):
    d = json.load(open(p, encoding='utf-8-sig'))['message_message']
    return {e['NAME_LABEL']: e['MESSAGE'] for e in d}


def limpiar(s):
    s = re.sub(r'<[^>]*>', '', s).strip()
    s = re.sub(r'\s*\+\s*$', '', s)
    s = re.sub(r'^(Ultra|Max|EX)\s+', '', s)
    return re.sub(r'\s+\d+$', '', s).strip()


def main():
    o, a = cargar(ORIG), cargar(ACT)
    filas = []
    for k, en in o.items():
        pref = re.sub(r'_\d+$', '', k)
        if pref in PREFIJOS:
            filas.append((k, pref, en, a.get(k, ''), limpiar(en) if pref.endswith('NAME') else ''))
    out = RAIZ / 'pruebas/terminologia/inventario.csv'
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ID', 'Prefijo', 'Ingles', 'EspanolActual', 'ClaveLimpia'])
        w.writerows(filas)
    sin = sum(1 for r in filas if r[1].endswith('NAME') and r[2] == r[3])
    print(len(filas), 'filas; nombres idénticos al inglés:', sin)


main()
