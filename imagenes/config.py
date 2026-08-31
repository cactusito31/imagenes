"""Formatos, tamanos, la clase Config y el fichero de ajustes de usuario."""
from __future__ import annotations
import json, os, re, unicodedata
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------
# clave, nombre PIL, extension, admite calidad, admite animacion
FORMATS = [
    ("webp", "WEBP", ".webp", True,  True),
    ("avif", "AVIF", ".avif", True,  True),
    ("jpg",  "JPEG", ".jpg",  True,  False),
    ("png",  "PNG",  ".png",  False, True),
    ("gif",  "GIF",  ".gif",  False, True),
    ("tiff", "TIFF", ".tiff", False, False),
    ("bmp",  "BMP",  ".bmp",  False, False),
]
FMT_KEYS = [f[0] for f in FORMATS]
PIL_NAME = {f[0]: f[1] for f in FORMATS}
EXT = {f[0]: f[2] for f in FORMATS}
HAS_QUALITY = {f[0]: f[3] for f in FORMATS}
HAS_ANIMATION = {f[0]: f[4] for f in FORMATS}
MIME = {"webp": "image/webp", "avif": "image/avif", "jpg": "image/jpeg",
        "png": "image/png", "gif": "image/gif", "tiff": "image/tiff",
        "bmp": "image/bmp"}

# Extensiones de entrada. Las de HEIC solo sirven si pillow-heif esta instalado.
INPUT_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif")
HEIF_EXTS = (".heic", ".heif")

DEFAULT_QUALITY = {"jpg": 85, "webp": 82, "avif": 60}

SIZE_PRESETS = {
    "thumb":  (300, 300),
    "medium": (800, 800),
    "large":  (1600, 1600),
    "full":   (1920, 1920),
}

FIT_MODES = ("ajustar", "recortar", "rellenar")
METADATA_MODES = ("limpiar", "conservar")
COLOR_MODES = ("conservar", "srgb")
ORIGINALES_MODES = ("dejar", "mover", "borrar")
CARPETA_ORIGINALES = "originales_procesados"


def has_heif_support() -> bool:
    """Registra el lector de HEIC/HEIF si el paquete opcional esta disponible."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        return True
    except Exception:
        return False


def input_extensions() -> Tuple[str, ...]:
    return INPUT_EXTS + HEIF_EXTS if has_heif_support() else INPUT_EXTS


@dataclass
class Config:
    input_path: str = ""
    output_dir: str = ""
    formats: List[str] = field(default_factory=lambda: ["webp"])
    sizes: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {"original": (0, 0)})
    quality: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_QUALITY))
    seo_prefix: str = ""
    overwrite: bool = True
    recursive: bool = True
    fit_mode: str = "ajustar"
    pad_color: str = "#ffffff"
    metadata: str = "limpiar"
    color: str = "conservar"
    workers: int = 0          # 0 = automatico
    make_snippet: bool = True
    exclude: List[str] = field(default_factory=list)   # patrones tipo *.tmp, borradores/*
    min_px: int = 0           # se saltan las imagenes cuyo lado mayor no llegue
    no_recompress: bool = False   # no rehacer lo que ya esta en el formato y medida
    originales: str = "dejar"     # dejar | mover | borrar

    def to_dict(self) -> dict:
        d = asdict(self)
        # las tuplas no sobreviven a JSON: se guardan como listas
        d["sizes"] = {k: list(v) for k, v in self.sizes.items()}
        d.pop("input_path", None)
        d.pop("output_dir", None)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        cfg = cls()
        for k, v in (d or {}).items():
            if not hasattr(cfg, k):
                continue
            if k == "sizes" and isinstance(v, dict):
                v = {kk: tuple(vv) for kk, vv in v.items()}
            if k == "quality" and isinstance(v, dict):
                q = dict(DEFAULT_QUALITY)
                q.update({kk: int(vv) for kk, vv in v.items()})
                v = q
            setattr(cfg, k, v)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        self.formats = [f for f in self.formats if f in FMT_KEYS] or ["webp"]
        if self.fit_mode not in FIT_MODES:
            self.fit_mode = "ajustar"
        if self.metadata not in METADATA_MODES:
            self.metadata = "limpiar"
        if self.color not in COLOR_MODES:
            self.color = "conservar"
        if self.originales not in ORIGINALES_MODES:
            self.originales = "dejar"
        self.min_px = max(0, int(self.min_px))
        self.exclude = [str(x) for x in (self.exclude or []) if str(x).strip()]
        if not self.sizes:
            self.sizes = {"original": (0, 0)}
        for k in ("jpg", "webp", "avif"):
            self.quality[k] = max(1, min(100, int(self.quality.get(k, DEFAULT_QUALITY[k]))))
        self.workers = max(0, min(64, int(self.workers)))

    @property
    def multi_size(self) -> bool:
        return len(self.sizes) > 1


# ---------------------------------------------------------------------------
# Presets de fabrica
# ---------------------------------------------------------------------------

BUILTIN_PRESETS: Dict[str, dict] = {
    "web": {
        "formats": ["webp", "avif"],
        "sizes": {"medium": [800, 800], "large": [1600, 1600]},
        "quality": {"webp": 82, "avif": 60, "jpg": 85},
        "metadata": "limpiar", "color": "srgb",
        "_desc": "WEBP + AVIF en mediano y grande, sin metadatos. Para publicar en web.",
    },
    "woo": {
        "formats": ["webp"],
        "sizes": {"thumb": [300, 300], "medium": [800, 800], "large": [1600, 1600]},
        "quality": {"webp": 82},
        "fit_mode": "rellenar", "pad_color": "#ffffff",
        "metadata": "limpiar", "color": "srgb",
        "_desc": "Fichas de producto: cuadradas con fondo blanco, en los 3 tamanos de WooCommerce.",
    },
    "rapido": {
        "formats": ["webp"],
        "sizes": {"large": [1600, 1600]},
        "quality": {"webp": 80},
        "_desc": "Un solo WEBP a 1600 px. Lo mas rapido.",
    },
    "maxima-calidad": {
        "formats": ["webp"],
        "sizes": {"original": [0, 0]},
        "quality": {"webp": 95},
        "metadata": "conservar", "color": "conservar",
        "_desc": "Tamano original, calidad 95, conserva metadatos y perfil de color.",
    },
}


# ---------------------------------------------------------------------------
# Fichero de ajustes
# ---------------------------------------------------------------------------

def config_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Imagenes")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "imagenes")


def config_file() -> str:
    return os.path.join(config_dir(), "config.json")


def load_settings() -> dict:
    try:
        with open(config_file(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> bool:
    """Guardar ajustes nunca debe tumbar la aplicacion."""
    try:
        os.makedirs(config_dir(), exist_ok=True)
        tmp = config_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, config_file())
        return True
    except OSError:
        return False


def remember(cfg: Config) -> None:
    """Guarda la ultima configuracion usada para ofrecerla como valor por defecto."""
    data = load_settings()
    data["ultimo"] = cfg.to_dict()
    save_settings(data)


def last_config() -> Config:
    return Config.from_dict(load_settings().get("ultimo", {}))


def all_presets() -> Dict[str, dict]:
    presets = dict(BUILTIN_PRESETS)
    presets.update(load_settings().get("presets", {}))
    return presets


def get_preset(name: str) -> Optional[Config]:
    p = all_presets().get(name)
    if p is None:
        return None
    return Config.from_dict({k: v for k, v in p.items() if not k.startswith("_")})


def save_preset(name: str, cfg: Config, desc: str = "") -> bool:
    data = load_settings()
    presets = data.setdefault("presets", {})
    entry = cfg.to_dict()
    entry["_desc"] = desc or ("Preset guardado: " + name)
    presets[name] = entry
    return save_settings(data)


def delete_preset(name: str) -> bool:
    data = load_settings()
    if name in data.get("presets", {}):
        del data["presets"][name]
        return save_settings(data)
    return False


# ---------------------------------------------------------------------------
# Utilidades de texto y de tamanos
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "imagen"


def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def parse_size(spec: str) -> Tuple[str, Tuple[int, int]]:
    """medium -> (medium,(800,800)); 800 -> (800,(800,800)); 900x600 -> (900x600,(900,600))."""
    spec = spec.strip().lower()
    if spec in ("original", "orig", "0"):
        return "original", (0, 0)
    if spec in SIZE_PRESETS:
        return spec, SIZE_PRESETS[spec]
    m = re.fullmatch(r"(\d{1,5})\s*[x*]\s*(\d{1,5})", spec)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w and h:
            return "%dx%d" % (w, h), (w, h)
    if spec.isdigit() and int(spec) > 0:
        n = int(spec)
        return str(n), (n, n)
    raise ValueError(
        "tamano no valido: " + repr(spec) + ". Usa original, thumb, medium, large, "
        "full, un numero (800) o ANCHOxALTO (900x600)."
    )


def parse_sizes(specs: List[str]) -> Dict[str, Tuple[int, int]]:
    out: Dict[str, Tuple[int, int]] = {}
    for s in specs:
        for part in str(s).split(","):
            part = part.strip()
            if part:
                k, v = parse_size(part)
                out[k] = v
    return out or {"original": (0, 0)}


def parse_formats(specs: List[str]) -> List[str]:
    out: List[str] = []
    for s in specs:
        for part in str(s).split(","):
            part = part.strip().lower()
            if not part:
                continue
            if part == "jpeg":
                part = "jpg"
            if part == "tif":
                part = "tiff"
            if part not in FMT_KEYS:
                raise ValueError("formato no valido: " + repr(part)
                                 + ". Elige entre: " + ", ".join(FMT_KEYS) + ".")
            if part not in out:
                out.append(part)
    return out or ["webp"]


def parse_color(spec) -> Tuple[int, int, int]:
    """Acepta #ffffff, ffffff, fff, blanco, negro, gris."""
    s = str(spec).strip().lower().lstrip("#")
    named = {"blanco": "ffffff", "negro": "000000", "gris": "808080",
             "white": "ffffff", "black": "000000", "gray": "808080"}
    s = named.get(s, s)
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6 or any(ch not in "0123456789abcdef" for ch in s):
        return (255, 255, 255)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
