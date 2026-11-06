"""Az utasításfa szerkesztése (beszúrás, törlés, mélységkorlát) – GUI nélkül.

A blokkszerkesztő ezeket a függvényeket hívja; a hibákat magyar üzenetű
`SzerkesztesiHiba` jelzi.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertek, Ertekadas, ErtekKif, Fordulas, Kiiras,
    Lepes, Utasitas, vezerlo_e,
)

MAX_VEZERLO_MELYSEG = 3
"""Legfeljebb ennyi vezérlőblokk ágyazható egymásba."""


class SzerkesztesiHiba(Exception):
    """Nem végrehajtható szerkesztési művelet (magyar üzenettel)."""


class BeszurasHelye(Enum):
    ELE = "elé"
    MOGE = "mögé"
    TORZSBE = "törzsbe"
    ELSE_AGBA = "else-ágba"


class BlokkFajta(Enum):
    """A menüből választható blokkok."""

    LEPES = "step forward"
    FORDULAS = "turn by"
    BANYASZAS = "mine here"
    KIIRAS = "print"
    ERTEKADAS = "set"
    HA = "if"
    HA_KULONBEN = "if-else"
    AMIG = "while"


VEZERLO_FAJTAK = (BlokkFajta.HA, BlokkFajta.HA_KULONBEN, BlokkFajta.AMIG)


@dataclass
class Pozicio:
    """Egy utasítás helye: melyik listában, hányadik, és hány vezérlőblokk van körülötte."""

    lista: list[Utasitas]
    index: int
    melyseg: int


def uj_blokk(fajta: BlokkFajta) -> Utasitas:
    """Alapértékekkel kitöltött új blokk."""
    if fajta is BlokkFajta.LEPES:
        return Lepes(Ertek("1"))
    if fajta is BlokkFajta.FORDULAS:
        return Fordulas(Ertek("1"))
    if fajta is BlokkFajta.BANYASZAS:
        return Banyaszas()
    if fajta is BlokkFajta.KIIRAS:
        return Kiiras(Ertek("0"))
    if fajta is BlokkFajta.ERTEKADAS:
        return Ertekadas("x", ErtekKif(Ertek("0")))
    if fajta is BlokkFajta.HA:
        return Elagazas(Ertek("true"))
    if fajta is BlokkFajta.HA_KULONBEN:
        return Elagazas(Ertek("true"), [], [])
    return Ciklus(Ertek("false"))


def torzsek(utasitas: Utasitas) -> list[list[Utasitas]]:
    """Egy vezérlőblokk törzsei (egyszerű utasításnál üres lista)."""
    if isinstance(utasitas, Ciklus):
        return [utasitas.torzs]
    if isinstance(utasitas, Elagazas):
        if utasitas.hamis_ag is None:
            return [utasitas.igaz_ag]
        return [utasitas.igaz_ag, utasitas.hamis_ag]
    return []


def pozicio_keres(lista: list[Utasitas], cel: Utasitas, melyseg: int = 0) -> Pozicio | None:
    """Megkeresi `cel` helyét a fában (azonosság alapján)."""
    for index, utasitas in enumerate(lista):
        if utasitas is cel:
            return Pozicio(lista, index, melyseg)
        for torzs in torzsek(utasitas):
            talalat = pozicio_keres(torzs, cel, melyseg + 1)
            if talalat is not None:
                return talalat
    return None


def _cel_pozicio(program: list[Utasitas], cel: Utasitas | None,
                 hely: BeszurasHelye) -> Pozicio:
    """Hová kerül az új blokk: lista, index és a lista vezérlő-mélysége."""
    if cel is None:
        if hely is BeszurasHelye.ELE:
            return Pozicio(program, 0, 0)
        if hely is BeszurasHelye.MOGE:
            return Pozicio(program, len(program), 0)
        raise SzerkesztesiHiba("Előbb jelölj ki egy vezérlőblokkot (if, if-else, while).")
    poz = pozicio_keres(program, cel)
    if poz is None:
        raise SzerkesztesiHiba("A kijelölt blokk nem található a programban.")
    if hely is BeszurasHelye.ELE:
        return poz
    if hely is BeszurasHelye.MOGE:
        return Pozicio(poz.lista, poz.index + 1, poz.melyseg)
    return _torzs_pozicio(cel, hely, poz.melyseg)


def _torzs_pozicio(cel: Utasitas, hely: BeszurasHelye, melyseg: int) -> Pozicio:
    if hely is BeszurasHelye.ELSE_AGBA:
        if not isinstance(cel, Elagazas) or cel.hamis_ag is None:
            raise SzerkesztesiHiba("Else-ágba csak if-else blokknál lehet beszúrni.")
        return Pozicio(cel.hamis_ag, len(cel.hamis_ag), melyseg + 1)
    if isinstance(cel, Ciklus):
        return Pozicio(cel.torzs, len(cel.torzs), melyseg + 1)
    if isinstance(cel, Elagazas):
        return Pozicio(cel.igaz_ag, len(cel.igaz_ag), melyseg + 1)
    raise SzerkesztesiHiba("Törzsbe csak vezérlőblokkba (if, if-else, while) lehet beszúrni.")


def beszuras_hiba(program: list[Utasitas], cel: Utasitas | None,
                  hely: BeszurasHelye, fajta: BlokkFajta) -> str | None:
    """None, ha a beszúrás megengedett; különben a magyar ok."""
    try:
        poz = _cel_pozicio(program, cel, hely)
    except SzerkesztesiHiba as hiba:
        return str(hiba)
    if fajta in VEZERLO_FAJTAK and poz.melyseg >= MAX_VEZERLO_MELYSEG:
        return f"Legfeljebb {MAX_VEZERLO_MELYSEG} vezérlőblokk ágyazható egymásba."
    return None


def beszur(program: list[Utasitas], cel: Utasitas | None,
           hely: BeszurasHelye, fajta: BlokkFajta) -> Utasitas:
    """Új blokkot szúr be; visszaadja az új blokkot."""
    hiba = beszuras_hiba(program, cel, hely, fajta)
    if hiba is not None:
        raise SzerkesztesiHiba(hiba)
    poz = _cel_pozicio(program, cel, hely)
    uj = uj_blokk(fajta)
    poz.lista.insert(poz.index, uj)
    return uj


def torol(program: list[Utasitas], cel: Utasitas) -> None:
    """Törli a blokkot a teljes tartalmával együtt."""
    poz = pozicio_keres(program, cel)
    if poz is None:
        raise SzerkesztesiHiba("A kijelölt blokk nem található a programban.")
    del poz.lista[poz.index]


def vezerlo_magassag(utasitas: Utasitas) -> int:
    """Hány vezérlőszint van a blokkban önmagával együtt (egyszerű utasításnál 0)."""
    if not vezerlo_e(utasitas):
        return 0
    return 1 + max((vezerlo_magassag(belso) for torzs in torzsek(utasitas) for belso in torzs), default=0)


def lista_melyseg(program: list[Utasitas], lista: list[Utasitas], melyseg: int = 0) -> int | None:
    """Hány vezérlőblokk veszi körül a `lista` törzset (None, ha nincs a fában)."""
    if lista is program:
        return melyseg
    for utasitas in program:
        for torzs in torzsek(utasitas):
            if torzs is lista:
                return melyseg + 1
            talalat = lista_melyseg(torzs, lista, melyseg + 1)
            if talalat is not None:
                return talalat
    return None


def _tartalmazza(utasitas: Utasitas, lista: list[Utasitas]) -> bool:
    """Igaz, ha `lista` az `utasitas` valamelyik (akár mélyebb) törzse."""
    for torzs in torzsek(utasitas):
        if torzs is lista or any(_tartalmazza(belso, lista) for belso in torzs):
            return True
    return False


def athelyezes_hiba(program: list[Utasitas], mozgatott: Utasitas,
                    cel_lista: list[Utasitas]) -> str | None:
    """None, ha a blokk áthúzható a `cel_lista` törzsbe; különben a magyar ok."""
    if _tartalmazza(mozgatott, cel_lista):
        return "Egy blokk nem húzható a saját törzsébe."
    melyseg = lista_melyseg(program, cel_lista)
    if melyseg is None:
        return "A célhely nem található a programban."
    if melyseg + vezerlo_magassag(mozgatott) > MAX_VEZERLO_MELYSEG:
        return f"Legfeljebb {MAX_VEZERLO_MELYSEG} vezérlőblokk ágyazható egymásba."
    return None


def athelyez(program: list[Utasitas], mozgatott: Utasitas,
             cel_lista: list[Utasitas], cel_index: int) -> None:
    """Áthúzás: a blokk (tartalmával együtt) a `cel_lista` `cel_index` helyére kerül."""
    hiba = athelyezes_hiba(program, mozgatott, cel_lista)
    if hiba is not None:
        raise SzerkesztesiHiba(hiba)
    poz = pozicio_keres(program, mozgatott)
    if poz is None:
        raise SzerkesztesiHiba("A mozgatott blokk nem található a programban.")
    if poz.lista is cel_lista and poz.index < cel_index:
        cel_index -= 1
    del poz.lista[poz.index]
    cel_lista.insert(cel_index, mozgatott)


def beszuras_ide_hiba(program: list[Utasitas], cel_lista: list[Utasitas],
                      fajta: BlokkFajta) -> str | None:
    """None, ha új `fajta` blokk tehető a `cel_lista` törzsbe."""
    melyseg = lista_melyseg(program, cel_lista)
    if melyseg is None:
        return "A célhely nem található a programban."
    if fajta in VEZERLO_FAJTAK and melyseg >= MAX_VEZERLO_MELYSEG:
        return f"Legfeljebb {MAX_VEZERLO_MELYSEG} vezérlőblokk ágyazható egymásba."
    return None


def beszur_ide(program: list[Utasitas], cel_lista: list[Utasitas], cel_index: int,
               fajta: BlokkFajta) -> Utasitas:
    """Új blokk a megadott törzs megadott helyére (a palettáról húzáshoz)."""
    hiba = beszuras_ide_hiba(program, cel_lista, fajta)
    if hiba is not None:
        raise SzerkesztesiHiba(hiba)
    uj = uj_blokk(fajta)
    cel_lista.insert(cel_index, uj)
    return uj


def else_ag_valt(elagazas: Elagazas) -> None:
    """if ↔ if-else: else-ág hozzáadása, vagy (tartalmával együtt) eltávolítása."""
    elagazas.hamis_ag = [] if elagazas.hamis_ag is None else None


def vezerlo_melyseg(program: list[Utasitas], cel: Utasitas) -> int:
    """Hány vezérlőblokk tartalmazza a blokkot (0 = legfelső szint)."""
    poz = pozicio_keres(program, cel)
    return poz.melyseg if poz is not None else 0


__all__ = [
    "MAX_VEZERLO_MELYSEG", "SzerkesztesiHiba", "BeszurasHelye", "BlokkFajta",
    "Pozicio", "uj_blokk", "torzsek", "pozicio_keres", "beszuras_hiba", "beszur",
    "torol", "vezerlo_melyseg", "vezerlo_e", "vezerlo_magassag", "lista_melyseg",
    "athelyezes_hiba", "athelyez", "beszuras_ide_hiba", "beszur_ide", "else_ag_valt",
]
