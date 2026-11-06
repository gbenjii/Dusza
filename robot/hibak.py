"""Hibakódok, magyar leírásaik és a futás közbeni hibát jelző kivétel."""

from enum import Enum


class HibaKod(Enum):
    """A futás közben előforduló hibák kódjai (pontosan ez kerül a naplóba)."""

    E_TYPE_MISMATCH = "E_TYPE_MISMATCH"
    E_UNINITIALIZED = "E_UNINITIALIZED"
    E_NON_BOOL_CONDITION = "E_NON_BOOL_CONDITION"
    E_BAD_OPERAND = "E_BAD_OPERAND"
    E_BEDROCK_HIT = "E_BEDROCK_HIT"
    E_NO_GOLD = "E_NO_GOLD"
    E_BAD_ARG = "E_BAD_ARG"


LIMIT_TULLEPES = "INSTRUCTION_COUNT_LIMIT_EXCEEDED"
"""Ez a sor kerül a naplóba, ha a program túllépi az utasításkorlátot."""

LIMIT_LEIRAS = "A program túllépte az 1000 végrehajtott sor korlátját."

HIBA_LEIRASOK: dict[HibaKod, str] = {
    HibaKod.E_TYPE_MISMATCH: "A változó típusa már rögzült, más típusú értéket nem kaphat.",
    HibaKod.E_UNINITIALIZED: "Értékadás előtt olvasott (nem inicializált) változó.",
    HibaKod.E_NON_BOOL_CONDITION: "Az if/while feltétele nem logikai érték.",
    HibaKod.E_BAD_OPERAND: "A művelet operandusa nem megfelelő típusú.",
    HibaKod.E_BEDROCK_HIT: "A robot falnak vagy a térkép szélének ütközött.",
    HibaKod.E_NO_GOLD: "Ezen a mezőn nincs arany, amit ki lehetne bányászni.",
    HibaKod.E_BAD_ARG: "Hibás típusú vagy tartományon kívüli paraméter.",
}


class FutasiHiba(Exception):
    """Futás közbeni hiba; a `kod` mező mondja meg, melyik."""

    def __init__(self, kod: HibaKod) -> None:
        super().__init__(kod.value)
        self.kod = kod
