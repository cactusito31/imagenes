"""El asistente es por donde entra casi todo el mundo y no tenia ni una prueba."""
import builtins
import os

import pytest

from imagenes import wizard as W
from imagenes.config import Config
from tests.test_core import hacer_imagen


@pytest.fixture
def responder(monkeypatch):
    """Sustituye el teclado por una lista de respuestas."""
    def _preparar(respuestas):
        pendientes = list(respuestas)

        def falso_input(prompt=""):
            if not pendientes:
                raise EOFError            # a partir de aqui, todo por defecto
            return pendientes.pop(0)

        monkeypatch.setattr(builtins, "input", falso_input)
        return pendientes
    return _preparar


@pytest.fixture(autouse=True)
def ajustes_aparte(monkeypatch, tmp_path):
    """Que las pruebas no toquen el config.json de verdad."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "ajustes"))


def test_todo_por_defecto_no_revienta(responder, tmp_path):
    responder([])
    hacer_imagen(os.path.join(str(tmp_path), "una.jpg"))
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.input_path == str(tmp_path)
    assert cfg.formats == ["webp"]


def test_elegir_preset_web(responder, tmp_path):
    # 2 = preset web; el resto por defecto
    responder(["2"])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.formats == ["webp", "avif"]
    assert list(cfg.sizes) == ["medium", "large"]
    assert cfg.color == "srgb"


def test_formatos_y_tamano_a_mano(responder, tmp_path):
    # partir de cero(6) -> formatos 1,3 -> tamano mediano(3) -> calidades por defecto
    responder(["6", "1,3", "3", "", ""])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.formats == ["webp", "jpg"]
    assert list(cfg.sizes) == ["medium"]


def test_tamano_personalizado(responder, tmp_path):
    # de cero -> webp -> 7 (personalizado) -> 900 x 600 -> encaje por defecto
    responder(["6", "1", "7", "900", "600"])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.sizes == {"900x600": (900, 600)}


def test_varios_tamanos(responder, tmp_path):
    responder(["6", "1", "6", "1,3"])       # varios -> miniatura y grande
    cfg = W.wizard(initial_path=str(tmp_path))
    assert list(cfg.sizes) == ["thumb", "large"]


def test_encaje_solo_se_pregunta_si_hay_medida(responder, tmp_path):
    """Con tamano original no tiene sentido preguntar como encajar."""
    responder(["6", "1", "1"])               # de cero, webp, original
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.fit_mode == "ajustar"


def test_nombre_seo(responder, tmp_path):
    responder(["6", "1", "1", "", "s", "Playa de Mojacar"])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.seo_prefix == "Playa de Mojacar"


def test_opciones_avanzadas(responder, tmp_path):
    # de cero, webp, original, calidad, sin SEO, avanzadas si:
    #   metadatos conservar(2), color srgb(2), recursivo n, sobrescribir n,
    #   snippet n, no-recomprimir s, sin patrones, sin minimo, originales mover(2)
    responder(["6", "1", "1", "", "n", "s", "2", "2", "n", "n", "n",
               "s", "", "n", "2"])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.metadata == "conservar"
    assert cfg.color == "srgb"
    assert cfg.recursive is False
    assert cfg.overwrite is False
    assert cfg.make_snippet is False
    assert cfg.no_recompress is True
    assert cfg.originales == "mover"


def test_borrar_originales_pide_confirmacion_y_se_puede_echar_atras(responder, tmp_path):
    """Elegir borrar y decir que no debe dejarlo en dejar, no en borrar."""
    responder(["6", "1", "1", "", "n", "s", "", "", "", "", "",
               "", "", "n", "3", "n"])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert cfg.originales == "dejar"


def test_los_pasos_se_numeran_sin_saltos(responder, tmp_path, capsys):
    """Cuando se omite el paso de encaje la numeracion no debe saltar."""
    responder(["6", "1", "1"])
    W.wizard(initial_path=str(tmp_path))
    salida = capsys.readouterr().out
    numeros = [int(l.split(".")[0].replace("---", "").strip())
               for l in salida.splitlines() if l.startswith("--- ") and "." in l]
    assert numeros == list(range(1, len(numeros) + 1)), numeros


def test_respuesta_invalida_vuelve_a_preguntar(responder, tmp_path):
    # "banana" no es un numero: debe insistir y aceptar el 3 siguiente
    responder(["6", "1", "banana", "3", ""])
    cfg = W.wizard(initial_path=str(tmp_path))
    assert list(cfg.sizes) == ["medium"]


def test_la_calidad_se_pregunta_solo_de_los_formatos_que_la_usan(responder, tmp_path, capsys):
    responder(["6", "4", "1"])               # solo PNG, que no tiene calidad
    W.wizard(initial_path=str(tmp_path))
    salida = capsys.readouterr().out
    assert "No aplica" in salida


def test_resolve_sizes_cae_en_original_si_no_se_elige_nada():
    assert W.resolve_sizes("loquesea", Config()) == {"original": (0, 0)}
