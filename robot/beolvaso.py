"""Bemeneti fájl beolvasása: első sor méret, utána a térkép, a többi a program.

Visszafelé is működik: a `bemenet_szoveg` ugyanilyen formátumú szöveget állít elő
(az IDE mentéséhez).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from terkep import MEZO_JELEK, Irany, Mezo, Robot, Terkep, Vilag


@dataclass
class Bemenet:
    """A beolvasott fájl tartalma."""

    vilag: Vilag
    program_sorok: list[str]


def beolvas_fajl(utvonal: str | Path) -> Bemenet:
    """Beolvassa és feldolgozza a bemeneti fájlt."""
    szoveg = Path(utvonal).read_text(encoding="utf-8-sig", errors="replace")
    return beolvas_szoveg(szoveg)


def beolvas_szoveg(szoveg: str) -> Bemenet:
    """A bemeneti fájl szövegét térképpé és programsorokká alakítja."""
    sorok = szoveg.splitlines()
    sorszam, oszlopszam = (int(resz) for resz in sorok[0].split())
    terkep_sorok = sorok[1:1 + sorszam]
    program_sorok = [sor.rstrip() for sor in sorok[1 + sorszam:]]
    program_sorok = [sor for sor in program_sorok if sor.strip()]
    vilag = vilag_letrehoz(terkep_sorok, oszlopszam)
    return Bemenet(vilag, program_sorok)


def vilag_letrehoz(terkep_sorok: list[str], oszlopszam: int) -> Vilag:
    """A térkép sorait mezőkké alakítja, és megkeresi a robotot."""
    mezok: list[list[Mezo]] = []
    robot = Robot(0, 0, Irany.KELET)
    for sor_index, sor in enumerate(terkep_sorok):
        jelek = sor.ljust(oszlopszam, ".")[:oszlopszam]
        mezo_sor = []
        for oszlop_index, jel in enumerate(jelek):
            irany = Irany.jelbol(jel)
            if irany is not None:
                robot = Robot(sor_index, oszlop_index, irany)
                mezo_sor.append(Mezo.URES)
            else:
                mezo_sor.append(MEZO_JELEK.get(jel, Mezo.URES))
        mezok.append(mezo_sor)
    return Vilag(Terkep(mezok), robot)


def bemenet_szoveg(vilag: Vilag, program_sorok: list[str]) -> str:
    """A térképet és a programot a bemeneti fájl formátumában adja vissza."""
    elso_sor = f"{vilag.terkep.sorok} {vilag.terkep.oszlopok}"
    sorok = [elso_sor, *vilag.terkep_sorai(), *program_sorok]
    return "\n".join(sorok) + "\n"
