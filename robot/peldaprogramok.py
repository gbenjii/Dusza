"""Beépített példák (térkép + program) az IDE „Példák” menüjéhez.

A szövegek a bemeneti fájl formátumában vannak, így a betöltésük ugyanúgy
történik, mint egy fájlé; az exe-ben is elérhetők (nincs külön fájl).
"""

from __future__ import annotations

from dataclasses import dataclass

TERKEP_VIDEO = (
    "5 10\n"
    ".#..@..#.@\n"
    ".#.##.##..\n"
    ">.@.@@.@.#\n"
    "##.#..#.#.\n"
    ".@..#..@..\n"
)

PROGRAM_AGYUJTO = """set count to 0
set megy to true
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

TERKEP_KORBE = (
    "5 8\n"
    "@..@...@\n"
    ".######.\n"
    ".######.\n"
    ".######.\n"
    ">..@...@\n"
)

PROGRAM_KORBE = """set db to 0
set kor to 0
set fut to true
while fut
  set arany to isThere 2
  if arany
    step forward 1
    mine here
    set db to db + 1
  else
    set fal to isThere 1
    if fal
      turn by 1
    else
      step forward 1
  set kor to kor + 1
  set fut to kor < 60
print db
"""

PROGRAM_LIMIT = """set n to 0
while true
  set n to n + 1
print n
"""

PROGRAM_HIBA = """set x to 5
print x
set kesz to x > 3
if kesz
  turn by 2
  step forward 3
  mine here
print 99
"""

PROGRAM_FELADAT = """set arany to isThere 2
set count to 0
turn by 0
print arany
if false
  print 1
else
  set x to isThere 3
print 9
"""


@dataclass(frozen=True)
class Pelda:
    """Egy menüpont: név, rövid leírás és a teljes bemeneti szöveg."""

    nev: str
    leiras: str
    szoveg: str


PELDAK: tuple[Pelda, ...] = (
    Pelda("Bemutató térkép (üres program)",
          "A videó forgatókönyvének térképe, üres programmal – építsd fel blokkokból!",
          TERKEP_VIDEO),
    Pelda("Aranygyűjtés egyenesen",
          "A feladatleírás programja: előre halad a falig, közben minden aranyat kibányász.",
          TERKEP_VIDEO + PROGRAM_AGYUJTO),
    Pelda("Körbejárás a fal mentén",
          "Falnál balra fordul, így körbejárja a pályát, és összeszedi az aranyat.",
          TERKEP_KORBE + PROGRAM_KORBE),
    Pelda("Utasításkorlát (végtelen ciklus)",
          "A while true ciklus az 1000. sor után INSTRUCTION_COUNT_LIMIT_EXCEEDED hibával áll le.",
          "3 3\n>..\n...\n...\n" + PROGRAM_LIMIT),
    Pelda("Futási hiba (E_BEDROCK_HIT)",
          "Megfordul és falnak megy: a futás hibakóddal leáll.",
          "2 4\n.>@.\n....\n" + PROGRAM_HIBA),
    Pelda("A feladatleírás naplópéldája",
          "A 4. fejezet példája: a napló a „8 isThere 3 E_BAD_ARG” sorral és EOR-ral zárul.",
          "3 15\n....@..........\n.#############.\n.......@...>...\n" + PROGRAM_FELADAT),
)
