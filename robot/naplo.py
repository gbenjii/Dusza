"""Naplósorok összeállítása, és a napló írása – igény szerint élőben, soronként a fájlba.

Élő írásnál minden sor azonnal a fájlba kerül (flush), így a naplófájl
nyomkövetés közben is megnyitható, és mindig az addigi lépéseket mutatja.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from hibak import LIMIT_TULLEPES, HibaKod

FUTAS_VEGE = "EOR"


def ertek_szoveg(ertek: int | bool) -> str:
    """Egész vagy logikai érték naplóbeli / konzolos alakja."""
    if type(ertek) is bool:
        return "true" if ertek else "false"
    return str(ertek)


@dataclass
class NaploSor:
    """Egy végrehajtott forrássor naplóbejegyzése."""

    sorszam: int
    reszek: list[str] = field(default_factory=list)
    hiba: HibaKod | None = None

    def hozzaad(self, resz: str) -> None:
        self.reszek.append(resz)

    def szoveg(self) -> str:
        elemek = [str(self.sorszam), *self.reszek]
        if self.hiba is not None:
            elemek.append(self.hiba.value)
        return " ".join(elemek)


class Naplo:
    """A napló sorai a végrehajtás sorrendjében; `elo_fajl` esetén élőben is ír."""

    def __init__(self, elo_fajl: str | Path | None = None) -> None:
        self.sorok: list[str] = []
        self._fajl: TextIO | None = None
        if elo_fajl is not None:
            self._fajl = open(elo_fajl, "w", encoding="utf-8", newline="\n")

    def _ir(self, sor: str) -> None:
        self.sorok.append(sor)
        if self._fajl is not None:
            self._fajl.write(sor + "\n")
            self._fajl.flush()

    def hozzaad(self, sor: NaploSor) -> None:
        self._ir(sor.szoveg())

    def lezar_eor(self) -> None:
        self._ir(FUTAS_VEGE)
        self.bezar()

    def lezar_limit(self) -> None:
        self._ir(LIMIT_TULLEPES)
        self.bezar()

    def bezar(self) -> None:
        """Lezárja az élő fájlt (megszakított futásnál is)."""
        if self._fajl is not None:
            self._fajl.close()
            self._fajl = None

    def szoveg(self) -> str:
        return "".join(sor + "\n" for sor in self.sorok)

    def fajlba_ir(self, utvonal: str | Path) -> None:
        Path(utvonal).write_text(self.szoveg(), encoding="utf-8", newline="\n")
