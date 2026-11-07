"""Verseny tesztek tömeges futtatása: BEMENET_MAPPA/input_NNN.txt → KIMENET_MAPPA/output_NNN.txt.

Használat (a projekt gyökeréből):
    python automate/futtat.py BEMENET_MAPPA KIMENET_MAPPA
    python automate/futtat.py BE KI --zip                  – a végén results.zip is készül
    python automate/futtat.py BE KI --robot robot/dist/robot.exe
                                                            – minden fájl külön "robot -q BE KI"
                                                              hívással (a lefordított exe tesztje)
    python automate/futtat.py BE KI --elvart ELVART_MAPPA  – a kimenetek összevetése elvárt
                                                              output_NNN.txt fájlokkal

Alapból a robot kódját ugyanebben a folyamatban hívja (gyors: 200+ fájl pár másodperc).
Minden napló végén ellenőrzi, hogy EOR vagy INSTRUCTION_COUNT_LIMIT_EXCEEDED sor áll-e,
és figyelmeztet, ha a sorszámozott bemenetek között hézag van.
A kilépési kód 0, ha minden fájl rendben lefutott (és egyezett az elvárttal).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
ROBOT_MAPPA = PROJEKT / "robot"
BEMENET_ELOTAG = "input_"
KIMENET_ELOTAG = "output_"
NAPLO_VEGEK = ("EOR", "INSTRUCTION_COUNT_LIMIT_EXCEEDED")
SORSZAM_MINTA = re.compile(r"^input_(\d+)\.txt$")

Futtato = Callable[[Path, Path], None]


@dataclass
class Eredmeny:
    """Egy bemeneti fájl futtatásának eredménye."""

    bemenet: Path
    kimenet: Path
    hiba: str | None = None
    elteres: str | None = None

    @property
    def rendben(self) -> bool:
        return self.hiba is None and self.elteres is None


def kimenet_neve(bemenet: Path, kimenet_mappa: Path) -> Path:
    """input_001.txt → KIMENET_MAPPA/output_001.txt; más nevű fájl elé output_ kerül."""
    nev = bemenet.name
    if nev.startswith(BEMENET_ELOTAG):
        nev = nev[len(BEMENET_ELOTAG):]
    return kimenet_mappa / (KIMENET_ELOTAG + nev)


def _rendezo_kulcs(fajl: Path) -> tuple[int, str]:
    talalat = SORSZAM_MINTA.match(fajl.name)
    return (int(talalat.group(1)) if talalat else sys.maxsize, fajl.name)


def bemenetek(mappa: Path, minta: str) -> list[Path]:
    """A minta szerinti fájlok, sorszám szerint rendezve (input_2 < input_10)."""
    return sorted((f for f in mappa.glob(minta) if f.is_file()), key=_rendezo_kulcs)


def hianyzo_sorszamok(fajlok: list[Path]) -> list[int]:
    """A sorszámozott bemenetek kihagyás nélkül követik egymást – ha nem, a hiányzók."""
    szamok = {int(t.group(1)) for f in fajlok if (t := SORSZAM_MINTA.match(f.name))}
    if not szamok:
        return []
    return sorted(set(range(min(szamok), max(szamok) + 1)) - szamok)


def beepitett_futtato() -> Futtato:
    """A robot -q módja ugyanebben a folyamatban (konzolra kiírás nélkül)."""
    sys.path.insert(0, str(ROBOT_MAPPA))
    from main import csendes_futtatas  # a robot/main.py

    def futtat(be: Path, ki: Path) -> None:
        csendes_futtatas(be, ki, kiiras=False)

    return futtat


def kulso_futtato(robot: Path, idokorlat: float) -> Futtato:
    """Minden fájl külön "robot -q BE KI" hívással; .py esetén a mostani Pythonnal."""
    parancs = [sys.executable, str(robot)] if robot.suffix == ".py" else [str(robot)]

    def futtat(be: Path, ki: Path) -> None:
        folyamat = subprocess.run(
            [*parancs, "-q", str(be), str(ki)],
            capture_output=True, text=True, errors="replace", timeout=idokorlat,
        )
        if folyamat.returncode != 0:
            uzenet = (folyamat.stderr or folyamat.stdout).strip().splitlines()
            raise RuntimeError(f"kilépési kód {folyamat.returncode}"
                               + (f": {uzenet[-1]}" if uzenet else ""))

    return futtat


def naplo_hiba(kimenet: Path) -> str | None:
    """Formai ellenőrzés: létezik, és EOR vagy limit-túllépés a vége."""
    if not kimenet.is_file():
        return "nem jött létre a kimeneti fájl"
    sorok = kimenet.read_text(encoding="utf-8", errors="replace").splitlines()
    if not sorok or sorok[-1] not in NAPLO_VEGEK:
        return "a napló nem EOR / INSTRUCTION_COUNT_LIMIT_EXCEEDED sorral zárul"
    return None


def elteres(kimenet: Path, elvart: Path) -> str | None:
    """Az első eltérő sor leírása, vagy None, ha a két napló egyezik."""
    if not elvart.is_file():
        return None
    kapott = kimenet.read_text(encoding="utf-8").splitlines()
    vart = elvart.read_text(encoding="utf-8-sig").splitlines()
    for i, (k, v) in enumerate(zip(kapott, vart), start=1):
        if k != v:
            return f"{i}. sor: kapott {k!r}, elvárt {v!r}"
    if len(kapott) != len(vart):
        return f"sorok száma: kapott {len(kapott)}, elvárt {len(vart)}"
    return None


def egy_fajl(futtato: Futtato, bemenet: Path, kimenet_mappa: Path,
             elvart_mappa: Path | None) -> Eredmeny:
    eredmeny = Eredmeny(bemenet, kimenet_neve(bemenet, kimenet_mappa))
    try:
        futtato(bemenet, eredmeny.kimenet)
    except Exception as hiba:  # egy rossz fájl ne állítsa meg a többit
        eredmeny.hiba = f"{type(hiba).__name__}: {hiba}"
        return eredmeny
    eredmeny.hiba = naplo_hiba(eredmeny.kimenet)
    if eredmeny.hiba is None and elvart_mappa is not None:
        eredmeny.elteres = elteres(eredmeny.kimenet, elvart_mappa / eredmeny.kimenet.name)
    return eredmeny


def zip_keszit(eredmenyek: list[Eredmeny], cel: Path) -> None:
    """results.zip: a kimeneti fájlok a zip gyökerében, almappa nélkül."""
    with zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED) as zf:
        for e in eredmenyek:
            if e.kimenet.is_file():
                zf.write(e.kimenet, arcname=e.kimenet.name)


def argumentumok(parameterek: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Robotszimulátor: input_NNN.txt fájlok tömeges futtatása.")
    p.add_argument("bemenet", type=Path, help="a mappa, ahol az input fájlok vannak")
    p.add_argument("kimenet", type=Path, help="ide kerülnek az output fájlok (létrehozza)")
    p.add_argument("--minta", default=BEMENET_ELOTAG + "*.txt",
                   help="a bemeneti fájlok mintája (alap: input_*.txt)")
    p.add_argument("--robot", type=Path,
                   help="robot.exe vagy main.py: fájlonként külön folyamatban fut")
    p.add_argument("-j", "--szalak", type=int, default=4,
                   help="párhuzamos folyamatok száma --robot esetén (alap: 4)")
    p.add_argument("--idokorlat", type=float, default=30.0,
                   help="egy fájl időkorlátja másodpercben --robot esetén (alap: 30)")
    p.add_argument("--elvart", type=Path,
                   help="mappa az elvárt output_NNN.txt fájlokkal az összevetéshez")
    p.add_argument("--zip", action="store_true",
                   help="results.zip készítése a kimeneti mappában")
    p.add_argument("-v", "--reszletes", action="store_true",
                   help="minden fájl eredményét kiírja, nem csak a hibásakat")
    return p.parse_args(parameterek)


def main(parameterek: list[str] | None = None) -> int:
    args = argumentumok(parameterek)
    if not args.bemenet.is_dir():
        print(f"Nincs ilyen bemeneti mappa: {args.bemenet}", file=sys.stderr)
        return 2
    fajlok = bemenetek(args.bemenet, args.minta)
    if not fajlok:
        print(f"Nincs {args.minta} fájl itt: {args.bemenet}", file=sys.stderr)
        return 2
    if hianyzok := hianyzo_sorszamok(fajlok):
        print(f"FIGYELEM: hiányzó sorszámok: {', '.join(map(str, hianyzok))}",
              file=sys.stderr)
    args.kimenet.mkdir(parents=True, exist_ok=True)

    if args.robot is not None:
        if not args.robot.is_file():
            print(f"Nincs ilyen robot: {args.robot}", file=sys.stderr)
            return 2
        futtato = kulso_futtato(args.robot.resolve(), args.idokorlat)
        szalak = max(1, args.szalak)
    else:
        futtato = beepitett_futtato()
        szalak = 1  # a beépített futtató gyors, és így nem kell szálbiztosnak lennie

    kezdet = time.perf_counter()
    with ThreadPoolExecutor(max_workers=szalak) as vegrehajto:
        eredmenyek = list(vegrehajto.map(
            lambda f: egy_fajl(futtato, f, args.kimenet, args.elvart), fajlok))
    eltelt = time.perf_counter() - kezdet

    for e in eredmenyek:
        if e.hiba:
            print(f"HIBA    {e.bemenet.name}: {e.hiba}")
        elif e.elteres:
            print(f"ELTÉR   {e.bemenet.name}: {e.elteres}")
        elif args.reszletes:
            print(f"OK      {e.bemenet.name} → {e.kimenet.name}")

    if args.zip:
        cel = args.kimenet / "results.zip"
        zip_keszit(eredmenyek, cel)
        print(f"results.zip elkészült: {cel}")

    hibas = sum(1 for e in eredmenyek if e.hiba)
    eltero = sum(1 for e in eredmenyek if e.elteres)
    osszegzes = f"Kész: {len(eredmenyek)} fájl {eltelt:.2f} mp alatt, {hibas} hibás"
    if args.elvart is not None:
        osszegzes += f", {eltero} eltér az elvárttól"
    print(osszegzes + f". Kimenet: {args.kimenet}")
    return 0 if all(e.rendben for e in eredmenyek) else 1


if __name__ == "__main__":
    sys.exit(main())
