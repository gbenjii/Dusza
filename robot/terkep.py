"""A robot világa: térkép, robot, irányok, felfedezett mezők és a szenzor.

A `Vilag` osztály a Robot API műveleteit valósítja meg (lépés, fordulás,
bányászás, isThere). A paraméterek típusát a futtató ellenőrzi.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum

from hibak import FutasiHiba, HibaKod


class Mezo(Enum):
    """Egy térképmező tartalma; az érték az isThere paraméterének felel meg."""

    URES = 0
    FAL = 1
    ARANY = 2


MEZO_JELEK: dict[str, Mezo] = {".": Mezo.URES, "#": Mezo.FAL, "@": Mezo.ARANY}
JEL_MEZOBOL: dict[Mezo, str] = {mezo: jel for jel, mezo in MEZO_JELEK.items()}


class Irany(Enum):
    """Égtájak: (sor-eltolás, oszlop-eltolás, jel).

    A felsorolás sorrendje az óramutatóval ellentétes (balra fordulás) sorrend.
    """

    KELET = (0, 1, ">")
    ESZAK = (-1, 0, "^")
    NYUGAT = (0, -1, "<")
    DEL = (1, 0, "v")

    @property
    def dsor(self) -> int:
        return self.value[0]

    @property
    def doszlop(self) -> int:
        return self.value[1]

    @property
    def jel(self) -> str:
        return self.value[2]

    def balra(self, negyedfordulatok: int) -> Irany:
        """Az irány `negyedfordulatok`-szor balra fordítva."""
        sorrend = list(Irany)
        index = (sorrend.index(self) + negyedfordulatok) % len(sorrend)
        return sorrend[index]

    @staticmethod
    def jelbol(jel: str) -> Irany | None:
        """A '>', '<', '^', 'v' jelhez tartozó irány, egyébként None."""
        for irany in Irany:
            if irany.jel == jel:
                return irany
        return None


@dataclass
class Robot:
    """A robot helye és iránya."""

    sor: int
    oszlop: int
    irany: Irany


@dataclass
class Terkep:
    """A térkép mezői soronként."""

    mezok: list[list[Mezo]]

    @property
    def sorok(self) -> int:
        return len(self.mezok)

    @property
    def oszlopok(self) -> int:
        return len(self.mezok[0]) if self.mezok else 0

    def bent_van(self, sor: int, oszlop: int) -> bool:
        return 0 <= sor < self.sorok and 0 <= oszlop < self.oszlopok

    def mezo(self, sor: int, oszlop: int) -> Mezo:
        """A mező tartalma; a térképen kívüli mező falnak számít."""
        if not self.bent_van(sor, oszlop):
            return Mezo.FAL
        return self.mezok[sor][oszlop]

    def beallit(self, sor: int, oszlop: int, mezo: Mezo) -> None:
        self.mezok[sor][oszlop] = mezo


class Vilag:
    """Térkép + robot + felfedezett mezők + kibányászott arany."""

    def __init__(self, terkep: Terkep, robot: Robot) -> None:
        self.terkep = terkep
        self.robot = robot
        self.felfedezett: set[tuple[int, int]] = {(robot.sor, robot.oszlop)}
        self.arany_db = 0

    def masolat(self) -> Vilag:
        """Független másolat (a futások ebből indulnak)."""
        return copy.deepcopy(self)

    def elotte(self) -> tuple[int, int]:
        """A robot előtti mező koordinátái (lehet a térképen kívül is)."""
        irany = self.robot.irany
        return self.robot.sor + irany.dsor, self.robot.oszlop + irany.doszlop

    def szenzor(self) -> Mezo:
        """Mit látna most az isThere (nem teszi felfedezetté a mezőt)."""
        return self.terkep.mezo(*self.elotte())

    def megnez(self, mezo_kod: int) -> bool:
        """isThere: igaz, ha az előtte lévő mező kódja `mezo_kod`."""
        sor, oszlop = self.elotte()
        if self.terkep.bent_van(sor, oszlop):
            self.felfedezett.add((sor, oszlop))
        return self.terkep.mezo(sor, oszlop).value == mezo_kod

    def lep(self, lepesszam: int) -> None:
        """Mezőnként előre lép; falnál megáll és E_BEDROCK_HIT hibát dob."""
        for _ in range(lepesszam):
            sor, oszlop = self.elotte()
            if self.terkep.mezo(sor, oszlop) is Mezo.FAL:
                raise FutasiHiba(HibaKod.E_BEDROCK_HIT)
            self.robot.sor = sor
            self.robot.oszlop = oszlop
            self.felfedezett.add((sor, oszlop))

    def fordul(self, negyedfordulatok: int) -> None:
        """Balra fordul a megadott számú negyedfordulattal."""
        self.robot.irany = self.robot.irany.balra(negyedfordulatok)

    def banyasz(self) -> None:
        """Kibányássza az aranyat a robot mezőjén, különben E_NO_GOLD."""
        sor, oszlop = self.robot.sor, self.robot.oszlop
        if self.terkep.mezo(sor, oszlop) is not Mezo.ARANY:
            raise FutasiHiba(HibaKod.E_NO_GOLD)
        self.terkep.beallit(sor, oszlop, Mezo.URES)
        self.arany_db += 1

    def terkep_sorai(self) -> list[str]:
        """A térkép szöveges alakja (a bemeneti fájl formátumában)."""
        sorok = []
        for sor_index, sor in enumerate(self.terkep.mezok):
            jelek = [JEL_MEZOBOL[mezo] for mezo in sor]
            if sor_index == self.robot.sor:
                jelek[self.robot.oszlop] = self.robot.irany.jel
            sorok.append("".join(jelek))
        return sorok
