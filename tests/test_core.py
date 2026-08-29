"""Pruebas del motor: son las que cubren los fallos reales de la version 1."""
import os

import pytest
from PIL import Image, ImageDraw

from imagenes import core
from imagenes.config import Config


def hacer_imagen(path, size=(600, 400), color=(200, 80, 60), mode="RGB", **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.new(mode, size, color)
    ImageDraw.Draw(img).rectangle([10, 10, size[0] - 10, size[1] - 10],
                                  outline=(255, 255, 255), width=5)
    img.save(path, **kw)
    return path


def convertir(cfg):
    cfg.validate()
    out = core.resolve_output_dir(cfg)
    inputs = core.collect_inputs(cfg.input_path, exclude_dir=out, recursive=cfg.recursive)
    jobs = core.plan(cfg, inputs)
    core.make_dirs(jobs)
    results = core.convert_all(cfg, jobs)
    return out, results


# ---------------------------------------------------------------------------
# Planificacion
# ---------------------------------------------------------------------------

def test_mismo_nombre_en_dos_subcarpetas_no_se_pisa(tmp_path):
    """El fallo mas grave de la v1: la salida era plana y una foto borraba a la otra."""
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "2024", "foto.jpg"))
    hacer_imagen(os.path.join(base, "2025", "foto.jpg"), color=(20, 90, 200))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)})
    out, results = convertir(cfg)

    assert os.path.exists(os.path.join(out, "2024", "foto.webp"))
    assert os.path.exists(os.path.join(out, "2025", "foto.webp"))
    assert sum(r.written for r in results) == 2


def test_mismo_nombre_distinta_extension_se_desambigua(tmp_path):
    """foto.png y foto.jpg dan los dos foto.webp: hay que numerar el segundo."""
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "choque.jpg"))
    hacer_imagen(os.path.join(base, "choque.png"))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)})
    out, results = convertir(cfg)

    generados = sorted(n for n in os.listdir(out) if n.endswith(".webp"))
    assert generados == ["choque-2.webp", "choque.webp"]
    assert sum(r.written for r in results) == 2


def test_nombres_seo_con_ceros_delante(tmp_path):
    base = str(tmp_path)
    for i in range(12):
        hacer_imagen(os.path.join(base, "img%02d.jpg" % i))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 seo_prefix="Playa de Mojacar")
    out, _ = convertir(cfg)

    nombres = sorted(os.listdir(out))
    assert nombres[0] == "playa-de-mojacar-01.webp"
    assert nombres[-1] == "playa-de-mojacar-12.webp"


def test_no_confunde_carpeta_parecida_a_la_de_salida(tmp_path):
    """imagenes_convertidas_old empieza igual pero NO debe excluirse."""
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "a.jpg"))
    hacer_imagen(os.path.join(base, "imagenes_convertidas_old", "vieja.jpg"))
    os.makedirs(os.path.join(base, "imagenes_convertidas"), exist_ok=True)
    hacer_imagen(os.path.join(base, "imagenes_convertidas", "ya_convertida.jpg"))

    out = os.path.join(base, "imagenes_convertidas")
    encontrados = [os.path.basename(p) for p in core.collect_inputs(base, exclude_dir=out)]
    assert "a.jpg" in encontrados
    assert "vieja.jpg" in encontrados
    assert "ya_convertida.jpg" not in encontrados


def test_no_recursivo_ignora_subcarpetas(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "raiz.jpg"))
    hacer_imagen(os.path.join(base, "dentro", "hijo.jpg"))
    encontrados = [os.path.basename(p) for p in core.collect_inputs(base, recursive=False)]
    assert encontrados == ["raiz.jpg"]
