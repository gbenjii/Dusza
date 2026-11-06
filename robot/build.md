# Fordítás és futtatás

## Platform
- Fejlesztve és tesztelve: **Windows 10 Pro (64 bit)**
- **Python 3.13.7** (legalább 3.11 kell a `match` és az `X | Y` típusjelölés miatt)
- Csak a standard könyvtárat használja: `tkinter` (felület), `unittest` (tesztek)
- Exe készítéséhez: **PyInstaller 6.15.0**

## Telepítés
1. Python telepítése a python.org-ról (a telepítőben legyen bepipálva a „tcl/tk and IDLE” és az „Add python.exe to PATH”).
2. PyInstaller telepítése:
   ```
   python -m pip install pyinstaller==6.15.0
   ```

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
Eredmény: `Ran 73 tests ... OK`

## Az exe elkészítése
```
python -m PyInstaller --onefile --name robot --clean --noconfirm main.py
```
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
nyelv/tokenizalo.py   behúzás + tokenek, kulcsszavak
nyelv/utasitasok.py   az utasításfa dataclass-ai
nyelv/elemzo.py       sorok → utasításfa
nyelv/kiiro.py        utasításfa → szöveg, sorszámozás
nyelv/ellenorzo.py    azonosító- és értékellenőrzés (szerkesztőhöz)
nyelv/szerkesztes.py  beszúrás, törlés, mélységkorlát (GUI nélkül, tesztelhető)
gui/                  foablak, blokkszerkeszto, tulajdonsag_panel, kodnezet, szimulator_nezet, tooltip
tesztek/              unittest tesztek
peldak/               példa bemenetek (001: a feladat példája, 002: bemutató, 003: limit)
input_video.txt       a bemutató térképe üres programmal
```
