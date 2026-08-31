"""Motor de conversion: busqueda de entradas, planificacion de salidas y conversion."""
from __future__ import annotations
import io, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fnmatch
import shutil
import threading

from PIL import Image, ImageOps, ImageSequence

from . import OUTPUT_FOLDER_NAME
from .config import (CARPETA_ORIGINALES, Config, EXT, HAS_ANIMATION, HAS_QUALITY, PIL_NAME,
                     input_extensions, natural_key, parse_color, slugify)

# Fotos de 100+ Mpx (panoramicas, escaneos) son legitimas aqui: subimos el
# limite anti-"decompression bomb" en vez de que Pillow las rechace.
Image.MAX_IMAGE_PIXELS = 512_000_000

# Windows corta las rutas en 260 caracteres. Al replicar el arbol de carpetas y
# anadir la subcarpeta del tamano, las rutas de salida se alargan bastante mas
# que en la version 1, que era plana: sin esto, una carpeta de origen larga
# hacia fallar todos los archivos con un enganoso "No such file or directory".
LIMITE_RUTA = 240
BARRA = chr(92)                       # una barra invertida
DOBLE_BARRA = BARRA * 2
PREFIJO_LARGO = DOBLE_BARRA + "?" + BARRA


def ruta_larga(path: str, forzar: bool = False) -> str:
    """Prefija la ruta para saltarse el limite de 260 caracteres de Windows.

    Con forzar=True se prefija aunque la ruta sea corta. Hace falta al recorrer
    carpetas: la raiz puede ser corta y las de dentro no, y os.walk hereda el
    prefijo de la raiz. Sin esto, os.walk se para en lo hondo y devuelve una
    lista vacia sin dar ningun error.
    """
    if os.name != "nt":
        return path
    p = os.path.abspath(path)
    if p.startswith(PREFIJO_LARGO) or (len(p) < LIMITE_RUTA and not forzar):
        return p
    if p.startswith(DOBLE_BARRA):
        return PREFIJO_LARGO + "UNC" + os.sep + p[2:]
    return PREFIJO_LARGO + p


def quitar_prefijo(path: str) -> str:
    """Devuelve la ruta legible: el prefijo solo vale para hablar con Windows."""
    if path.startswith(PREFIJO_LARGO + "UNC" + os.sep):
        return DOBLE_BARRA + path[len(PREFIJO_LARGO) + 4:]
    if path.startswith(PREFIJO_LARGO):
        return path[len(PREFIJO_LARGO):]
    return path


class PixelBudget:
    """Limita cuantos pixeles hay descomprimidos a la vez.

    Los hilos siguen siendo los que son, pero solo entran a decodificar los que
    quepan en el presupuesto. Sin esto, 8 hilos con fotos de 12 Mpx y varios
    tamanos llegaban a 2,6 GB, y con un escaneo grande se disparaba.
    """

    def __init__(self, limite: int):
        self.limite = max(1, limite)
        self.usado = 0
        self._cv = threading.Condition()

    def acquire(self, n: int) -> int:
        n = max(1, min(n, self.limite))
        with self._cv:
            # Si una sola imagen no cabe, se la deja pasar sola en vez de
            # bloquear para siempre.
            while self.usado and self.usado + n > self.limite:
                self._cv.wait()
            self.usado += n
        return n

    def release(self, n: int) -> None:
        with self._cv:
            self.usado = max(0, self.usado - n)
            self._cv.notify_all()


class _SinPresupuesto:
    def acquire(self, n): return n
    def release(self, n): pass


# Dos frenos distintos, porque el gasto tiene dos origenes distintos:
#
# 1) La imagen descomprimida que cada hilo tiene viva. Se cobra por pixel y
#    solo estorba con panoramicas o escaneos muy grandes.
# 2) La codificacion a AVIF. Medido con fotos de 12 Mpx: unos 390 MB por
#    conversion simultanea, y por encima de 4 a la vez NO se gana tiempo
#    (62 s con 4 hilos, 66 s con 8). Limitar solo esto deja que el trabajo
#    barato (WEBP, JPG) siga yendo a todo lo que dan los hilos.
PRESUPUESTO_BYTES = 1_500_000_000
BYTES_POR_PIXEL_DEFECTO = 16
MAX_AVIF_SIMULTANEOS = 4


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
    destino_original: str = ""      # solo si se pide mover los originales


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

def esta_excluido(rel: str, patrones) -> bool:
    """Compara el patron contra la ruta relativa y contra cada tramo suelto,
    para que tanto 'borradores/*' como 'borradores' o '*.tmp.*' funcionen."""
    if not patrones:
        return False
    rel = rel.replace(os.sep, "/")
    tramos = rel.split("/")
    for pat in patrones:
        pat = pat.replace(os.sep, "/").strip()
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(tramos[-1], pat):
            return True
        if any(fnmatch.fnmatch(t, pat) for t in tramos[:-1]):
            return True
    return False


def collect_inputs(path: str, exclude_dir: str = "", recursive: bool = True,
                   exclude: Optional[List[str]] = None, min_px: int = 0) -> List[str]:
    exts = input_extensions()
    if os.path.isfile(ruta_larga(path)):
        return [path] if path.lower().endswith(exts) else []

    # OJO: no reutilizar el nombre 'exclude', que es el de los patrones.
    dir_excluida = os.path.normcase(os.path.abspath(exclude_dir)) if exclude_dir else ""
    files: List[str] = []
    # Se recorre con el prefijo de ruta larga: sin el, os.walk no entra en las
    # carpetas hondas y se saltaba las imagenes SIN dar ningun error.
    for dirpath, dirnames, names in os.walk(ruta_larga(path, forzar=True)):
        dirpath = quitar_prefijo(dirpath)
        here = os.path.normcase(os.path.abspath(dirpath))
        # Comparar por segmentos de ruta: 'imagenes_convertidas_old' no debe
        # confundirse con 'imagenes_convertidas'.
        if dir_excluida and (here == dir_excluida
                             or here.startswith(dir_excluida + os.sep)):
            dirnames[:] = []
            continue
        for n in names:
            if not n.lower().endswith(exts):
                continue
            completo = os.path.join(dirpath, n)
            if exclude:
                rel = os.path.relpath(completo, os.path.abspath(path))
                if esta_excluido(rel, exclude):
                    continue
            files.append(completo)
        if not recursive:
            dirnames[:] = []
    if min_px:
        files = [f for f in files if _lado_mayor(f) >= min_px]
    # Ordena por ruta completa para que las carpetas no se entremezclen.
    return sorted(files, key=lambda p: [natural_key(part) for part in p.split(os.sep)])


def _lado_mayor(path: str) -> int:
    """Lee solo la cabecera: no hace falta descomprimir para saber la medida."""
    try:
        with Image.open(ruta_larga(path)) as im:
            return max(im.size)
    except Exception:
        return 0


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
        if cfg.originales == "mover":
            job.destino_original = os.path.join(out_root, CARPETA_ORIGINALES,
                                                rel_dir, os.path.basename(src))
        jobs.append(job)
    return jobs


def make_dirs(jobs: List[Job]) -> None:
    """Crea todas las carpetas antes de lanzar los hilos (evita carreras)."""
    for d in {os.path.dirname(t.path) for j in jobs for t in j.targets}:
        os.makedirs(ruta_larga(d), exist_ok=True)


# ---------------------------------------------------------------------------
# Tratamiento de imagen
# ---------------------------------------------------------------------------

# Solo estos formatos pueden traer una animacion. Hace falta mirarlo porque
# los JPEG de iPhone son MPO (llevan una segunda imagen incrustada) y declaran
# n_frames = 2 sin estar animados: tratarlos como animacion se saltaba la
# rotacion EXIF y el perfil de color, y salian tumbados.
CLAVE_POR_FORMATO_PIL = {v: k for k, v in PIL_NAME.items()}
CLAVE_POR_FORMATO_PIL["MPO"] = "jpg"


def ya_esta_bien(clave_origen: str, medida, t: Target, cfg: Config) -> bool:
    """Cierto si rehacer este archivo no aportaria nada: mismo formato y la
    imagen ya cabe en la medida pedida. Evita recomprimir y perder calidad."""
    if not cfg.no_recompress or clave_origen != t.fmt:
        return False
    ancho, alto = t.dims
    if not ancho or not alto:
        return True
    if cfg.fit_mode != "ajustar":
        return False        # recortar y rellenar cambian la medida siempre
    return medida[0] <= ancho and medida[1] <= alto


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


def _guardar_atomico(guardar, path: str) -> None:
    """Escribe a un temporal y renombra al terminar.

    Si algo se tuerce a media escritura (disco lleno, corte de luz, Ctrl+C) lo
    que queda es un .tmp, no un archivo con el nombre bueno y el contenido roto.
    """
    destino = ruta_larga(path)
    temporal = destino + ".tmp"
    try:
        guardar(temporal)
        os.replace(temporal, destino)
    except BaseException:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise


def save_image(img: Image.Image, path: str, fmt: str, cfg: Config,
               icc: Optional[bytes] = None, exif: Optional[bytes] = None) -> None:
    kw = save_kwargs(fmt, cfg, icc, exif)
    pil = PIL_NAME[fmt]

    def guardar(destino):
        if fmt == "jpg":
            try:
                img.save(destino, pil, subsampling="4:2:0", **kw)
                return
            except Exception:
                img.save(destino, pil, **kw)
                return
        img.save(destino, pil, **kw)

    _guardar_atomico(guardar, path)


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
    _guardar_atomico(lambda destino: frames[0].save(destino, PIL_NAME[fmt], **kw), path)


# ---------------------------------------------------------------------------
# Conversion de una imagen (se ejecuta en un hilo)
# ---------------------------------------------------------------------------

def _agrupar_por_tamano(targets):
    """Los targets vienen ordenados por tamano; se agrupan para poder soltar
    la imagen redimensionada en cuanto acaba su ultimo formato."""
    grupos, actual, clave = [], [], None
    for t in targets:
        if t.size_name != clave:
            if actual:
                grupos.append((clave, actual))
            clave, actual = t.size_name, []
        actual.append(t)
    if actual:
        grupos.append((clave, actual))
    return grupos


def convert_one(job: Job, cfg: Config, pad_rgb: Tuple[int, int, int],
                budget=None, cancel=None, avif_gate=None) -> Result:
    res = Result(src=job.src)
    name = os.path.basename(job.src)
    budget = budget or _SinPresupuesto()
    try:
        in_bytes = os.path.getsize(ruta_larga(job.src))
    except OSError:
        in_bytes = 0

    reservado = 0
    try:
        with Image.open(ruta_larga(job.src)) as im:
            # El tamano se conoce sin descomprimir: se pide sitio ANTES de cargar.
            w, h = im.size
            reservado = budget.acquire(w * h * BYTES_POR_PIXEL_DEFECTO)

            animated = is_animated(im)
            clave_origen = CLAVE_POR_FORMATO_PIL.get((im.format or "").upper(), "")
            icc = im.info.get("icc_profile")

            if animated:
                base = im
                base.load()
                exif = None
            else:
                base = ImageOps.exif_transpose(im) or im
                base.load()
                # El exif se lee DESPUES de enderezar: exif_transpose quita ya la
                # etiqueta de orientacion y asi no se gira dos veces.
                exif = base.info.get("exif")
                if cfg.color == "srgb":
                    base, icc = to_srgb(base, icc)
            res.width, res.height = base.size

            for size_name, targets in _agrupar_por_tamano(job.targets):
                if cancel is not None and cancel.is_set():
                    break
                redimensionada = None
                for t in targets:
                    if cancel is not None and cancel.is_set():
                        break
                    if os.path.exists(ruta_larga(t.path)) and not cfg.overwrite:
                        res.skipped += 1
                        res.messages.append(("skip", "ya existe, se omite: " + t.path))
                        continue
                    if ya_esta_bien(clave_origen, (res.width, res.height), t, cfg):
                        res.skipped += 1
                        res.messages.append(
                            ("skip", "%s ya esta en %s y dentro de la medida, no se toca"
                             % (name, t.fmt.upper())))
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
                            if redimensionada is None:
                                redimensionada = fit_image(base, t.dims, cfg.fit_mode, pad_rgb)
                            listo = prepare_for_format(redimensionada, t.fmt)
                            if t.fmt == "avif" and avif_gate is not None:
                                with avif_gate:
                                    save_image(listo, t.path, t.fmt, cfg, icc, exif)
                            else:
                                save_image(listo, t.path, t.fmt, cfg, icc, exif)

                        out_bytes = os.path.getsize(ruta_larga(t.path))
                        with Image.open(ruta_larga(t.path)) as chk:
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
                        res.messages.append(("error", "%s -> %s: %s"
                                             % (name, t.path, _explicar(e, t.path))))
                # Fuera la copia de este tamano antes de pasar al siguiente.
                redimensionada = None
        res.ok = res.errors == 0
        if res.ok and res.written and cfg.originales != "dejar":
            _apartar_original(job, cfg, res)
    except Exception as e:
        res.errors += 1
        res.ok = False
        res.messages.append(("error", "%s: no se pudo abrir (%s)"
                             % (name, _explicar(e, job.src))))
    finally:
        if reservado:
            budget.release(reservado)
    return res


def _apartar_original(job: Job, cfg: Config, res: Result) -> None:
    """Mueve o borra el original, pero SOLO si todo salio bien y se escribio
    algo. Ante la menor duda, el original se queda donde esta."""
    try:
        if cfg.originales == "mover" and job.destino_original:
            os.makedirs(ruta_larga(os.path.dirname(job.destino_original)), exist_ok=True)
            destino = job.destino_original
            n = 2
            while os.path.exists(ruta_larga(destino)):
                raiz, ext = os.path.splitext(job.destino_original)
                destino = "%s-%d%s" % (raiz, n, ext)
                n += 1
            shutil.move(ruta_larga(job.src), ruta_larga(destino))
        elif cfg.originales == "borrar":
            os.remove(ruta_larga(job.src))
    except OSError as e:
        res.messages.append(("warn", "no se pudo apartar el original %s (%s)"
                             % (os.path.basename(job.src), e)))


def _explicar(e: Exception, path: str) -> str:
    """Windows dice 'No such file or directory' cuando en realidad la ruta es
    demasiado larga. Merece la pena decirlo con todas las letras."""
    if isinstance(e, OSError) and len(os.path.abspath(path)) >= LIMITE_RUTA:
        return ("la ruta tiene %d caracteres y Windows no llega: acorta los nombres "
                "de carpeta o usa -o con una carpeta de destino mas corta"
                % len(os.path.abspath(path)))
    return str(e)


@dataclass
class Batch:
    results: List[Result] = field(default_factory=list)
    interrupted: bool = False


def default_workers(n_jobs: int) -> int:
    cpu = os.cpu_count() or 4
    return max(1, min(cpu, 8, n_jobs))


def convert_all(cfg: Config, jobs: List[Job], on_progress=None) -> Batch:
    """Convierte en paralelo. Pillow libera el GIL al codificar, asi que los
    hilos dan paralelismo real sin los problemas de multiprocessing + PyInstaller.

    Ctrl+C corta de verdad: cancela lo que aun no ha empezado y avisa a los
    hilos en marcha para que no sigan con los tamanos que les quedan.
    """
    pad_rgb = parse_color(cfg.pad_color)
    workers = cfg.workers or default_workers(len(jobs))
    budget = PixelBudget(PRESUPUESTO_BYTES)
    avif_gate = threading.Semaphore(max(1, min(MAX_AVIF_SIMULTANEOS, workers)))
    cancel = threading.Event()
    lote = Batch()

    if workers <= 1:
        try:
            for i, job in enumerate(jobs, 1):
                lote.results.append(convert_one(job, cfg, pad_rgb, budget, cancel, avif_gate))
                if on_progress:
                    on_progress(i, os.path.basename(job.src), lote.results[-1])
        except KeyboardInterrupt:
            lote.interrupted = True
        return lote

    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(convert_one, j, cfg, pad_rgb, budget, cancel, avif_gate): j for j in jobs}
    try:
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            lote.results.append(r)
            if on_progress:
                on_progress(i, os.path.basename(futures[fut].src), r)
    except KeyboardInterrupt:
        lote.interrupted = True
        cancel.set()
        pool.shutdown(wait=False, cancel_futures=True)
        for fut in futures:
            if fut.done() and not fut.cancelled() and fut.exception() is None:
                r = fut.result()
                if r not in lote.results:
                    lote.results.append(r)
    finally:
        pool.shutdown(wait=True)

    # as_completed llega desordenado: se reordena para que el informe sea estable.
    order = {j.src: i for i, j in enumerate(jobs)}
    lote.results.sort(key=lambda r: order.get(r.src, 0))
    return lote
