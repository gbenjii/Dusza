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
- Minden szabályra és naplózási határesetre unittest készült (`python -m unittest discover -s tesztek -t .`, 73 teszt).
- A feladat példáját és a bemutatóprogramot kézzel is végigszámoltuk, és összevetettük a naplóval.
- A `-q` módot 200 bemeneti fájllal futtattuk (`futtat_mind.bat`), és mértük az időt.
- Az IDE-t kézzel kipróbáltuk: beszúrás, törlés, mélységkorlát, hibás azonosító, futtatás, nyomkövetés, kézi vezérlés.
- *Kódátnézés: ki, mikor, mit javított.*

## 5 konkrét eset
1. **Hibás tesztprogramok javítása.** Az MI eleinte `while i < 499` alakú teszteket írt, de ez nem helyes MineScript (a feltétel csak egyetlen V lehet). A tesztek elbuktak, ebből derült ki. Javítás: segédváltozó (`set c to i < N`, `while c`).
2. **Utasításkorlát.** Ellenőriztük, hogy pontosan 1000 sornál még `EOR` jön, 1001-nél pedig `INSTRUCTION_COUNT_LIMIT_EXCEEDED`, és utána nincs `EOR`. Erre külön tesztek vannak (3n+4 soros ciklussal).
3. **Logikai típus Pythonban.** A `bool` az `int` alosztálya, ezért `isinstance` helyett `type(x) is int` kell. Enélkül a `turn by true` nem adna `E_BAD_ARG` hibát.
4. **Kiértékelési sorrend.** `true or c` nem rövidzáras, ezért `E_UNINITIALIZED` a helyes eredmény. Az `=` és `<>` csak a 2. operandus után ellenőrzi a típusokat. Ezeket tesztekkel rögzítettük.
5. **GUI-indítási hiba.** A blokkszerkesztő egy belső mezője (`_kovetkezo_y`) a fájlbetöltéskor még nem létezett. A füstteszt (smoke test) mutatta ki, javítás: inicializálás a konstruktorban.

*(Cseréljétek a saját tapasztalataitokra, ha eltérnek.)*
