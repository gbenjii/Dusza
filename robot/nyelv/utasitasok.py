"""A MineScript utasításfa adatszerkezetei (dataclass-ok).

Az utasítások `eq=False`-szal készülnek, hogy a szerkesztő azonosság alapján
találja meg őket (két egyforma `mine here` is külön blokk).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ErtekFajta(Enum):
    """Egy V token fajtája."""

    AZONOSITO = "azonosító"
    SZAM = "szám"
    LOGIKAI = "logikai"


IGAZ = "true"
HAMIS = "false"


@dataclass
class Ertek:
    """Egyetlen V token: azonosító, szám (0..100) vagy true/false."""

    szoveg: str

    @property
    def fajta(self) -> ErtekFajta:
        if self.szoveg in (IGAZ, HAMIS):
            return ErtekFajta.LOGIKAI
        if self.szoveg.isascii() and self.szoveg.isdigit():
            return ErtekFajta.SZAM
        return ErtekFajta.AZONOSITO


class Muvelet(Enum):
    """Kétoperandusú műveletek; az érték a forráskódbeli jel."""

    PLUSZ = "+"
    MINUSZ = "-"
    SZOR = "*"
    EGYENLO = "="
    NEM_EGYENLO = "<>"
    KISEBB = "<"
    KISEBB_EGYENLO = "<="
    NAGYOBB = ">"
    NAGYOBB_EGYENLO = ">="
    ES = "and"
    VAGY = "or"


EGESZ_OPERANDUSU = (
    Muvelet.PLUSZ, Muvelet.MINUSZ, Muvelet.SZOR,
    Muvelet.KISEBB, Muvelet.KISEBB_EGYENLO, Muvelet.NAGYOBB, Muvelet.NAGYOBB_EGYENLO,
)
LOGIKAI_OPERANDUSU = (Muvelet.ES, Muvelet.VAGY)
EGYENLOSEGI = (Muvelet.EGYENLO, Muvelet.NEM_EGYENLO)


# ---- Kifejezések (a set jobb oldala) ----

@dataclass
class ErtekKif:
    """set x to V"""

    ertek: Ertek


@dataclass
class IsThereKif:
    """set x to isThere V"""

    ertek: Ertek


@dataclass
class NotKif:
    """set x to not V"""

    ertek: Ertek


@dataclass
class MuveletKif:
    """set x to V op V"""

    bal: Ertek
    muvelet: Muvelet
    jobb: Ertek


Kifejezes = ErtekKif | IsThereKif | NotKif | MuveletKif


# ---- Utasítások ----

@dataclass(eq=False)
class Lepes:
    """step forward V"""

    ertek: Ertek
    sorszam: int = 0


@dataclass(eq=False)
class Fordulas:
    """turn by V"""

    ertek: Ertek
    sorszam: int = 0


@dataclass(eq=False)
class Banyaszas:
    """mine here"""

    sorszam: int = 0


@dataclass(eq=False)
class Kiiras:
    """print V"""

    ertek: Ertek
    sorszam: int = 0


@dataclass(eq=False)
class Ertekadas:
    """set NEV to KIF"""

    nev: str
    kif: Kifejezes
    sorszam: int = 0


@dataclass(eq=False)
class Elagazas:
    """if V / blokk / [else / blokk]; hamis_ag None, ha nincs else."""

    feltetel: Ertek
    igaz_ag: list[Utasitas] = field(default_factory=list)
    hamis_ag: list[Utasitas] | None = None
    sorszam: int = 0
    else_sorszam: int = 0


@dataclass(eq=False)
class Ciklus:
    """while V / blokk"""

    feltetel: Ertek
    torzs: list[Utasitas] = field(default_factory=list)
    sorszam: int = 0


Utasitas = Lepes | Fordulas | Banyaszas | Kiiras | Ertekadas | Elagazas | Ciklus


def vezerlo_e(utasitas: Utasitas) -> bool:
    """Vezérlőblokk-e (if / if-else / while)."""
    return isinstance(utasitas, (Elagazas, Ciklus))
