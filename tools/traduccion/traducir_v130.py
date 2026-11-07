"""Traduce con Ollama (Ortenzya) las líneas nuevas/modificadas de la v1.3.0.0, con glosario canónico filtrado y ejemplos de la misma familia.
Uso: python traducir_v130.py [--extraer] [--traducir]   Salidas: traduccion/v130/{lineas_en.json, es_ortenzya.jsonl}"""
import argparse, csv, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from traducir_masivo import llamar, validar, MARCA, SISTEMA, RAIZ

V = RAIZ / "traduccion/v130"
MOD = "hf.co/llmfan46/gemma-4-Ortenzya-The-Creative-Wordsmith-31B-it-uncensored-heretic-GGUF:Q4_K_M"
L = lambda p: {x["NAME_LABEL"]: x["MESSAGE"] for x in json.loads(Path(p).read_text(encoding="utf-8-sig"))["message_message"]}


def extraer():
    nuevo = L(V / "message_1300_original.json"); viejo = L(RAIZ / "pruebas/gust_enc/06_decode_message/message.json")
    n = {k: t for k, t in nuevo.items() if t.strip() and (k not in viejo or viejo[k] != t)}
    (V / "lineas_en.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8"); print(len(n), "líneas,", sum(map(len, n.values())), "caracteres")


def glosario_csv():
    with open(RAIZ / "docs/FAIRY_TAIL_GLOSARIO_CANONICO.csv", encoding="utf-8-sig", newline="") as f:
        return [(r["Inglés"].strip(), (r["Español definitivo"] or r["Español actual"]).strip(), r["Tipo"]) for r in csv.DictReader(f) if r["Inglés"].strip() and (r["Español definitivo"] or r["Español actual"]).strip()]


def traducir():
    en = json.loads((V / "lineas_en.json").read_text(encoding="utf-8")); cand = L(RAIZ / "traduccion/candidato_ia/message.json"); orig = L(RAIZ / "pruebas/gust_enc/06_decode_message/message.json")
    glos = glosario_csv(); guia = (RAIZ / "docs/GUIA_ESTILO_ES.md").read_text(encoding="utf-8")[:2500]
    sal = V / "es_ortenzya.jsonl"; hechos = {json.loads(l)["id"] for l in sal.read_text(encoding="utf-8").splitlines() if l and json.loads(l).get("ok")} if sal.exists() else set()
    grupos = {}
    for k, t in en.items():
        if k not in hechos: grupos.setdefault(re.sub(r"_?\d+$", "", k), []).append((k, t))
    for pref, g in sorted(grupos.items()):
        for i in range(0, len(g), 15):
            lote = g[i:i + 15]; texto = " ".join(t for _, t in lote).lower()
            gl = sorted({(a, b) for a, b, _ in glos if len(a) > 3 and re.search(r"(?<![a-z])" + re.escape(a.lower()) + r"(?![a-z])", texto)}, key=lambda x: -len(x[0]))[:60]
            ej = [(orig[k], cand[k]) for k in cand if k.startswith(pref) and k in orig and cand[k] != orig[k] and k not in en][:12]
            sis = SISTEMA + "\n".join(f"- {a} => {b}" for a, b in gl) + ("\nEjemplos ya traducidos de la misma familia (mantén su estilo y vocabulario):\n" + "\n".join(f"- {a} => {b}" for a, b in ej) if ej else "") + "\nGuía de estilo:\n" + guia
            for intento in range(3):
                try: r = {x["id"]: x["es"] for x in llamar(MOD, sis, lote)}; break
                except Exception as e: print("reintento", pref, e); time.sleep(5); r = {}
            with open(sal, "a", encoding="utf-8") as f:
                for k, t in lote:
                    es = r.get(k, ""); m = validar(t, es) if es else "falta"
                    f.write(json.dumps({"id": k, "en": t, "es": es, "ok": m is None, "motivo": m}, ensure_ascii=False) + "\n")
            print(pref, i, len(lote), flush=True)


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--extraer", action="store_true"); a.add_argument("--traducir", action="store_true"); a = a.parse_args()
    if a.extraer: extraer()
    if a.traducir: traducir()
