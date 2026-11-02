# Componentes de terceros incluidos en el instalador

El instalador (EXE) incorpora estos componentes. Sus licencias están en la carpeta [`licencias/`](licencias/).

| Componente | Licencia | Dónde |
|---|---|---|
| **gust_tools** (`gust_enc.exe`, sin modificar, commit `c93b4b71`) — https://github.com/VitaSmith/gust_tools | GPL-3.0 o posterior (con aviso tipo zlib en algunas partes) | `third_party/gust_tools/`, `licencias/gust_tools_LICENSE.txt` |
| **Microsoft WebView2 SDK** | BSD de Microsoft | `licencias/WebView2_LICENSE.txt`, `licencias/WebView2_NOTICE.txt` |
| **.NET / WPF** | MIT | https://github.com/dotnet |
| **DirectXTex / texconv** (solo para generar texturas; no va en el EXE) | MIT | `licencias/DirectXTex_MIT.txt` |

`gust_enc.exe` se ejecuta como programa independiente; el código fuente correspondiente es el del repositorio indicado, en el commit citado, sin cambios.

El juego FAIRY TAIL 2, sus textos, imágenes y marcas pertenecen a sus titulares. Este repositorio no contiene archivos del juego.

Los nombres, enlaces y datos de fichas de `datos/wiki_es_hechizos.json` y del glosario proceden de la **Fairy Tail Wiki en español** (Fandom), contenido bajo CC BY-SA 3.0; solo se recogen títulos, nombres y enlaces, no los artículos.
