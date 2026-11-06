# Fordítás és futtatás

## Platform
- Fejlesztve és tesztelve: **Windows 10 Pro (64 bit)**
- **Python 3.13.7** (legalább 3.11 kell a `match` és az `X | Y` típusjelölés miatt)
- Linuxon is kipróbálva (Ubuntu, Python 3.13, X11)
- Felület: **customtkinter 6.0.0** (a `tkinter`-re épül), tesztek: `unittest`
- A `-q` (csendes) mód csak a standard könyvtárat használja, customtkinter nélkül is fut
- Exe készítéséhez: **PyInstaller 6.15.0**

## Telepítés
1. Python telepítése a python.org-ról (a telepítőben legyen bepipálva a „tcl/tk and IDLE” és az „Add python.exe to PATH”).
2. A customtkinter és a PyInstaller telepítése:
   ```
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller==6.15.0
   ```
   Linuxon (rendszer-Pythonnál): `python3 -m pip install --user customtkinter`,
   valamint a `python3-tk` csomag kell.

## Linux: betűtípusok és a uv
A felület csak akkor néz ki jól Linuxon, ha a Python Tk-ja **Xft**-vel készült,
mert csak így látja a rendszer betűtípusait (DejaVu, Noto, Ubuntu).
- A rendszer Pythonja (`/usr/bin/python3` + `python3-tk` csomag): Tk 8.6, xft – **jó**.
- A uv által letöltött Python (python-build-standalone): Tk 9.0, Xft nélkül – csak
  régi X11-betűk, élsimítás nélkül, egyes jelek helyén négyzet. Ilyenkor a program
  a legjobb X11-betűre vált, és figyelmeztet az állapotsorban.

Ezért a `Dusza/pyproject.toml` beállítása `python-preference = "only-system"`, és a
`.python-version` értéke `3.13`. Így a uv a gépre telepített Pythonból készíti a `.venv`-et:
```
uv sync
uv run python program/robot/main.py program/robot/input_video.txt output_video.txt
```
Ellenőrzés: `uv run python -c "import tkinter as t; print(t.Tk().tk.call('::tk::pkgconfig','get','fontsystem'))"` → `xft`.
Windowson ez a gond nem jelentkezik, ott a Tk a Windows saját betűkezelését használja.

## Futtatás forrásból (a `robot` mappában)
```
python main.py BE KI        – IDE, BE betöltése, napló: KI
python main.py -q BE KI     – felület nélkül: futtatás, napló KI-be, kilépés
python main.py              – IDE üres programmal (napló: naplo.txt)
```

## Tesztek
```
python -m unittest discover -s tesztek -t .
```
Eredmény: `Ran 87 tests ... OK`

## Az exe elkészítése
```
python -m PyInstaller --clean --noconfirm robot.spec
```
- A `robot.spec` a customtkinter téma- és betűfájljait is becsomagolja
  (enélkül az exe indításkor hibát adna). Kézzel ugyanez:
  `python -m PyInstaller --onefile --name robot --collect-data customtkinter main.py`
- Eredmény: `dist\robot.exe` (egyetlen fájl, kb. 11 MB).
- Konzolos exe készül (nincs `--noconsole`), hogy a `-q` módban a `print` kimenet látható legyen.
- A `futtat_mind.bat` először a saját mappájában, aztán a `dist` mappában keresi a `robot.exe`-t; ha nincs meg, a `python main.py`-t használja.

## Tömeges futtatás
```
futtat_mind.bat [mappa]
```
A mappában (alapértelmezés: az aktuális mappa) minden `input_NNN.txt` fájlból `output_NNN.txt` lesz.
Mért idő: 200 fájl kb. 5,5 perc alatt fut le `robot.exe`-vel. Fájlonként kb. 1,6 s, ennek nagy része az egyfájlos exe kicsomagolása.
`python main.py`-jal kb. 0,15 s egy fájl.

## Mappaszerkezet
```
main.py               parancssor, -q mód / IDE indítása
beolvaso.py           bemeneti fájl → térkép + programsorok (és vissza, mentéshez)
terkep.py             Mezo, Irany, Robot, Terkep, Vilag (Robot API, felfedezés, szenzor)
hibak.py              hibakódok és magyar leírásaik
naplo.py              naplósorok és a naplófájl
futtato.py            soronkénti végrehajtás generátorral (a -q, az animáció és a nyomkövetés is erre épül)
nyelv/tokenizalo.py   tokenizálás a 2.1 pont szerint: behúzás, tokenek fajtával (kulcsszó, azonosító, szám, logikai, operátor)
nyelv/utasitasok.py   az utasításfa dataclass-ai
nyelv/elemzo.py       sorok → utasításfa
nyelv/kiiro.py        utasításfa → szöveg, sorszámozás
nyelv/ellenorzo.py    azonosító- és értékellenőrzés (szerkesztőhöz)
nyelv/szerkesztes.py  beszúrás, áthelyezés (húzás), törlés, else-ág, mélységkorlát (GUI nélkül, tesztelhető)
gui/                  foablak, blokkszerkeszto (paletta, húzás, mezők), kodnezet, szimulator_nezet,
                      stilus (betűtípusok, színek), tooltip
tesztek/              unittest tesztek
peldak/               példa bemenetek (001: a feladat példája, 002: bemutató, 003: limit)
input_video.txt       a bemutató térképe üres programmal
```
