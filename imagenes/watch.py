"""Modo vigilancia: deja la carpeta abierta y convierte lo que vaya llegando."""
from __future__ import annotations
import os
import time
from typing import Dict, Set

from . import core, runner
from .config import Config
from .ui import banner, c, human_time


def _instantanea(cfg: Config, out_dir: str) -> Dict[str, tuple]:
    """Ruta -> (tamano, fecha). Sirve para saber que hay y si ha parado de crecer."""
    fotos = core.collect_inputs(cfg.input_path, exclude_dir=out_dir,
                                recursive=cfg.recursive, exclude=cfg.exclude,
                                min_px=0)
    estado = {}
    for f in fotos:
        try:
            st = os.stat(core.ruta_larga(f))
            estado[f] = (st.st_size, st.st_mtime)
        except OSError:
            pass
    return estado


def vigilar(cfg: Config, intervalo: int = 5) -> int:
    """Convierte lo que aparezca. Se sale con Ctrl+C.

    Un archivo no se toca hasta que su tamano se mantiene igual entre dos
    vueltas: asi no se convierte una foto a medio copiar, que es el fallo
    clasico de cualquier carpeta vigilada.
    """
    out_dir = core.resolve_output_dir(cfg)
    banner("VIGILANDO  -  Ctrl+C para salir")
    print("   Carpeta : %s" % c(cfg.input_path, "cyan"))
    print("   Salida  : %s" % c(out_dir, "cyan"))
    print("   Formatos: %s   Tamanos: %s"
          % (c(", ".join(f.upper() for f in cfg.formats), "cyan"),
             c(", ".join(cfg.sizes), "cyan")))
    print("   Repaso cada %s s" % c(str(intervalo), "cyan"))
    if cfg.originales != "dejar":
        print("   %s" % c("Los originales se van a %s" % cfg.originales, "yellow"))
    print()

    # Lo que ya estaba al arrancar no se toca: solo interesa lo que llegue.
    ya_vistas: Set[str] = set(_instantanea(cfg, out_dir))
    if ya_vistas:
        print(c("   Habia %d imagen(es) de antes; se quedan como estan." % len(ya_vistas), "dim"))
    pendientes: Dict[str, tuple] = {}
    tandas = convertidas = 0
    desde = time.time()

    try:
        while True:
            time.sleep(intervalo)
            ahora = _instantanea(cfg, out_dir)

            listas = []
            for ruta, firma in ahora.items():
                if ruta in ya_vistas:
                    continue
                if pendientes.get(ruta) == firma:
                    listas.append(ruta)          # dos vueltas igual: ya no crece
                else:
                    pendientes[ruta] = firma     # recien llegada o aun copiandose

            # Lo que ha desaparecido deja de estar pendiente
            for ruta in list(pendientes):
                if ruta not in ahora:
                    del pendientes[ruta]

            if not listas:
                continue

            for ruta in listas:
                pendientes.pop(ruta, None)
                ya_vistas.add(ruta)

            listas.sort()
            print(c("[%s] %d imagen(es) nueva(s)"
                    % (time.strftime("%H:%M:%S"), len(listas)), "bold"))
            jobs = core.plan(cfg, listas)
            runner.execute(cfg, jobs, out_dir)
            tandas += 1
            convertidas += len(listas)
            # Si se movieron o borraron, ya no estan: que no cuenten como vistas.
            if cfg.originales != "dejar":
                ya_vistas -= set(listas)
            print()

    except KeyboardInterrupt:
        print(c(chr(10) + "Vigilancia terminada.", "bold", "cyan"))
        print("   %d tanda(s), %d imagen(es), durante %s"
              % (tandas, convertidas, human_time(time.time() - desde)))
        return 0
