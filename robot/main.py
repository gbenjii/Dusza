"""Belépési pont: parancssori paraméterek, -q (felület nélküli) mód vagy az IDE.

Használat:
    robot.exe BE KI       – az IDE megnyitása a BE fájllal, a napló helye KI
    robot.exe -q BE KI    – futtatás felület nélkül, napló a KI fájlba, majd kilépés
"""

from __future__ import annotations

import sys

from beolvaso import beolvas_fajl
from futtato import Futtato
from nyelv.elemzo import elemez

CSENDES_KAPCSOLO = "-q"
HASZNALAT = (
    "Használat:\n"
    "  robot.exe BE KI       – IDE indítása, BE betöltése, napló: KI\n"
    "  robot.exe -q BE KI    – futtatás felület nélkül, napló: KI"
)


def csendes_futtatas(be_utvonal: str, ki_utvonal: str) -> Futtato:
    """Betölt, végigfuttat, megírja a naplót. A kiírások a konzolra mennek."""
    bemenet = beolvas_fajl(be_utvonal)
    program = elemez(bemenet.program_sorok)
    futtato = Futtato(program, bemenet.vilag, kiiro=print)
    futtato.futtat_vegig()
    futtato.naplo.fajlba_ir(ki_utvonal)
    return futtato


def main(argumentumok: list[str]) -> int:
    """A parancssori paraméterek feldolgozása; a visszatérési érték a kilépési kód."""
    if argumentumok and argumentumok[0] == CSENDES_KAPCSOLO:
        if len(argumentumok) != 3:
            print(HASZNALAT)
            return 2
        csendes_futtatas(argumentumok[1], argumentumok[2])
        return 0
    be_utvonal = argumentumok[0] if len(argumentumok) >= 1 else None
    ki_utvonal = argumentumok[1] if len(argumentumok) >= 2 else None
    from gui.foablak import inditas  # csak itt töltjük be: a -q mód így gyors
    inditas(be_utvonal, ki_utvonal)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
