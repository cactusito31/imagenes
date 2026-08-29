import os

import pytest

from imagenes import cli
from imagenes.config import Config
from tests.test_core import hacer_imagen


def parse(argv):
    return cli.build_parser().parse_args(argv)


def test_sin_opciones_es_modo_asistente():
    assert cli.is_batch(parse([])) is False
    assert cli.is_batch(parse(["C:/fotos"])) is False


def test_con_opciones_es_modo_directo():
    assert cli.is_batch(parse(["C:/fotos", "-f", "webp"])) is True
    assert cli.is_batch(parse(["C:/fotos", "--preset", "web"])) is True


def test_las_opciones_ganan_al_preset(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))     # no tocar los ajustes reales
    args = parse(["C:/fotos", "--preset", "web", "-f", "jpg", "-q", "70"])
    cfg = cli.config_from_args(args)
    assert cfg.formats == ["jpg"]
    assert cfg.quality["jpg"] == 70
    assert list(cfg.sizes) == ["medium", "large"]    # lo demas sigue viniendo del preset


def test_preset_inexistente_avisa(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    with pytest.raises(SystemExit):
        cli.config_from_args(parse(["C:/fotos", "--preset", "no-existe"]))


def test_formato_invalido_da_error_claro(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    with pytest.raises(ValueError) as e:
        cli.config_from_args(parse(["C:/fotos", "-f", "xcf"]))
    assert "xcf" in str(e.value)


def test_simular_no_escribe_nada(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    base = tmp_path / "fotos"
    hacer_imagen(os.path.join(str(base), "una.jpg"))

    code = cli.main([str(base), "-f", "webp", "-s", "medium", "--simular"])
    assert code == 0
    assert not os.path.exists(os.path.join(str(base), "imagenes_convertidas"))
    assert "no se ha escrito nada" in capsys.readouterr().out.lower()


def test_modo_directo_convierte_de_verdad(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    base = tmp_path / "fotos"
    hacer_imagen(os.path.join(str(base), "una.jpg"))

    code = cli.main([str(base), "-f", "webp", "-s", "medium"])
    assert code == 0
    assert os.path.exists(os.path.join(str(base), "imagenes_convertidas", "una.webp"))


def test_salida_a_otra_carpeta(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    base = tmp_path / "fotos"
    destino = tmp_path / "destino"
    hacer_imagen(os.path.join(str(base), "una.jpg"))

    assert cli.main([str(base), "-f", "webp", "-o", str(destino)]) == 0
    assert os.path.exists(os.path.join(str(destino), "una.webp"))


def test_ruta_inexistente_devuelve_error(tmp_path):
    assert cli.main([str(tmp_path / "no-existe"), "-f", "webp"]) == 1


def test_el_modo_directo_no_arrastra_la_configuracion_anterior(tmp_path, monkeypatch):
    """El mismo comando debe dar el mismo resultado, se haya hecho lo que se haya
    hecho antes. Solo el asistente recuerda."""
    from imagenes.config import Config, remember
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    remember(Config(fit_mode="rellenar", formats=["png"], sizes={"thumb": (300, 300)},
                    metadata="conservar"))

    cfg = cli.config_from_args(parse(["C:/fotos", "-f", "webp", "-s", "large"]))
    assert cfg.fit_mode == "ajustar"        # no el rellenar que quedo guardado
    assert cfg.metadata == "limpiar"
    assert list(cfg.sizes) == ["large"]
