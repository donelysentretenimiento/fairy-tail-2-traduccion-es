# FAIRY TAIL 2 — Traducción al español

Traducción **no oficial** de aficionados al español de España · **By Donelys Entretenimiento**

![Instalador](docs/capturas/bienvenida.png)

## Qué incluye

- Menús, textos y diálogos en español, con la terminología de Fairy Tail revisada.
- Fuente con `ñ`, `¿`, `¡`, tildes y comillas, y texturas traducidas (título, menús, efectos de combate).
- Instalador para Windows: un único `.exe`, sin necesidad de Internet ni de ningún cargador de mods.

## Cómo se instala

1. Descarga el instalador desde [Releases](../../releases).
2. Ábrelo y elige la carpeta del juego (la que contiene `FAIRY_TAIL_2.exe`).
3. Pulsa **Instalar traducción**. Antes de cambiar nada se guarda una copia de seguridad.

Para volver al juego original: abre el instalador y pulsa **Restaurar originales**.

Necesitas tu propia copia de FAIRY TAIL 2. El instalador no incluye ningún archivo del juego: solo textos y diferencias que se aplican sobre tus archivos.

**Compatibilidad.** El instalador no comprueba sumas de verificación de tus archivos: acepta cualquier versión del juego cuya estructura sea la esperada y rechaza, sin tocar nada, las que no lo son. Antes de instalar guarda una copia de tus archivos y, si algo falla o cancelas, lo revierte todo.

## Para desarrolladores

```bash
dotnet build src/FT2ES.slnx -c Release
dotnet publish src/FT2ES.App -c Release -r win-x64 --self-contained
```

Las pruebas del motor (`src/FT2ES.EngineTests`) necesitan tus propios archivos originales del juego: define `FT2_TRABAJO` con la carpeta que contiene `backups_juego\`.

## Licencias

Código: [MIT](LICENSE). Componentes de terceros: [NOTICE.md](NOTICE.md). Agradecimientos: [AGRADECIMIENTOS.md](AGRADECIMIENTOS.md).

FAIRY TAIL es obra de Hiro Mashima. FAIRY TAIL 2 pertenece a KOEI TECMO GAMES y Gust. Este proyecto no está afiliado a ellos ni a Kodansha.
