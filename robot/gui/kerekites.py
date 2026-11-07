"""Élsimított lekerekített téglalapok tk.Canvas-ra – Pillow nélkül, csak a standard könyvtárral.

A Tk vászon (főleg Linuxon) nem simítja az éleket, ezért a sima `create_polygon`-nal
rajzolt kerek sarkok recések. Itt a négy sarok egy-egy kis, alfa csatornás PNG-kép
(a vászon tartalmára keveredik), az egyenes részek pedig sima téglalapok:

    ┌─╮      sarok-kép │ felső szegélycsík │ sarok-kép
    │ │      bal csík  │     kitöltés      │ jobb csík
    ╰─╯      sarok-kép │ alsó szegélycsík  │ sarok-kép

A sarokképeket túlmintavételezéssel (pixelenként 4×4 minta) számoljuk, és
gyorsítótárban tartjuk sugár / színek / szegélyvastagság szerint, így egy
újrarajzoláskor nem kell újra kiszámolni őket.
"""

from __future__ import annotations

import base64
import struct
import tkinter as tk
import zlib

MINTAVETEL = 4
"""Pixelenként ennyiszer ennyi mintából számoljuk a lefedettséget."""

_kepek: dict[tuple, tk.PhotoImage] = {}


def _png(szelesseg: int, magassag: int, rgba: bytes) -> str:
    """Nyers RGBA pixelekből base64-es PNG (a Tk PhotoImage ezt közvetlenül betölti)."""
    def darab(tipus: bytes, adat: bytes) -> bytes:
        return struct.pack(">I", len(adat)) + tipus + adat + struct.pack(">I", zlib.crc32(tipus + adat))

    sor_hossz = szelesseg * 4
    nyers = b"".join(b"\x00" + rgba[i * sor_hossz:(i + 1) * sor_hossz] for i in range(magassag))
    fejlec = struct.pack(">IIBBBBB", szelesseg, magassag, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + darab(b"IHDR", fejlec) + darab(b"IDAT", zlib.compress(nyers, 9))
           + darab(b"IEND", b""))
    return base64.b64encode(png).decode("ascii")


def _rgb(vaszon: tk.Misc, szin: str) -> tuple[int, int, int]:
    piros, zold, kek = vaszon.winfo_rgb(szin)
    return piros >> 8, zold >> 8, kek >> 8


def _bal_felso_sarok(r: int, vastag: int, kitoltes: tuple | None,
                     szegely: tuple | None) -> list[tuple[int, int, int, int]]:
    """A bal felső sarok r×r pixele (RGBA); a kör középpontja a négyzet jobb alsó csúcsa."""
    belso_r = r - vastag if szegely is not None else r
    lepes = 1 / MINTAVETEL
    osszes = MINTAVETEL * MINTAVETEL
    pixelek = []
    for py in range(r):
        for px in range(r):
            kulso = belso = 0
            for i in range(MINTAVETEL):
                dy = r - (py + (i + 0.5) * lepes)
                for j in range(MINTAVETEL):
                    dx = r - (px + (j + 0.5) * lepes)
                    tav2 = dx * dx + dy * dy
                    if tav2 <= r * r:
                        kulso += 1
                        if belso_r > 0 and tav2 <= belso_r * belso_r:
                            belso += 1
            if kulso == 0:
                pixelek.append((0, 0, 0, 0))
                continue
            gyuru = kulso - belso
            szinek = []
            for csatorna in range(3):
                osszeg = 0.0
                if szegely is not None:
                    osszeg += szegely[csatorna] * gyuru
                if kitoltes is not None:
                    osszeg += kitoltes[csatorna] * belso
                szinek.append(round(osszeg / max(kulso if kitoltes is not None else gyuru, 1)))
            # Kitöltés nélkül csak a szegélygyűrű látszik.
            fedes = kulso if kitoltes is not None else gyuru
            pixelek.append((*szinek, round(255 * fedes / osszes)))
    return pixelek


def _sarok_kepek(vaszon: tk.Misc, r: int, kitoltes: str, szegely: str,
                 vastag: int) -> tuple[tk.PhotoImage, ...]:
    """A négy sarok képe (bal felső, jobb felső, bal alsó, jobb alsó), gyorsítótárból."""
    kulcs = (str(vaszon.tk), r, kitoltes, szegely, vastag)
    if kulcs + ("bf",) in _kepek:
        return tuple(_kepek[kulcs + (nev,)] for nev in ("bf", "jf", "ba", "ja"))
    kitoltes_rgb = _rgb(vaszon, kitoltes) if kitoltes else None
    szegely_rgb = _rgb(vaszon, szegely) if szegely and vastag > 0 else None
    alap = _bal_felso_sarok(r, vastag, kitoltes_rgb, szegely_rgb)
    sorok = [alap[y * r:(y + 1) * r] for y in range(r)]
    tukrozesek = {
        "bf": sorok,
        "jf": [sor[::-1] for sor in sorok],
        "ba": sorok[::-1],
        "ja": [sor[::-1] for sor in sorok[::-1]],
    }
    for nev, kepsorok in tukrozesek.items():
        rgba = bytes(ertek for sor in kepsorok for pixel in sor for ertek in pixel)
        _kepek[kulcs + (nev,)] = tk.PhotoImage(master=vaszon, data=_png(r, r, rgba), format="png")
    return tuple(_kepek[kulcs + (nev,)] for nev in ("bf", "jf", "ba", "ja"))


def kerek_teglalap(vaszon: tk.Canvas, x0: float, y0: float, x1: float, y1: float, r: float = 6,
                   fill: str = "", outline: str = "", width: float = 1, dash=None, tags=()) -> None:
    """Lekerekített téglalap élsimított sarkokkal; a szegély a téglalapon belülre kerül.

    Szaggatott szegélyhez (dash) a régi, sokszöges rajzolást használjuk, mert a
    szaggatás a csíkokra bontva nem folytonos.
    """
    x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
    r = int(round(min(r, (x1 - x0) / 2, (y1 - y0) / 2)))
    vastag = int(round(width)) if outline else 0
    if dash is not None or r < 2:
        _sokszog(vaszon, x0, y0, x1, y1, r, fill=fill, outline=outline, width=width, dash=dash, tags=tags)
        return
    bf, jf, ba, ja = _sarok_kepek(vaszon, r, fill, outline, vastag)
    if fill:
        vaszon.create_rectangle(x0 + r, y0, x1 - r, y1, fill=fill, width=0, tags=tags)
        vaszon.create_rectangle(x0, y0 + r, x1, y1 - r, fill=fill, width=0, tags=tags)
    if vastag:
        for csik in ((x0 + r, y0, x1 - r, y0 + vastag), (x0 + r, y1 - vastag, x1 - r, y1),
                     (x0, y0 + r, x0 + vastag, y1 - r), (x1 - vastag, y0 + r, x1, y1 - r)):
            vaszon.create_rectangle(*csik, fill=outline, width=0, tags=tags)
    vaszon.create_image(x0, y0, image=bf, anchor="nw", tags=tags)
    vaszon.create_image(x1 - r, y0, image=jf, anchor="nw", tags=tags)
    vaszon.create_image(x0, y1 - r, image=ba, anchor="nw", tags=tags)
    vaszon.create_image(x1 - r, y1 - r, image=ja, anchor="nw", tags=tags)


def _sokszog(vaszon: tk.Canvas, x0, y0, x1, y1, r, **opciok) -> None:
    opciok = {kulcs: ertek for kulcs, ertek in opciok.items() if ertek is not None}
    pontok = (x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
              x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0)
    vaszon.create_polygon(pontok, smooth=True, **opciok)
