"""Orquestacion: prepara el trabajo, lo ejecuta y lo cuenta por pantalla."""
from __future__ import annotations
import os
from typing import List, Tuple

from . import OUTPUT_FOLDER_NAME
from .config import Config, slugify
from . import core, report
from .ui import Progress, c, error, human, section, warn


def prepare(cfg: Config) -> Tuple[List[str], List[core.Job], str]:
    out_dir = core.resolve_output_dir(cfg)
    inputs = core.collect_inputs(cfg.input_path, exclude_dir=out_dir, recursive=cfg.recursive)
    jobs = core.plan(cfg, inputs) if inputs else []
    return inputs, jobs, out_dir


def print_summary(cfg: Config, inputs: List[str], jobs: List[core.Job], out_dir: str) -> None:
    n_out = sum(len(j.targets) for j in jobs)
    print("\n" + c("-" * 58, "magenta"))
    print(c("  RESUMEN", "bold", "magenta"))
    print("   Entrada : %s" % cfg.input_path)
    print("   Imagenes: %s   ->  %s archivos de salida"
          % (c(str(len(inputs)), "bold"), c(str(n_out), "bold")))
    print("   Formatos: %s" % c(", ".join(f.upper() for f in cfg.formats), "cyan"))
    print("   Tamanos : %s" % c(", ".join(cfg.sizes), "cyan"))
    if cfg.fit_mode != "ajustar":
        extra = " sobre %s" % cfg.pad_color if cfg.fit_mode == "rellenar" else ""
        print("   Encaje  : %s%s" % (c(cfg.fit_mode, "cyan"), extra))
    if cfg.seo_prefix:
        pad = len(str(len(inputs)))
        print("   Nombre  : %s-%s, -%s, ..." % (slugify(cfg.seo_prefix),
                                                "1".zfill(pad), "2".zfill(pad)))
    print("   Color   : %s   Metadatos: %s" % (cfg.color, cfg.metadata))
    print("   Salida  : %s" % c(out_dir, "cyan"))
    print(c("             %s" % ("subcarpetas por tamano" if cfg.multi_size
                                 else "imagenes sueltas (un solo tamano)"), "dim"))
    if not cfg.overwrite:
        print(c("             no se sobrescribe lo que ya exista", "dim"))
    print(c("-" * 58, "magenta"))


def execute(cfg: Config, jobs: List[core.Job], out_dir: str, quiet: bool = False) -> int:
    core.make_dirs(jobs)
    total = len(jobs)
    workers = cfg.workers or core.default_workers(total)

    if not quiet:
        print("\n" + c("-" * 58, "dim"))
        print("Convirtiendo %s imagen(es) con %s hilo(s)"
              % (c(str(total), "bold"), c(str(workers), "bold")))
        print(c("-" * 58, "dim"))

    bar = Progress(total, enabled=not quiet)
    bar.update(0, "")
    lote = core.convert_all(cfg, jobs, on_progress=bar.update)
    results = lote.results
    bar.clear()

    rows, ok, written, skipped, errors = [], 0, 0, 0, 0
    for r in results:
        rows.extend(r.rows)
        written += r.written
        skipped += r.skipped
        errors += r.errors
        if r.ok:
            ok += 1
        for level, msg in r.messages:
            if quiet and level == "skip":
                continue
            if level == "error":
                error(msg)
            elif level == "warn":
                warn(msg)
            else:
                print(c("  [=] " + msg, "yellow"))
        if not quiet and r.written:
            print("  %s %s %s -> %s"
                  % (c("[ok]", "green", "bold"), os.path.basename(r.src),
                     c("(%dx%d)" % (r.width, r.height), "dim"),
                     c("%d archivo(s)" % r.written, "green")))

    csv_path = report.write_csv(rows, out_dir) if rows else ""
    snip_path = ""
    if rows and cfg.make_snippet and (cfg.multi_size or len(cfg.formats) > 1):
        snip_path = report.write_snippet(rows, out_dir)

    t = report.totals(rows)
    line_color = "green" if errors == 0 and not lote.interrupted else "yellow"
    print("\n" + c("=" * 58, line_color))
    if lote.interrupted:
        print(c("  INTERRUMPIDO. Esto es lo que dio tiempo a hacer:", "bold", "yellow"))
    print(c("  Listo. Imagenes: %d   Archivos creados: %d   Omitidos: %d   Errores: %d"
            % (ok, written, skipped, errors), "bold", line_color))
    if t["entrada"]:
        signo = "ahorro" if t["ahorro"] >= 0 else "aumento"
        print("  Original: %s   ->   Generado: %s   (%s %s, %s%%)"
              % (human(t["entrada"]), human(t["salida"]),
                 signo, human(abs(t["ahorro"])), t["ahorro_pct"]))
    print("  Guardado en: %s" % c(out_dir, "cyan"))
    if csv_path:
        print(c("  Informe: %s" % os.path.basename(csv_path), "dim"))
    if snip_path:
        print(c("  HTML <picture> listo para pegar: %s" % os.path.basename(snip_path), "dim"))
    print(c("=" * 58, line_color))
    if lote.interrupted:
        print(c("  Para seguir donde lo dejaste, repite el comando con "
                "--no-sobrescribir", "dim"))
        return 130
    return 0 if errors == 0 else 1


def run(cfg: Config, quiet: bool = False) -> int:
    inputs, jobs, out_dir = prepare(cfg)
    if not inputs:
        error("No se han encontrado imagenes en esa ruta.")
        if not cfg.recursive:
            print(c("   (estas en modo no recursivo: prueba sin --no-recursivo)", "dim"))
        return 1
    return execute(cfg, jobs, out_dir, quiet=quiet)
