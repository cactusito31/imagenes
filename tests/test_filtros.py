"""Filtros de entrada y que hacer con los originales."""
import os

from PIL import Image

from imagenes import core
from imagenes.config import CARPETA_ORIGINALES, Config
from tests.test_core import convertir, hacer_imagen


def test_excluir_por_carpeta(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "buena.jpg"))
    hacer_imagen(os.path.join(base, "borradores", "mala.jpg"))

    encontradas = [os.path.basename(p)
                   for p in core.collect_inputs(base, exclude=["borradores/*"])]
    assert encontradas == ["buena.jpg"]


def test_excluir_por_patron_de_nombre(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "buena.jpg"))
    hacer_imagen(os.path.join(base, "copia.tmp.jpg"))

    encontradas = [os.path.basename(p) for p in core.collect_inputs(base, exclude=["*.tmp.*"])]
    assert encontradas == ["buena.jpg"]


def test_min_px_salta_los_iconos(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "icono.png"), size=(48, 48))
    hacer_imagen(os.path.join(base, "firma.png"), size=(200, 60))
    hacer_imagen(os.path.join(base, "foto.jpg"), size=(1200, 800))

    encontradas = [os.path.basename(p) for p in core.collect_inputs(base, min_px=400)]
    assert encontradas == ["foto.jpg"]


def test_no_recomprimir_deja_en_paz_lo_que_ya_esta_bien(tmp_path):
    """Un WEBP que ya cabe en la medida no debe volver a comprimirse."""
    base = str(tmp_path)
    p = os.path.join(base, "ya.webp")
    os.makedirs(base, exist_ok=True)
    Image.new("RGB", (600, 400), (200, 80, 60)).save(p, quality=82)

    cfg = Config(input_path=base, formats=["webp"], sizes={"large": (1600, 1600)},
                 no_recompress=True)
    _, results = convertir(cfg)
    assert sum(r.skipped for r in results) == 1
    assert sum(r.written for r in results) == 0


def test_no_recomprimir_si_rehace_cuando_hay_que_reducir(tmp_path):
    base = str(tmp_path)
    p = os.path.join(base, "grande.webp")
    os.makedirs(base, exist_ok=True)
    Image.new("RGB", (3000, 2000), (200, 80, 60)).save(p, quality=82)

    cfg = Config(input_path=base, formats=["webp"], sizes={"medium": (800, 800)},
                 no_recompress=True)
    out, results = convertir(cfg)
    assert sum(r.written for r in results) == 1
    with Image.open(os.path.join(out, "grande.webp")) as im:
        assert max(im.size) == 800


def test_no_recomprimir_si_rehace_cuando_cambia_el_formato(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "foto.jpg"), size=(600, 400))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 no_recompress=True)
    _, results = convertir(cfg)
    assert sum(r.written for r in results) == 1


def test_mover_originales(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "sub", "foto.jpg"))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 originales="mover")
    out, _ = convertir(cfg)

    assert not os.path.exists(os.path.join(base, "sub", "foto.jpg"))
    assert os.path.exists(os.path.join(out, CARPETA_ORIGINALES, "sub", "foto.jpg"))
    assert os.path.exists(os.path.join(out, "sub", "foto.webp"))


def test_borrar_originales(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "foto.jpg"))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 originales="borrar")
    out, _ = convertir(cfg)

    assert not os.path.exists(os.path.join(base, "foto.jpg"))
    assert os.path.exists(os.path.join(out, "foto.webp"))


def test_el_original_no_se_toca_si_algo_fallo(tmp_path):
    """Regla de oro: ante la menor duda, el original se queda donde esta."""
    base = str(tmp_path)
    rota = os.path.join(base, "rota.jpg")
    os.makedirs(base, exist_ok=True)
    with open(rota, "wb") as f:
        f.write(b"esto no es una imagen")

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 originales="borrar")
    convertir(cfg)
    assert os.path.exists(rota), "se ha borrado un original que no se pudo convertir"


def test_el_original_no_se_toca_si_no_se_escribio_nada(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "foto.jpg"))
    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)})
    convertir(cfg)                       # primera pasada: se crea la salida

    cfg.originales = "borrar"
    cfg.overwrite = False                # segunda: todo omitido, nada escrito
    convertir(cfg)
    assert os.path.exists(os.path.join(base, "foto.jpg"))
