"""Közös segédfüggvények a tesztekhez."""

from __future__ import annotations

from beolvaso import beolvas_szoveg
from futtato import Futtato
from nyelv.elemzo import elemez

ALAP_TERKEP = "1 3\n>..\n"
"""Kis térkép: a robot keletre néz, előtte két üres mező."""


def futtat(program: str, terkep: str = ALAP_TERKEP) -> Futtato:
    """A térkép + program szöveget végigfuttatja; a futtatót adja vissza."""
    bemenet = beolvas_szoveg(terkep + program)
    futtato = Futtato(elemez(bemenet.program_sorok), bemenet.vilag)
    futtato.futtat_vegig()
    return futtato


def naplo(program: str, terkep: str = ALAP_TERKEP) -> list[str]:
    """Csak a napló sorai."""
    return futtat(program, terkep).naplo.sorok


def sorok(*programsorok: str) -> str:
    """Programsorokból fájlszöveg (soronként egy utasítás)."""
    return "".join(sor + "\n" for sor in programsorok)
