import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EN = ROOT / "referencia_actual" / "message"
OLD = ROOT / "originales" / "bundle_traduccion" / "message"
OUT = ROOT / "traduccion" / "menu"
FILES = (
    "str_menu_define", "str_quick_menu_define", "str_quick_menu_command_name",
    "str_quick_menu_command_text", "str_option_define", "str_saveload_define",
    "str_balloon_select", "str_key_guide", "str_system_message", "str_dlc_title_steam",
)
MARKER = re.compile(r"(<[^<>]+>|\^[0-9]+|%[0-9$]*[sdif])")
TECHNICAL = re.compile(r"^(?:<[^<>]+>|\^[0-9]+|%[0-9$]*[sdif]|[0-9x.＋★ /®-])+$")

EXACT = {
    "No": "No", "Morning": "Mañana", "Day": "Día", "Dusk": "Atardecer", "Night": "Noche",
    "Normal": "Normal", "General": "General", "Balanced": "Equilibrado", "Performance": "Rendimiento",
    "Ultra Quality Plus": "Calidad ultra plus", "Ultra Quality": "Calidad ultra", "Ultra Performance": "Rendimiento ultra",
    "Native Anti-Aliasing": "Suavizado nativo", "Cursor": "Cursor", "Unison Raid": "Unison Raid",
    "Do you want to save changes before exiting?": "¿Quieres guardar los cambios antes de salir?",
    "All settings will be restored to their default values. Proceed?": "Se restablecerán todos los ajustes predeterminados. ¿Quieres continuar?",
    "Save Settings": "Guardar ajustes", "Inverted": "Invertida", "Change with <IM15>": "Cambiar con <IM15>",
    "Change with <IM13>": "Cambiar con <IM13>", "STORY": "HISTORIA", "BALANCED": "EQUILIBRADA",
    "HARD": "DIFÍCIL", "RAGNAROK": "RAGNAROK", "Quality": "Calidad", "Mid": "Media",
    "Edit Button Assignment": "Editar asignación de botones", "Shallow": "Baja", "Semi-Shallow": "Media-baja",
    "Semi-Deep": "Media-alta", "Deep": "Alta", "Camera<CR>Settings": "Ajustes de<CR>cámara",
    "Control<CR>Settings": "Ajustes de<CR>controles", "Game<CR>Settings": "Ajustes del<CR>juego",
    "Graphics<CR>Settings": "Ajustes<CR>gráficos", "Audio<CR>Settings": "Ajustes de<CR>sonido",
    "Vertical Camera": "Cámara vertical", "Horizontal Camera": "Cámara horizontal", "Zoom Controls": "Controles de zoom",
    "Camera Sensitivity (Vertical)": "Sensibilidad de cámara (vertical)", "Camera Sensitivity (Horizontal)": "Sensibilidad de cámara (horizontal)",
    "Camera Autocorrect": "Autocorrección de cámara", "Button Assignment": "Asignación de botones",
    'Reassign "Confirm" Button': 'Reasignar botón «Confirmar»', "Vibration": "Vibración", "Rumble": "Vibración",
    "Dash Movement Input": "Entrada para correr", "Cursor Speed": "Velocidad del cursor", "Difficulty": "Dificultad",
    "Autosave": "Guardado automático", "Map Rotation": "Rotación del mapa", "Compass Display": "Mostrar brújula",
    "Field Dialog": "Diálogos de exploración", "Event Autoplay": "Reproducción automática de eventos",
    "Event Dialog": "Diálogos de eventos", "Operation Mode": "Modo de funcionamiento",
    "Local Reflection Quality": "Calidad de reflejos locales", "DOF": "Profundidad de campo",
    "Motion Blur": "Desenfoque de movimiento", "Bloom": "Resplandor", "Light Shaft": "Haces de luz",
    "BGM Volume": "Volumen de música", "SFX Volume": "Volumen de efectos", "Speech Volume": "Volumen de voces",
    "Cutscene Volume": "Volumen de cinemáticas", "Font Color Support": "Ayuda mediante colores de texto",
    "Would you like to configure the options?": "¿Quieres configurar las opciones?",
    "Are you sure you want to restore to default settings?": "¿Seguro que quieres restablecer los ajustes predeterminados?",
    "Button reassignment settings": "Ajustes de reasignación de botones", "Select the button used to confirm.": "Selecciona el botón de confirmación.",
    "Configure resolution scaling to improve image quality and frame rate.": "Configura el escalado de resolución para mejorar la calidad de imagen y la tasa de fotogramas.",
    "Take a defensive stance.": "Adopta una postura defensiva.", "Change the attack target (left).": "Cambia el objetivo del ataque (izquierda).",
    "Change the attack target (right).": "Cambia el objetivo del ataque (derecha).", "Change target": "Cambiar objetivo",
    "Control camera direction (Unchangeable)": "Controlar dirección de la cámara (no se puede cambiar)",
    "Open pose screen": "Abrir pantalla de poses", "Use up Awakening Gauge to awaken": "Consume el medidor de Despertar para despertar",
    "Use Extreme Magic": "Usar Magia extrema", "Skip battle animation": "Omitir animación de combate",
    "Disable battle animation skipping": "Desactivar omisión de animaciones de combate", "Change character": "Cambiar de personaje",
    "Change camera display distance": "Cambiar distancia de la cámara", "Toggle between ally and enemy information": "Alternar información de aliados y enemigos",
    "Display skill information": "Mostrar información de habilidades", "Switch character displaying information": "Cambiar el personaje cuya información se muestra",
    "Scroll the screen": "Desplazar la pantalla", "Return to battle": "Volver al combate", "Toggle magic sheet displayed": "Cambiar la hoja de magia mostrada",
    "Move the cursor": "Mover el cursor", "Select an item on the list. ": "Selecciona un elemento de la lista. ",
    "Use to switch between items. (Cannot be changed.)": "Permite cambiar de elemento. (No se puede modificar.)",
    "Move camera position": "Mover la cámara", "Control the camera.": "Controla la cámara.", "Reset the camera position.": "Restablece la posición de la cámara.",
    "Rotate the camera.": "Gira la cámara.", "Make the screen roll.": "Inclina la pantalla.", "Choose the Zoom in button.": "Selecciona el botón de acercar.",
    "Choose the Zoom out button.": "Selecciona el botón de alejar.", "Change the operating speed.": "Cambia la velocidad de funcionamiento.",
    "Toggle the UI display On/Off.": "Muestra u oculta la interfaz.", "Switch to Character Control Mode.": "Cambia al modo de control del personaje.",
    "Choose the Confirm button for all screens.": "Selecciona el botón de confirmación para todas las pantallas.",
    "Choose the Cancel button for all screens.": "Selecciona el botón de cancelación para todas las pantallas.",
    "Align the character with the focal point.": "Alinea el personaje con el punto focal.", "Use to switch between items. ": "Permite cambiar de elemento. ",
    "Cancel. ": "Cancelar. ", "Change to Camera Control Mode.": "Cambia al modo de control de cámara.",
    "Move the character horizontally.": "Mueve el personaje horizontalmente.", "Move the character vertically.": "Mueve el personaje verticalmente.",
    "Rotate the character.": "Gira el personaje.", "Perform a skill": "Usar una habilidad", "Move the cursor to the Goal Icon": "Mover el cursor al icono de objetivo",
    "Select character to swap out": "Seleccionar personaje que sustituir", "Select ally to perform a Link Attack or Unison Raid": "Seleccionar aliado para ejecutar un Ataque de vínculo o Unison Raid",
    "Display Guide Marks": "Mostrar señales de orientación", "Switch Map": "Cambiar mapa",
    "The additional content required for the selected save data is not installed. The load has been canceled.": "No está instalado el contenido adicional necesario para los datos guardados seleccionados. Se ha cancelado la carga.",
    "You do not have any items which can be given.": "No tienes ningún objeto que puedas entregar.",
    "Are you sure you want to skip?": "¿Seguro que quieres omitirlo?", "Please wait...": "Espera...", "Creating system data...": "Creando datos del sistema...",
    "Change Category": "Cambiar categoría", "Change Page": "Cambiar de página", "Change Character": "Cambiar de personaje",
    "Remove": "Retirar", "Sort": "Ordenar", "OK": "Aceptar", "Reset": "Restablecer", "Use": "Usar",
    "Check": "Examinar", "Show Manual": "Mostrar manual", "Lv. ": "Nv. ", "Skill List": "Lista de habilidades",
    "Skill Detail": "Detalles de habilidad", "Passive": "Pasiva", "Main Menu": "Menú principal", "Quests": "Misiones",
    "Party": "Grupo", "Changing Room": "Vestuario", "Battle Preparation": "Preparativos de combate", "System": "Sistema",
    "Character": "Personaje", "Team": "Equipo", "Database": "Base de datos", "Magic Origin": "Origen mágico",
    "Skill Equip": "Equipar habilidades", "Equip Lacrima": "Equipar Lácrimas", "Details": "Detalles",
    "Rest Effect": "Efecto de descanso", "Target": "Objetivo", "Style": "Estilo", "Break Damage": "Daño de ruptura",
    "Skill Sheet Change": "Cambiar hoja de habilidades", "World Encyclopedia": "Enciclopedia del mundo",
    "Item Info": "Información de objetos", "Enemy Info": "Información de enemigos", "Extreme Magic": "Magia extrema",
    "ALL": "TODO", "Required Items": "Objetos necesarios", "Lucy's Novel": "Novela de Lucy", "Main Events": "Eventos principales",
    "Character Events": "Eventos de personajes", "Other Events": "Otros eventos", "Prologue": "Prólogo",
    "Camera Control": "Control de cámara", "Power": "Potencia", "Element": "Elemento", "Requirements": "Requisitos",
    "Passive Skills": "Habilidades pasivas", "Type": "Tipo", "Sub-Menu": "Submenú", "Elemental Resistance": "Resistencia elemental",
    "Awakening Information": "Información de Despertar", "Consumption Gauge": "Medidor de consumo",
    "Awakening Gauge": "Medidor de Despertar", "Finisher Skill": "Habilidad final", "Flashback Episode": "Episodio de recuerdos",
    "Auto Training Complete!": "¡Entrenamiento automático completado!", "Skill Learned": "Habilidad aprendida",
    "Insufficient Lacrima": "Lácrimas insuficientes", "Combat Characters": "Personajes combatientes", "Support": "Apoyo",
    "Extreme Magic List": "Lista de Magia extrema", "Reserve Team": "Equipo de reserva", "Supporting Characters": "Personajes de apoyo",
    "Set all Combat Characters": "Asignar todos los personajes combatientes", "Confirm Support": "Confirmar apoyo",
    "Change Active Party Members": "Cambiar miembros activos del grupo", "Story Completed": "Historia completada",
    "Arena": "Arena", "Rematch": "Revancha", "Trial Mode": "Modo desafío", "Exit Arena": "Salir de la Arena",
    "VICTORY!": "¡VICTORIA!", "New Record": "Nuevo récord", "First Reward": "Primera recompensa", "Record": "Récord",
    "Jump": "Saltar", "Next": "Siguiente",
    "Change Cursor Speed": "Cambiar velocidad del cursor",
}

UNCHANGED = {"No", "Normal", "General", "Arena", "RAGNAROK", "Unison Raid", "Cursor", "Intel® XeSS", "MSAA", "TAA", "FXAA", "<STR0>:<STR1>", "<CLOR>MVP<CLNR>"}

BY_ID = {
    "STR_MENU_DEFINE_268": "¿Volver al título?<CR><CLRE>Nota: se perderán todos los datos no guardados.<CLNR>",
    "STR_MENU_DEFINE_359": "<KEY_ASSIGN_BASIC_ANALOGSTICK_R>Control de cámara",
    "STR_MENU_DEFINE_390": "Accede al siguiente enlace desde tu PC o dispositivo móvil para consultar el manual del juego.",
    "STR_MENU_DEFINE_391": "No se ha podido conectar a la red. Accede al siguiente enlace desde tu PC o dispositivo móvil para consultar el manual del juego.",
    "STR_MENU_DEFINE_393": "¿Formar pareja con Natsu?", "STR_MENU_DEFINE_394": "¿Preguntar a Gray y Juvia?",
    "STR_MENU_DEFINE_395": "¿Preguntar a Gajeel y Levy?", "STR_MENU_DEFINE_396": "¿Preguntar a Erza y Jellal?",
    "STR_MENU_DEFINE_403": "Se han desbloqueado los siguientes elementos:<CR><CR>Atuendo de Natsu: «Juego anterior de Fairy Tail»<CR>Atuendo de Lucy: «Juego anterior de Fairy Tail»<CR>Atuendo de Lucy: «Vestido estelar: forma de Tauro»<CR>Atuendo de Lucy: «Vestido estelar: forma de Sagitario»<CR>Atuendo de Lucy: «Vestido estelar: forma de Acuario»<CR>Atuendo de Erza: «Juego anterior de Fairy Tail»<CR>Atuendo de Erza: «Armadura Rueda del Cielo»<CR>Atuendo de Erza: «Hakama carmesí»<CR>Atuendo de Erza: «Armadura del Dios del Viento»<CR>Atuendo de Erza: «Armadura Nakagami»<CR>Atuendo de Gray: «Juego anterior de Fairy Tail»<CR>Atuendo de Laxus: «Juego anterior de Fairy Tail»<CR>Atuendo de Wendy: «Juego anterior de Fairy Tail»<CR>Atuendo de Gajeel: «Juego anterior de Fairy Tail»<CR>Atuendo de Juvia: «Juego anterior de Fairy Tail»<CR>Atuendo de Mirajane: «Juego anterior de Fairy Tail»<CR>Atuendo de Gildarts: «Juego anterior de Fairy Tail»",
    "STR_MENU_DEFINE_418": "¿Ver esta historia desde el punto de vista de Natsu?", "STR_MENU_DEFINE_419": "¿Ver esta historia desde el punto de vista de Lucy?",
    "STR_MENU_DEFINE_420": "Si continúas, no podrás volver a la misión principal hasta que completes el evento. ¿Quieres continuar?",
    "STR_MENU_DEFINE_425": "Vuelve a enfrentarte a enemigos poderosos contra los que ya has luchado.",
    "STR_MENU_DEFINE_426": "Supera una exigente serie de combates contra varios enemigos poderosos.",
    "STR_MENU_DEFINE_427": "Sal de la Arena y vuelve a Magnolia.", "STR_MENU_DEFINE_428": "¿Salir de la Arena y volver a Magnolia?",
    "STR_MENU_DEFINE_429": "¿Salir de la Arena y volver a Magnolia?<CR><CLRE>Nota: se restablecerá tu progreso.<CLNR>",
    "STR_MENU_DEFINE_430": "¿Iniciar un combate?<CR>Dificultad: <STR0>",
    "STR_MENU_DEFINE_431": "¿Reintentar el combate?<CR><CLRE>Nota: si estás disputando una serie de combates, <CR>volverás a empezar desde el primero.",
    "STR_MENU_DEFINE_434": "Dificultad: <STR0>", "STR_MENU_DEFINE_438": "Revancha: <STR0>", "STR_MENU_DEFINE_439": "Desafío: <STR0>",
    "STR_MENU_DEFINE_442": "¿Salir de la historia «Aguas termales de Fairy Tail»?<CR>Después podrás volver a jugarla desde el principio interactuando de nuevo con este cartel.",
    "STR_MENU_DEFINE_445": "<CLOR>Mejor récord<CLNR>", "STR_MENU_DEFINE_447": "¿Ir a la Arena?",
    "STR_MENU_DEFINE_500": "<CLRE>Cambiar la dificultad durante una serie de combates de la Arena no modificará el poder de los enemigos. Los cambios se aplicarán cuando termine la serie.<CLNR>",
    "STR_MENU_DEFINE_501": "Se ha añadido «Acnologia» a las revanchas de la Arena.",
    "STR_QUICK_MENU_DEFINE_262": "Selecciona una tecla.<CR><CLRE>Nota:<CLNR>«%s»<CLRE> no se puede utilizar en este ajuste.<CLNR>",
    "STR_OPTION_DEFINE_123": "Hay dos ajustes para el control vertical de la cámara:<CR>- Normal: al empujar <IM27> hacia delante, la cámara sube.<CR>- Invertida: al empujar <IM27> hacia delante, la cámara baja.",
    "STR_OPTION_DEFINE_124": "Hay dos ajustes para el control horizontal de la cámara:<CR>- Normal: al inclinar <IM27> a la derecha, la cámara se mueve a la derecha.<CR>- Invertida: al inclinar <IM27> a la derecha, la cámara se mueve a la izquierda.",
    "STR_OPTION_DEFINE_125": "Hay dos ajustes de zoom disponibles:<CR>- Normal: pulsa <KEY_ASSIGN_FIELD_ZOOM_IN> para acercar <CR>　y <KEY_ASSIGN_FIELD_ZOOM_OUT> para alejar.<CR>- Invertido: pulsa <KEY_ASSIGN_FIELD_ZOOM_OUT> para acercar <CR>　y <KEY_ASSIGN_FIELD_ZOOM_IN> para alejar.",
    "STR_OPTION_DEFINE_126": "La velocidad vertical de la cámara tiene diez niveles.<CR>Cuanto mayor sea el número, más rápido se moverá la cámara.",
    "STR_OPTION_DEFINE_127": "La velocidad horizontal de la cámara tiene diez niveles.<CR>Cuanto mayor sea el número, más rápido se moverá la cámara.",
    "STR_OPTION_DEFINE_129": "Actívalo para restablecer automáticamente la cámara detrás del personaje.",
    "STR_OPTION_DEFINE_133": "Selecciona el botón utilizado para confirmar.",
    "STR_OPTION_DEFINE_134": "Actívalo para habilitar la vibración del mando.<CR><CLGR>Nota: solo se aplica a mandos <CR>compatibles con vibración.<CLNR>",
    "STR_OPTION_DEFINE_135": "Actívalo para habilitar la vibración del mando.",
    "STR_OPTION_DEFINE_136": "Actívalo para habilitar la vibración del mando inalámbrico.",
    "STR_OPTION_DEFINE_137": "Configura la entrada para correr.<CR>■Pulsa <KEY_ASSIGN_FIELD_DASH>＋<KEY_ASSIGN_FIELD_MOVE>:<CR>Solo corres mientras mantienes pulsado <KEY_ASSIGN_FIELD_DASH>.<CR>■Cambiar con <KEY_ASSIGN_FIELD_DASH>:<CR>Alterna el movimiento del personaje entre caminar y correr con <KEY_ASSIGN_FIELD_DASH>.",
    "STR_OPTION_DEFINE_139": "La velocidad del cursor en el mapa del mundo tiene diez niveles.<CR>Cuanto mayor sea el número, más rápido se moverá el cursor.",
    "STR_OPTION_DEFINE_141": "Cambia la dificultad del juego.<CR><CLGR>Puedes cambiarla durante la partida. No afecta al progreso ni al desarrollo de los personajes.<CLNR><CR><CR>-HISTORIA: Para quienes quieran disfrutar tranquilamente de la historia.<CR>-EQUILIBRADA: Para quienes quieran disfrutar de la historia y los combates.<CR>-DIFÍCIL: Para quienes busquen combates exigentes.<CR>-RAGNAROK: Para quienes quieran enfrentarse a los enemigos más poderosos.",
    "STR_OPTION_DEFINE_142": "Actívalo para habilitar el guardado automático.",
    "STR_OPTION_DEFINE_143": "Actívalo para que el mapa gire según la orientación de la cámara.",
    "STR_OPTION_DEFINE_144": "Actívalo para mostrar la brújula en la parte superior de la pantalla.",
    "STR_OPTION_DEFINE_145": "Actívalo para mostrar subtítulos en los diálogos de exploración que no formen parte de un evento.",
    "STR_OPTION_DEFINE_147": "La velocidad de reproducción automática tiene diez niveles.<CR>Cuanto mayor sea el número, más rápido avanzará el texto durante los eventos.",
    "STR_OPTION_DEFINE_148": "Al activarlo, los diálogos de exploración aparecen como texto en pantalla.",
    "STR_OPTION_DEFINE_150": "Puedes dar prioridad a distintos aspectos durante la partida.<CR>- Calidad: prioriza la calidad de imagen, pero aumenta la carga de procesamiento.<CR>- Rendimiento: prioriza la fluidez, pero reduce la calidad de imagen.",
    "STR_OPTION_DEFINE_151": "Ajusta la calidad de los reflejos locales en tiempo real (RLR).",
    "STR_OPTION_DEFINE_152": "Ajusta la profundidad de campo.", "STR_OPTION_DEFINE_153": "Indica si se aplica desenfoque al moverse los objetos.",
    "STR_OPTION_DEFINE_154": "Activa o desactiva el resplandor.", "STR_OPTION_DEFINE_155": "Activa o desactiva los haces de luz.",
    "STR_OPTION_DEFINE_157": "El volumen de la música tiene diez niveles. <CLGR>Puedes silenciarla ajustándolo a 0<CLNR>.",
    "STR_OPTION_DEFINE_158": "El volumen de los efectos tiene diez niveles. <CLGR>Puedes silenciarlos ajustándolo a 0<CLNR>.",
    "STR_OPTION_DEFINE_159": "El volumen de las voces tiene diez niveles. <CLGR>Puedes silenciarlas ajustándolo a 0<CLNR>.",
    "STR_OPTION_DEFINE_160": "Puedes ajustar el volumen de los efectos y las voces de las cinemáticas entre 0 y 10.<CR>Cuanto mayor sea el valor, mayor será el volumen.<CR>El valor 0 <CLGR>silencia los efectos y las voces.<CLNR>",
    "STR_OPTION_DEFINE_174": "Cambia el color de determinados textos de la siguiente forma:<CR><CLGR>Texto<CLNR><CR><CLRE>Texto<CLNR><CR><CLYL>Texto<CLNR><CR><CLOR>Texto<CLNR><CR><CLPU>Texto<CLNR>",
}

SEGMENTS = {
    "Move": "Mover", "Change": "Cambiar", "Return": "Volver", "Volume": "Volumen", "Deliver": "Entregar",
    "Display": "Mostrar", "Submenu": "Submenú", "Auto-Play": "Reproducción automática", "Event Log": "Registro de eventos",
    "Close Menu": "Cerrar menú", "Select the": "Seleccionar", "Show Manual": "Mostrar manual", "Adjust Speed": "Ajustar velocidad",
    "Attack Burst": "Ráfaga de ataque", "Requirements": "Requisitos", "Select Enemy": "Seleccionar enemigo",
    "Special Menu": "Menú especial", "Check Enemies": "Examinar enemigos", "Move / Rotate": "Mover / Girar",
    "Select Recipe": "Seleccionar receta", "Booster Charge": "Carga de impulso", "Remove Lacrima": "Retirar Lácrima",
    "Show / Hide UI": "Mostrar / Ocultar interfaz", "Play voice-over": "Reproducir voz", "Add 1 Ingredient": "Añadir 1 ingrediente",
    "Tracking Setting": "Configurar seguimiento", "Check Terminology": "Consultar terminología", "Change Terminology": "Cambiar terminología",
    "Show / Hide All UI": "Mostrar / Ocultar toda la interfaz", "Zoom In / Zoom Out": "Acercar / Alejar",
    "Remove 1 Ingredient": "Retirar 1 ingrediente", "Select the Quantity": "Seleccionar cantidad",
    "Change Score Display": "Cambiar visualización de puntuación", "Remove Ability Piece": "Retirar pieza de habilidad",
    "Return to Current Location": "Volver a la ubicación actual", "Return to Current Position": "Volver a la posición actual",
    "Add to / Delete from Wishlist": "Añadir a / Eliminar de favoritos",
    "Select": "Seleccionar", "Confirm": "Confirmar", "Cancel": "Cancelar", "Back": "Volver", "Change Page": "Cambiar de página",
    "Change UI Display": "Cambiar visualización de la interfaz", "Reset Settings": "Restablecer ajustes", "Details": "Detalles",
    "Guard": "Defender", "Skip": "Omitir", "Jump": "Saltar", "Dash": "Correr", "Field Attack": "Ataque en el campo",
    "Main Menu": "Menú principal", "Running Dash": "Carrera", "Change Main Character": "Cambiar personaje principal",
    "Guide Marks": "Señales de orientación", "Zoom In": "Acercar", "Zoom Out": "Alejar", "Change Page": "Cambiar de página",
    "Next": "Siguiente",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def records(doc):
    return [item for value in doc.values() if isinstance(value, list) for item in value if isinstance(item, dict) and "MESSAGE" in item]


def marker_list(text):
    return MARKER.findall(text)


def translate_segments(text):
    pieces = re.split(r"(<[^<>]+>)", text)
    changed = False
    for i, piece in enumerate(pieces):
        lead, core, tail = piece[: len(piece) - len(piece.lstrip())], piece.strip(), piece[len(piece.rstrip()) :]
        if core in SEGMENTS:
            pieces[i] = lead + SEGMENTS[core] + tail
            changed = True
    return "".join(pieces) if changed else text


def validate(source, target, stem):
    left, right = records(source), records(target)
    assert len(left) == len(right), f"record count: {stem}"
    for original, translated in zip(left, right):
        assert list(original) == list(translated), f"keys/order: {stem}:{original.get('NAME_LABEL')}"
        assert all(original[key] == translated[key] for key in original if key != "MESSAGE"), f"protected field: {stem}:{original.get('NAME_LABEL')}"
        assert marker_list(original["MESSAGE"]) == marker_list(translated["MESSAGE"]), f"markers: {stem}:{original.get('NAME_LABEL')}"


def self_check():
    sample = "<KEY_A>Select <KEY_B>Back"
    assert translate_segments(sample) == "<KEY_A>Seleccionar <KEY_B>Volver"
    assert marker_list(sample) == marker_list(translate_segments(sample))


def main():
    self_check()
    OUT.mkdir(parents=True, exist_ok=True)
    unresolved = []
    translated = technical = inherited = 0
    for stem in FILES:
        source = load(EN / f"{stem}.json")
        target = load(OLD / f"{stem}.json")
        source_by_id = {x.get("NAME_LABEL"): x for x in records(source)}
        for item in records(target):
            label = item.get("NAME_LABEL")
            english = source_by_id[label]["MESSAGE"]
            if item["MESSAGE"] != english:
                inherited += 1
                continue
            if not english or TECHNICAL.fullmatch(english):
                technical += 1
                continue
            menu_number = int(label.rsplit("_", 1)[1]) if stem == "str_menu_define" and label else -1
            if english in UNCHANGED or (stem == "str_menu_define" and (menu_number in {405, 410, 411, 415, 416} or 450 <= menu_number <= 484)):
                technical += 1
                continue
            candidate = BY_ID.get(label, EXACT.get(english, english))
            chapter = re.fullmatch(r"Chapter (\d+)", english)
            bonus = re.fullmatch(r"Bonus Ch\. (\d+)", english)
            if chapter:
                candidate = f"Capítulo {chapter.group(1)}"
            elif bonus:
                candidate = f"Capítulo extra {bonus.group(1)}"
            if candidate == english and stem == "str_key_guide":
                candidate = translate_segments(english)
            if candidate != english:
                if marker_list(candidate) != marker_list(english):
                    raise ValueError(f"markers differ: {stem}:{label}")
                item["MESSAGE"] = candidate
                translated += 1
            else:
                unresolved.append((stem, label, english))
        validate(source, target, stem)
        (OUT / f"{stem}.json").write_text(json.dumps(target, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    print(f"inherited={inherited} translated={translated} technical={technical} unresolved={len(unresolved)}")
    for row in unresolved:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
