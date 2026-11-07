"""Revisa es_ortenzya.jsonl contra el glosario canónico y reglas básicas. Salida: traduccion/v130/revision.json (problemas por id)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from traducir_masivo import MARCA, RAIZ
from traducir_v130 import V, glosario_csv

glos = [(a, b) for a, b, _ in glosario_csv() if len(a) > 3]
rows = [json.loads(l) for l in (V / "es_ortenzya.jsonl").read_text(encoding="utf-8").splitlines() if l]
ultimo = {}
for r in rows: ultimo[r["id"]] = r
prob = {}
ING = re.compile(r"\b(the|and|you|your|with|will|can|of|to|is|are|for|this|that)\b", re.I)
for k, r in ultimo.items():
    en, es = r["en"], r["es"]; p = []
    if not r["ok"]: p.append(f"validación: {r['motivo']}")
    if MARCA.findall(en) != MARCA.findall(es): p.append("marcadores distintos")
    if len(ING.findall(MARCA.sub("", es))) >= 2: p.append("posible inglés restante")
    for a, b in glos:
        if re.search(r"(?<![a-z])" + re.escape(a.lower()) + r"(?![a-z])", en.lower()) and b.lower() not in es.lower() and a.lower() != b.lower():
            p.append(f"glosario: «{a}» → «{b}» no aparece")
    if "«" in es or "»" in es: p.append("comillas angulares")
    if p: prob[k] = p
json.dump(prob, open(V / "revision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(ultimo), "líneas;", len(prob), "con avisos")
for k, p in list(prob.items())[:60]: print(k, "|", ultimo[k]["en"][:50], "=>", ultimo[k]["es"][:50], "|", "; ".join(p)[:120])
