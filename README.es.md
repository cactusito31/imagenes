# Imagenes

*[English](README.md) · **Español***

Conversor y redimensionador de imagenes por terminal, con asistente guiado y
modo directo para automatizar. Convierte lotes a **WEBP, AVIF, JPG, PNG, GIF,
TIFF y BMP**, y lee ademas **HEIC/HEIF** (las fotos del iPhone).

[![tests](https://github.com/cactusito31/imagenes/actions/workflows/tests.yml/badge.svg)](https://github.com/cactusito31/imagenes/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

La salida va **siempre** a una subcarpeta `imagenes_convertidas` dentro de la
carpeta de origen (o donde digas con `-o`). Nunca toca los originales.

---

## Caracteristicas

- **Lotes recursivos**: replica el arbol de carpetas de origen, asi dos
  `foto.jpg` en subcarpetas distintas no se pisan.
- **Varios formatos y tamanos a la vez**: `-f webp,avif -s 800,1600`.
- **Presets** (`web`, `woo`, `rapido`, `maxima-calidad`) y presets propios.
- **Modos de encaje**: `ajustar`, `recortar`, `rellenar` (nunca amplian una
  imagen pequena).
- **Control de metadatos** (`limpiar` quita el EXIF, incluida la ubicacion GPS)
  y **de perfil de color** (`conservar` o convertir a `srgb`).
- **Conversion en paralelo** con techo de memoria: las conversiones
  simultaneas se frenan solas si entran panoramicas o escaneos grandes.
- **Escritura atomica**: se escribe a un `.tmp` y se renombra al final; un
  corte a media faena no deja un archivo con el nombre bueno y el contenido roto.
- **Modo vigilancia** (`--vigilar`): deja la carpeta abierta y convierte lo que
  vaya llegando.
- **Filtros**: `--excluir PATRON`, `--min-px N`, `--no-recomprimir`.
- **Gestion de originales**: `--originales dejar|mover|borrar` (solo borra si la
  conversion salio sin un solo error).
- **Informe** `reporte-FECHA.csv` con el ahorro real y `snippet.html` con el
  `<picture>`/`srcset` ya montado.
- Integracion con Windows: acceso directo, arrastrar carpeta sobre el `.exe`,
  menu contextual "Convertir imagenes" y "Enviar a".

## Instalacion

### Opcion A — descargar el ejecutable (Windows, sin instalar nada)

Descarga `imagenes-*-windows-x64.exe` de la
[ultima Release](https://github.com/cactusito31/imagenes/releases/latest) y
ejecutalo. No necesita Python.

> Windows SmartScreen puede avisar por ser un binario sin firmar: *Mas
> informacion > Ejecutar de todas formas*.

Para integrarlo en el sistema (acceso directo, menu contextual, comando
`imagenes` en la terminal), clona el repo y ejecuta `INSTALAR.bat`.

### Opcion B — con pipx / pip (cualquier sistema)

```sh
pipx install imagenes
imagenes --help
```

Para leer fotos HEIC/HEIF de iPhone: `pipx install "imagenes[heif]"`.

### Opcion C — desde el codigo

```sh
git clone https://github.com/cactusito31/imagenes
cd imagenes
python -m pip install -r requirements.txt
python imagenes.py --help
```

En Windows sin compilar nada tambien vale `EJECUTAR_sin_compilar.bat`.
Para generar tu propio `.exe`: `CREAR_EXE.bat` (usa `imagenes.spec`).

## Uso

### Asistente guiado

Ejecutalo sin argumentos y te va preguntando. Recuerda lo que elegiste la
ultima vez y lo ofrece por defecto.

```sh
imagenes
```

### Modo directo (sin preguntas)

Pensado para repetir y para automatizar: no hereda nada de la vez anterior, el
mismo comando da siempre el mismo resultado. Lo que no digas se queda en los
valores de fabrica (o en los del preset, con `--preset`).

```sh
imagenes C:\fotos --preset web
imagenes C:\fotos -f webp,avif -s 800,1600 -q 82
imagenes C:\fotos -f jpg -s 1000x1000 --encaje recortar
imagenes C:\fotos --preset woo --seo silla-oficina
imagenes C:\fotos --preset web --simular          # ensena lo que haria
imagenes C:\fotos --excluir borradores/* --min-px 400
imagenes C:\fotos --preset web --originales mover
imagenes C:\fotos --preset web --vigilar          # se queda esperando
imagenes --presets                                # lista los presets
imagenes --diagnostico                            # que hay disponible
imagenes --help                                   # todas las opciones
```

## Presets

| Preset           | Que hace                                                            |
|------------------|--------------------------------------------------------------------|
| `web`            | WEBP + AVIF en 800 y 1600, sin metadatos, en sRGB.                 |
| `woo`            | Cuadradas con fondo blanco en 300/800/1600 (fichas de WooCommerce). |
| `rapido`         | Un solo WEBP a 1600.                                               |
| `maxima-calidad` | Tamano original, calidad 95, conserva todo.                        |

Presets propios, desde el asistente o asi:

```sh
imagenes --preset web -q 90 --guardar-preset web-alta
```

Se guardan en `%APPDATA%\Imagenes\config.json`.

## Que hace con tus archivos

- Con varios tamanos, una subcarpeta por tamano.
- Con subcarpetas dentro, se replica el arbol.
- Si dos archivos dan el mismo nombre de salida (`foto.png` y `foto.jpg` dan
  los dos `foto.webp`), el segundo sale como `foto-2.webp`.
- `errores.log` junto al informe, solo si hubo problemas.
- `Ctrl+C` corta de verdad: cancela la cola, dice lo que dio tiempo a hacer y
  recuerda como seguir (`--no-sobrescribir`).

El manual completo, con todos los detalles de encaje, color, metadatos,
animaciones, rutas largas de Windows y calidades orientativas, esta en
[`LEEME.txt`](LEEME.txt).

## Desarrollo

```
imagenes/        el codigo (cli, config, core, report, runner, ui, watch, wizard)
tests/           77 pruebas
imagenes.spec    receta de PyInstaller
```

```sh
python -m pip install -e ".[heif,dev]"
python -m pytest tests -q
```

El historial de versiones esta en [`CHANGELOG.md`](CHANGELOG.md).

## Licencia

[MIT](LICENSE) &copy; 2026 Salva Borrego (cactusito31)
