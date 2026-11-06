"""Azonosítók és V értékek ellenőrzése a szerkesztőhöz, magyar hibaüzenetekkel."""

from __future__ import annotations

from nyelv.tokenizalo import kulcsszo_e
from nyelv.utasitasok import HAMIS, IGAZ

LEGKISEBB_SZAM = 0
LEGNAGYOBB_SZAM = 100


def _betu_e(karakter: str) -> bool:
    return karakter.isascii() and karakter.isalpha()


def _szamjegy_e(karakter: str) -> bool:
    return karakter.isascii() and karakter.isdigit()


def azonosito_hiba(nev: str) -> str | None:
    """None, ha `nev` érvényes azonosító; különben magyar hibaüzenet."""
    if nev == "":
        return "A név nem lehet üres."
    if not _betu_e(nev[0]):
        return f"„{nev}”: az azonosítónak betűvel (a–z, A–Z) kell kezdődnie."
    for karakter in nev:
        if not (_betu_e(karakter) or _szamjegy_e(karakter)):
            return f"„{nev}”: az azonosító csak betűt és számjegyet tartalmazhat."
    if kulcsszo_e(nev):
        return f"„{nev}” kulcsszó, nem lehet azonosító (kis-/nagybetűtől függetlenül)."
    return None


def ertek_hiba(szoveg: str) -> str | None:
    """None, ha `szoveg` érvényes V érték (azonosító, 0..100, true, false)."""
    if szoveg == "":
        return "Az érték nem lehet üres."
    if szoveg in (IGAZ, HAMIS):
        return None
    if all(_szamjegy_e(karakter) for karakter in szoveg):
        if LEGKISEBB_SZAM <= int(szoveg) <= LEGNAGYOBB_SZAM:
            return None
        return f"„{szoveg}”: a szám {LEGKISEBB_SZAM} és {LEGNAGYOBB_SZAM} között lehet."
    return azonosito_hiba(szoveg)


def leptetheto_e(szoveg: str) -> bool:
    """Szám vagy logikai érték: a szerkesztőben −/+ gombbal léptethető."""
    return szoveg in (IGAZ, HAMIS) or (szoveg.isascii() and szoveg.isdigit())


def ertek_leptet(szoveg: str, irany: int) -> str:
    """A −/+ gomb hatása: számnál ±1 (0..100 között), logikainál true ↔ false.

    Változónévnél nincs mit léptetni, ilyenkor a szöveg változatlan.
    """
    if szoveg in (IGAZ, HAMIS):
        return HAMIS if szoveg == IGAZ else IGAZ
    if szoveg.isascii() and szoveg.isdigit():
        uj = min(LEGNAGYOBB_SZAM, max(LEGKISEBB_SZAM, int(szoveg) + irany))
        return str(uj)
    return szoveg
