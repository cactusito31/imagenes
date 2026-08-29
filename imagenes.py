#!/usr/bin/env python3
"""Lanzador de la aplicacion. La logica vive en el paquete imagenes/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PIL import Image  # noqa: F401
except ImportError:
    sys.exit("Falta Pillow. Instala:\n    python -m pip install --user Pillow")

from imagenes.cli import entry

if __name__ == "__main__":
    raise SystemExit(entry())
