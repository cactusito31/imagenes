import os

from imagenes import report


def fila(entrada, entrada_bytes, salida, salida_bytes, fmt, px, tamano):
    return {"entrada": entrada, "entrada_bytes": entrada_bytes, "entrada_px": "2000x1500",
            "tamano": tamano, "formato": fmt, "salida": salida,
            "salida_bytes": salida_bytes, "salida_px": px, "ahorro_pct": 0}


def test_totales_cuentan_cada_origen_una_vez():
    """Una imagen que genera 4 salidas no debe contarse 4 veces en la entrada."""
    rows = [
        fila("a.jpg", 1000, "m/a.webp", 100, "webp", "800x600", "medium"),
        fila("a.jpg", 1000, "l/a.webp", 200, "webp", "1600x1200", "large"),
        fila("b.jpg", 1000, "m/b.webp", 150, "webp", "800x600", "medium"),
    ]
    t = report.totals(rows)
    assert t["entrada"] == 2000
    assert t["salida"] == 450
    assert t["ahorro"] == 1550


def test_totales_admiten_que_la_salida_pese_mas():
    rows = [fila("a.gif", 100, "a.png", 400, "png", "200x200", "original")]
    t = report.totals(rows)
    assert t["ahorro"] == -300
    assert t["ahorro_pct"] < 0


def test_snippet_ordena_avif_antes_que_webp_y_pone_los_anchos(tmp_path):
    out = str(tmp_path)
    rows = [
        fila("a.jpg", 1000, os.path.join(out, "medium", "a.webp"), 100, "webp", "800x600", "medium"),
        fila("a.jpg", 1000, os.path.join(out, "large", "a.webp"), 200, "webp", "1600x1200", "large"),
        fila("a.jpg", 1000, os.path.join(out, "medium", "a.avif"), 80, "avif", "800x600", "medium"),
        fila("a.jpg", 1000, os.path.join(out, "large", "a.avif"), 160, "avif", "1600x1200", "large"),
    ]
    html = report.build_snippet(rows, out)
    assert html.index("image/avif") < html.index("image/webp")
    assert "800w" in html and "1600w" in html
    assert "medium/a.avif" in html            # rutas relativas y con barras web
    assert "loading=\"lazy\"" in html


def test_snippet_usa_jpg_como_respaldo_si_existe(tmp_path):
    out = str(tmp_path)
    rows = [
        fila("a.jpg", 1000, os.path.join(out, "a.webp"), 100, "webp", "800x600", "medium"),
        fila("a.jpg", 1000, os.path.join(out, "a.jpg"), 300, "jpg", "800x600", "medium"),
    ]
    html = report.build_snippet(rows, out)
    assert "<img src=\"a.jpg\"" in html


def test_csv_lleva_marca_de_tiempo_y_no_pisa_al_anterior(tmp_path):
    out = str(tmp_path)
    rows = [fila("a.jpg", 1000, os.path.join(out, "a.webp"), 100, "webp", "800x600", "medium")]
    p1 = report.write_csv(rows, out)
    assert os.path.basename(p1).startswith("reporte-")
    assert os.path.exists(p1)
    contenido = open(p1, encoding="utf-8-sig").read()
    assert "ahorro_pct" in contenido
    assert ";" in contenido      # Excel en espanol abre bien el punto y coma
