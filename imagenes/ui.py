"""Colores ANSI, preguntas del asistente y barra de progreso. Sin dependencias."""
from __future__ import annotations
import os, sys, time


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
_CODES = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m", "red": "\033[31m",
    "green": "\033[32m", "yellow": "\033[33m", "blue": "\033[34m",
    "magenta": "\033[35m", "cyan": "\033[36m", "white": "\033[37m",
}


def c(text: str, *styles: str) -> str:
    if not USE_COLOR or not styles:
        return text
    return "".join(_CODES.get(s, "") for s in styles) + text + _CODES["reset"]


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def human_time(secs: float) -> str:
    secs = int(max(0, secs))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60:02d}s"
    return f"{secs // 3600}h {(secs % 3600) // 60:02d}m"


def banner(text: str) -> None:
    line = "=" * 58
    print(c(line, "cyan"))
    print(c(f"   {text}", "bold", "cyan"))
    print(c(line, "cyan"))


def section(text: str) -> None:
    print("\n" + c(text, "bold", "yellow"))


def warn(text: str) -> None:
    print(f"  {c('[!]', 'yellow', 'bold')} {text}")


def error(text: str) -> None:
    print(f"  {c('[X]', 'red', 'bold')} {text}")


def clean_path(raw: str) -> str:
    """Quita comillas y espacios: permite arrastrar carpetas a la terminal."""
    return raw.strip().strip('"').strip("'").strip()


# --------------------------------------------------------------------------
# Preguntas
# --------------------------------------------------------------------------

def ask(prompt: str, default: str = "") -> str:
    hint = c(f" [{default}]", "dim") if default else ""
    try:
        val = input(f"{c(prompt, 'white')}{hint}: ").strip()
    except EOFError:
        return default
    return val or default


def ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    d = "S/n" if default_yes else "s/N"
    while True:
        r = ask(f"{prompt} ({d})").lower()
        if not r:
            return default_yes
        if r in ("s", "si", "sí", "y", "yes"):
            return True
        if r in ("n", "no"):
            return False
        print(c("   Responde s o n.", "red"))


def ask_int(prompt: str, default: int, lo: int, hi: int) -> int:
    while True:
        r = ask(prompt, str(default))
        try:
            v = int(r)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(c(f"   Escribe un numero entre {lo} y {hi}.", "red"))


def ask_path(prompt: str, must_exist: bool = True, default: str = "") -> str:
    while True:
        r = clean_path(ask(prompt, default))
        if not r:
            print(c("   No puede estar vacio.", "red"))
            continue
        if must_exist and not os.path.exists(r):
            print(c(f"   No existe: {r}", "red"))
            print(c("   Consejo: arrastra la carpeta a la ventana o pega la ruta.", "dim"))
            continue
        return r


def ask_multichoice(title, options, default_keys):
    """options: lista de (clave, etiqueta). Devuelve lista de claves."""
    print("\n" + c(title, "bold", "yellow"))
    for i, (_, label) in enumerate(options, 1):
        print(f"   {c(str(i) + ')', 'cyan', 'bold')} {label}")
    default_nums = ",".join(str(i) for i, (k, _) in enumerate(options, 1) if k in default_keys)
    while True:
        r = ask("   Elige (numeros separados por coma)", default_nums)
        try:
            idx = [int(x) for x in r.replace(" ", "").split(",") if x]
            if idx and all(1 <= i <= len(options) for i in idx):
                seen, keys = set(), []
                for i in idx:
                    k = options[i - 1][0]
                    if k not in seen:
                        seen.add(k)
                        keys.append(k)
                return keys
        except ValueError:
            pass
        print(c("   Introduce numeros validos, por ejemplo: 1,2", "red"))


def ask_single_choice(title, options, default_key=None, default_num=1):
    """options: lista de (clave, etiqueta). Devuelve una clave."""
    print("\n" + c(title, "bold", "yellow"))
    for i, (_, label) in enumerate(options, 1):
        print(f"   {c(str(i) + ')', 'cyan', 'bold')} {label}")
    if default_key is not None:
        for i, (k, _) in enumerate(options, 1):
            if k == default_key:
                default_num = i
                break
    while True:
        r = ask("   Elige una opcion", str(default_num))
        try:
            i = int(r)
            if 1 <= i <= len(options):
                return options[i - 1][0]
        except ValueError:
            pass
        print(c("   Introduce un numero valido.", "red"))


# --------------------------------------------------------------------------
# Barra de progreso
# --------------------------------------------------------------------------

class Progress:
    """Barra de una sola linea con porcentaje y tiempo restante estimado."""

    def __init__(self, total: int, width: int = 28, enabled: bool = True):
        self.total = max(1, total)
        self.width = width
        self.done = 0
        self.start = time.perf_counter()
        self.enabled = enabled and sys.stdout.isatty()
        self._last_len = 0

    def update(self, done: int, label: str = "") -> None:
        self.done = done
        if not self.enabled:
            return
        frac = min(1.0, done / self.total)
        filled = int(self.width * frac)
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = time.perf_counter() - self.start
        eta = (elapsed / frac - elapsed) if frac > 0 else 0
        if len(label) > 28:
            label = label[:25] + "..."
        line = (f"  {c('[' + bar + ']', 'cyan')} {done}/{self.total} "
                f"{c(f'{frac * 100:3.0f}%', 'bold')}  faltan {human_time(eta)}  {c(label, 'dim')}")
        pad = max(0, self._last_len - len(line))
        sys.stdout.write("\r" + line + " " * pad)
        sys.stdout.flush()
        self._last_len = len(line)

    def clear(self) -> None:
        if self.enabled and self._last_len:
            sys.stdout.write("\r" + " " * self._last_len + "\r")
            sys.stdout.flush()
            self._last_len = 0
