#!/usr/bin/env python3
"""
imagenes - Conversor de imagenes por terminal, 100% guiado y con colores.

    imagenes

La salida se crea SIEMPRE dentro de la carpeta de origen, en una subcarpeta
'imagenes_convertidas'. Con varios tamanos se crean subcarpetas por tamano;
con uno solo, las imagenes van sueltas.
"""
from __future__ import annotations
import csv, os, re, sys, unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Falta Pillow. Instala:\n    python -m pip install --user Pillow")

# ---- Color ANSI, sin dependencias ----
def _enable_windows_ansi() -> None:
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass
_enable_windows_ansi()
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
_CODES = {"reset":"\033[0m","bold":"\033[1m","dim":"\033[2m","red":"\033[31m",
"green":"\033[32m","yellow":"\033[33m","blue":"\033[34m","magenta":"\033[35m",
"cyan":"\033[36m","white":"\033[37m"}
def c(text: str, *styles: str) -> str:
    if not USE_COLOR or not styles:
        return text
    return "".join(_CODES.get(s,"") for s in styles) + text + _CODES["reset"]

INPUT_EXTS = (".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff",".gif")
OUTPUT_FOLDER_NAME = "imagenes_convertidas"
FORMATS = [("webp","WEBP",".webp"),("jpg","JPEG",".jpg"),("png","PNG",".png"),
           ("bmp","BMP",".bmp"),("tiff","TIFF",".tiff")]
FMT_BY_KEY = {k:(p,e) for k,p,e in FORMATS}
SIZE_PRESETS = {"thumb":(300,300),"medium":(800,800),"large":(1600,1600),"full":(1920,1920)}

@dataclass
class Config:
    input_path: str = ""
    output_dir: str = ""
    formats: List[str] = field(default_factory=lambda: ["webp"])
    sizes: Dict[str, Tuple[int,int]] = field(default_factory=lambda: {"original":(0,0)})
    jpeg_quality: int = 85
    webp_quality: int = 82
    seo_prefix: str = ""
    overwrite: bool = True

def slugify(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+","-",text)
    text = re.sub(r"-{2,}","-",text).strip("-")
    return text or "imagen"
def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]
def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)
def human(n: float) -> str:
    for u in ("B","KB","MB","GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u=="B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"
def clean_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'").strip()
def banner(text: str) -> None:
    line = "="*58
    print(c(line,"cyan")); print(c(f"   {text}","bold","cyan")); print(c(line,"cyan"))
def section(text: str) -> None:
    print("\n" + c(text,"bold","yellow"))

def ask(prompt: str, default: str="") -> str:
    hint = c(f" [{default}]","dim") if default else ""
    try:
        val = input(f"{c(prompt,'white')}{hint}: ").strip()
    except EOFError:
        return default
    return val or default
def ask_yes_no(prompt: str, default_yes: bool=True) -> bool:
    d = "S/n" if default_yes else "s/N"
    while True:
        r = ask(f"{prompt} ({d})").lower()
        if not r: return default_yes
        if r in ("s","si","sí","y","yes"): return True
        if r in ("n","no"): return False
        print(c("   Responde s o n.","red"))
def ask_int(prompt: str, default: int, lo: int, hi: int) -> int:
    while True:
        r = ask(prompt, str(default))
        try:
            v = int(r)
            if lo <= v <= hi: return v
        except ValueError:
            pass
        print(c(f"   Escribe un numero entre {lo} y {hi}.","red"))
def ask_path(prompt: str, must_exist: bool=True, allow_empty: bool=False) -> str:
    while True:
        r = clean_path(ask(prompt))
        if not r and allow_empty: return ""
        if not r:
            print(c("   No puede estar vacio.","red")); continue
        if must_exist and not os.path.exists(r):
            print(c(f"   No existe: {r}","red"))
            print(c("   Consejo: arrastra la carpeta a la ventana o pega la ruta.","dim")); continue
        return r
def ask_multichoice(title, options, default_keys):
    print("\n" + c(title,"bold","yellow"))
    for i,(_,label) in enumerate(options,1):
        print(f"   {c(str(i)+')','cyan','bold')} {label}")
    default_nums = ",".join(str(i) for i,(k,_) in enumerate(options,1) if k in default_keys)
    while True:
        r = ask("   Elige (numeros separados por coma)", default_nums)
        try:
            idx = [int(x) for x in r.replace(" ","").split(",") if x]
            if idx and all(1 <= i <= len(options) for i in idx):
                seen=set(); keys=[]
                for i in idx:
                    k = options[i-1][0]
                    if k not in seen: seen.add(k); keys.append(k)
                return keys
        except ValueError:
            pass
        print(c("   Introduce numeros validos, por ejemplo: 1,2","red"))
def ask_single_choice(title, options, default_num):
    print("\n" + c(title,"bold","yellow"))
    for i,(_,label) in enumerate(options,1):
        print(f"   {c(str(i)+')','cyan','bold')} {label}")
    while True:
        r = ask("   Elige una opcion", str(default_num))
        try:
            i = int(r)
            if 1 <= i <= len(options): return options[i-1][0]
        except ValueError:
            pass
        print(c("   Introduce un numero valido.","red"))

def wizard() -> Config:
    cfg = Config()
    banner("IMAGENES  -  conversor guiado")
    print(c("Responde a cada pregunta. Pulsa ENTER para el valor por","dim"))
    print(c("defecto (lo que aparece entre corchetes).","dim"))
    section("--- 1. Que quieres convertir ---")
    cfg.input_path = ask_path("Carpeta con las imagenes (o un solo archivo)", must_exist=True)
    fmt_opts = [(k,k.upper()) for k,_,_ in FORMATS]
    cfg.formats = ask_multichoice("--- 2. A que formato(s) lo quieres convertir ---", fmt_opts, ["webp"])
    size_opts = [("original","Mantener el tamano original"),("thumb","Miniatura  (max 300 px)"),
        ("medium","Mediano    (max 800 px)"),("large","Grande     (max 1600 px)"),
        ("full","Completo   (max 1920 px)"),("varios","Varios tamanos a la vez (elegir)"),
        ("custom","Tamano personalizado (yo escribo los pixeles)")]
    cfg.sizes = resolve_sizes(ask_single_choice("--- 3. A que tamano ---", size_opts, 1))
    section("--- 4. Calidad ---")
    if "jpg" in cfg.formats:
        cfg.jpeg_quality = ask_int("Calidad JPG (1-100, mas = mejor)", 85, 1, 100)
    if "webp" in cfg.formats:
        cfg.webp_quality = ask_int("Calidad WEBP (1-100, mas = mejor)", 82, 1, 100)
    if not ("jpg" in cfg.formats or "webp" in cfg.formats):
        print(c("   (No aplica a los formatos elegidos.)","dim"))
    section("--- 5. Nombre de los archivos ---")
    if ask_yes_no("Quieres renombrarlos con un nombre SEO?", default_yes=False):
        prefix = ask("   Escribe el nombre base (ej: playa-mojacar)", "imagen")
        cfg.seo_prefix = prefix
        print(c(f"   Se llamaran: {slugify(prefix)}-1, {slugify(prefix)}-2, ...","dim"))
    return cfg
def resolve_sizes(choice):
    if choice == "original": return {"original":(0,0)}
    if choice in SIZE_PRESETS: return {choice: SIZE_PRESETS[choice]}
    if choice == "varios":
        opts = [("thumb","Miniatura (300)"),("medium","Mediano (800)"),("large","Grande (1600)"),
                ("full","Completo (1920)"),("original","Original")]
        keys = ask_multichoice("   Elige los tamanos que quieres generar:", opts, ["medium","large"])
        return {k: SIZE_PRESETS.get(k,(0,0)) for k in keys} or {"original":(0,0)}
    if choice == "custom":
        w = ask_int("   Ancho maximo en pixeles", 1200, 1, 20000)
        h = ask_int("   Alto maximo en pixeles", 1200, 1, 20000)
        return {f"{w}x{h}":(w,h)}
    return {"original":(0,0)}

def open_fixed(p): return ImageOps.exif_transpose(Image.open(p))
def resize_to_fit(img, mw, mh):
    o = img.copy()
    if mw and mh: o.thumbnail((mw,mh), Image.Resampling.LANCZOS)
    return o
def prepare_for_format(img, fmt):
    if fmt in ("jpg","bmp"):
        if img.mode in ("RGBA","LA","P"):
            r = img.convert("RGBA"); bg = Image.new("RGB", r.size, (255,255,255))
            bg.paste(r, mask=r.split()[-1]); return bg
        return img if img.mode == "RGB" else img.convert("RGB")
    return img.convert("RGBA") if img.mode == "P" else img
def save_image(img, path, fmt, cfg):
    pil = FMT_BY_KEY[fmt][0]
    if fmt == "jpg":
        kw = dict(quality=cfg.jpeg_quality, optimize=True, progressive=True)
        try: img.save(path, pil, subsampling="4:2:0", **kw); return
        except Exception: img.save(path, pil, **kw); return
    if fmt == "webp": img.save(path, pil, quality=cfg.webp_quality, method=6)
    elif fmt == "png": img.save(path, pil, optimize=True)
    else: img.save(path, pil)
def collect_inputs(path, exclude_dir=""):
    if os.path.isfile(path):
        return [path] if path.lower().endswith(INPUT_EXTS) else []
    exclude = os.path.abspath(exclude_dir) if exclude_dir else ""
    files = []
    for dp,_,ns in os.walk(path):
        if exclude and os.path.abspath(dp).startswith(exclude): continue
        for n in ns:
            if n.lower().endswith(INPUT_EXTS): files.append(os.path.join(dp,n))
    return sorted(files, key=lambda x: natural_key(os.path.basename(x)))
def run(cfg) -> int:
    base = cfg.input_path if os.path.isdir(cfg.input_path) else os.path.dirname(cfg.input_path)
    cfg.output_dir = os.path.join(base, OUTPUT_FOLDER_NAME)
    inputs = collect_inputs(cfg.input_path, exclude_dir=cfg.output_dir)
    if not inputs:
        print(c("\nNo se han encontrado imagenes en esa ruta.","red")); return 1
    ensure_dir(cfg.output_dir)
    multi = len(cfg.sizes) > 1
    rows = []; cnt = 1; ok = errors = written = 0
    print("\n" + c("-"*58,"dim"))
    print(f"Convirtiendo {c(str(len(inputs)),'bold')} imagen(es)")
    print(f"-> formatos: {c(', '.join(f.upper() for f in cfg.formats),'cyan')}")
    print(f"-> tamanos : {c(', '.join(cfg.sizes),'cyan')}")
    print(f"-> salida  : {c(cfg.output_dir,'cyan')}")
    print(c("   (una subcarpeta por cada tamano)" if multi else "   (imagenes sueltas dentro de la carpeta)","dim"))
    print(c("-"*58,"dim") + "\n")
    for inp in inputs:
        in_bytes = os.path.getsize(inp)
        stem = os.path.splitext(os.path.basename(inp))[0]
        if cfg.seo_prefix:
            out_stem = f"{slugify(cfg.seo_prefix)}-{cnt}"; cnt += 1
        else:
            out_stem = stem
        try:
            src = open_fixed(inp)
        except Exception as e:
            print(f"  {c('[X]','red','bold')} {os.path.basename(inp)}: no se pudo abrir ({e})")
            errors += 1; continue
        for sn,(mw,mh) in cfg.sizes.items():
            rz = resize_to_fit(src, mw, mh)
            for fmt in cfg.formats:
                od = os.path.join(cfg.output_dir, sn) if multi else cfg.output_dir
                ensure_dir(od); op = os.path.join(od, out_stem + FMT_BY_KEY[fmt][1])
                ob = ""
                if os.path.exists(op) and not cfg.overwrite:
                    print(f"  {c('[=]','yellow')} ya existe, se omite: {op}")
                else:
                    try:
                        save_image(prepare_for_format(rz, fmt), op, fmt, cfg)
                        ob = str(os.path.getsize(op)); written += 1
                    except Exception as e:
                        print(f"  {c('[X]','red','bold')} {op}: error al guardar ({e})")
                        errors += 1; continue
                rows.append({"entrada":inp,"entrada_bytes":str(in_bytes),"tamano":sn,
                             "formato":fmt,"salida":op,"salida_bytes":ob})
        w,h = src.size
        print(f"  {c('[ok]','green','bold')} {os.path.basename(inp)} {c(f'({w}x{h})','dim')} -> {c(out_stem,'green')}")
        ok += 1
    if rows:
        rp = os.path.join(cfg.output_dir, "reporte.csv")
        with open(rp,"w",newline="",encoding="utf-8") as f:
            wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wcsv.writeheader(); wcsv.writerows(rows)
    total_out = sum(int(r["salida_bytes"]) for r in rows if r["salida_bytes"])
    print("\n" + c("="*58,"green"))
    print(c(f"  Listo. Imagenes: {ok}   Archivos creados: {written}   Errores: {errors}","bold","green" if errors==0 else "yellow"))
    if total_out: print(f"  Peso total de salida: {c(human(total_out),'bold')}")
    print(f"  Guardado en: {c(cfg.output_dir,'cyan')}")
    print(c("="*58,"green"))
    return 0 if errors == 0 else 1
def main() -> int:
    try:
        while True:
            cfg = wizard()
            multi = len(cfg.sizes) > 1
            destino = os.path.join(cfg.input_path if os.path.isdir(cfg.input_path)
                                   else os.path.dirname(cfg.input_path), OUTPUT_FOLDER_NAME)
            print("\n" + c("-"*58,"magenta"))
            print(c("  RESUMEN","bold","magenta"))
            print(f"   Entrada : {cfg.input_path}")
            print(f"   Formatos: {c(', '.join(f.upper() for f in cfg.formats),'cyan')}")
            print(f"   Tamanos : {c(', '.join(cfg.sizes),'cyan')}")
            if cfg.seo_prefix: print(f"   Nombre  : {slugify(cfg.seo_prefix)}-1, -2, ...")
            print(f"   Salida  : {c(destino,'cyan')}")
            print(c(f"             {'subcarpetas por tamano' if multi else 'imagenes sueltas (un solo tamano)'}","dim"))
            print(c("-"*58,"magenta"))
            if ask_yes_no("Empezar la conversion?", default_yes=True):
                run(cfg)
            else:
                print(c("Cancelado.","yellow"))
            if not ask_yes_no("\nConvertir otra tanda?", default_yes=False):
                print(c("Hasta luego!","bold","cyan")); return 0
    except KeyboardInterrupt:
        print(c("\nCancelado.","yellow")); return 130
if __name__ == "__main__":
    raise SystemExit(main())
