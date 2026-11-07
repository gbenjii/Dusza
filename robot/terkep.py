"""A robot világa: térkép, robot, irányok, felfedezett mezők, szenzor és statisztika.

A `Vilag` osztály valósítja meg a Robot API műveleteit (lépés, fordulás,
bányászás, isThere), valamint a térképszerkesztő egyszerű műveleteit.
A paraméterek típusát a futtató ellenőrzi, nem ez a modul.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum

from hibak import FutasiHiba, HibaKod

MIN_MERET = 1
MAX_MERET = 15


class Mezo(Enum):
    """Egy térképmező tartalma; az érték az isThere paraméterének felel meg."""

    URES = 0
    FAL = 1
    ARANY = 2


MEZO_JELEK: dict[str, Mezo] = {".": Mezo.URES, "#": Mezo.FAL, "@": Mezo.ARANY}
JEL_MEZOBOL: dict[Mezo, str] = {mezo: jel for jel, mezo in MEZO_JELEK.items()}
MEZO_NEVEK: dict[Mezo, str] = {Mezo.URES: "üres kamra", Mezo.FAL: "fal", Mezo.ARANY: "aranyrög"}


class Irany(Enum):
    """Égtájak: (sor-eltolás, oszlop-eltolás, jel, szög fokban).

    A felsorolás sorrendje az óramutatóval ellentétes (balra fordulás) sorrend.
    """

    KELET = (0, 1, ">", 0)
    ESZAK = (-1, 0, "^", 90)
    NYUGAT = (0, -1, "<", 180)
    DEL = (1, 0, "v", 270)

    @property
    def dsor(self) -> int:
        return self.value[0]

    @property
    def doszlop(self) -> int:
        return self.value[1]

    @property
    def jel(self) -> str:
        return self.value[2]

    @property
    def szog(self) -> int:
        return self.value[3]

    @property
    def nev(self) -> str:
        return IRANY_NEVEK[self]

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


IRANY_NEVEK: dict[Irany, str] = {
    Irany.KELET: "kelet", Irany.ESZAK: "észak", Irany.NYUGAT: "nyugat", Irany.DEL: "dél",
}


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

    def arany_db(self) -> int:
        """Hány aranyrög van még a térképen."""
        return sum(sor.count(Mezo.ARANY) for sor in self.mezok)


class Vilag:
    """Térkép + robot + felfedezett mezők + kibányászott arany + statisztika."""

    def __init__(self, terkep: Terkep, robot: Robot) -> None:
        self.terkep = terkep
        self.robot = robot
        kezdo = (robot.sor, robot.oszlop)
        self.felfedezett: set[tuple[int, int]] = {kezdo}
        self.kibanyaszott: set[tuple[int, int]] = set()
        self.nyomvonal: list[tuple[int, int]] = [kezdo]
        self.utvonal: list[tuple[int, int]] = []
        self.arany_db = 0
        self.lepesszam = 0
        self.fordulasszam = 0

    def masolat(self) -> Vilag:
        """Független másolat (a futások ebből indulnak)."""
        return copy.deepcopy(self)

    # ---------- Érzékelés ----------

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

    def osszes_arany(self) -> int:
        """A kiinduló térkép összes aranya (kibányászott + még meglévő)."""
        return self.arany_db + self.terkep.arany_db()

    # ---------- Robot API ----------

    def lep(self, lepesszam: int) -> None:
        """Mezőnként előre lép; falnál megáll és E_BEDROCK_HIT hibát dob.

        Az érintett mezők az `utvonal` listába kerülnek (az animációhoz).
        """
        self.utvonal = []
        for _ in range(lepesszam):
            sor, oszlop = self.elotte()
            if self.terkep.mezo(sor, oszlop) is Mezo.FAL:
                raise FutasiHiba(HibaKod.E_BEDROCK_HIT)
            self.robot.sor = sor
            self.robot.oszlop = oszlop
            self.felfedezett.add((sor, oszlop))
            self.utvonal.append((sor, oszlop))
            self.nyomvonal.append((sor, oszlop))
            self.lepesszam += 1

    def fordul(self, negyedfordulatok: int) -> None:
        """Balra fordul a megadott számú negyedfordulattal.

        A statisztikában csak a valódi irányváltás számít (a turn by 0 / 4 nem fordulás).
        """
        regi_irany = self.robot.irany
        self.robot.irany = regi_irany.balra(negyedfordulatok)
        if self.robot.irany is not regi_irany:
            self.fordulasszam += 1

    def banyasz(self) -> None:
        """Kibányássza az aranyat a robot mezőjén, különben E_NO_GOLD."""
        sor, oszlop = self.robot.sor, self.robot.oszlop
        if self.terkep.mezo(sor, oszlop) is not Mezo.ARANY:
            raise FutasiHiba(HibaKod.E_NO_GOLD)
        self.terkep.beallit(sor, oszlop, Mezo.URES)
        self.kibanyaszott.add((sor, oszlop))
        self.arany_db += 1

    # ---------- Térképszerkesztés ----------

    def mezo_szerkeszt(self, sor: int, oszlop: int, mezo: Mezo) -> bool:
        """Mező átírása; a robot mezője csak üres lehet. Sikeres-e."""
        if not self.terkep.bent_van(sor, oszlop):
            return False
        if (sor, oszlop) == (self.robot.sor, self.robot.oszlop) and mezo is not Mezo.URES:
            return False
        self.terkep.beallit(sor, oszlop, mezo)
        return True

    def robot_athelyez(self, sor: int, oszlop: int) -> bool:
        """A robot áthelyezése; ha már ott áll, balra fordul. Sikeres-e."""
        if not self.terkep.bent_van(sor, oszlop):
            return False
        if (sor, oszlop) == (self.robot.sor, self.robot.oszlop):
            self.robot.irany = self.robot.irany.balra(1)
            return True
        self.terkep.beallit(sor, oszlop, Mezo.URES)
        self.robot = Robot(sor, oszlop, self.robot.irany)
        self.felfedezett = {(sor, oszlop)}
        self.nyomvonal = [(sor, oszlop)]
        return True

    def atmeretezve(self, sorok: int, oszlopok: int) -> Vilag:
        """Új, átméretezett világ (levágás vagy üres mezőkkel bővítés)."""
        sorok = max(MIN_MERET, min(MAX_MERET, sorok))
        oszlopok = max(MIN_MERET, min(MAX_MERET, oszlopok))
        mezok = [[self.terkep.mezo(s, o) if self.terkep.bent_van(s, o) else Mezo.URES
                  for o in range(oszlopok)] for s in range(sorok)]
        robot = Robot(min(self.robot.sor, sorok - 1), min(self.robot.oszlop, oszlopok - 1), self.robot.irany)
        mezok[robot.sor][robot.oszlop] = Mezo.URES
        return Vilag(Terkep(mezok), robot)

    def terkep_sorai(self) -> list[str]:
        """A térkép szöveges alakja (a bemeneti fájl formátumában)."""
        sorok = []
        for sor_index, sor in enumerate(self.terkep.mezok):
            jelek = [JEL_MEZOBOL[mezo] for mezo in sor]
            if sor_index == self.robot.sor:
                jelek[self.robot.oszlop] = self.robot.irany.jel
            sorok.append("".join(jelek))
        return sorok
