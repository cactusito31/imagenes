import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _ajustes_aislados(monkeypatch, tmp_path):
    """Ningun test toca el config.json real del usuario.

    config_dir() mira APPDATA en Windows y XDG_CONFIG_HOME en Linux/macOS, asi
    que hay que redirigir los dos o las pruebas se contaminan entre si en el
    sistema donde el otro no aplica.
    """
    base = tmp_path / "_ajustes"
    monkeypatch.setenv("APPDATA", str(base))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(base))
