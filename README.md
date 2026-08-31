# Imagenes

***English** · [Español](README.es.md)*

A terminal image converter with a guided wizard and a scriptable direct mode.
Batch-convert folders to **WEBP, AVIF, JPG, PNG, GIF, TIFF and BMP**, and read
**HEIC/HEIF** too (iPhone photos).

[![tests](https://github.com/cactusito31/imagenes/actions/workflows/tests.yml/badge.svg)](https://github.com/cactusito31/imagenes/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> The CLI, the wizard and the full manual ([`LEEME.txt`](LEEME.txt)) are in
> **Spanish**. This page is a summary for a wider audience.

Output **always** goes to an `imagenes_convertidas` subfolder inside the source
folder (or wherever you point `-o`). Originals are never touched.

---

## Features

- **Recursive batches** that mirror the source tree, so two `photo.jpg` files
  in different subfolders don't overwrite each other.
- **Several formats and sizes at once**: `-f webp,avif -s 800,1600`.
- **Presets** (`web`, `woo`, `rapido`, `maxima-calidad`) plus your own.
- **Fit modes**: fit inside, crop to exact size, pad to exact size (never
  upscales a small image).
- **Metadata control** (strip EXIF, including GPS location) and **color-profile
  control** (keep the ICC profile or convert to sRGB).
- **Parallel conversion with a memory ceiling**: concurrent jobs throttle
  themselves when panoramas or large scans come in (measured: 8 × 100 Mpx
  images drop from 9.5 GB to 1.2 GB).
- **Atomic writes**: everything is written to a `.tmp` and renamed at the end,
  so an interrupted run never leaves a correctly named but corrupt file.
- **Watch mode** (`--vigilar`): keep a folder open and convert whatever lands
  in it, waiting until each file stops growing.
- **Filters**: `--excluir PATTERN`, `--min-px N`, `--no-recomprimir`.
- **Original handling**: `--originales dejar|mover|borrar` (only deletes if the
  run finished without a single error).
- **Reports**: `reporte-DATE.csv` with the real byte savings, and a
  `snippet.html` with a ready-to-paste `<picture>`/`srcset`.
- **Windows integration**: desktop shortcut, drag a folder onto the `.exe`,
  right-click *"Convertir imagenes"*, and *Send to*.

## Install

### Option A — download the executable (Windows, nothing to install)

Grab `imagenes-*-windows-x64.exe` from the
[latest release](https://github.com/cactusito31/imagenes/releases/latest) and
run it. No Python needed.

> Windows SmartScreen may warn because the binary is unsigned:
> *More info > Run anyway*.

To wire it into the system (shortcut, context menu, an `imagenes` command in
any terminal), clone the repo and run `INSTALAR.bat`.

### Option B — pipx / pip (any OS)

```sh
pipx install imagenes
imagenes --help
```

For iPhone HEIC/HEIF reading: `pipx install "imagenes[heif]"`.

### Option C — from source

```sh
git clone https://github.com/cactusito31/imagenes
cd imagenes
python -m pip install -r requirements.txt
python imagenes.py --help
```

Build your own `.exe` with `CREAR_EXE.bat` (uses `imagenes.spec`).

## Usage

### Guided wizard

Run it with no arguments and it walks you through the options, remembering your
last choices as defaults.

```sh
imagenes
```

### Direct mode (no questions)

Built for repetition and automation: it inherits nothing from the previous run,
so the same command always produces the same result. Anything you don't set
stays at factory defaults (or the preset's, with `--preset`).

```sh
imagenes ./photos --preset web
imagenes ./photos -f webp,avif -s 800,1600 -q 82
imagenes ./photos -f jpg -s 1000x1000 --encaje recortar   # crop to exact size
imagenes ./photos --preset woo --seo office-chair
imagenes ./photos --preset web --simular                  # dry run
imagenes ./photos --excluir drafts/* --min-px 400
imagenes ./photos --preset web --originales mover          # move originals aside
imagenes ./photos --preset web --vigilar                   # watch mode
imagenes --presets                                        # list presets
imagenes --diagnostico                                    # what's available
imagenes --help                                           # every option
```

## Presets

| Preset           | What it does                                                        |
|------------------|--------------------------------------------------------------------|
| `web`            | WEBP + AVIF at 800 and 1600, no metadata, sRGB.                    |
| `woo`            | Square, white background, at 300/800/1600 (WooCommerce product images). |
| `rapido`         | A single WEBP at 1600.                                             |
| `maxima-calidad` | Original size, quality 95, keeps everything.                       |

Save your own from the wizard, or:

```sh
imagenes --preset web -q 90 --guardar-preset web-high
```

They live in `%APPDATA%\Imagenes\config.json`.

## What it does with your files

- Multiple sizes → one subfolder per size.
- Nested subfolders → the tree is mirrored.
- If two files map to the same output name (`photo.png` and `photo.jpg` both
  give `photo.webp`), the second becomes `photo-2.webp`.
- `errores.log` next to the report, only when something went wrong.
- `Ctrl+C` really stops: it cancels the queue, reports what got done, and
  reminds you how to resume (`--no-sobrescribir`).

The complete manual — fit modes, color, metadata, animation handling, Windows
long-path limits and quality guidance — is in [`LEEME.txt`](LEEME.txt) (Spanish).

## Development

```
imagenes/        the code (cli, config, core, report, runner, ui, watch, wizard)
tests/           77 tests
imagenes.spec    PyInstaller recipe
```

```sh
python -m pip install -e ".[heif,dev]"
python -m pytest tests -q
```

Version history is in [`CHANGELOG.md`](CHANGELOG.md) (Spanish).

## License

[MIT](LICENSE) &copy; 2026 Salva Borrego (cactusito31)
