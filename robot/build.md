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
python main.py -m MAPPA     – a mappa minden input_NNN.txt fájlja → output_NNN.txt, egy menetben
python main.py              – IDE üres programmal (napló: naplo.txt)
```

## Tesztek
```
python -m unittest discover -s tesztek -t .
```
Eredmény: `Ran 106 tests ... OK`

## Az exe elkészítése
```
python -m PyInstaller --clean --noconfirm robot.spec
```
- A `robot.spec` a customtkinter téma- és betűfájljait is becsomagolja
  (enélkül az exe indításkor hibát adna). Kézzel ugyanez:
  `python -m PyInstaller --onefile --name robot --collect-data customtkinter main.py`
- Eredmény: `dist\robot.exe` (egyetlen fájl, kb. 12 MB). Másold a `robot` mappába is
  (`copy /y dist\robot.exe robot.exe`), mert a `futtat_mind.bat` először ott keresi.
- Ellenőrizve customtkinter 5.2.2-vel és 6.0.0-val is; a beadott exe 6.0.0-val készült.
- Konzolos exe készül (nincs `--noconsole`), hogy a `-q` módban a `print` kimenet látható legyen.
- A `futtat_mind.bat` először a saját mappájában, aztán a `dist` mappában keresi a `robot.exe`-t; ha nincs meg, a `python main.py`-t használja.

## Tömeges futtatás (verseny tesztek)
```
futtat_mind.bat MAPPA              – gyors: egyetlen „robot.exe -m MAPPA” hívás
futtat_mind.bat MAPPA egyenkent    – minden fájl külön „robot.exe -q BE KI” hívással
```
A mappa minden `input_NNN.txt` fájljából `output_NNN.txt` lesz, végül a kimenetekből
`results.zip` készül (a fájlok a zip gyökerében, ahogy a beadás kéri).
Mért idő (200 fájl, `robot.exe`): **7 s** a `-m` móddal, kb. 5,5 perc egyenként (ott fájlonként
kb. 1,6 s az egyfájlos exe kicsomagolása). Egy hibás bemenet nem állítja meg a többit.

## Mappaszerkezet
```
main.py               parancssor, -q mód / IDE indítása
beolvaso.py           bemeneti fájl → térkép + programsorok (és vissza, mentéshez)
terkep.py             Mezo, Irany, Robot, Terkep, Vilag (Robot API, felfedezés, szenzor)
hibak.py              hibakódok és magyar leírásaik
naplo.py              naplósorok és a naplófájl (élő írás: futás közben soronként)
peldaprogramok.py     a Példák menü beépített térképei és programjai
futtato.py            soronkénti végrehajtás generátorral; előjelzés (SorElott) a töréspontokhoz
nyelv/tokenizalo.py   tokenizálás a 2.1 pont szerint: behúzás, tokenek fajtával (kulcsszó, azonosító, szám, logikai, operátor)
nyelv/utasitasok.py   az utasításfa dataclass-ai
nyelv/elemzo.py       sorok → utasításfa
nyelv/kiiro.py        utasításfa → szöveg, sorszámozás
nyelv/ellenorzo.py    azonosító- és értékellenőrzés (szerkesztőhöz)
nyelv/szerkesztes.py  beszúrás, áthelyezés (húzás), törlés, else-ág, mélységkorlát (GUI nélkül, tesztelhető)
gui/                  foablak (futtatás, töréspontok, fájlok, példák), blokkszerkeszto (paletta,
                      húzás, mezők), kodnezet (színezés, töréspontok), szimulator_nezet
                      (animáció, térképszerkesztő), stilus (betűtípusok, színek), tooltip
tesztek/              unittest tesztek
peldak/               példa bemenetek (001: a feladat példája, 002: bemutató, 003: limit)
input_video.txt       a bemutató térképe üres programmal
```
