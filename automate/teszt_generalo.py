"""Hibakereső teszt bemenetek (input_NNN.txt) és elvárt kimenetek a Robotszimulátorhoz.

Használat (a projekt gyökeréből):
    python automate/teszt_generalo.py                  – automate/teszt mappába
    python automate/teszt_generalo.py CEL_MAPPA --veletlen 50 --mag 7

Az esetek szándékosan azokra a pontokra céloznak, ahol egy megvalósítás nagy eséllyel
hibázik: sorvégek (CRLF, BOM, hiányzó záró újsor), behúzás és else-hozzárendelés,
kulcsszóval kezdődő azonosítók, a kiértékelés sorrendje és az első hiba, negatív
API-paraméter, naplóformátum hibánál, utasításlimit pontosan az 1000. sornál,
forgásirány, bányászott mező állapota. Utánuk véletlenszerű, mélyen egymásba ágyazott
programok jönnek.

Az elvárt naplók (CEL_MAPPA/elvart/output_NNN.txt) a független `referencia.py`
értelmezővel készülnek. Összevetés:
    python automate/futtat.py automate/teszt KIMENET --elvart automate/teszt/elvart
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

from referencia import naplo_szovegbol

ALAP_CEL = Path(__file__).resolve().parent / "teszt"
IRANYOK = "><^v"
# Kulcsszóval kezdődő / végződő nevek: a hibás tokenizálót megzavarják.
AZONOSITOK = ["a", "x", "Arany", "arany", "iffy", "tox", "notfal", "orr", "setx",
              "whilee", "here2", "by1", "endif", "printx"]
OPERATOROK_EGESZ = ["+", "-", "*"]
OPERATOROK_HASONLITO = ["<", "<=", ">", ">="]
OPERATOROK_EGYENLO = ["=", "<>"]
OPERATOROK_LOGIKAI = ["and", "or"]
MAX_MELYSEG = 3


@dataclass
class Eset:
    leiras: str
    terkep: str  # az első sor (méret) nélkül
    program: str
    sorvege: str = "\n"
    bom: bool = False
    zaro_ujsor: bool = True

    def szoveg(self) -> str:
        sorok = self.terkep.strip("\n").splitlines()
        sorok.insert(0, f"{len(sorok)} {len(sorok[0])}")
        program = self.program.strip("\n")
        if program:
            sorok += program.splitlines()
        szoveg = self.sorvege.join(sorok) + (self.sorvege if self.zaro_ujsor else "")
        return ("﻿" if self.bom else "") + szoveg


def limit_program(elotag_sorok: int, utana: str) -> str:
    """Számláló ciklus: pontosan `elotag_sorok` + 3*N + 1 végrehajtott sor, utána `utana`.

    Az előtag 4 sora (n = 331, i, c) + (elotag_sorok - 4) darab print; a ciklus 331-szer fut.
    """
    return "\n".join([
        "set n to 100 * 3",
        "set n to n + 31",
        "set i to 0",
        "set c to i < n",
        *["print n"] * (elotag_sorok - 4),
        "while c",
        "  set i to i + 1",
        "  set c to i < n",
        utana,
    ])


# --- Kézi esetek -----------------------------------------------------------------

BANYASZ_TERKEP = """
....@..........
.#############.
.......@...>.@@
"""

BANYASZ_PROGRAM = """
set count to 0
set fal to isThere 1
set megy to not fal
while megy
  set arany to isThere 2
  if arany
    step forward 1
    mine here
    set count to count + 1
  else
    step forward 1
  set fal to isThere 1
  set megy to not fal
print count
"""

LABIRINTUS = """
>.#....@.#....@
.#.###.#.#.##.#
.#...#...#..#..
.###.#####.#.#.
.....@...#.#.#.
####.###.#.#.#.
...#...#...#.@.
.#.###.#####.##
.#.@...#.....#.
.#####.#.###.#.
.....#...#.@.#.
.###.#####.###.
.#.@.#.....#...
.#.###.###.#.#.
...#.....#...#@
"""

LABIRINTUS_PROGRAM = """
set count to 0
set fut to true
while fut
  turn by 1
  set fal to isThere 1
  while fal
    turn by 3
    set fal to isThere 1
  set arany to isThere 2
  step forward 1
  if arany
    mine here
    set count to count + 1
  set fut to count < 6
print count
"""

KEZI_ESETEK = [
    # --- Beolvasás: sorvégek, BOM, záró újsor
    Eset("CRLF sorvégek (Windowson készült fájl)", BANYASZ_TERKEP, BANYASZ_PROGRAM,
         sorvege="\r\n"),
    Eset("CRLF sorvégek, az utolsó sor végén nincs újsor", BANYASZ_TERKEP, BANYASZ_PROGRAM,
         sorvege="\r\n", zaro_ujsor=False),
    Eset("UTF-8 BOM a fájl elején + CRLF", ">.@", "step forward 1\nset a to isThere 2\nprint a",
         sorvege="\r\n", bom=True),
    Eset("Üres program, a térkép utolsó sora után nincs újsor", "..\n.<", "", zaro_ujsor=False),
    Eset("Üres program CRLF-fel", "v", "", sorvege="\r\n"),
    Eset("A program utolsó sora (while törzse) után nincs újsor", ">..", """
set m to true
while m
  step forward 1
  set m to isThere 0""", zaro_ujsor=False),

    # --- Tokenizálás, azonosítók
    Eset("Kulcsszóval kezdődő azonosítók (iffy, tox, notfal, ortho, andy, printer...)", ">..", """
set iffy to 1
set whilex to true
set setup to iffy + 2
set tox to setup * 3
set notfal to not whilex
set ortho to whilex or notfal
set andy to tox - iffy
set trueish to andy > 5
set printer to 0
set here1 to isThere 0
set by2 to 2
set forwardx to by2
set mine2 to here1 and trueish
set elsee to notfal = false
print setup
print tox
print notfal
print ortho
print andy
print trueish
print mine2
print elsee
step forward printer
turn by by2
print forwardx
"""),
    Eset("Számjegyet tartalmazó azonosítók, kis-nagybetű (a1b2, Z9, count/Count)", ">.", """
set a1b2 to 7
set Z9 to 100
set count to a1b2 + 93
set Count to count = Z9
print count
print Count
set q1 to Z9 - count
print q1
"""),
    Eset("Vezető nullás számok (007, 093, 00) – értékük 7, 93, 0", ">..", """
set a to 007
set b to a + 093
print b
step forward 00
turn by 04
print a
"""),

    # --- Behúzás, blokkok, else
    Eset("Az else a külső if-hez tartozik (azonos behúzás), a belső if-nek nincs else-e", ">.", """
if true
  if false
    print 1
else
  print 2
print 3
"""),
    Eset("Két egymás utáni if: az else a másodikhoz tartozik", ">.", """
if false
  print 1
if false
  print 2
else
  print 3
print 4
"""),
    Eset("Több szint egyszerre záródik (3 szint → 0), else minden szinten", ">.", """
set i to 0
set c to true
while c
  if c
    if true
      set i to i + 1
    else
      print 99
  else
    print 98
  set c to i < 2
print i
"""),
    Eset("Blokkonként eltérő behúzás (1, 4 és 7 szóköz)", ">.", """
set n to 0
set megy to true
while megy
 set n to n + 1
 set k to n = 2
 if k
    print n
 else
       print 0
 set megy to n < 3
print n
"""),
    Eset("Három while egymásban, mindegyik többször fut", ">.", """
set a to 0
set ca to true
while ca
  set b to 0
  set cb to true
  while cb
    set d to 0
    set cd to true
    while cd
      set d to d + 1
      set cd to d < 2
    set b to b + 1
    set cb to b < 2
  set a to a + 1
  set ca to a < 2
print a
print b
print d
"""),
    Eset("Az else ág a beágyazott ciklus után, a törzs végén újabb if", ">..@", """
set k to 0
set f to false
if f
  print 1
else
  while true
    set k to k + 1
    set v to k < 3
    if v
      print k
    else
      step forward 3
      mine here
      print 100
      set f to true
    set w to not f
    if w
      turn by 4
    else
      print 7
      while false
        print 8
      print 9
      step forward 1
"""),
    Eset("while hamis feltétellel, utána rögtön else nélküli if", ">.", """
set a to false
while a
  print 1
if a
  print 2
print 3
"""),

    # --- Kiértékelési sorrend, első hiba
    Eset("true + c: az első operandus rossz típusa előbb derül ki → E_BAD_OPERAND", ">.",
         "set x to true + c"),
    Eset("c + true: az első operandus nincs inicializálva → E_UNINITIALIZED", ">.",
         "set x to c + true"),
    Eset("true = c: az = első operandusa bármilyen típusú, a második nincs → E_UNINITIALIZED",
         ">.", "set x to true = c"),
    Eset("c = 1: nem inicializált első operandus → E_UNINITIALIZED", ">.", "set x to c = 1"),
    Eset("1 = true: típuseltérés a második operandus után → E_BAD_OPERAND", ">.",
         "set a to 1\nset x to a = true"),
    Eset("true and 5: a második operandus nem logikai → E_BAD_OPERAND", ">.",
         "set x to true and 5"),
    Eset("5 or c: az első operandus rossz, a c-t már nem kell vizsgálni → E_BAD_OPERAND", ">.",
         "set x to 5 or c"),
    Eset("false < 3 → E_BAD_OPERAND", ">.", "set x to false < 3"),
    Eset("3 >= true → E_BAD_OPERAND", ">.", "set x to 3 >= true"),
    Eset("not c → E_UNINITIALIZED", ">.", "set x to not c"),
    Eset("set x to x + 1, ha x még nem létezik → E_UNINITIALIZED", ">.", "set x to x + 1"),
    Eset("Sikertelen értékadás után a futás leáll (nincs további sor)", ">.", """
set a to 1
set b to a and true
print a
"""),

    # --- Típusok
    Eset("E_TYPE_MISMATCH: egészbe összehasonlítás eredménye", ">.", """
set x to 1
set x to 1 < 2
"""),
    Eset("E_TYPE_MISMATCH isThere után: az API-hívás is a naplóba kerül a hiba előtt", ">@", """
set a to 5
set a to isThere 2
"""),
    Eset("Logikai változó újraírása logikaival rendben, egészzel nem", ">.", """
set b to true
set b to false
set b to not b
print b
set b to 0
"""),
    Eset("Nagy és negatív egészek (a 0..100 csak a forráskódra vonatkozik)", ">.", """
set a to 100
set b to a * a
set c to b * b
set d to 0 - c
print d
set e to d - d
print e
set f to d < e
print f
set g to d * d
print g
"""),
    Eset("Egyenlőség logikaiakkal és egészekkel, határ-összehasonlítások", ">.", """
set t to true
set f to false
set a to t = f
set b to t <> f
set c to f = false
set d to 0 = 0
set e to 7 <> 7
set g to 0 <= 0
set h to 100 >= 100
set i to 100 > 100
set j to 0 < 0
print a
print b
print c
print d
print e
print g
print h
print i
print j
"""),

    # --- API-paraméterek és naplóformátum
    Eset("turn by negatív érték (változóból) → E_BAD_ARG, a napló a kiértékelt értéket mutatja",
         ">.", "set n to 0 - 1\nturn by n"),
    Eset("step forward negatív érték → E_BAD_ARG", ">..", "set n to 2 - 5\nstep forward n"),
    Eset("step forward logikai változóval → E_BAD_ARG", ">..", "set n to true\nstep forward n"),
    Eset("isThere változóból kapott 3-mal → E_BAD_ARG", ">.", "set w to 3\nset r to isThere w"),
    Eset("isThere true → E_BAD_ARG", ">.", "set r to isThere true"),
    Eset("isThere nem inicializált változóval → isThere E_UNINITIALIZED", ">.",
         "set r to isThere w"),
    Eset("turn by nem inicializált változóval", ">.", "turn by k"),
    Eset("print nem inicializált változóval", ">.", "print k"),
    Eset("isThere negatív értékkel", ">.", "set w to 0 - 2\nset r to isThere w"),
    Eset("print logikai literál és isThere minden kódra", ">#", """
print true
print false
print 0
set a to isThere 0
set b to isThere 1
set c to isThere 2
"""),

    # --- Robot és térkép
    Eset("Forgás iránya: balra (óramutatóval ellentétesen), sarokban, minden irány", """
...
..@
.@v
""", """
set a to isThere 1
print a
turn by 1
set b to isThere 1
print b
turn by 1
set c to isThere 2
print c
turn by 1
set d to isThere 2
print d
turn by 99
set e to isThere 2
print e
"""),
    Eset("A bányászott mező üres lesz (isThere 0 igaz, isThere 2 hamis), újra bányászva E_NO_GOLD",
         ">@.", """
step forward 1
mine here
turn by 2
step forward 1
turn by 2
set e to isThere 0
set g to isThere 2
print e
print g
step forward 1
mine here
"""),
    Eset("A robot kiinduló mezője üres kamra lesz, amikor elhagyja", ".>.", """
step forward 1
turn by 2
set e to isThere 0
print e
step forward 1
set r to isThere 0
print r
"""),
    Eset("step forward pontosan a térkép széléig rendben, step forward 0 falnál rendben", ">...#",
         """
step forward 3
step forward 0
set a to isThere 1
print a
step forward 1
"""),
    Eset("step forward 14 egy 1x15-ös sávon: az átlépett rögök megmaradnak", ">@@@@@@@@@@@@@@",
         """
step forward 14
mine here
turn by 2
set a to isThere 2
print a
step forward 13
mine here
step forward 1
"""),
    Eset("15x1-es függőleges térkép, dél felé haladva bányászik a széléig", """
v
@
.
@
@
.
.
@
.
.
.
@
.
.
@
""", """
set n to 0
set fut to true
while fut
  set van to isThere 2
  step forward 1
  if van
    mine here
    set n to n + 1
  set fal to isThere 1
  set fut to not fal
print n
step forward 1
"""),
    Eset("step forward 100 kis térképen → E_BEDROCK_HIT", ">..", "step forward 100"),
    Eset("Falba ütközés a lépés közepén aranyon át", ">@@#", "step forward 3"),
    Eset("Bányászás a kiinduló mezőn → E_NO_GOLD", "@>@", "mine here"),
    Eset("A feladat bányász programja (a sor végén két rög a szélen)", BANYASZ_TERKEP,
         BANYASZ_PROGRAM),
    Eset("Labirintus 15x15: bal kézi falkövetés (a limitig fut)", LABIRINTUS,
         LABIRINTUS_PROGRAM),

    # --- Feltételek
    Eset("while egész feltétellel → E_NON_BOOL_CONDITION a while sorában", ">.",
         "set n to 1\nwhile n\n  print n"),
    Eset("if nem inicializált feltétellel", ">.", "if van\n  print 1"),
    Eset("Hiba a while törzsében: logikai + egész → E_BAD_OPERAND", ">..", """
set m to true
while m
  step forward 1
  set m to isThere 0
  set q to m + 1
"""),

    # --- Utasításlimit határai
    Eset("Pontosan 1000 végrehajtott sor, az 1000. sor hibás → hiba + EOR", ">.",
         limit_program(5, "mine here")),
    Eset("Az 1001. sor hibás lenne → INSTRUCTION_COUNT_LIMIT_EXCEEDED, nincs hibakód", ">.",
         limit_program(6, "mine here")),
    Eset("Az 1000. sor egy hamis if, az else lenne az 1001. → limit", ">.",
         limit_program(5, "if false\n  print 1\nelse\n  print 2")),
    Eset("Az 1000. sor a while utolsó (hamis) feltétel-kiértékelése → EOR", ">.",
         limit_program(6, "")),
    Eset("Az 1000. sor egy igaz if, a törzse lenne az 1001. → limit", ">.",
         limit_program(5, "if true\n  print 1")),
    Eset("Végtelen ciklus üres hatású törzzsel", ">.", "while true\n  turn by 0"),
]


# --- Véletlen esetek ---------------------------------------------------------------

def veletlen_terkep(rnd: random.Random) -> str:
    sorok, oszlopok = rnd.randint(1, 15), rnd.randint(1, 15)
    suly_fal, suly_arany = rnd.uniform(0, 0.35), rnd.uniform(0, 0.3)
    racs = [[rnd.choices(".#@", [1 - suly_fal - suly_arany, suly_fal, suly_arany])[0]
             for _ in range(oszlopok)] for _ in range(sorok)]
    racs[rnd.randrange(sorok)][rnd.randrange(oszlopok)] = rnd.choice(IRANYOK)
    return "\n".join("".join(sor) for sor in racs)


class ProgramIro:
    """Nyelvtanilag helyes MineScript program; a típusokra többnyire figyel,
    de kis valószínűséggel szándékosan hibás (futási hibát okozó) sort ír."""

    def __init__(self, rnd: random.Random, hiba_esely: float) -> None:
        self.rnd = rnd
        self.hiba_esely = hiba_esely
        self.tipusok: dict[str, str] = {}  # azonosító → "int" / "bool"
        self.sorok: list[str] = []

    def _hibazik(self) -> bool:
        return self.rnd.random() < self.hiba_esely

    def _valtozo(self, tipus: str) -> str | None:
        jeloltek = [v for v, t in self.tipusok.items() if t == tipus]
        return self.rnd.choice(jeloltek) if jeloltek else None

    def egesz(self, maximum: int = 100) -> str:
        if self._hibazik():
            return self.rnd.choice(["true", "false", self.rnd.choice(AZONOSITOK)])
        valtozo = self._valtozo("int")
        if valtozo and self.rnd.random() < 0.4:
            return valtozo
        return str(self.rnd.randint(0, maximum))

    def logikai(self) -> str:
        if self._hibazik():
            return self.rnd.choice([str(self.rnd.randint(0, 9)), self.rnd.choice(AZONOSITOK)])
        valtozo = self._valtozo("bool")
        if valtozo and self.rnd.random() < 0.6:
            return valtozo
        return self.rnd.choice(["true", "false"])

    def ertekadas(self, behuzas: str) -> None:
        nev = self.rnd.choice(AZONOSITOK)
        tipus = self.tipusok.get(nev) or self.rnd.choice(["int", "bool"])
        if self._hibazik():
            tipus = "bool" if tipus == "int" else "int"
        if tipus == "int":
            jobb = self.rnd.choice([
                self.egesz(),
                f"{self.egesz()} {self.rnd.choice(OPERATOROK_EGESZ)} {self.egesz(10)}",
            ])
        else:
            fajta = self.rnd.randrange(5)
            if fajta == 0:
                jobb = self.logikai()
            elif fajta == 1:
                jobb = f"isThere {self.rnd.choice('0122') if not self._hibazik() else '3'}"
            elif fajta == 2:
                jobb = f"{self.egesz()} {self.rnd.choice(OPERATOROK_HASONLITO)} {self.egesz()}"
            elif fajta == 3:
                op = self.rnd.choice(OPERATOROK_LOGIKAI + OPERATOROK_EGYENLO)
                jobb = f"{self.logikai()} {op} {self.logikai()}"
            else:
                jobb = f"not {self.logikai()}"
        self.tipusok.setdefault(nev, tipus)
        self.sorok.append(f"{behuzas}set {nev} to {jobb}")

    def parancs(self, behuzas: str) -> None:
        fajta = self.rnd.choices(["step", "turn", "mine", "print", "set"], [3, 2, 1, 1, 4])[0]
        if fajta == "step":
            self.sorok.append(f"{behuzas}step forward {self.egesz(2)}")
        elif fajta == "turn":
            self.sorok.append(f"{behuzas}turn by {self.egesz(5)}")
        elif fajta == "mine":
            self.sorok.append(f"{behuzas}mine here")
        elif fajta == "print":
            ertek = self.egesz() if self.rnd.random() < 0.5 else self.logikai()
            self.sorok.append(f"{behuzas}print {ertek}")
        else:
            self.ertekadas(behuzas)

    def blokk(self, behuzas: str, melyseg: int, darab: int) -> None:
        for _ in range(darab):
            if melyseg < MAX_MELYSEG and self.rnd.random() < 0.25:
                self.vezerlo(behuzas, melyseg)
            else:
                self.parancs(behuzas)

    def vezerlo(self, behuzas: str, melyseg: int) -> None:
        belso = behuzas + " " * self.rnd.choice([1, 2, 2, 4])
        fajta = self.rnd.choice(["if", "ifelse", "while"])
        if fajta == "while":
            # Tipikus minta: a feltétel a törzs végén frissül a szenzor alapján.
            feltetel = self.rnd.choice(["fal", "megy", "arany"])
            self.sorok.append(f"{behuzas}set {feltetel} to isThere {self.rnd.choice('012')}")
            self.tipusok.setdefault(feltetel, "bool")
            self.sorok.append(f"{behuzas}while {self.logikai() if self._hibazik() else feltetel}")
            self.blokk(belso, melyseg + 1, self.rnd.randint(1, 3))
            if self.tipusok[feltetel] == "bool":
                self.sorok.append(
                    f"{belso}set {feltetel} to isThere {self.rnd.choice('012')}")
            return
        self.sorok.append(f"{behuzas}if {self.logikai()}")
        self.blokk(belso, melyseg + 1, self.rnd.randint(1, 3))
        if fajta == "ifelse":
            self.sorok.append(f"{behuzas}else")
            self.blokk(belso, melyseg + 1, self.rnd.randint(1, 3))

    def program(self) -> str:
        self.blokk("", 0, self.rnd.randint(1, 12))
        return "\n".join(self.sorok)


def veletlen_eset(rnd: random.Random, sorszam: int) -> Eset:
    hiba_esely = rnd.choice([0.0, 0.0, 0.03, 0.1])
    leiras = f"Véletlen #{sorszam} (hibaesély {hiba_esely:.0%})"
    return Eset(leiras, veletlen_terkep(rnd), ProgramIro(rnd, hiba_esely).program())


# --- Kiírás --------------------------------------------------------------------------

def general(cel: Path, veletlen_db: int, mag: int) -> list[Eset]:
    rnd = random.Random(mag)
    esetek = KEZI_ESETEK + [veletlen_eset(rnd, i + 1) for i in range(veletlen_db)]
    elvart = cel / "elvart"
    elvart.mkdir(parents=True, exist_ok=True)
    for regi in [*cel.glob("input_*.txt"), *elvart.glob("output_*.txt")]:
        regi.unlink()
    for i, eset in enumerate(esetek, start=1):
        szoveg = eset.szoveg()
        (cel / f"input_{i:03d}.txt").write_bytes(szoveg.encode("utf-8"))
        naplo = naplo_szovegbol(szoveg)
        (elvart / f"output_{i:03d}.txt").write_bytes(("\n".join(naplo) + "\n").encode("utf-8"))
    tartalom = [f"# Teszt bemenetek\n\nElőállította: `automate/teszt_generalo.py` "
                f"(mag: {mag}, véletlen esetek: {veletlen_db}).\n"
                "Az elvárt naplók az `elvart` mappában vannak (`automate/referencia.py`).\n",
                "| Fájl | Leírás |", "|---|---|"]
    tartalom += [f"| input_{i:03d}.txt | {e.leiras} |" for i, e in enumerate(esetek, start=1)]
    (cel / "README.md").write_text("\n".join(tartalom) + "\n", encoding="utf-8")
    return esetek


def main() -> None:
    p = argparse.ArgumentParser(description="Robotszimulátor hibakereső teszt bemenetek.")
    p.add_argument("cel", type=Path, nargs="?", default=ALAP_CEL,
                   help=f"célmappa (alap: {ALAP_CEL})")
    p.add_argument("--veletlen", type=int, default=30, help="véletlen esetek száma (alap: 30)")
    p.add_argument("--mag", type=int, default=2026, help="a véletlen generátor magja")
    args = p.parse_args()
    esetek = general(args.cel, args.veletlen, args.mag)
    print(f"{len(esetek)} bemenet és elvárt kimenet elkészült: {args.cel}")


if __name__ == "__main__":
    main()
