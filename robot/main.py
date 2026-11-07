"""Belépési pont: parancssori paraméterek, -q (csendes) mód, tömeges mód vagy az IDE.

Használat:
    robot.exe BE KI       – az IDE megnyitása a BE fájllal, a napló helye KI
    robot.exe -q BE KI    – futtatás felület nélkül, napló a KI fájlba, majd kilépés
    robot.exe -m MAPPA    – a mappa minden input_NNN.txt fájlját lefuttatja egyetlen
                            folyamatban (output_NNN.txt), így 200+ fájl is pár másodperc
"""

from __future__ import annotations

import sys
from pathlib import Path

from beolvaso import beolvas_fajl
from futtato import Futtato
from nyelv.elemzo import elemez

CSENDES_KAPCSOLO = "-q"
MAPPA_KAPCSOLO = "-m"
BEMENET_ELOTAG = "input_"
KIMENET_ELOTAG = "output_"
HASZNALAT = (
    "Használat:\n"
    "  robot.exe BE KI       – IDE indítása, BE betöltése, napló: KI\n"
    "  robot.exe -q BE KI    – futtatás felület nélkül, napló: KI\n"
    "  robot.exe -m MAPPA    – minden input_NNN.txt → output_NNN.txt egy menetben"
)


def _konzol_utf8() -> None:
    """Az ékezetes üzenetek ne okozzanak hibát régi kódlapú konzolon sem."""
    for folyam in (sys.stdout, sys.stderr):
        try:
            folyam.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def csendes_futtatas(be_utvonal: str | Path, ki_utvonal: str | Path,
                     kiiras: bool = True) -> Futtato:
    """Betölt, végigfuttat, megírja a naplót. A kiírások (print) a konzolra mennek."""
    bemenet = beolvas_fajl(be_utvonal)
    program = elemez(bemenet.program_sorok)
    futtato = Futtato(program, bemenet.vilag, kiiro=print if kiiras else None)
    futtato.futtat_vegig()
    futtato.naplo.fajlba_ir(ki_utvonal)
    return futtato


def kimenet_neve(bemenet: Path) -> Path:
    """input_001.txt → output_001.txt (ugyanabban a mappában)."""
    return bemenet.with_name(KIMENET_ELOTAG + bemenet.name[len(BEMENET_ELOTAG):])


def mappa_futtatas(mappa: str | Path) -> tuple[int, int]:
    """A mappa összes input_*.txt fájlja; visszaadja: (sikeres, hibás) darabszám."""
    sikeres = hibas = 0
    for bemenet in sorted(Path(mappa).glob(BEMENET_ELOTAG + "*.txt")):
        try:
            csendes_futtatas(bemenet, kimenet_neve(bemenet), kiiras=False)
            sikeres += 1
        except Exception as hiba:  # egy rossz fájl ne állítsa meg a többit
            print(f"HIBA: {bemenet.name}: {hiba}", file=sys.stderr)
            hibas += 1
    return sikeres, hibas


def main(argumentumok: list[str]) -> int:
    """A parancssori paraméterek feldolgozása; a visszatérési érték a kilépési kód."""
    _konzol_utf8()
    if argumentumok and argumentumok[0] == CSENDES_KAPCSOLO:
        if len(argumentumok) != 3:
            print(HASZNALAT)
            return 2
        csendes_futtatas(argumentumok[1], argumentumok[2])
        return 0
    if argumentumok and argumentumok[0] == MAPPA_KAPCSOLO:
        if len(argumentumok) != 2:
            print(HASZNALAT)
            return 2
        sikeres, hibas = mappa_futtatas(argumentumok[1])
        print(f"Kész: {sikeres} fájl lefuttatva, {hibas} hibás.")
        return 0 if hibas == 0 else 1
    be_utvonal = argumentumok[0] if len(argumentumok) >= 1 else None
    ki_utvonal = argumentumok[1] if len(argumentumok) >= 2 else None
    # Linuxon Xft nélküli Tk-val (pl. a uv saját Pythonja) a szövegek csúnyák lennének:
    # ilyenkor a felület a gép Xft-s Pythonjával indul újra (lásd gui/xft_inditas.py).
    from gui.xft_inditas import ujrainditas_xft_pythonnal
    ujrainditas_xft_pythonnal(str(Path(__file__).resolve()), argumentumok)
    from gui.foablak import inditas  # csak itt töltjük be: a -q mód így gyors
    inditas(be_utvonal, ki_utvonal)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
