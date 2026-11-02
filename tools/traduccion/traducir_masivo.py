"""Traducción masiva EN->ES(España) con Ollama local. Reanudable (JSONL), valida marcadores.

Uso:
  python traducir_masivo.py --modelo M --salida pruebas/traduccion_ia/M.jsonl [--muestra 40 --semilla 7] [--limite N]
Cada línea JSONL: {"id","en","es","ok","motivo"}. Los ya hechos (ok=true) se omiten al reanudar.
"""
import argparse, csv, json, random, re, sys, time, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / "pruebas/gust_enc/06_decode_message/message.json"
MENU = RAIZ / "docs/TEXTOS_MENU.csv"
GLOS = RAIZ / "docs/GLOSARIO_CANONICO.csv"
MARCA = re.compile(r"<[^>]*>|%[0-9]*[sd]")
OLLAMA = "http://localhost:11434/api/chat"

SISTEMA = """Eres traductor profesional de videojuegos (FAIRY TAIL 2, JRPG basado en el manga Fairy Tail). Traduce del inglés al español de España (castellano peninsular, tuteo, sin voseo ni regionalismos latinoamericanos).
REGLAS ESTRICTAS:
- Copia EXACTAMENTE, sin cambiar ni traducir, todas las marcas entre < > (p. ej. <CR>, <CLNR>, <NUM0>, <CLGR>, <KEY_ASSIGN_...>, <IM00>, <STR0>) y los %s, %d. Mantén el mismo número de cada una y colócalas donde corresponda en la frase.
- No traduzcas nombres propios: personajes, gremios, magias, técnicas ni lugares (Natsu, Lucy, Erza, Fairy Tail, Dragon Slayer, Fairy Heart...). Sí traduce el resto.
- Estilo natural, conciso (cabe en cuadros de texto de juego). Los diálogos conservan el tono del personaje. Los nombres de objeto/habilidad: breves.
- Caracteres permitidos normales del español (á é í ó ú ñ ü ¿ ¡). Usa comillas " " rectas, no « ».
- Devuelve SOLO JSON {"items":[{"id":...,"es":...}]} con todos los ids recibidos, en el mismo orden.
Glosario obligatorio:
"""


def glosario():
    with open(GLOS, encoding="utf-8-sig", newline="") as f:
        return "\n".join(f"- {r['original_en']} => {r['traduccion_es']}" for r in csv.DictReader(f))


def cargar(solo_menu_pendiente=False):
    msgs = json.loads(FUENTE.read_text(encoding="utf-8-sig"))["message_message"]
    with open(MENU, encoding="utf-8-sig", newline="") as f:
        menu = {r["identificador"] for r in csv.DictReader(f)}
    if solo_menu_pendiente:   # registros de menú que siguen idénticos al inglés (no traducidos aún)
        with open(MENU, encoding="utf-8-sig", newline="") as f:
            pend = {r["identificador"] for r in csv.DictReader(f) if r["estado"].startswith("pendiente") and re.search(r"[A-Za-z]{3}", MARCA.sub("", r["ingles_actual"]))}
        return [(m["NAME_LABEL"], m["MESSAGE"]) for m in msgs if m["NAME_LABEL"] in pend and m["MESSAGE"].strip()]
    return [(m["NAME_LABEL"], m["MESSAGE"]) for m in msgs if m["NAME_LABEL"] not in menu and m["MESSAGE"].strip()]


def lotes(items, max_n=20, max_c=2500):
    grupos = {}
    for i, t in items:
        grupos.setdefault(re.sub(r"_?\d+$", "", i), []).append((i, t))
    for _, g in sorted(grupos.items()):
        cur, n = [], 0
        for it in g:
            if cur and (len(cur) >= max_n or n + len(it[1]) > max_c):
                yield cur; cur, n = [], 0
            cur.append(it); n += len(it[1])
        if cur:
            yield cur


def llamar(modelo, sistema, lote, think=False):
    cuerpo = {
        "model": modelo, "stream": False, "think": think,
        "options": {"temperature": 0.3, "num_ctx": 16384, "num_predict": 8192},
        "format": {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": {
            "type": "object", "required": ["id", "es"], "properties": {"id": {"type": "string"}, "es": {"type": "string"}}}}}},
        "messages": [{"role": "system", "content": sistema},
                     {"role": "user", "content": json.dumps([{"id": i, "en": t} for i, t in lote], ensure_ascii=False)}],
    }
    req = urllib.request.Request(OLLAMA, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(json.loads(r.read())["message"]["content"])["items"]


def validar(en, es):
    if MARCA.findall(en) != MARCA.findall(es):
        return "marcadores"
    if not es.strip():
        return "vacio"
    if len(es) > len(en) * 2.2 + 20:
        return "demasiado_largo"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--muestra", type=int, default=0)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--menu-pendiente", action="store_true")
    a = ap.parse_args()
    items = cargar(a.menu_pendiente)
    if a.muestra:
        random.Random(a.semilla).shuffle(items); items = sorted(items[:a.muestra])
    salida = Path(a.salida); salida.parent.mkdir(parents=True, exist_ok=True)
    hechos = set()
    if salida.exists():
        for l in salida.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r["ok"]: hechos.add(r["id"])
    items = [x for x in items if x[0] not in hechos]
    if a.limite: items = items[:a.limite]
    sistema = SISTEMA + glosario()
    print(f"{len(items)} textos pendientes ({len(hechos)} ya hechos)", flush=True)
    t0 = time.time(); n = 0
    with open(salida, "a", encoding="utf-8") as out:
        for lote in lotes(items):
            en = dict(lote); res = {}
            try:
                res = {r["id"]: r["es"] for r in llamar(a.modelo, sistema, lote, a.think)}
            except Exception as e:
                print("lote fallido:", e, flush=True)
            for i, t in lote:
                es = res.get(i)
                mot = "faltante" if es is None else validar(t, es)
                if mot:  # reintento individual
                    try:
                        es2 = llamar(a.modelo, sistema, [(i, t)], a.think)[0]["es"]
                        if not validar(t, es2): es, mot = es2, None
                    except Exception: pass
                out.write(json.dumps({"id": i, "en": t, "es": es, "ok": mot is None, "motivo": mot}, ensure_ascii=False) + "\n")
            out.flush(); n += len(lote)
            print(f"{n}/{len(items)} {n/(time.time()-t0):.2f} textos/s", flush=True)


if __name__ == "__main__":
    main()
