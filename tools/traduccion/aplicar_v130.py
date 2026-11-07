"""Aplica correcciones manuales (glosario canónico/wiki ES) a es_ortenzya.jsonl -> es_final.json y las integra en candidato_ia/message.json."""
import json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from traducir_masivo import MARCA, RAIZ
from traducir_v130 import V

P = "STR_"
fix = {  # id sin prefijo -> traducción definitiva
 "ACTION_NAME_0144": "Círculo Mágico de Resonancia: Canción Sagrada de Doble Ala", "ACTION_NAME_0525": "Círculo Mágico de Resonancia: Canción Sagrada de Doble Ala",
 "ACTION_NAME_0516": "Círculo Mágico de Cinco Niveles: Canción Sagrada", "ACTION_NAME_0532": "Círculo Mágico de Cinco Niveles: Canción Sagrada+", "ACTION_NAME_0542": "Círculo Mágico de Cinco Niveles: Canción Sagrada++",
 "ACTION_NAME_0517": "Círculo Mágico de Tres Niveles: Espejo de Agua", "ACTION_NAME_0533": "Círculo Mágico de Tres Niveles: Espejo de Agua+", "ACTION_NAME_0543": "Círculo Mágico de Tres Niveles: Espejo de Agua++",
 "ACTION_NAME_0529": "Pleiades+", "ACTION_NAME_0539": "Pleiades++", "ACTION_NAME_0534": "Abyss Break+", "ACTION_NAME_0544": "Abyss Break++",
 "BUFF_NAME_130": "Daño Ataque enlazado¡", "BUFF_NAME_131": "Daño Unison Raid¡", "BUFF_NAME_132": "Daño Magia Extrema¡",
 "BUFF_TEXT_129": "Aumenta el daño de los ataques enlazados, los Unison Raid y la Magia Extrema.", "BUFF_TEXT_130": "Aumenta el daño de los ataques enlazados.",
 "BUFF_TEXT_131": "Aumenta el daño de los Unison Raid.", "BUFF_TEXT_132": "Aumenta el daño de la Magia Extrema.",
 "QUEST_CHARA_TITLE_103": "¡Contemplad al Estratega de Fairy Tail!",
 "REACTION_VOICE_613": "Este es... tu último combate.", "REACTION_VOICE_631": "¡Ejecutad nuestra estrategia!", "REACTION_VOICE_637": "¡Seguid avanzando!",
 "REACTION_VOICE_648": "¡Vaya—!", "REACTION_VOICE_659": "¡Nieve Eterna: Dios del Rayo de Fuego!", "REACTION_VOICE_660": "¿Eh? ¿Qué se supone que significa eso...?",
 "FIELDMAP_TWEET_1784": None, "FIELDMAP_TWEET_1851": "Eh.", "FIELDMAP_TWEET_1770": "Ha quedado todo limpio.", "FIELDMAP_TWEET_2020": "¡¿Tú... \"dividiste\" a Natsu?!",
}
rep = {  # sustituciones de texto dentro de la traducción
 "ACTION_COMMENT_0060": [("Ataques en Cadena, Incursiones Unísonas y Magia Extrema", "ataques enlazados, Unison Raid y Magia Extrema")],
 "FIELDMAP_TWEET_1992": [("Táctica de Fairy Tail", "Estratega de Fairy Tail")], "FIELDMAP_TWEET_1993": [("Táctica", "Estratega"), ("protectores", "protectoras")],
 "FIELDMAP_TWEET_1971": [("tengan", "tened")], "FIELDMAP_TWEET_2026": [("tengan", "tened")],
 "FIELDMAP_TWEET_2015": [("¡Sí. ¡Celebrar", "Sí. ¡Celebrar")], "FIELDMAP_TWEET_2019": [('"Crush"', '"Aplastar"')],
 "FIELDMAP_TWEET_1784": [("¿Aún más fuerte?!", "¡¿Aún más fuerte?!")],
}
r = {}
for l in (V / "es_ortenzya.jsonl").read_text(encoding="utf-8").splitlines():
    x = json.loads(l); r[x["id"]] = x
fin = {k: x["es"] for k, x in r.items()}
for k, v in fix.items():
    if v is not None: fin[P + k] = v
for k, lst in rep.items():
    for a, b in lst:
        assert a in fin[P + k], (k, a); fin[P + k] = fin[P + k].replace(a, b)
# títulos de evento = mismo español que el título de personaje con idéntico inglés
chara = {x["en"]: fin[k] for k, x in r.items() if k.startswith(P + "QUEST_CHARA_TITLE")}
for k, x in r.items():
    if k.startswith(P + "EVENT_TITLE_NAME") and x["en"] in chara: fin[k] = chara[x["en"]]
# comprobaciones
mal = []
for k, es in fin.items():
    en = r[k]["en"]
    if MARCA.findall(en) != MARCA.findall(es): mal.append((k, "marcadores"))
    if es.count("¿") != es.count("?") or es.count("¡") != es.count("!"):
        if not (k.endswith(("BUFF_NAME_130", "131", "132")) or "¡" in es and es.endswith("¡")): mal.append((k, "signos", es[:70]))
print("problemas:", mal[:30], len(mal))
(V / "es_final.json").write_text(json.dumps(fin, ensure_ascii=False, indent=1), encoding="utf-8")
# integrar en el candidato
cp = RAIZ / "traduccion/candidato_ia/message.json"
shutil.copy2(cp, V / "candidato_antes_v130.json")
raw = json.loads(cp.read_text(encoding="utf-8-sig")); lst = raw["message_message"]; idx = {x["NAME_LABEL"]: x for x in lst}
nuevos = camb = 0
for k, es in fin.items():
    if k in idx: idx[k]["MESSAGE"] = es; camb += 1
    else: lst.append({"NAME_LABEL": k, "MESSAGE": es}); nuevos += 1
# etiquetas de la 1.3.0.0 sin texto propio (vacías) no hacen falta en el candidato
cp.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8-sig"); print("candidato: añadidas", nuevos, "| actualizadas", camb)
