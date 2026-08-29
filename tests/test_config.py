import pytest

from imagenes.config import (Config, parse_color, parse_formats, parse_size,
                             parse_sizes, natural_key, slugify)


def test_slugify_quita_acentos_y_simbolos():
    assert slugify("Playa de Mojacar!") == "playa-de-mojacar"
    assert slugify("  Cabo   de  Gata  ") == "cabo-de-gata"
    assert slugify("###") == "imagen"


def test_natural_key_ordena_por_numero():
    nombres = ["img10", "img2", "img1"]
    assert sorted(nombres, key=natural_key) == ["img1", "img2", "img10"]


@pytest.mark.parametrize("spec,esperado", [
    ("original", ("original", (0, 0))),
    ("medium", ("medium", (800, 800))),
    ("800", ("800", (800, 800))),
    ("900x600", ("900x600", (900, 600))),
    ("900X600", ("900x600", (900, 600))),
])
def test_parse_size(spec, esperado):
    assert parse_size(spec) == esperado


def test_parse_size_rechaza_basura():
    with pytest.raises(ValueError):
        parse_size("grandote")


def test_parse_sizes_admite_comas():
    assert parse_sizes(["medium,300"]) == {"medium": (800, 800), "300": (300, 300)}


def test_parse_formats_normaliza_alias():
    assert parse_formats(["jpeg,tif"]) == ["jpg", "tiff"]
    with pytest.raises(ValueError):
        parse_formats(["xcf"])


def test_parse_color():
    assert parse_color("blanco") == (255, 255, 255)
    assert parse_color("#000") == (0, 0, 0)
    assert parse_color("no-es-un-color") == (255, 255, 255)


def test_config_sobrevive_al_json():
    cfg = Config(formats=["webp", "avif"], sizes={"medium": (800, 800)},
                 quality={"webp": 70, "jpg": 90, "avif": 55}, fit_mode="recortar")
    vuelta = Config.from_dict(cfg.to_dict())
    assert vuelta.formats == ["webp", "avif"]
    assert vuelta.sizes == {"medium": (800, 800)}     # las tuplas se recuperan
    assert vuelta.quality["webp"] == 70
    assert vuelta.fit_mode == "recortar"


def test_validate_corrige_valores_imposibles():
    cfg = Config(formats=["xcf"], fit_mode="raro", quality={"webp": 500})
    cfg.validate()
    assert cfg.formats == ["webp"]
    assert cfg.fit_mode == "ajustar"
    assert cfg.quality["webp"] == 100
