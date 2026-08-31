"""Pruebas de los tres fallos verificados con medidas: Ctrl+C, memoria y rutas."""
import os
import threading
import time

import pytest
from PIL import Image

from imagenes import core
from imagenes.config import Config
from tests.test_core import convertir, hacer_imagen


# ---------------------------------------------------------------------------
# Ctrl+C
# ---------------------------------------------------------------------------

def test_ctrl_c_no_procesa_toda_la_cola(tmp_path, monkeypatch):
    """Antes, Ctrl+C dejaba que se procesaran las 84 imagenes de la cola igual."""
    base = str(tmp_path)
    for i in range(40):
        hacer_imagen(os.path.join(base, "img%02d.jpg" % i), size=(200, 150))

    vistas = []
    original = core.convert_one

    def lento(job, cfg, pad, budget=None, cancel=None, avif_gate=None):
        vistas.append(job.src)
        time.sleep(0.05)
        return original(job, cfg, pad, budget, cancel, avif_gate)

    monkeypatch.setattr(core, "convert_one", lento)

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)}, workers=4)
    cfg.validate()
    out = core.resolve_output_dir(cfg)
    jobs = core.plan(cfg, core.collect_inputs(base, exclude_dir=out))
    core.make_dirs(jobs)

    def cortar(hechas, etiqueta):
        if hechas >= 2:
            raise KeyboardInterrupt

    lote = core.convert_all(cfg, jobs, on_progress=cortar)

    assert lote.interrupted is True
    # Solo pueden colarse las que ya estaban en vuelo, no las 40. El limite
    # exacto depende de la carrera entre el aviso y el cierre del pool, asi que
    # se comprueba el orden de magnitud, no un numero clavado.
    assert len(vistas) < len(jobs), "el Ctrl+C no ha cancelado la cola"
    assert len(vistas) <= 2 + 2 * cfg.workers


def test_la_cancelacion_corta_tambien_los_tamanos_que_faltan(tmp_path):
    """Un hilo ya en marcha no debe terminar los 4 tamanos que le quedaban."""
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "una.jpg"), size=(400, 300))

    cfg = Config(input_path=base, formats=["webp"],
                 sizes={"thumb": (300, 300), "medium": (800, 800),
                        "large": (1600, 1600), "full": (1920, 1920)})
    cfg.validate()
    out = core.resolve_output_dir(cfg)
    jobs = core.plan(cfg, core.collect_inputs(base, exclude_dir=out))
    core.make_dirs(jobs)

    cancelado = threading.Event()
    cancelado.set()
    res = core.convert_one(jobs[0], cfg, (255, 255, 255), cancel=cancelado)
    assert res.written == 0


# ---------------------------------------------------------------------------
# Presupuesto de memoria
# ---------------------------------------------------------------------------

def test_el_presupuesto_deja_pasar_lo_que_cabe():
    b = core.PixelBudget(1000)
    b.acquire(400)
    b.acquire(400)
    assert b.usado == 800


def test_el_presupuesto_hace_esperar_cuando_no_cabe():
    b = core.PixelBudget(1000)
    b.acquire(800)
    entro = threading.Event()

    def segundo():
        b.acquire(800)
        entro.set()

    t = threading.Thread(target=segundo, daemon=True)
    t.start()
    assert not entro.wait(0.3), "deberia estar esperando: no cabe"
    b.release(800)
    assert entro.wait(2), "al liberar deberia entrar"


def test_una_imagen_enorme_pasa_sola_en_vez_de_bloquearse():
    """Si una sola imagen no cabe en el presupuesto, no puede quedarse colgada."""
    b = core.PixelBudget(1000)
    concedido = b.acquire(50_000)
    assert concedido == 1000
    b.release(concedido)
    assert b.usado == 0


# ---------------------------------------------------------------------------
# Rutas largas de Windows
# ---------------------------------------------------------------------------

def test_ruta_corta_no_se_toca():
    p = os.path.abspath(os.path.join("C:" + os.sep, "corta", "f.jpg"))
    assert core.ruta_larga(p) == p


@pytest.mark.skipif(os.name != "nt", reason="el limite de 260 es de Windows")
def test_ruta_larga_lleva_prefijo():
    larga = "C:" + os.sep + os.sep.join(["carpeta-de-nombre-bastante-largo"] * 10) + os.sep + "f.jpg"
    assert core.ruta_larga(larga).startswith(core.PREFIJO_LARGO)


@pytest.mark.skipif(os.name != "nt", reason="el limite de 260 es de Windows")
def test_convierte_aunque_la_ruta_pase_de_260(tmp_path):
    """Replicar el arbol mas la subcarpeta del tamano alarga mucho la salida:
    antes fallaban todos los archivos con un enganoso No such file or directory."""
    hondo = str(tmp_path)
    for _ in range(4):
        hondo = os.path.join(hondo, "carpeta-con-un-nombre-francamente-largo-de-cliente")
    # Hasta para MONTAR el caso hace falta el prefijo de ruta larga.
    os.makedirs(core.ruta_larga(hondo), exist_ok=True)
    origen = os.path.join(hondo, "producto-con-nombre-descriptivo-muy-largo-para-seo.jpg")
    Image.new("RGB", (600, 400), (200, 80, 60)).save(core.ruta_larga(origen))

    cfg = Config(input_path=str(tmp_path), formats=["webp"],
                 sizes={"medium": (800, 800), "large": (1600, 1600)})
    out, results = convertir(cfg)

    # Hasta para CONTAR los resultados hace falta el prefijo: os.walk a secas
    # no entra en las carpetas hondas y devolveria una lista vacia.
    generados = [os.path.join(core.quitar_prefijo(r), n)
                 for r, _, fs in os.walk(core.ruta_larga(out, forzar=True)) for n in fs
                 if n.endswith(".webp")]
    assert len(generados) == 2, [m for r in results for m in r.messages]
    assert max(len(p) for p in generados) > 260, "la prueba no llega a forzar el limite"
