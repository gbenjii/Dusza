"""Független referencia-értelmező a Robotszimulátor feladathoz – csak a PDF alapján.

A `robot` kódjától szándékosan függetlenül készült: ugyanabból a bemenetből elkészíti
az elvárt naplót, így a két megvalósítás összevethető (teszt_generalo.py → elvart/).

Használat:
    python automate/referencia.py BE KI      – egy fájl naplója
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

LIMIT = 1000
IRANYOK = {">": (0, 1), "^": (-1, 0), "<": (0, -1), "v": (1, 0)}
BALRA = {">": "^", "^": "<", "<": "v", "v": ">"}
ARITMETIKA = {"+", "-", "*"}
HASONLITAS = {"<", "<=", ">", ">="}
EGYENLOSEG = {"=", "<>"}
LOGIKA = {"and", "or"}


class Hiba(Exception):
    def __init__(self, kod: str) -> None:
        self.kod = kod


class Limit(Exception):
    pass


class Leall(Exception):
    """A hiba már a naplóban van, a futás véget ér."""


@dataclass
class Sor:
    szam: int
    behuzas: int
    tokenek: list[str]
    torzs: list[Sor] = field(default_factory=list)
    kulonben: list[Sor] | None = None
    kulonben_szam: int = 0


def elemez(sorok: list[tuple[int, str]]) -> list[Sor]:
    """(sorszám, szöveg) párokból utasításfa a behúzás alapján."""
    poz = 0

    def blokk(min_behuzas: int) -> list[Sor]:
        nonlocal poz
        eredmeny: list[Sor] = []
        szint = None
        while poz < len(sorok):
            szam, szoveg = sorok[poz]
            behuzas = len(szoveg) - len(szoveg.lstrip(" "))
            if behuzas < min_behuzas or (szint is not None and behuzas < szint):
                break
            if szint is None:
                szint = behuzas
            tokenek = szoveg.split()
            if tokenek[0] == "else":
                break
            poz += 1
            s = Sor(szam, behuzas, tokenek)
            if tokenek[0] in ("if", "while"):
                s.torzs = blokk(behuzas + 1)
                if tokenek[0] == "if" and poz < len(sorok):
                    kszam, kszoveg = sorok[poz]
                    kbeh = len(kszoveg) - len(kszoveg.lstrip(" "))
                    if kszoveg.split()[0] == "else" and kbeh == behuzas:
                        poz += 1
                        s.kulonben_szam = kszam
                        s.kulonben = blokk(behuzas + 1)
            eredmeny.append(s)
        return eredmeny

    return blokk(0)


def tipus(v: int | bool) -> str:
    return "bool" if type(v) is bool else "int"


def szoveg(v: int | bool) -> str:
    return ("true" if v else "false") if type(v) is bool else str(v)


class Gep:
    def __init__(self, terkep: list[list[str]], program: list[Sor]) -> None:
        self.terkep = terkep
        self.program = program
        self.valtozok: dict[str, int | bool] = {}
        self.naplo: list[str] = []
        self.szamlalo = 0
        for r, sor in enumerate(terkep):
            for c, jel in enumerate(sor):
                if jel in IRANYOK:
                    self.poz, self.irany = (r, c), jel
                    sor[c] = "."

    # --- értékek
    def ertek(self, tok: str) -> int | bool:
        if tok == "true":
            return True
        if tok == "false":
            return False
        if tok.isdigit():
            return int(tok)
        if tok not in self.valtozok:
            raise Hiba("E_UNINITIALIZED")
        return self.valtozok[tok]

    def elotte(self) -> str:
        dr, dc = IRANYOK[self.irany]
        r, c = self.poz[0] + dr, self.poz[1] + dc
        if 0 <= r < len(self.terkep) and 0 <= c < len(self.terkep[0]):
            return self.terkep[r][c]
        return "#"

    def api_param(self, reszek: list[str], tok: str) -> int | bool:
        v = self.ertek(tok)
        reszek.append(szoveg(v))
        return v

    def szamitott(self, tok: list[str], reszek: list[str]) -> int | bool:
        if len(tok) == 1:
            return self.ertek(tok[0])
        if tok[0] == "isThere":
            reszek.append("isThere")
            w = self.api_param(reszek, tok[1])
            if type(w) is bool or w not in (0, 1, 2):
                raise Hiba("E_BAD_ARG")
            eredmeny = self.elotte() == ".#@"[w]
            reszek.append(szoveg(eredmeny))
            return eredmeny
        if tok[0] == "not":
            v = self.ertek(tok[1])
            if type(v) is not bool:
                raise Hiba("E_BAD_OPERAND")
            return not v
        a_tok, op, b_tok = tok
        a = self.ertek(a_tok)
        if op in ARITMETIKA | HASONLITAS and type(a) is bool:
            raise Hiba("E_BAD_OPERAND")
        if op in LOGIKA and type(a) is not bool:
            raise Hiba("E_BAD_OPERAND")
        b = self.ertek(b_tok)
        if op in ARITMETIKA | HASONLITAS and type(b) is bool:
            raise Hiba("E_BAD_OPERAND")
        if op in LOGIKA and type(b) is not bool:
            raise Hiba("E_BAD_OPERAND")
        if op in EGYENLOSEG and tipus(a) != tipus(b):
            raise Hiba("E_BAD_OPERAND")
        return {
            "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
            "<": lambda: a < b, "<=": lambda: a <= b, ">": lambda: a > b,
            ">=": lambda: a >= b, "=": lambda: a == b, "<>": lambda: a != b,
            "and": lambda: a and b, "or": lambda: a or b,
        }[op]()

    def feltetel(self, tok: str) -> bool:
        v = self.ertek(tok)
        if type(v) is not bool:
            raise Hiba("E_NON_BOOL_CONDITION")
        return v

    # --- végrehajtás
    def lep_sor(self, szam: int, reszek: list[str]) -> None:
        self.szamlalo += 1
        if self.szamlalo > LIMIT:
            self.naplo.append("INSTRUCTION_COUNT_LIMIT_EXCEEDED")
            raise Limit
        reszek.insert(0, str(szam))

    def futtat_sor(self, s: Sor) -> None:
        reszek: list[str] = []
        self.lep_sor(s.szam, reszek)
        try:
            self.vegrehajt(s, reszek)
        except Hiba as h:
            reszek.append(h.kod)
            self.naplo.append(" ".join(reszek))
            raise Leall from None

    def vegrehajt(self, s: Sor, reszek: list[str]) -> None:
        t = s.tokenek
        kulcs = t[0]
        if kulcs == "set":
            v = self.szamitott(t[3:], reszek)
            if t[1] in self.valtozok and tipus(self.valtozok[t[1]]) != tipus(v):
                raise Hiba("E_TYPE_MISMATCH")
            self.valtozok[t[1]] = v
            self.naplo.append(" ".join(reszek))
        elif kulcs in ("step", "turn"):
            reszek += t[:2]
            n = self.api_param(reszek, t[2])
            if type(n) is bool or n < 0:
                raise Hiba("E_BAD_ARG")
            if kulcs == "turn":
                for _ in range(n % 4):
                    self.irany = BALRA[self.irany]
            else:
                dr, dc = IRANYOK[self.irany]
                for _ in range(n):
                    if self.elotte() == "#":
                        raise Hiba("E_BEDROCK_HIT")
                    self.poz = (self.poz[0] + dr, self.poz[1] + dc)
            self.naplo.append(" ".join(reszek))
        elif kulcs == "mine":
            reszek += ["mine", "here"]
            r, c = self.poz
            if self.terkep[r][c] != "@":
                raise Hiba("E_NO_GOLD")
            self.terkep[r][c] = "."
            self.naplo.append(" ".join(reszek))
        elif kulcs == "print":
            reszek.append("print")
            self.api_param(reszek, t[1])
            self.naplo.append(" ".join(reszek))
        elif kulcs == "if":
            ag = self.feltetel(t[1])
            self.naplo.append(" ".join(reszek))
            if ag:
                self.blokk(s.torzs)
            elif s.kulonben is not None:
                self.lep_sor(s.kulonben_szam, kulonben := [])
                self.naplo.append(" ".join(kulonben))
                self.blokk(s.kulonben)
        elif kulcs == "while":
            ag = self.feltetel(t[1])
            self.naplo.append(" ".join(reszek))
            while ag:
                self.blokk(s.torzs)
                reszek = []
                self.lep_sor(s.szam, reszek)
                try:
                    ag = self.feltetel(t[1])
                except Hiba as h:
                    self.naplo.append(" ".join([*reszek, h.kod]))
                    raise Leall from None
                self.naplo.append(" ".join(reszek))

    def blokk(self, sorok: list[Sor]) -> None:
        for s in sorok:
            self.futtat_sor(s)

    def fut(self) -> list[str]:
        try:
            self.blokk(self.program)
            self.naplo.append("EOR")
        except Leall:
            self.naplo.append("EOR")
        except Limit:
            pass
        return self.naplo


def naplo_szovegbol(bemenet: str) -> list[str]:
    sorok = bemenet.lstrip("﻿").splitlines()
    r, c = map(int, sorok[0].split())
    terkep = [list(sor[:c]) for sor in sorok[1:1 + r]]
    program = [(i, s.rstrip()) for i, s in enumerate(sorok[1 + r:], start=1) if s.strip()]
    return Gep(terkep, elemez(program)).fut()


def main() -> None:
    be, ki = sys.argv[1:3]
    naplo = naplo_szovegbol(Path(be).read_text(encoding="utf-8"))
    Path(ki).write_text("\n".join(naplo) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
