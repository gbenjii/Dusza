# MI-eszközök használata

> Sablon: a *dőlt* részeket a csapat töltse ki a valós adatokkal.

## Eszközök, modellek, verziók
| Eszköz | Modell / verzió | Mire használtuk |
|---|---|---|
| Claude Code (asztali alkalmazás) | Claude Opus 5.5 (`claude-opus-5-5`) | kódgenerálás, tesztek, dokumentáció |
| *további eszköz* | *modell, verzió* | *pl. ötletelés, hibakeresés* |

## Mire és kb. hány %-ban
| Rész | MI aránya (becslés) | Megjegyzés |
|---|---|---|
| Értelmező, futtató, napló (1. fázis) | *…%* | *pl. a vázat az MI írta, a határeseteket mi pontosítottuk* |
| Unittest tesztek | *…%* | |
| IDE / tkinter felület (2. fázis) | *…%* | |
| Exe, batch, dokumentáció (3. fázis) | *…%* | |
| **Összesen** | *…%* | |

## Hogyan ellenőriztük
- Minden szabályra és naplózási határesetre unittest készült (`python -m unittest discover -s tesztek -t .`, 106 teszt).
- A feladat példáját és a bemutatóprogramot kézzel is végigszámoltuk, és összevetettük a naplóval.
- A teljes feladatleírást (PDF) pontról pontra összevetettük a programmal, a videó forgatókönyvét is.
- A `-q` és a `-m` módot 200 bemeneti fájllal futtattuk (`futtat_mind.bat`), és mértük az időt.
- Az IDE-hez szkriptelt füsttesztet írtunk (nyomkövetés, élő napló, töréspont, kézi vezérlés,
  térképszerkesztés, példák), és képernyőképeken ellenőriztük a megjelenést.
- A felületet a customtkinter két verziójával (5.2.2 és 6.0.0) is kipróbáltuk.
- *Kódátnézés: ki, mikor, mit javított.*

## 5 konkrét eset
1. **Utasításkorlát.** Ellenőriztük, hogy pontosan 1000 sornál még `EOR` jön, 1001-nél pedig `INSTRUCTION_COUNT_LIMIT_EXCEEDED`, és utána nincs `EOR`. Erre külön tesztek vannak (3n+4 soros ciklussal).
2. **Logikai típus Pythonban.** A `bool` az `int` alosztálya, ezért `isinstance` helyett `type(x) is int` kell. Enélkül a `turn by true` nem adna `E_BAD_ARG` hibát.
3. **Kiértékelési sorrend.** `true or c` nem rövidzáras, ezért `E_UNINITIALIZED` a helyes eredmény. Az `=` és `<>` csak a 2. operandus után ellenőrzi a típusokat. Ezeket tesztekkel rögzítettük.
4. **Élő napló a videóhoz.** Az első változat csak a futás végén írta ki a naplót. A PDF újraolvasásakor derült ki, hogy a videóban nyomkövetés *közben* is meg kell nyitni a naplófájlt. Javítás: a napló soronként íródik a fájlba (flush), erre külön teszt is van.
5. **Tömeges futtatás gyorsítása.** A 200 fájl egyenkénti `-q` futtatása 5,5 percig tartott, mert az egyfájlos exe minden indításkor kicsomagolja magát. Az MI javaslatára készült a `-m MAPPA` mód (egy folyamat, minden fájl), így 7 másodperc lett. A kimeneteket bájtra összevetettük az egyenkénti futtatáséval.

*(A PDF pontosan 5 esetet kér. Cseréljétek a saját tapasztalataitokra, ha eltérnek – pl. Dániel customtkinteres felületének egy esetére.)*
