"""Punto de entrada: asistente guiado, o modo directo por linea de ordenes."""
from __future__ import annotations
import argparse
import os
import sys

from . import __version__
from .config import (Config, FMT_KEYS, HAS_ANIMATION, PIL_NAME, all_presets,
                     config_file, delete_preset, get_preset, has_heif_support,
                     input_extensions, parse_formats, parse_sizes,
                     save_preset, slugify)
from . import runner
from .ui import ask_yes_no, banner, c, clean_path, error, section

EPILOGO = """ejemplos:
  imagenes                                  asistente guiado de siempre
  imagenes C:\fotos                         asistente con la carpeta ya puesta
                                            (tambien vale arrastrarla sobre el .exe)
  imagenes C:\fotos --preset web            sin preguntas, con el preset web
  imagenes C:\fotos -f webp,avif -s 800,1600
  imagenes C:\fotos -f jpg -s 1000x1000 --encaje recortar
  imagenes C:\fotos --preset woo --seo silla-oficina
  imagenes C:\fotos --preset web --simular  ensena lo que haria, sin tocar nada
  imagenes --presets                        lista los presets disponibles
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="imagenes",
        description="Conversor de imagenes: WEBP, AVIF, JPG, PNG, GIF, TIFF y BMP.",
        epilog=EPILOGO,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument("ruta", nargs="?", help="carpeta o archivo de entrada")
    p.add_argument("-f", "--formatos", action="append",
                   help="formatos de salida separados por coma (webp,avif,jpg,png,gif,tiff,bmp)")
    p.add_argument("-s", "--tamanos", action="append",
                   help="original, thumb, medium, large, full, un numero (800) o ANCHOxALTO")
    p.add_argument("-q", "--calidad", type=int, help="calidad 1-100 para todos los formatos")
    p.add_argument("--calidad-jpg", type=int)
    p.add_argument("--calidad-webp", type=int)
    p.add_argument("--calidad-avif", type=int)
    p.add_argument("--seo", metavar="NOMBRE",
                   help="renombra a NOMBRE-001, NOMBRE-002...")
    p.add_argument("--encaje", choices=("ajustar", "recortar", "rellenar"),
                   help="ajustar (por defecto), recortar a medida exacta o rellenar con fondo")
    p.add_argument("--fondo", metavar="COLOR",
                   help="color de relleno: blanco, negro, gris o #rrggbb")
    p.add_argument("--metadatos", choices=("limpiar", "conservar"),
                   help="EXIF: limpiar (quita el GPS) o conservar")
    p.add_argument("--color", choices=("conservar", "srgb"),
                   help="perfil ICC: conservar el original o convertir a sRGB")
    p.add_argument("-o", "--salida", metavar="CARPETA",
                   help="carpeta de destino (por defecto, imagenes_convertidas dentro del origen)")
    p.add_argument("--preset", metavar="NOMBRE", help="parte de un preset guardado")
    p.add_argument("--hilos", type=int, metavar="N", help="numero de hilos (0 = automatico)")
    p.add_argument("--no-recursivo", action="store_true", help="no entrar en las subcarpetas")
    p.add_argument("--no-sobrescribir", action="store_true", help="omitir lo que ya exista")
    p.add_argument("--sin-snippet", action="store_true", help="no generar snippet.html")
    p.add_argument("--simular", action="store_true",
                   help="ensena lo que se generaria, sin escribir nada")
    p.add_argument("--guardar-preset", metavar="NOMBRE",
                   help="guarda estas opciones como preset y sale")
    p.add_argument("--borrar-preset", metavar="NOMBRE", help="borra un preset guardado y sale")
    p.add_argument("--presets", action="store_true", help="lista los presets y sale")
    p.add_argument("--diagnostico", action="store_true",
                   help="ensena que formatos y funciones estan disponibles, y sale")
    p.add_argument("-V", "--version", action="version",
                   version="imagenes %s" % __version__)
    return p


# Opciones que, si aparecen, hacen que no se pregunte nada.
BATCH_FLAGS = ("formatos", "tamanos", "calidad", "calidad_jpg", "calidad_webp",
               "calidad_avif", "seo", "encaje", "fondo", "metadatos", "color",
               "salida", "preset", "hilos", "no_recursivo", "no_sobrescribir",
               "sin_snippet", "simular")


def is_batch(args) -> bool:
    for name in BATCH_FLAGS:
        v = getattr(args, name, None)
        if v not in (None, False):
            return True
    return False


def config_from_args(args) -> Config:
    if args.preset:
        cfg = get_preset(args.preset)
        if cfg is None:
            raise SystemExit(
                "No existe el preset %s. Los disponibles son: %s"
                % (args.preset, ", ".join(all_presets())))
    else:
        # El modo directo NO hereda la configuracion de la vez anterior: el mismo
        # comando tiene que dar siempre el mismo resultado, se haya hecho lo que se
        # haya hecho antes. Lo que se recuerda es solo para el asistente.
        cfg = Config()

    if args.formatos:
        cfg.formats = parse_formats(args.formatos)
    if args.tamanos:
        cfg.sizes = parse_sizes(args.tamanos)
    if args.calidad is not None:
        for k in ("jpg", "webp", "avif"):
            cfg.quality[k] = args.calidad
    for k, v in (("jpg", args.calidad_jpg), ("webp", args.calidad_webp),
                 ("avif", args.calidad_avif)):
        if v is not None:
            cfg.quality[k] = v
    if args.seo is not None:
        cfg.seo_prefix = args.seo
    if args.encaje:
        cfg.fit_mode = args.encaje
    if args.fondo:
        cfg.pad_color = args.fondo
    if args.metadatos:
        cfg.metadata = args.metadatos
    if args.color:
        cfg.color = args.color
    if args.salida:
        cfg.output_dir = clean_path(args.salida)
    if args.hilos is not None:
        cfg.workers = args.hilos
    if args.no_recursivo:
        cfg.recursive = False
    if args.no_sobrescribir:
        cfg.overwrite = False
    if args.sin_snippet:
        cfg.make_snippet = False
    cfg.validate()
    return cfg


def list_presets() -> int:
    print(c("Presets disponibles:", "bold"))
    for name, p in all_presets().items():
        print("  %s  %s" % (c(name.ljust(16), "cyan", "bold"), p.get("_desc", "")))
        print("      formatos: %s   tamanos: %s"
              % (", ".join(p.get("formats", [])), ", ".join(p.get("sizes", {}))))
    print(c("\nAjustes en: %s" % config_file(), "dim"))
    print(c("Uso: imagenes CARPETA --preset NOMBRE", "dim"))
    return 0


def diagnostico() -> int:
    """Para saber por que algo no funciona sin tener que adivinar."""
    import platform
    import PIL
    from PIL import Image, features
    from .core import default_workers

    Image.init()
    print(c("imagenes %s" % __version__, "bold"))
    print("  Python  : %s" % platform.python_version())
    print("  Pillow  : %s" % PIL.__version__)
    print("  Sistema : %s %s" % (platform.system(), platform.release()))
    empaquetado = getattr(sys, "frozen", False)
    print("  Origen  : %s" % ("ejecutable compilado" if empaquetado else "codigo Python"))
    print("  Hilos   : %d por defecto" % default_workers(100))
    print("  Ajustes : %s" % config_file())
    print()
    print(c("Formatos de salida:", "bold"))
    for k in FMT_KEYS:
        ok = PIL_NAME[k] in Image.SAVE
        anim = " (conserva animaciones)" if HAS_ANIMATION[k] else ""
        print("  %-6s %s%s" % (k, c("disponible", "green") if ok else c("NO", "red"), anim))
    print()
    print(c("Entrada:", "bold"))
    heif = has_heif_support()
    print("  HEIC/HEIF (fotos de iPhone): %s"
          % (c("si", "green") if heif else c("no - falta pillow-heif", "yellow")))
    print("  AVIF: %s" % (c("si", "green") if features.check("avif") else c("no", "yellow")))
    print("  Extensiones que se leen: %s" % ", ".join(input_extensions()))
    return 0


def simulate(cfg: Config) -> int:
    inputs, jobs, out_dir = runner.prepare(cfg)
    if not inputs:
        error("No se han encontrado imagenes en esa ruta.")
        return 1
    runner.print_summary(cfg, inputs, jobs, out_dir)
    section("--- Se generaria (primeros 20) ---")
    shown = 0
    for j in jobs:
        for t in j.targets:
            if shown >= 20:
                break
            print("   %s" % os.path.relpath(t.path, out_dir))
            shown += 1
        if shown >= 20:
            break
    total = sum(len(j.targets) for j in jobs)
    if total > shown:
        print(c("   ... y %d mas" % (total - shown), "dim"))
    print(c("\nSimulacion: no se ha escrito nada.", "yellow", "bold"))
    return 0


def interactive_loop(initial_path: str = "") -> int:
    from .config import remember
    from .wizard import offer_save_preset, wizard
    while True:
        cfg = wizard(initial_path)
        initial_path = ""          # solo la primera vuelta usa la ruta arrastrada
        inputs, jobs, out_dir = runner.prepare(cfg)
        if not inputs:
            error("No se han encontrado imagenes en esa ruta.")
        else:
            runner.print_summary(cfg, inputs, jobs, out_dir)
            if ask_yes_no("Empezar la conversion?", default_yes=True):
                remember(cfg)
                runner.execute(cfg, jobs, out_dir)
                offer_save_preset(cfg)
            else:
                print(c("Cancelado.", "yellow"))
        if not ask_yes_no("\nConvertir otra tanda?", default_yes=False):
            print(c("Hasta luego!", "bold", "cyan"))
            return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.diagnostico:
        return diagnostico()

    if args.presets:
        return list_presets()

    if args.borrar_preset:
        if delete_preset(args.borrar_preset):
            print("Preset borrado: %s" % args.borrar_preset)
            return 0
        error("No existe ese preset (los de fabrica no se pueden borrar).")
        return 1

    if args.guardar_preset:
        cfg = config_from_args(args)
        if save_preset(slugify(args.guardar_preset), cfg):
            print("Preset guardado: %s" % slugify(args.guardar_preset))
            print(c("Uso: imagenes CARPETA --preset %s" % slugify(args.guardar_preset), "dim"))
            return 0
        error("No se ha podido guardar el preset.")
        return 1

    ruta = clean_path(args.ruta) if args.ruta else ""
    if ruta and not os.path.exists(ruta):
        error("No existe: %s" % ruta)
        return 1

    # Sin opciones: asistente de siempre. Con una ruta suelta (o arrastrando una
    # carpeta sobre el .exe) el asistente arranca con esa ruta ya rellenada.
    if not is_batch(args):
        return interactive_loop(ruta)

    if not ruta:
        error("Falta la carpeta o el archivo de entrada.")
        print(c("Prueba:  imagenes --help", "dim"))
        return 1

    try:
        cfg = config_from_args(args)
    except ValueError as e:
        error(str(e))
        return 1
    cfg.input_path = ruta

    if args.simular:
        return simulate(cfg)

    banner("IMAGENES %s" % __version__)
    inputs, jobs, out_dir = runner.prepare(cfg)
    if not inputs:
        error("No se han encontrado imagenes en esa ruta.")
        return 1
    runner.print_summary(cfg, inputs, jobs, out_dir)
    return runner.execute(cfg, jobs, out_dir)


def entry() -> int:
    has_heif_support()          # registra HEIC/HEIF si esta disponible
    try:
        return main()
    except KeyboardInterrupt:
        print(c("\nCancelado.", "yellow"))
        return 130
    except BrokenPipeError:
        return 0
