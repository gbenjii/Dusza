"""Utasításfa → forrásszöveg, valamint a sorszámok újraosztása szerkesztés után."""

from __future__ import annotations

from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertekadas, ErtekKif, Fordulas, IsThereKif,
    Kifejezes, Kiiras, Lepes, MuveletKif, NotKif, Utasitas,
)

BEHUZAS = "  "


def kifejezes_szoveg(kif: Kifejezes) -> str:
    """A set jobb oldalának szöveges alakja."""
    if isinstance(kif, ErtekKif):
        return kif.ertek.szoveg
    if isinstance(kif, IsThereKif):
        return f"isThere {kif.ertek.szoveg}"
    if isinstance(kif, NotKif):
        return f"not {kif.ertek.szoveg}"
    return f"{kif.bal.szoveg} {kif.muvelet.value} {kif.jobb.szoveg}"


def fej_szoveg(utasitas: Utasitas) -> str:
    """Az utasítás saját sorának szövege (behúzás nélkül)."""
    if isinstance(utasitas, Lepes):
        return f"step forward {utasitas.ertek.szoveg}"
    if isinstance(utasitas, Fordulas):
        return f"turn by {utasitas.ertek.szoveg}"
    if isinstance(utasitas, Banyaszas):
        return "mine here"
    if isinstance(utasitas, Kiiras):
        return f"print {utasitas.ertek.szoveg}"
    if isinstance(utasitas, Ertekadas):
        return f"set {utasitas.nev} to {kifejezes_szoveg(utasitas.kif)}"
    if isinstance(utasitas, Elagazas):
        return f"if {utasitas.feltetel.szoveg}"
    return f"while {utasitas.feltetel.szoveg}"


def program_sorai(program: list[Utasitas]) -> list[str]:
    """A teljes program forrássorai, szintenként 2 szóköz behúzással."""
    sorok: list[str] = []
    _blokk_sorai(program, 0, sorok)
    return sorok


def _blokk_sorai(utasitasok: list[Utasitas], szint: int, sorok: list[str]) -> None:
    elotag = BEHUZAS * szint
    for utasitas in utasitasok:
        sorok.append(elotag + fej_szoveg(utasitas))
        if isinstance(utasitas, Ciklus):
            _blokk_sorai(utasitas.torzs, szint + 1, sorok)
        if isinstance(utasitas, Elagazas):
            _blokk_sorai(utasitas.igaz_ag, szint + 1, sorok)
            if utasitas.hamis_ag is not None:
                sorok.append(elotag + "else")
                _blokk_sorai(utasitas.hamis_ag, szint + 1, sorok)


def sorszamoz(program: list[Utasitas]) -> None:
    """Újraosztja a sorszámokat úgy, hogy egyezzenek a `program_sorai` soraival."""
    _sorszamoz_blokk(program, 1)


def _sorszamoz_blokk(utasitasok: list[Utasitas], kovetkezo: int) -> int:
    for utasitas in utasitasok:
        utasitas.sorszam = kovetkezo
        kovetkezo += 1
        if isinstance(utasitas, Ciklus):
            kovetkezo = _sorszamoz_blokk(utasitas.torzs, kovetkezo)
        if isinstance(utasitas, Elagazas):
            kovetkezo = _sorszamoz_blokk(utasitas.igaz_ag, kovetkezo)
            if utasitas.hamis_ag is not None:
                utasitas.else_sorszam = kovetkezo
                kovetkezo = _sorszamoz_blokk(utasitas.hamis_ag, kovetkezo + 1)
    return kovetkezo
