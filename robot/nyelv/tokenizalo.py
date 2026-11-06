"""Egy forrássor szétbontása behúzásra és tokenekre, valamint a kulcsszavak."""

from __future__ import annotations

from dataclasses import dataclass

KULCSSZAVAK: tuple[str, ...] = (
    "and", "by", "else", "false", "forward", "here", "if", "isThere", "mine",
    "not", "or", "print", "set", "step", "to", "true", "turn", "while",
)
_KULCSSZAVAK_KISBETUVEL = frozenset(szo.lower() for szo in KULCSSZAVAK)


@dataclass
class TokenSor:
    """Egy programsor: 1-től számozott sorszám, behúzás (szóközök) és tokenek."""

    sorszam: int
    behuzas: int
    tokenek: list[str]


def tokenizal_sor(sor: str, sorszam: int) -> TokenSor:
    """Egy sor tokenekre bontása (a tokenek között szóköz áll)."""
    tartalom = sor.lstrip(" ")
    behuzas = len(sor) - len(tartalom)
    return TokenSor(sorszam, behuzas, tartalom.split())


def tokenizal(sorok: list[str]) -> list[TokenSor]:
    """Az összes programsor tokenizálása."""
    return [tokenizal_sor(sor, index + 1) for index, sor in enumerate(sorok)]


def kulcsszo_e(szo: str) -> bool:
    """Kulcsszó-e a szó bármilyen kis-/nagybetűs alakban."""
    return szo.lower() in _KULCSSZAVAK_KISBETUVEL
