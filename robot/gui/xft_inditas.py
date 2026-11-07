"""Linuxon a felület Xft-s Tk-val induljon, különben a szövegek csúnyák és elcsúsznak.

A uv által letöltött Pythonok (python-build-standalone) Tk-ja Xft nélkül készül: csak a
régi X11-betűket látja (élsimítás nélkül, hiányzó jelekkel, rossz méretezéssel). Ezen a
Pythonon belül nem lehet segíteni, mert a Tk bele van fordítva. Ha viszont a gépen van
olyan Python, amelynek a Tk-ja Xft-s (pl. /usr/bin/python3 a python3-tk csomaggal),
akkor a felületet azzal indítjuk újra. A customtkinter-t és társait a mostani
környezetből adjuk át (PYTHONPATH), mert ezek tiszta Python csomagok.

Csak a felületes indításnál fut (a -q és -m mód érintetlen), Windowson és a
lefordított exe-ben semmit nem csinál. Kikapcsolható: ROBOT_NINCS_UJRAINDITAS=1.
"""

from __future__ import annotations

import glob
import importlib.util
import os
import subprocess
import sys

TILTO_VALTOZO = "ROBOT_NINCS_UJRAINDITAS"
"""Ha be van állítva, nincs újraindítás (ez védi a végtelen újraindítást is)."""

_PROBA = (
    "import sys, tkinter\n"
    "assert sys.version_info >= (3, 11)\n"
    "import customtkinter\n"
    "r = tkinter.Tk(); r.withdraw()\n"
    "print(r.tk.call('::tk::pkgconfig', 'get', 'fontsystem'))\n"
    "r.destroy()\n"
)


def _sajat_tk_xft_nelkuli() -> bool:
    """Igaz, ha a futó Python Tk-ja X11-en Xft nélküli (vagy nem tudjuk eldönteni: hamis)."""
    import tkinter
    try:
        gyoker = tkinter.Tk()
    except tkinter.TclError:
        return False  # nincs kijelző: a felület úgysem indulna, ne bonyolítsuk
    try:
        gyoker.withdraw()
        if gyoker.tk.call("tk", "windowingsystem") != "x11":
            return False
        return str(gyoker.tk.call("::tk::pkgconfig", "get", "fontsystem")) != "xft"
    except tkinter.TclError:
        return False
    finally:
        gyoker.destroy()


def _jelolt_pythonok() -> list[str]:
    jeloltek = ["/usr/bin/python3", "/usr/local/bin/python3"]
    for minta in ("/usr/bin/python3.[0-9]*", "/usr/local/bin/python3.[0-9]*"):
        jeloltek += sorted((p for p in glob.glob(minta) if not p.endswith("-config")), reverse=True)
    sajat = os.path.realpath(sys.executable)
    egyedi: list[str] = []
    for jelolt in jeloltek:
        valodi = os.path.realpath(jelolt)
        if os.access(jelolt, os.X_OK) and valodi != sajat and valodi not in map(os.path.realpath, egyedi):
            egyedi.append(jelolt)
    return egyedi


def _csomag_utvonal() -> str | None:
    """A customtkinter-t tartalmazó site-packages mappa (a mostani környezetből)."""
    spec = importlib.util.find_spec("customtkinter")
    if spec is None or spec.origin is None:
        return None
    return os.path.dirname(os.path.dirname(spec.origin))


def ujrainditas_xft_pythonnal(main_utvonal: str, argumentumok: list[str]) -> None:
    """Ha kell és lehet, a felületet Xft-s Tk-jú Pythonnal indítja újra (nem tér vissza).

    Ha nincs ilyen Python, visszatér, és a felület a mostani Pythonnal indul
    (ilyenkor a stilus modul a legjobb régi X11-betűkre vált és figyelmeztet).
    """
    if not sys.platform.startswith("linux") or getattr(sys, "frozen", False):
        return
    if os.environ.get(TILTO_VALTOZO) or not _sajat_tk_xft_nelkuli():
        return
    kornyezet = dict(os.environ)
    kornyezet[TILTO_VALTOZO] = "1"
    csomagok = _csomag_utvonal()
    if csomagok:
        regi = kornyezet.get("PYTHONPATH")
        kornyezet["PYTHONPATH"] = csomagok + (os.pathsep + regi if regi else "")
    for python in _jelolt_pythonok():
        try:
            proba = subprocess.run([python, "-c", _PROBA], env=kornyezet, capture_output=True,
                                   text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            continue
        if proba.returncode == 0 and proba.stdout.strip() == "xft":
            print(f"A felület a(z) {python} Pythonnal indul, mert ennek a Tk-ja támogatja a "
                  "rendszer betűtípusait (Xft); a mostani Pythoné nem.", file=sys.stderr)
            sys.stderr.flush()
            sys.stdout.flush()
            os.execve(python, [python, main_utvonal, *argumentumok], kornyezet)
