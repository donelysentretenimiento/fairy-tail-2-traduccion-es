"""Traduce los diálogos de los EBM (EventMessageData) con Ollama. Reanudable (JSONL). Lotes = escena (archivo) con 2 líneas de contexto.
Uso: traducir_ebm.py --modelo M --salida pruebas/traduccion_ia/ebm_ortenzya.jsonl [--archivos MS01_120,...]"""
import argparse, csv, glob, json, os, re, sys, time, urllib.request
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, R + '/tools/ebm'); import ebm
sys.path.insert(0, R + '/tools/traduccion'); import traducir_masivo as tm
CARPETA = r'C:\Juegos\FAIRY TAIL 2\MASTER\ENG\EventMessageData'
SIS = """Eres traductor profesional de videojuegos (FAIRY TAIL 2, JRPG basado en el manga Fairy Tail). Traduces DIÁLOGOS de escenas del inglés al español de España (castellano peninsular, tuteo, sin voseo ni regionalismos latinoamericanos).
Recibes líneas de una misma escena, en orden, cada una con el personaje que habla ("speaker") y el texto en inglés ("en"). Algunas líneas ("contexto": true) son solo contexto previo: NO las traduzcas ni las devuelvas.
REGLAS ESTRICTAS:
- Mantén la voz de cada personaje (Natsu impulsivo y directo; Erza formal y firme; Lucy cercana; Happy infantil, dice «aye»; Gray seco; Elfman: «¡de hombres!»; etc.) y la coherencia entre líneas de la escena.
- Plural informal de España: «vosotros/os/vuestro» (nunca «ustedes»). Tuteo con una sola persona.
- Copia EXACTAMENTE las marcas <CR> y los símbolos ♥ * — tal cual, y colócalos de forma equivalente. No añadas marcas nuevas.
- No traduzcas nombres propios (personajes, gremios, magias, técnicas, lugares): Natsu, Lucy, Erza, Fairy Tail, Dragon Slayer, Fairy Heart, Lumen Histoire...
- Texto natural y conciso (cabe en un cuadro de diálogo): no más de ~1,3 veces la longitud del inglés si es posible.
- Devuelve SOLO JSON {"items":[{"id":...,"es":...}]} con todos los ids no-contexto, en el mismo orden.
Glosario obligatorio:
"""
def llamar(modelo, sistema, lote):
    cuerpo = {"model": modelo, "stream": False, "think": False, "options": {"temperature": 0.35, "num_ctx": 16384, "num_predict": 8192},
              "format": {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": {"type": "object", "required": ["id", "es"], "properties": {"id": {"type": "string"}, "es": {"type": "string"}}}}}},
              "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": json.dumps(lote, ensure_ascii=False)}]}
    req = urllib.request.Request(tm.OLLAMA, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r: return json.loads(json.loads(r.read())["message"]["content"])["items"]
def quien(r): return re.sub(r'^CHARACTER_', '', r['A']).replace('_YOKO', '').replace('_', ' ').title() if r['A'] != 'CHARACTER_NONE' else r['B']
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--modelo', required=True); ap.add_argument('--salida', required=True); ap.add_argument('--archivos', default='')
    a = ap.parse_args(); sis = SIS + tm.glosario(); hechos = set()
    if os.path.exists(a.salida):
        for l in open(a.salida, encoding='utf-8'):
            r = json.loads(l); hechos.add(r['id']) if r['ok'] else None
    pend = 0; trabajo = []
    for p in sorted(glob.glob(CARPETA + '/*.ebm')):
        nombre = os.path.basename(p)[len('EVENT_MESSAGE_'):-4]
        if a.archivos and nombre not in a.archivos.split(','): continue
        recs, _ = ebm.parse(open(p, 'rb').read())
        lineas = [(f'{nombre}#{i}', quien(r), r['texto_b'].decode('utf-8')) for i, r in enumerate(recs) if r['texto_b']]
        if lineas: trabajo.append((nombre, lineas))
    total = sum(len(l) for _, l in trabajo); print(total, 'líneas;', len(hechos), 'ya hechas', flush=True); t0 = time.time(); n = 0
    with open(a.salida, 'a', encoding='utf-8') as out:
        for nombre, lineas in trabajo:
            for k in range(0, len(lineas), 20):
                lote_l = [x for x in lineas[k:k + 20] if x[0] not in hechos]
                if not lote_l: continue
                ctx = lineas[max(0, k - 2):k] if k else []
                lote = [{"id": i, "speaker": s, "en": t, "contexto": True} for i, s, t in ctx] + [{"id": i, "speaker": s, "en": t} for i, s, t in lote_l]
                res = {}
                try: res = {r["id"]: r["es"] for r in llamar(a.modelo, sis, lote)}
                except Exception as e: print('lote fallido', nombre, e, flush=True)
                for i, s, t in lote_l:
                    es = res.get(i); mot = 'faltante' if es is None else None
                    if es is not None:
                        if tm.MARCA.findall(t) != tm.MARCA.findall(es): mot = 'marcadores'
                        elif not es.strip(): mot = 'vacio'
                        elif len(es) > len(t) * 2.2 + 20: mot = 'demasiado_largo'
                    if mot:
                        try:
                            es2 = llamar(a.modelo, sis, [{"id": i, "speaker": s, "en": t}])[0]["es"]
                            if tm.MARCA.findall(t) == tm.MARCA.findall(es2) and es2.strip(): es, mot = es2, None
                        except Exception: pass
                    out.write(json.dumps({"id": i, "speaker": s, "en": t, "es": es, "ok": mot is None, "motivo": mot}, ensure_ascii=False) + "\n")
                out.flush(); n += len(lote_l); print(f'{nombre} {n}/{total - len(hechos)} {n / (time.time() - t0):.2f} líneas/s', flush=True)
main()
