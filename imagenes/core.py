"""Motor de conversion: busqueda de entradas, planificacion de salidas y conversion."""
from __future__ import annotations
import io, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageOps, ImageSequence

from . import OUTPUT_FOLDER_NAME
from .config import (Config, EXT, HAS_ANIMATION, HAS_QUALITY, PIL_NAME,
                     input_extensions, natural_key, parse_color, slugify)

# Fotos de 100+ Mpx (panoramicas, escaneos) son legitimas aqui: subimos el
# limite anti-"decompression bomb" en vez de que Pillow las rechace.
Image.MAX_IMAGE_PIXELS = 512_000_000


# ---------------------------------------------------------------------------
# Estructuras
# ---------------------------------------------------------------------------

@dataclass
class Target:
    size_name: str
    dims: Tuple[int, int]
    fmt: str
    path: str


@dataclass
class Job:
    src: str
    targets: List[Target] = field(default_factory=list)


@dataclass
class Result:
    src: str
    ok: bool = False
    width: int = 0
    height: int = 0
    written: int = 0
    skipped: int = 0
    errors: int = 0
    rows: List[dict] = field(default_factory=list)
    messages: List[Tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------

def collect_inputs(path: str, exclude_dir: str = "", recursive: bool = True) -> List[str]:
    exts = input_extensions()
    if os.path.isfile(path):
        return [path] if path.lower().endswith(exts) else []

    exclude = os.path.normcase(os.path.abspath(exclude_dir)) if exclude_dir else ""
    files: List[str] = []
    for dirpath, dirnames, names in os.walk(path):
        here = os.path.normcase(os.path.abspath(dirpath))
        # Comparar por segmentos de ruta: 'imagenes_convertidas_old' no debe
        # confundirse con 'imagenes_convertidas'.
        if exclude and (here == exclude or here.startswith(exclude + os.sep)):
            dirnames[:] = []
            continue
        for n in names:
            if n.lower().endswith(exts):
                files.append(os.path.join(dirpath, n))
        if not recursive:
            dirnames[:] = []
    # Ordena por ruta completa para que las carpetas no se entremezclen.
    return sorted(files, key=lambda p: [natural_key(part) for part in p.split(os.sep)])


def resolve_output_dir(cfg: Config) -> str:
    if cfg.output_dir:
        return os.path.abspath(cfg.output_dir)
    base = cfg.input_path if os.path.isdir(cfg.input_path) else os.path.dirname(cfg.input_path)
    return os.path.abspath(os.path.join(base or ".", OUTPUT_FOLDER_NAME))


# ---------------------------------------------------------------------------
# Planificacion
# ---------------------------------------------------------------------------

def plan(cfg: Config, inputs: List[str]) -> List[Job]:
    """Calcula por adelantado todas las rutas de salida.

    Hace dos cosas que la version 1 no hacia:
      - replica el arbol de subcarpetas, para que dos 'foto.jpg' en carpetas
        distintas no se pisen;
      - detecta colisiones que el arbol no resuelve (foto.png y foto.jpg dan
        el mismo foto.webp) y desambigua con un sufijo -2, -3...
    """
    base = cfg.input_path if os.path.isdir(cfg.input_path) else os.path.dirname(cfg.input_path)
    base = os.path.abspath(base or ".")
    out_root = resolve_output_dir(cfg)
    multi = cfg.multi_size
    pad = len(str(len(inputs)))          # relleno con ceros: -001, -002...
    used: Dict[str, str] = {}            # ruta normalizada -> origen que la ocupa
    jobs: List[Job] = []

    for i, src in enumerate(inputs, 1):
        if cfg.seo_prefix:
            stem = "%s-%0*d" % (slugify(cfg.seo_prefix), pad, i)
        else:
            stem = os.path.splitext(os.path.basename(src))[0]

        rel_dir = os.path.relpath(os.path.dirname(os.path.abspath(src)), base)
        if rel_dir == os.curdir:
            rel_dir = ""

        job = Job(src=src)
        for size_name, dims in cfg.sizes.items():
            for fmt in cfg.formats:
                parts = [out_root]
                if multi:
                    parts.append(size_name)
                if rel_dir:
                    parts.append(rel_dir)
                folder = os.path.join(*parts)
                path = os.path.join(folder, stem + EXT[fmt])

                key = os.path.normcase(path)
                if key in used:
                    n = 2
                    while os.path.normcase(
                            os.path.join(folder, "%s-%d%s" % (stem, n, EXT[fmt]))) in used:
                        n += 1
                    path = os.path.join(folder, "%s-%d%s" % (stem, n, EXT[fmt]))
                    key = os.path.normcase(path)
                used[key] = src
                job.targets.append(Target(size_name, dims, fmt, path))
        jobs.append(job)
    return jobs


def make_dirs(jobs: List[Job]) -> None:
    """Crea todas las carpetas antes de lanzar los hilos (evita carreras)."""
    for d in {os.path.dirname(t.path) for j in jobs for t in j.targets}:
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Tratamiento de imagen
# ---------------------------------------------------------------------------

# Solo estos formatos pueden traer una animacion. Hace falta mirarlo porque
# los JPEG de iPhone son MPO (llevan una segunda imagen incrustada) y declaran
# n_frames = 2 sin estar animados: tratarlos como animacion se saltaba la
# rotacion EXIF y el perfil de color, y salian tumbados.
ANIMATED_FORMATS = {"GIF", "WEBP", "PNG", "APNG", "AVIF"}


def is_animated(img: Image.Image) -> bool:
    if (getattr(img, "format", "") or "").upper() not in ANIMATED_FORMATS:
        return False
    return getattr(img, "n_frames", 1) > 1


def to_srgb(img: Image.Image, icc: Optional[bytes]):
    """Convierte al espacio sRGB. Devuelve (imagen, icc_a_incrustar)."""
    if not icc:
        return img, None
    try:
        from PIL import ImageCms
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        mode = "RGBA" if img.mode in ("RGBA", "LA") else "RGB"
        return ImageCms.profileToProfile(img, src, dst, outputMode=mode), None
    except Exception:
        # Si el perfil esta corrupto, mejor incrustarlo que estropear el color.
        return img, icc


def fit_image(img: Image.Image, dims: Tuple[int, int], mode: str,
              pad_rgb: Tuple[int, int, int]) -> Image.Image:
    """Redimensiona segun el modo de encaje. Nunca amplia una imagen pequena
    salvo en 'recortar', donde el tamano exacto es el objetivo."""
    w, h = dims
    if not w or not h:
        return img
    if mode == "recortar":
        return ImageOps.fit(img, (w, h), Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    out = img.copy()
    out.thumbnail((w, h), Image.Resampling.LANCZOS)
    if mode != "rellenar" or out.size == (w, h):
        return out

    canvas = Image.new("RGBA", (w, h), pad_rgb + (255,))
    src = out.convert("RGBA")
    canvas.paste(src, ((w - out.width) // 2, (h - out.height) // 2), src)
    return canvas


def prepare_for_format(img: Image.Image, fmt: str) -> Image.Image:
    """Aplana la transparencia sobre blanco en los formatos que no la admiten."""
    if fmt in ("jpg", "bmp"):
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            return bg
        return img if img.mode == "RGB" else img.convert("RGB")
    if fmt == "gif":
        return img
    if img.mode == "P":
        return img.convert("RGBA")
    if img.mode == "CMYK" and fmt in ("webp", "avif", "png"):
        return img.convert("RGB")
    return img


def save_kwargs(fmt: str, cfg: Config, icc: Optional[bytes], exif: Optional[bytes]) -> dict:
    kw: dict = {}
    if HAS_QUALITY[fmt]:
        kw["quality"] = cfg.quality.get(fmt, 82)
    if fmt == "webp":
        kw["method"] = 6
    elif fmt == "jpg":
        kw.update(optimize=True, progressive=True)
    elif fmt == "png":
        kw["optimize"] = True
    if cfg.color == "conservar" and icc:
        kw["icc_profile"] = icc
    if cfg.metadata == "conservar" and exif:
        kw["exif"] = exif
    return kw


def save_image(img: Image.Image, path: str, fmt: str, cfg: Config,
               icc: Optional[bytes] = None, exif: Optional[bytes] = None) -> None:
    kw = save_kwargs(fmt, cfg, icc, exif)
    pil = PIL_NAME[fmt]
    if fmt == "jpg":
        try:
            img.save(path, pil, subsampling="4:2:0", **kw)
            return
        except Exception:
            img.save(path, pil, **kw)
            return
    img.save(path, pil, **kw)


def save_animation(src: Image.Image, path: str, fmt: str, cfg: Config,
                   dims: Tuple[int, int], pad_rgb) -> None:
    """Conserva la animacion de un GIF/WEBP en vez de quedarse con el primer fotograma."""
    frames = []
    for frame in ImageSequence.Iterator(src):
        f = fit_image(frame.convert("RGBA"), dims, cfg.fit_mode, pad_rgb)
        frames.append(prepare_for_format(f, fmt))
    kw = save_kwargs(fmt, cfg, None, None)
    kw.update(save_all=True, append_images=frames[1:],
              loop=src.info.get("loop", 0), duration=src.info.get("duration", 100))
    if fmt == "gif":
        kw.pop("quality", None)
        kw["disposal"] = 2
    frames[0].save(path, PIL_NAME[fmt], **kw)


# ---------------------------------------------------------------------------
# Conversion de una imagen (se ejecuta en un hilo)
# ---------------------------------------------------------------------------

def convert_one(job: Job, cfg: Config, pad_rgb: Tuple[int, int, int]) -> Result:
    res = Result(src=job.src)
    name = os.path.basename(job.src)
    try:
        in_bytes = os.path.getsize(job.src)
    except OSError:
        in_bytes = 0

    try:
        with Image.open(job.src) as im:
            animated = is_animated(im)
            icc = im.info.get("icc_profile")

            if animated:
                base = im
                base.load()
                exif = None
                res.width, res.height = base.size
            else:
                base = ImageOps.exif_transpose(im) or im
                base.load()
                # El exif se lee DESPUES de enderezar: exif_transpose quita ya la
                # etiqueta de orientacion y asi no se gira dos veces.
                exif = base.info.get("exif")
                res.width, res.height = base.size
                if cfg.color == "srgb":
                    base, icc = to_srgb(base, icc)

            # Un solo redimensionado por tamano, reutilizado por todos los formatos.
            cache: Dict[str, Image.Image] = {}

            for t in job.targets:
                if os.path.exists(t.path) and not cfg.overwrite:
                    res.skipped += 1
                    res.messages.append(("skip", "ya existe, se omite: " + t.path))
                    continue
                try:
                    if animated and HAS_ANIMATION[t.fmt]:
                        base.seek(0)
                        save_animation(base, t.path, t.fmt, cfg, t.dims, pad_rgb)
                        base.seek(0)
                    else:
                        if animated:
                            base.seek(0)
                            res.messages.append((
                                "warn",
                                "%s: %s no admite animacion, se guarda el primer fotograma"
                                % (name, t.fmt.upper())))
                        if t.size_name not in cache:
                            cache[t.size_name] = fit_image(base, t.dims, cfg.fit_mode, pad_rgb)
                        img = prepare_for_format(cache[t.size_name], t.fmt)
                        save_image(img, t.path, t.fmt, cfg, icc, exif)

                    out_bytes = os.path.getsize(t.path)
                    with Image.open(t.path) as chk:
                        ow, oh = chk.size
                    res.written += 1
                    res.rows.append({
                        "entrada": job.src,
                        "entrada_bytes": in_bytes,
                        "entrada_px": "%dx%d" % (res.width, res.height),
                        "tamano": t.size_name,
                        "formato": t.fmt,
                        "salida": t.path,
                        "salida_bytes": out_bytes,
                        "salida_px": "%dx%d" % (ow, oh),
                        "ahorro_pct": round(100 * (1 - out_bytes / in_bytes), 1) if in_bytes else "",
                    })
                except Exception as e:
                    res.errors += 1
                    res.messages.append(("error", "%s -> %s: %s" % (name, t.path, e)))
        res.ok = res.errors == 0
    except Exception as e:
        res.errors += 1
        res.ok = False
        res.messages.append(("error", "%s: no se pudo abrir (%s)" % (name, e)))
    return res


def default_workers(n_jobs: int) -> int:
    cpu = os.cpu_count() or 4
    return max(1, min(cpu, 8, n_jobs))


def convert_all(cfg: Config, jobs: List[Job], on_progress=None) -> List[Result]:
    """Convierte en paralelo. Pillow libera el GIL al codificar, asi que los
    hilos dan paralelismo real sin los problemas de multiprocessing + PyInstaller."""
    pad_rgb = parse_color(cfg.pad_color)
    workers = cfg.workers or default_workers(len(jobs))
    results: List[Result] = []

    if workers <= 1:
        for i, job in enumerate(jobs, 1):
            results.append(convert_one(job, cfg, pad_rgb))
            if on_progress:
                on_progress(i, os.path.basename(job.src))
        return results

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(convert_one, j, cfg, pad_rgb): j for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            results.append(fut.result())
            if on_progress:
                on_progress(i, os.path.basename(futures[fut].src))
    # as_completed llega desordenado: se reordena para que el informe sea estable.
    order = {j.src: i for i, j in enumerate(jobs)}
    results.sort(key=lambda r: order.get(r.src, 0))
    return results
