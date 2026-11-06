"""Naplósorok összeállítása és a napló fájlba írása."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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
    """A teljes napló sorai a végrehajtás sorrendjében."""

    def __init__(self) -> None:
        self.sorok: list[str] = []

    def hozzaad(self, sor: NaploSor) -> None:
        self.sorok.append(sor.szoveg())

    def lezar_eor(self) -> None:
        self.sorok.append(FUTAS_VEGE)

    def lezar_limit(self) -> None:
        self.sorok.append(LIMIT_TULLEPES)

    def szoveg(self) -> str:
        return "".join(sor + "\n" for sor in self.sorok)

    def fajlba_ir(self, utvonal: str | Path) -> None:
        Path(utvonal).write_text(self.szoveg(), encoding="utf-8", newline="\n")
