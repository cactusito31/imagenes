"""Informe CSV y fragmento HTML con <picture>/srcset listo para pegar."""
from __future__ import annotations
import csv, html, os, time
from typing import Dict, List

from .config import MIME

CSV_FIELDS = ["entrada", "entrada_bytes", "entrada_px", "tamano", "formato",
              "salida", "salida_bytes", "salida_px", "ahorro_pct"]

# Orden de preferencia en <picture>: el navegador coge el primero que entiende.
PICTURE_ORDER = ["avif", "webp"]
FALLBACK_ORDER = ["jpg", "png", "webp", "gif"]


def write_csv(rows: List[dict], output_dir: str) -> str:
    """Un CSV por tanda, con marca de tiempo: ya no se pisa el de la vez anterior."""
    if not rows:
        return ""
    name = "reporte-%s.csv" % time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(output_dir, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return path


def _width_of(px: str) -> int:
    try:
        return int(str(px).split("x")[0])
    except (ValueError, IndexError):
        return 0


def build_snippet(rows: List[dict], output_dir: str) -> str:
    """Genera un <picture> por imagen de origen, con srcset por ancho real."""
    by_src: Dict[str, List[dict]] = {}
    for r in rows:
        by_src.setdefault(r["entrada"], []).append(r)

    blocks = []
    for src, items in by_src.items():
        by_fmt: Dict[str, List[dict]] = {}
        for r in items:
            by_fmt.setdefault(r["formato"], []).append(r)

        sources = []
        for fmt in PICTURE_ORDER:
            if fmt not in by_fmt:
                continue
            parts = []
            for r in sorted(by_fmt[fmt], key=lambda x: _width_of(x["salida_px"])):
                rel = os.path.relpath(r["salida"], output_dir).replace(os.sep, "/")
                w = _width_of(r["salida_px"])
                parts.append("%s %dw" % (html.escape(rel), w) if w else html.escape(rel))
            if parts:
                sources.append('    <source type="%s" srcset="%s">'
                               % (MIME[fmt], ",\n            ".join(parts)))

        fallback = None
        for fmt in FALLBACK_ORDER:
            if fmt in by_fmt:
                fallback = max(by_fmt[fmt], key=lambda x: _width_of(x["salida_px"]))
                break
        if fallback is None:
            continue
        rel = os.path.relpath(fallback["salida"], output_dir).replace(os.sep, "/")
        w = _width_of(fallback["salida_px"])
        h = 0
        try:
            h = int(str(fallback["salida_px"]).split("x")[1])
        except (ValueError, IndexError):
            pass
        alt = os.path.splitext(os.path.basename(fallback["salida"]))[0].replace("-", " ")

        img = ('    <img src="%s" width="%d" height="%d" loading="lazy" '
               'decoding="async" alt="%s">' % (html.escape(rel), w, h, html.escape(alt)))
        blocks.append("  <!-- %s -->\n  <picture>\n%s\n%s\n  </picture>"
                      % (html.escape(os.path.basename(src)),
                         "\n".join(sources) if sources else "", img))

    if not blocks:
        return ""
    return (
        "<!-- Generado por imagenes. Rutas relativas a esta carpeta.\n"
        "     Ajusta el atributo alt: se ha rellenado con el nombre del archivo. -->\n"
        + "\n\n".join(b for b in blocks)
        + "\n"
    )


def write_snippet(rows: List[dict], output_dir: str) -> str:
    txt = build_snippet(rows, output_dir)
    if not txt:
        return ""
    path = os.path.join(output_dir, "snippet.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return path


def totals(rows: List[dict]) -> dict:
    """Peso de entrada contando cada origen una sola vez, aunque genere 6 salidas."""
    seen = set()
    in_bytes = 0
    for r in rows:
        if r["entrada"] not in seen:
            seen.add(r["entrada"])
            in_bytes += int(r["entrada_bytes"] or 0)
    out_bytes = sum(int(r["salida_bytes"] or 0) for r in rows)
    return {"entrada": in_bytes, "salida": out_bytes,
            "ahorro": in_bytes - out_bytes,
            "ahorro_pct": round(100 * (1 - out_bytes / in_bytes), 1) if in_bytes else 0.0}


def write_error_log(results, output_dir: str) -> str:
    """Deja por escrito los problemas: en una tanda larga, cerrar la ventana ya
    no se lleva por delante la lista de lo que fallo."""
    tab, salto = chr(9), chr(10)
    lineas = []
    for r in results:
        for nivel, msg in r.messages:
            if nivel in ("error", "warn"):
                lineas.append(tab.join([nivel.upper(), r.src, msg]))
    if not lineas:
        return ""
    path = os.path.join(output_dir, "errores.log")
    cabecera = "# imagenes - problemas de la tanda del " + time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        f.write(cabecera + salto)
        f.write(salto.join(lineas) + salto)
    return path
