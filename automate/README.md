# Automatizálás

Verseny tesztek tömeges futtatása és teszt bemenetek generálása a `robot` programhoz.
A parancsokat a projekt gyökeréből kell futtatni.

## Futtatás: `futtat.py`

```
python automate/futtat.py BEMENET_MAPPA KIMENET_MAPPA [kapcsolók]
```

A `BEMENET_MAPPA` minden `input_NNN.txt` fájljából egy `KIMENET_MAPPA/output_NNN.txt` napló lesz.

| Kapcsoló | Jelentés |
|---|---|
| `--zip` | `results.zip` a kimeneti mappában (a naplók a zip gyökerében) |
| `--robot ÚTVONAL` | `robot.exe` vagy `main.py` futtatása fájlonként külön `-q` hívással |
| `-j N` | párhuzamos folyamatok `--robot` esetén (alap: 4) |
| `--idokorlat MP` | egy fájl időkorlátja `--robot` esetén (alap: 30) |
| `--elvart MAPPA` | a naplók összevetése elvárt `output_NNN.txt` fájlokkal |
| `--minta GLOB` | más fájlnév-minta (alap: `input_*.txt`) |
| `-v` | minden fájl eredményének kiírása |

`--robot` nélkül a robot kódja ugyanebben a folyamatban fut, ez a leggyorsabb mód.
A script ellenőrzi, hogy minden napló `EOR` vagy `INSTRUCTION_COUNT_LIMIT_EXCEEDED` sorral zárul-e,
és figyelmeztet, ha hiányzik egy sorszám. Ha minden rendben van, a kilépési kód 0.

Példák:
```
python automate/futtat.py automate/teszt kimenet --zip
python automate/futtat.py robot/peldak kimenet --elvart robot/peldak
python automate/futtat.py automate/teszt kimenet2 --robot robot/dist/robot.exe --elvart kimenet
```

## Teszt bemenetek: `teszt_generalo.py`

```
python automate/teszt_generalo.py [CÉLMAPPA] [--veletlen 30] [--mag 2026]
python automate/futtat.py automate/teszt kimenet --elvart automate/teszt/elvart
```

Alapból az `automate/teszt` mappába ír. Az esetek azokat a pontokat célozzák, ahol egy megvalósítás
nagy eséllyel hibázik:
- sorvégek: CRLF, BOM, hiányzó záró újsor;
- behúzás: eltérő mértékű behúzások, több szint egyszerre záródik, melyik `if`-hez tartozik az `else`;
- kulcsszóval kezdődő azonosítók (`iffy`, `tox`, `notfal`);
- a kiértékelés sorrendje és az első hiba (`true + c` vagy `c + true`);
- negatív és logikai API-paraméterek, és a naplóformátum hiba esetén;
- utasításlimit pontosan az 1000. és az 1001. sornál;
- forgásirány, a bányászott mező és a kiinduló mező állapota.

Ezek után jönnek a véletlenszerű, mélyen egymásba ágyazott programok.

Az elvárt naplókat (`teszt/elvart/`) a `referencia.py` állítja elő. Ez a PDF alapján, a `robot` kódjától
függetlenül írt értelmező, így ha a két megvalósítás eltér, az valamelyikük hibáját jelzi.
Az egyes esetek leírása a `teszt/README.md` fájlban van.
