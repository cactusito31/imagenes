"""Pruebas de calidad de imagen: color, EXIF, transparencia, animacion y encaje."""
import os

from PIL import Image, ImageCms, ImageDraw

from imagenes import core
from imagenes.config import Config
from tests.test_core import convertir, hacer_imagen


def test_perfil_icc_no_se_pierde(tmp_path):
    """La v1 no pasaba icc_profile al guardar: las fotos salian desaturadas."""
    base = str(tmp_path)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    hacer_imagen(os.path.join(base, "con_perfil.jpg"), quality=95, icc_profile=icc)

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)},
                 color="conservar")
    out, _ = convertir(cfg)

    with Image.open(os.path.join(out, "con_perfil.webp")) as im:
        assert im.info.get("icc_profile"), "se ha perdido el perfil de color"


def test_modo_srgb_convierte_y_no_incrusta_perfil(tmp_path):
    base = str(tmp_path)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    hacer_imagen(os.path.join(base, "con_perfil.jpg"), quality=95, icc_profile=icc)

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)}, color="srgb")
    out, _ = convertir(cfg)

    with Image.open(os.path.join(out, "con_perfil.webp")) as im:
        assert not im.info.get("icc_profile")


def test_orientacion_exif_se_aplica_una_sola_vez(tmp_path):
    """Apaisada con orientacion 6 debe salir vertical, y sin la etiqueta puesta."""
    base = str(tmp_path)
    img = Image.new("RGB", (800, 400), (120, 60, 180))
    exif = Image.Exif()
    exif[274] = 6
    p = os.path.join(base, "girada.jpg")
    img.save(p, exif=exif, quality=95)

    cfg = Config(input_path=base, formats=["jpg"], sizes={"original": (0, 0)},
                 metadata="conservar")
    out, _ = convertir(cfg)

    with Image.open(os.path.join(out, "girada.jpg")) as im:
        assert im.size == (400, 800), "no se ha enderezado"
        assert im.getexif().get(274) in (None, 1), "la etiqueta sigue puesta: se giraria dos veces"


def test_metadatos_limpiar_quita_el_gps(tmp_path):
    base = str(tmp_path)
    img = Image.new("RGB", (400, 300), (10, 10, 10))
    exif = Image.Exif()
    exif[271] = "MarcaCamara"
    p = os.path.join(base, "conmeta.jpg")
    img.save(p, exif=exif, quality=95)

    cfg = Config(input_path=base, formats=["jpg"], sizes={"original": (0, 0)},
                 metadata="limpiar")
    out, _ = convertir(cfg)
    with Image.open(os.path.join(out, "conmeta.jpg")) as im:
        assert im.getexif().get(271) is None


def test_transparencia_se_aplana_en_jpg_y_se_conserva_en_webp(tmp_path):
    base = str(tmp_path)
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([50, 50, 350, 350], fill=(220, 40, 40, 255))
    im.save(os.path.join(base, "trans.png"))

    cfg = Config(input_path=base, formats=["jpg", "webp"], sizes={"original": (0, 0)})
    out, _ = convertir(cfg)

    with Image.open(os.path.join(out, "trans.jpg")) as j:
        assert j.mode == "RGB"
        assert j.getpixel((2, 2)) == (255, 255, 255)
    with Image.open(os.path.join(out, "trans.webp")) as w:
        assert w.mode == "RGBA"


def test_gif_animado_conserva_los_fotogramas(tmp_path):
    """La v1 se quedaba con el primer fotograma, sin avisar."""
    base = str(tmp_path)
    frames = []
    for i in range(6):
        f = Image.new("RGB", (200, 200), (20, 20, 30))
        ImageDraw.Draw(f).ellipse([i * 20, i * 20, i * 20 + 80, i * 20 + 80],
                                  fill=(255 - i * 30, 40 + i * 30, 120))
        frames.append(f.convert("P", palette=Image.Palette.ADAPTIVE))
    frames[0].save(os.path.join(base, "anim.gif"), save_all=True,
                   append_images=frames[1:], duration=100, loop=0)

    cfg = Config(input_path=base, formats=["webp", "jpg"], sizes={"original": (0, 0)})
    out, results = convertir(cfg)

    with Image.open(os.path.join(out, "anim.webp")) as w:
        assert getattr(w, "n_frames", 1) == 6, "se ha perdido la animacion"
    # y en JPG, que no puede animarse, tiene que avisar
    avisos = [m for r in results for lvl, m in r.messages if lvl == "warn"]
    assert any("animacion" in m for m in avisos)


def test_encaje_recortar_da_medida_exacta(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "ancha.jpg"), size=(1200, 400))

    cfg = Config(input_path=base, formats=["webp"], sizes={"500x500": (500, 500)},
                 fit_mode="recortar")
    out, _ = convertir(cfg)
    with Image.open(os.path.join(out, "ancha.webp")) as im:
        assert im.size == (500, 500)


def test_encaje_rellenar_da_medida_exacta_con_fondo(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "ancha.jpg"), size=(1200, 400))

    cfg = Config(input_path=base, formats=["png"], sizes={"500x500": (500, 500)},
                 fit_mode="rellenar", pad_color="negro")
    out, _ = convertir(cfg)
    with Image.open(os.path.join(out, "ancha.png")) as im:
        assert im.size == (500, 500)
        assert im.convert("RGB").getpixel((2, 2)) == (0, 0, 0)


def test_ajustar_no_amplia_las_pequenas(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "chica.jpg"), size=(200, 150))

    cfg = Config(input_path=base, formats=["webp"], sizes={"large": (1600, 1600)})
    out, _ = convertir(cfg)
    with Image.open(os.path.join(out, "chica.webp")) as im:
        assert im.size == (200, 150)


def test_no_sobrescribir_omite_lo_que_ya_existe(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "una.jpg"))

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)})
    convertir(cfg)
    cfg.overwrite = False
    _, results = convertir(cfg)
    assert sum(r.skipped for r in results) == 1
    assert sum(r.written for r in results) == 0


def test_archivo_corrupto_no_tumba_la_tanda(tmp_path):
    base = str(tmp_path)
    hacer_imagen(os.path.join(base, "buena.jpg"))
    with open(os.path.join(base, "rota.jpg"), "wb") as f:
        f.write(b"esto no es una imagen")

    cfg = Config(input_path=base, formats=["webp"], sizes={"original": (0, 0)})
    out, results = convertir(cfg)
    assert os.path.exists(os.path.join(out, "buena.webp"))
    assert sum(r.errors for r in results) == 1
    assert sum(r.written for r in results) == 1
