"""La version del paquete y la de pyproject.toml no pueden divergir."""
import pathlib
import re

from imagenes import __version__

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_version_pyproject_coincide_con_el_paquete():
    txt = (ROOT / "pyproject.toml").read_text("utf-8")
    m = re.search(r'^version = "([^"]+)"', txt, re.M)
    assert m, "no se encontro version en pyproject.toml"
    assert m.group(1) == __version__, (
        "pyproject.toml (%s) e imagenes/__init__.py (%s) no coinciden"
        % (m.group(1), __version__))
