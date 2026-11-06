"""Soronkénti feldolgozás / tokenizálás a feladatleírás 2.1 pontja szerint.

1. Sorokra bontás: minden sor egy utasítás; a sor eleji szóközök száma a behúzás.
2. Tokenizálás: a behúzás után a sort a szóközök mentén daraboljuk.
3. A sor értelmezése: az első token (kulcsszó) adja meg az utasítás fajtáját.
4. Nincs beágyazott kifejezés: minden simpleval egyetlen token.

Minden token kap egy fajtát (kulcsszó, azonosító, szám, logikai érték, operátor),
így az elemző és a megjelenítés is tudja, mivel dolgozik.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

KULCSSZAVAK: tuple[str, ...] = (
    "and", "by", "else", "false", "forward", "here", "if", "isThere", "mine",
    "not", "or", "print", "set", "step", "to", "true", "turn", "while",
)
_KULCSSZAVAK_KISBETUVEL = frozenset(szo.lower() for szo in KULCSSZAVAK)

LOGIKAI_ERTEKEK = ("true", "false")
OPERATOROK: tuple[str, ...] = ("+", "-", "*", "=", "<>", "<", "<=", ">", ">=", "and", "or", "not")
UTASITAS_KULCSSZAVAK: tuple[str, ...] = ("step", "turn", "mine", "print", "set", "if", "else", "while")
"""Ezek állhatnak egy sor elején (a sor értelmezéséhez)."""


class TokenFajta(Enum):
    KULCSSZO = "kulcsszó"
    AZONOSITO = "azonosító"
    SZAM = "szám"
    LOGIKAI = "logikai érték"
    OPERATOR = "operátor"
    ISMERETLEN = "ismeretlen"


@dataclass(frozen=True)
class Token:
    """A program legkisebb önálló egysége: a szövege és a fajtája."""

    szoveg: str
    fajta: TokenFajta

    def __str__(self) -> str:
        return self.szoveg


def _betu_e(karakter: str) -> bool:
    return karakter.isascii() and karakter.isalpha()


def _szamjegy_e(karakter: str) -> bool:
    return karakter.isascii() and karakter.isdigit()


def token_fajta(szoveg: str) -> TokenFajta:
    """Egy darab szövegének besorolása az EBNF szerint (kis-/nagybetű számít)."""
    if szoveg in LOGIKAI_ERTEKEK:
        return TokenFajta.LOGIKAI
    if szoveg in OPERATOROK:
        return TokenFajta.OPERATOR
    if szoveg in KULCSSZAVAK:
        return TokenFajta.KULCSSZO
    if szoveg and all(_szamjegy_e(k) for k in szoveg):
        return TokenFajta.SZAM
    if szoveg and _betu_e(szoveg[0]) and all(_betu_e(k) or _szamjegy_e(k) for k in szoveg):
        return TokenFajta.AZONOSITO
    return TokenFajta.ISMERETLEN


@dataclass
class TokenSor:
    """Egy programsor: 1-től számozott sorszám, behúzás (szóközök száma) és a tokenek."""

    sorszam: int
    behuzas: int
    tokenek_: list[Token]

    @property
    def tokenek(self) -> list[str]:
        """A tokenek szövegei (az elemző ezekkel dolgozik)."""
        return [token.szoveg for token in self.tokenek_]

    @property
    def kulcsszo(self) -> str:
        """Az első token: ez határozza meg, milyen utasításról van szó."""
        return self.tokenek_[0].szoveg if self.tokenek_ else ""


def tokenizal_sor(sor: str, sorszam: int) -> TokenSor:
    """1–2. lépés: behúzás leválasztása, majd darabolás a szóközök mentén."""
    tartalom = sor.rstrip("\r\n").lstrip(" ")
    behuzas = len(sor) - len(sor.lstrip(" "))
    darabok = [darab for darab in tartalom.split(" ") if darab != ""]
    return TokenSor(sorszam, behuzas, [Token(darab, token_fajta(darab)) for darab in darabok])


def tokenizal(sorok: list[str]) -> list[TokenSor]:
    """Az összes programsor tokenizálása (a sorszám a sor indexe + 1)."""
    return [tokenizal_sor(sor, index + 1) for index, sor in enumerate(sorok)]


def kulcsszo_e(szo: str) -> bool:
    """Kulcsszó-e a szó bármilyen kis-/nagybetűs alakban (azonosító nem lehet ilyen)."""
    return szo.lower() in _KULCSSZAVAK_KISBETUVEL
