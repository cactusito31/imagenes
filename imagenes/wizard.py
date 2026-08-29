"""Asistente interactivo. Recuerda la ultima configuracion y admite presets."""
from __future__ import annotations
import os
from typing import Dict, Tuple

from . import __version__
from .config import (Config, DEFAULT_QUALITY, FMT_KEYS, HAS_QUALITY,
                     SIZE_PRESETS, all_presets, get_preset, last_config,
                     save_preset, slugify)
from .ui import (ask, ask_int, ask_multichoice, ask_path, ask_single_choice,
                 ask_yes_no, banner, c, section)


class Pasos:
    """Numera los pasos sobre la marcha: si uno se omite, no queda un hueco."""

    def __init__(self):
        self.n = 0

    def titulo(self, texto: str) -> str:
        self.n += 1
        return "--- %d. %s ---" % (self.n, texto)


def _sizes_label(cfg: Config) -> str:
    return ", ".join(cfg.sizes)


def choose_starting_point(default_cfg: Config, paso: Pasos) -> Config:
    """Preset, ultima configuracion o partir de cero."""
    presets = all_presets()
    opts = [("_ultima", "Lo mismo que la ultima vez  (%s / %s)"
             % (", ".join(f.upper() for f in default_cfg.formats), _sizes_label(default_cfg)))]
    for name, p in presets.items():
        opts.append((name, "Preset %s - %s" % (name, p.get("_desc", ""))))
    opts.append(("_manual", "Configurarlo todo paso a paso"))

    key = ask_single_choice(paso.titulo("De donde partimos"), opts, default_key="_ultima")
    if key == "_manual":
        return Config()
    if key == "_ultima":
        return default_cfg
    return get_preset(key) or Config()


def ask_formats(cfg: Config, paso: Pasos) -> None:
    labels = {"webp": "WEBP  (recomendado para web)",
              "avif": "AVIF  (el que menos pesa; navegadores modernos)",
              "jpg":  "JPG   (compatible con todo)",
              "png":  "PNG   (sin perdida, admite transparencia)",
              "gif":  "GIF   (conserva animaciones)",
              "tiff": "TIFF  (imprenta)",
              "bmp":  "BMP   (sin comprimir)"}
    opts = [(k, labels[k]) for k in FMT_KEYS]
    cfg.formats = ask_multichoice(paso.titulo("A que formato(s)"), opts, cfg.formats)


def resolve_sizes(choice: str, cfg: Config) -> Dict[str, Tuple[int, int]]:
    if choice == "original":
        return {"original": (0, 0)}
    if choice in SIZE_PRESETS:
        return {choice: SIZE_PRESETS[choice]}
    if choice == "varios":
        opts = [("thumb", "Miniatura (300)"), ("medium", "Mediano (800)"),
                ("large", "Grande (1600)"), ("full", "Completo (1920)"),
                ("original", "Original")]
        keys = ask_multichoice("   Elige los tamanos que quieres generar:", opts,
                               [k for k in cfg.sizes if k in dict(opts)] or ["medium", "large"])
        return {k: SIZE_PRESETS.get(k, (0, 0)) for k in keys} or {"original": (0, 0)}
    if choice == "custom":
        w = ask_int("   Ancho maximo en pixeles", 1200, 1, 20000)
        h = ask_int("   Alto maximo en pixeles", 1200, 1, 20000)
        return {"%dx%d" % (w, h): (w, h)}
    return {"original": (0, 0)}


def ask_sizes(cfg: Config, paso: Pasos) -> None:
    opts = [("original", "Mantener el tamano original"),
            ("thumb", "Miniatura  (max 300 px)"),
            ("medium", "Mediano    (max 800 px)"),
            ("large", "Grande     (max 1600 px)"),
            ("full", "Completo   (max 1920 px)"),
            ("varios", "Varios tamanos a la vez (elegir)"),
            ("custom", "Tamano personalizado (yo escribo los pixeles)")]
    current = list(cfg.sizes)
    default = current[0] if len(current) == 1 and current[0] in dict(opts) else "varios"
    choice = ask_single_choice(paso.titulo("A que tamano"), opts, default_key=default)
    cfg.sizes = resolve_sizes(choice, cfg)


def ask_fit(cfg: Config, paso: Pasos) -> None:
    if all(d == (0, 0) for d in cfg.sizes.values()):
        return
    opts = [("ajustar", "Ajustar   - cabe dentro de la medida, respeta la proporcion"),
            ("recortar", "Recortar  - medida exacta, recorta lo que sobra (fichas de producto)"),
            ("rellenar", "Rellenar  - medida exacta, anade fondo alrededor (no recorta nada)")]
    cfg.fit_mode = ask_single_choice(paso.titulo("Como encajar en la medida"), opts,
                                     default_key=cfg.fit_mode)
    if cfg.fit_mode == "rellenar":
        cfg.pad_color = ask("   Color de fondo (blanco, negro, gris o #rrggbb)", cfg.pad_color)


def ask_quality(cfg: Config, paso: Pasos) -> None:
    con_calidad = [f for f in cfg.formats if HAS_QUALITY[f]]
    section(paso.titulo("Calidad"))
    if not con_calidad:
        print(c("   (No aplica a los formatos elegidos.)", "dim"))
        return
    pistas = {"jpg": "85 esta bien para casi todo",
              "webp": "82 equivale mas o menos a un JPG 90",
              "avif": "60 pesa un tercio menos que WEBP 82"}
    for f in con_calidad:
        cfg.quality[f] = ask_int("Calidad %s (1-100, %s)" % (f.upper(), pistas.get(f, "")),
                                 cfg.quality.get(f, DEFAULT_QUALITY.get(f, 82)), 1, 100)


def ask_naming(cfg: Config, paso: Pasos) -> None:
    section(paso.titulo("Nombre de los archivos"))
    tiene = bool(cfg.seo_prefix)
    if ask_yes_no("Quieres renombrarlos con un nombre SEO?", default_yes=tiene):
        cfg.seo_prefix = ask("   Escribe el nombre base (ej: playa-mojacar)",
                             cfg.seo_prefix or "imagen")
        base = slugify(cfg.seo_prefix)
        print(c("   Se llamaran: %s-001, %s-002, ..." % (base, base), "dim"))
    else:
        cfg.seo_prefix = ""


def ask_advanced(cfg: Config, paso: Pasos) -> None:
    section(paso.titulo("Opciones avanzadas"))
    if not ask_yes_no("Quieres revisarlas? (metadatos, color, subcarpetas...)", default_yes=False):
        return
    cfg.metadata = ask_single_choice(
        "   Metadatos EXIF (fecha, camara, GPS):",
        [("limpiar", "Limpiarlos   - recomendado para publicar en web (quita el GPS)"),
         ("conservar", "Conservarlos - util para archivo fotografico")],
        default_key=cfg.metadata)
    cfg.color = ask_single_choice(
        "   Perfil de color:",
        [("conservar", "Conservar el original - fiel, incrusta el perfil ICC"),
         ("srgb", "Convertir a sRGB     - mas compatible y ligero, ideal para web")],
        default_key=cfg.color)
    cfg.recursive = ask_yes_no("   Buscar tambien dentro de las subcarpetas?", cfg.recursive)
    cfg.overwrite = ask_yes_no("   Sobrescribir los archivos que ya existan?", cfg.overwrite)
    cfg.make_snippet = ask_yes_no("   Generar el snippet.html con picture/srcset?", cfg.make_snippet)


def offer_save_preset(cfg: Config) -> None:
    if not ask_yes_no("\nGuardar esta configuracion como preset para reutilizarla?", False):
        return
    name = slugify(ask("   Nombre del preset", "mi-preset"))
    desc = ask("   Descripcion corta (opcional)", "")
    if save_preset(name, cfg, desc):
        print(c("   Guardado. La proxima vez saldra en la lista, y desde la terminal:", "dim"))
        print(c("   imagenes CARPETA --preset %s" % name, "cyan"))
    else:
        print(c("   No se ha podido guardar el preset.", "red"))


def wizard(initial_path: str = "") -> Config:
    banner("IMAGENES %s  -  conversor guiado" % __version__)
    print(c("Responde a cada pregunta. Pulsa ENTER para el valor por", "dim"))
    print(c("defecto (lo que aparece entre corchetes).", "dim"))

    paso = Pasos()
    section(paso.titulo("Que quieres convertir"))
    if initial_path and os.path.exists(initial_path):
        print("   %s %s" % (c("[ok]", "green", "bold"), initial_path))
        path = initial_path
    else:
        path = ask_path("Carpeta con las imagenes (o un solo archivo)")

    cfg = choose_starting_point(last_config(), paso)
    cfg.input_path = path

    ask_formats(cfg, paso)
    ask_sizes(cfg, paso)
    ask_fit(cfg, paso)
    ask_quality(cfg, paso)
    ask_naming(cfg, paso)
    ask_advanced(cfg, paso)
    cfg.validate()
    return cfg
