# Auditoría forense de terminología de ataques y habilidades

## Alcance y método
- **Inventario** (`datos/inventario.csv`): 2.136 IDs de 24 prefijos; el glosario cubre los 914 nombres (ACTION_NAME 780, TEAMSKILL_NAME 50, SKILL_TREE_ORIGIN_NAME 84).
- **Prueba de identidad = japonés del propio juego.** Se descifró `MASTER/JPN/fixed_data/message/message.json.e` y se cruzó por ID (`tools/terminologia/cruce_japones.py`): el kanji del ID debe ser idéntico al campo `Kanji` de UNA ficha de la wiki ES (índice completo de 1.132 fichas con plantilla `Hechizos`, `datos/wiki_es_hechizos.json`). El nombre inglés ya no prueba nada por sí solo.
- **Fuentes**: Fairy Tail Wiki en español (nivel 3, no oficial; consultada por API y en el navegador). **No consultados**: manga de Norma, doblaje de España ni fansubs; **ningún término está CONFIRMADO POR EDICIÓN ESPAÑOLA**. La guía gamecap.jp no se necesitó: el japonés sale del propio juego.
- Scripts: `tools/terminologia/{recolectar_wiki,emparejar_es,indexar_hechizos_es,recolectar_personajes,puente_variantes,inventario,cruce_japones,localizar_pendientes,glosario}.py`. Un único recolector (`recolector.lock`) con caché por petición (`http_cache/`).

## Resultados (914 filas de nombres)
| Estado | Filas |
|---|---|
| DOCUMENTADO POR LA COMUNIDAD (wiki ES, kanji idéntico o revisada a mano) | 118 |
| LOCALIZACIÓN PROPIA (Ortenzya + japonés del juego; sin fuente española) — aplicada | 187 |
| NOMBRE CONSERVADO (nombre propio/técnico o la wiki lo mantiene en inglés) | 166 |
| LOCALIZACIÓN PROPIA (Ortenzya previa, sin revisar ni fuente) — sin cambios | 370 |
| Ranuras vacías del juego (no se tocan) | 70 |
| PENDIENTE (cadenas con marcador `ATK + <NUM0>%`) | 3 |

**304 IDs cambiados** (117 de la wiki + 187 de localización propia) en `traduccion/terminologia_overrides.json`, aplicados por `tools/traduccion/integrar_ia.py` antes de `correcciones.json`. Antes/después: 304 cambiados, 0 fuera de los overrides, 0 ranuras vacías tocadas, 0 marcadores alterados, 0 rechazos. Copia previa en `datos/antes/`.

## Revisión de las 92 correcciones anteriores
64 quedan **probadas por kanji idéntico** (0 contradicen el japonés). De las 28 restantes (14 técnicas) se mantienen 10 con la salvedad registrada en el CSV (variante simplificada, puntuación, kana) y se retiran 3 sin apoyo: Sand Wave, Water Blast y Crush.

## Errores propios detectados
1. Pasada intermedia: ~71 ranuras vacías rellenadas con «Narukami» (corregido; ahora las ranuras vacías nunca se tocan).
2. Se descartó Famished Soul con información incompleta; ahora resuelto con el japonés del ID.

## Pruebas
- Integración y marcadores: hechas. Paquete del instalador reconstruido (ver `RESULTADOS_PRUEBAS.md`).
- **Prueba real en el juego (2026-11-02, Windows):** instalado el `message.json.e` nuevo , arranque correcto, título/menús/ayuda en español. En el combate contra Ajeel Raml (capturas en `datos/juego/`: `evento_04.png`, `c2_01.png`, `c2_03.png`, `c2_05.png`) se ven **«Puño de Hierro del Dragón de Fuego»** (Y/1), **«Rugido del Dragón de Fuego»** (B/2) y la técnica enemiga **«Espada de Arena»**, con tildes correctas y **sin desbordes** en la rueda de comandos ni en el banner. Visto en juego: 3 de los 304 nombres.
- **No visto aún:** técnicas de Lucy, Erza, Wendy y demás, árbol de habilidades, Unison Raid, tutoriales de técnicas y diálogos con técnicas (EBM).

## Pendientes auténticos
1. Contrastar con Norma y el doblaje de España para llegar a CONFIRMADO; fansubs no investigados.
2. Los 187 nombres de localización propia son criterio, no fuente: revisarlos con anime/manga.
3. 370 traducciones de Ortenzya previas siguen sin fuente; columna «Personaje» casi vacía.
4. No auditados: descripciones, estados, tutoriales, los 513 EBM (nombres de técnicas en diálogos) y personajes DLC/apoyo.
5. Cadenas con marcador (`ATK + <NUM0>%`) sin tratar.
6. Ampliar la prueba visual en el juego (solo se vieron 3 nombres).

## Auditoría de los diálogos EBM y restos en inglés (2026-11-02)
- **EBM** (`tools/terminologia/auditar_ebm.py` → `docs/AUDITORIA_EBM_TECNICAS.csv`): 7.103 líneas, 50 menciones de técnicas por su nombre. 25 estaban inconsistentes con el glosario (p. ej. «Rugido del Dragon Slayer de Fuego», «Sobre Skelter» por Over Skelter, nombres en inglés) y se corrigieron **por línea** (`traduccion/ebm_correcciones.json` + `tools/terminologia/corregir_ebm.py`, idempotente, ejecutar tras `construir_ebm.py`). Después, 6 líneas más con inglés residual (Hmph, *Gulp*, *Sigh*, «otro strongest»). Comprobado: 31 líneas cambiadas en 19+ archivos, cabeceras, colas y marcadores intactos. Las 7 discrepancias que quedan son falsos positivos justificados (concepto «esencia de la magia», poema «Water Bind of Love»).
- **Consolidación de términos** (`tools/terminologia/normalizar_terminos.py` → `traduccion/terminologia_textos.json`, por ID): Link Attack → «Ataque enlazado» (dossier), Fairy Rank → «Rango de Fairy», Break (sustantivo) → «Ruptura», Bane Particles → «Partículas Bane», Grand Chariot y Eternal Flare conservados. 38 cambios por ID y frase.
- **Restos en inglés** (`tools/terminologia/restos_ingles.py` → `traduccion/restos_ingles.json`, `docs/AUDITORIA_RESTOS_INGLES.csv`): de 1.127 mensajes idénticos al inglés, ~840 son legítimos (créditos 442+62, nombres de personajes 85+83, técnicas conservadas, licencias legales, términos gráficos). Se tradujeron **135**: 97 efectos de objeto (antes totalmente sin traducir, p. ej. «Tuning Heart M» → «Corazón de Afinación M», «Puni Slayer» → «Cazador de Punis»), apodos de Spriggan, monstruos/jefes, títulos de evento, «Taller de Lucy», dificultades. Propuestas del modelo con correcciones manuales (el modelo copió el efecto japonés en 12 nombres); son **localización propia**.
- **Flechas ↑/↓** (41 cadenas): no existen en la fuente del juego; sustituidas por «+»/«-» en `integrar_ia.py` (SUST).
- **Texturas** (`tools/texturas/efectos_combate_es.py`, `extraer_candidatas.py`): hojas de efectos de combate `dfd3bf79` (2048) y `d2c84a3b` (1024): LINK ATTACK → ATAQUE ENLAZADO, BREAK → RUPTURA, **WEAK → DÉBIL, RESIST → RESISTE**, CURED → CURADO, MISS → FALLO, NO EFFECT → SIN EFECTO, DAMAGE → DAÑO, NEXT → SIG., FAIRY RANK → RANGO/FAIRY, FAIRY RANK UP! → ¡RANGO DE FAIRY AUMENTADO!. UNISON RAID, COMBO, logos y dígitos se conservan. Las otras 12 texturas localizadas son logotipos y avisos legales (Gust, Koei Tecmo, Hiro Mashima, aviso japonés) y se dejan.
- **Visto en el juego**: DÉBIL / RESISTE en la ficha de Natsu («Resistencia elemental»); combate real con «Puño de Hierro del Dragón de Fuego», «Rugido del Dragón de Fuego» y «Espada de Arena»; título, menús, Base de datos y Ayuda en español; arranque correcto con todo instalado. **No visto**: ATAQUE ENLAZADO, RUPTURA, FALLO, CURADO, SIN EFECTO y los efectos de objeto (la prueba derivó en la pantalla Guardar sin guardar nada).
- **Sin resolver / observado**: «Velocida» → **«Veloz»** (`STR_BATTLE_DEFINE_057`, vía `traduccion/correcciones.json`; cabe en las dos pantallas, visto en juego); sigue cortado «Defens(a)» en Personajes (caja de ~6 caracteres, `STR_BATTLE_DEFINE_056`); «DATA» de Guardar sigue en inglés (textura no localizada); carpeta `word` ya revisada (sin texto traducible, ver abajo); licencias legales en inglés por decisión previa.
- Carpeta `word` revisada: `MASTER/ENG` no la tiene (solo JPN y FRA, 288 y 240 B). `word.xml.e` es una tabla gramatical de artículos (definido/indefinido, singular/plural) con valores de prueba (`TEST`, `CHARACTER_TEST`) y `COMMON_NOTHING` («なし»); en inglés no se usa. Sin texto traducible; no hay que crear nada para el español.
