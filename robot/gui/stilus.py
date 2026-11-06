"""Közös megjelenés: betűtípusok, színek, customtkinter beállítások.

A betűtípust a gépen ténylegesen elérhető családok közül választjuk: Windowson
Segoe UI / Consolas, Linuxon DejaVu / Noto / Ubuntu. Így nem jelennek meg
hiányzó karakterek (üres négyzetek) az ékezetes betűk és a jelek helyén.
Emojit szándékosan nem használunk, csak olyan jeleket, amelyek ezekben a
betűtípusokban biztosan megvannak (▶ ■ ▲ ▼ ← → ↑ ↺ ✕).

Linuxon a Tk csak akkor látja a rendszer betűtípusait, ha Xft-vel fordították.
A uv / python-build-standalone Pythonok Tk-ja Xft nélküli („x11” fontrendszer):
ilyenkor csak a régi X11-betűk érhetők el, ezek közül a helvetica és a courier
a legjobb. Ezt az `XFT_HIANYZIK` jelzi, a főablak figyelmeztet is rá.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

_SANS_JELOLTEK = ("Segoe UI", "DejaVu Sans", "Noto Sans", "Ubuntu", "Cantarell",
                  "Liberation Sans", "Arial", "Helvetica", "Nimbus Sans L")
_MONO_JELOLTEK = ("Consolas", "DejaVu Sans Mono", "Noto Sans Mono", "Ubuntu Mono",
                  "Liberation Mono", "Cascadia Mono", "Courier New", "Courier", "Nimbus Mono L")

SANS = "TkDefaultFont"
MONO = "TkFixedFont"
XFT_HIANYZIK = False
"""Igaz, ha a Tk Linuxon Xft nélkül fut (csak régi X11-betűk érhetők el)."""
XFT_UZENET = ("Figyelem: ennek a Pythonnak a Tk-ja nem támogatja a rendszer betűtípusait (Xft), "
              "ezért a betűk elnagyoltak lehetnek. Megoldás: rendszer-Python (lásd build.md).")

# ---- Színek (világos téma; a blokkszínek a feladatleírás ábráit követik) ----
HATTER = "#eef1f6"
PANEL = "#ffffff"
SZEGELY = "#d0d7e2"
SZOVEG = "#1f2937"
HALVANY = "#6b7280"
KIEMELO = "#2563eb"

SZIN_OK = "#15803d"
SZIN_HIBA = "#b91c1c"
SZIN_FUT = "#c2410c"
SZIN_INFO = "#334155"

GOMB_FUTTAT = ("#16a34a", "#15803d")
GOMB_LEPES = ("#2563eb", "#1d4ed8")
GOMB_ALLJ = ("#dc2626", "#b91c1c")
GOMB_SEMLEGES = ("#64748b", "#475569")


def _elso_elerheto(jeloltek: tuple[str, ...], tartalek: str) -> str:
    """Az első létező család (X11-betűknél a nevek kisbetűsek, ezért kisbetűsen hasonlítunk)."""
    elerheto = {csalad.lower(): csalad for csalad in tkfont.families()}
    for csalad in jeloltek:
        if csalad.lower() in elerheto:
            return elerheto[csalad.lower()]
    return tartalek


def _xft_hianyzik(gyoker: tk.Misc) -> bool:
    if gyoker.tk.call("tk", "windowingsystem") != "x11":
        return False
    try:
        return str(gyoker.tk.call("::tk::pkgconfig", "get", "fontsystem")) != "xft"
    except tk.TclError:
        return False


def beallit(gyoker: tk.Misc) -> None:
    """A gyökérablak létrehozása után kell hívni (a családok csak ekkor kérdezhetők le)."""
    global SANS, MONO, XFT_HIANYZIK
    XFT_HIANYZIK = _xft_hianyzik(gyoker)
    SANS = _elso_elerheto(_SANS_JELOLTEK, "TkDefaultFont")
    MONO = _elso_elerheto(_MONO_JELOLTEK, "TkFixedFont")
    for nev in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(nev).configure(family=SANS, size=10)
        except tk.TclError:
            pass
    try:
        tkfont.nametofont("TkFixedFont").configure(family=MONO, size=10)
    except tk.TclError:
        pass
    gyoker.option_add("*Menu.font", (SANS, 10))
    gyoker.option_add("*Dialog.msg.font", (SANS, 10))


def ctk_alap() -> None:
    """Téma és megjelenés (a gyökérablak előtt hívandó)."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


# A régi X11-betűk 11 képpont alatt hibásak (pl. eltűnik az „i”), ezért ott ez a legkisebb méret.
X11_MIN_PX = 11


def _px(meret: int) -> int:
    return max(meret, X11_MIN_PX) if XFT_HIANYZIK else meret


def betu(meret: int = 11, vastag: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=SANS, size=_px(meret), weight="bold" if vastag else "normal")


def mono(meret: int = 11, vastag: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=MONO, size=_px(meret), weight="bold" if vastag else "normal")


def tk_betu(meret: int = 10, vastag: bool = False) -> tuple:
    """Sima tk vezérlőkhöz (Canvas, Text, Menu)."""
    return (SANS, meret, "bold") if vastag else (SANS, meret)


def tk_mono(meret: int = 10, vastag: bool = False) -> tuple:
    return (MONO, meret, "bold") if vastag else (MONO, meret)
