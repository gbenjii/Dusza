# Teszt bemenetek

Előállította: `automate/teszt_generalo.py` (mag: 2026, véletlen esetek: 30).
Az elvárt naplók az `elvart` mappában vannak (`automate/referencia.py`).

| Fájl | Leírás |
|---|---|
| input_001.txt | CRLF sorvégek (Windowson készült fájl) |
| input_002.txt | CRLF sorvégek, az utolsó sor végén nincs újsor |
| input_003.txt | UTF-8 BOM a fájl elején + CRLF |
| input_004.txt | Üres program, a térkép utolsó sora után nincs újsor |
| input_005.txt | Üres program CRLF-fel |
| input_006.txt | A program utolsó sora (while törzse) után nincs újsor |
| input_007.txt | Kulcsszóval kezdődő azonosítók (iffy, tox, notfal, ortho, andy, printer...) |
| input_008.txt | Számjegyet tartalmazó azonosítók, kis-nagybetű (a1b2, Z9, count/Count) |
| input_009.txt | Vezető nullás számok (007, 093, 00) – értékük 7, 93, 0 |
| input_010.txt | Az else a külső if-hez tartozik (azonos behúzás), a belső if-nek nincs else-e |
| input_011.txt | Két egymás utáni if: az else a másodikhoz tartozik |
| input_012.txt | Több szint egyszerre záródik (3 szint → 0), else minden szinten |
| input_013.txt | Blokkonként eltérő behúzás (1, 4 és 7 szóköz) |
| input_014.txt | Három while egymásban, mindegyik többször fut |
| input_015.txt | Az else ág a beágyazott ciklus után, a törzs végén újabb if |
| input_016.txt | while hamis feltétellel, utána rögtön else nélküli if |
| input_017.txt | true + c: az első operandus rossz típusa előbb derül ki → E_BAD_OPERAND |
| input_018.txt | c + true: az első operandus nincs inicializálva → E_UNINITIALIZED |
| input_019.txt | true = c: az = első operandusa bármilyen típusú, a második nincs → E_UNINITIALIZED |
| input_020.txt | c = 1: nem inicializált első operandus → E_UNINITIALIZED |
| input_021.txt | 1 = true: típuseltérés a második operandus után → E_BAD_OPERAND |
| input_022.txt | true and 5: a második operandus nem logikai → E_BAD_OPERAND |
| input_023.txt | 5 or c: az első operandus rossz, a c-t már nem kell vizsgálni → E_BAD_OPERAND |
| input_024.txt | false < 3 → E_BAD_OPERAND |
| input_025.txt | 3 >= true → E_BAD_OPERAND |
| input_026.txt | not c → E_UNINITIALIZED |
| input_027.txt | set x to x + 1, ha x még nem létezik → E_UNINITIALIZED |
| input_028.txt | Sikertelen értékadás után a futás leáll (nincs további sor) |
| input_029.txt | E_TYPE_MISMATCH: egészbe összehasonlítás eredménye |
| input_030.txt | E_TYPE_MISMATCH isThere után: az API-hívás is a naplóba kerül a hiba előtt |
| input_031.txt | Logikai változó újraírása logikaival rendben, egészzel nem |
| input_032.txt | Nagy és negatív egészek (a 0..100 csak a forráskódra vonatkozik) |
| input_033.txt | Egyenlőség logikaiakkal és egészekkel, határ-összehasonlítások |
| input_034.txt | turn by negatív érték (változóból) → E_BAD_ARG, a napló a kiértékelt értéket mutatja |
| input_035.txt | step forward negatív érték → E_BAD_ARG |
| input_036.txt | step forward logikai változóval → E_BAD_ARG |
| input_037.txt | isThere változóból kapott 3-mal → E_BAD_ARG |
| input_038.txt | isThere true → E_BAD_ARG |
| input_039.txt | isThere nem inicializált változóval → isThere E_UNINITIALIZED |
| input_040.txt | turn by nem inicializált változóval |
| input_041.txt | print nem inicializált változóval |
| input_042.txt | isThere negatív értékkel |
| input_043.txt | print logikai literál és isThere minden kódra |
| input_044.txt | Forgás iránya: balra (óramutatóval ellentétesen), sarokban, minden irány |
| input_045.txt | A bányászott mező üres lesz (isThere 0 igaz, isThere 2 hamis), újra bányászva E_NO_GOLD |
| input_046.txt | A robot kiinduló mezője üres kamra lesz, amikor elhagyja |
| input_047.txt | step forward pontosan a térkép széléig rendben, step forward 0 falnál rendben |
| input_048.txt | step forward 14 egy 1x15-ös sávon: az átlépett rögök megmaradnak |
| input_049.txt | 15x1-es függőleges térkép, dél felé haladva bányászik a széléig |
| input_050.txt | step forward 100 kis térképen → E_BEDROCK_HIT |
| input_051.txt | Falba ütközés a lépés közepén aranyon át |
| input_052.txt | Bányászás a kiinduló mezőn → E_NO_GOLD |
| input_053.txt | A feladat bányász programja (a sor végén két rög a szélen) |
| input_054.txt | Labirintus 15x15: bal kézi falkövetés (a limitig fut) |
| input_055.txt | while egész feltétellel → E_NON_BOOL_CONDITION a while sorában |
| input_056.txt | if nem inicializált feltétellel |
| input_057.txt | Hiba a while törzsében: logikai + egész → E_BAD_OPERAND |
| input_058.txt | Pontosan 1000 végrehajtott sor, az 1000. sor hibás → hiba + EOR |
| input_059.txt | Az 1001. sor hibás lenne → INSTRUCTION_COUNT_LIMIT_EXCEEDED, nincs hibakód |
| input_060.txt | Az 1000. sor egy hamis if, az else lenne az 1001. → limit |
| input_061.txt | Az 1000. sor a while utolsó (hamis) feltétel-kiértékelése → EOR |
| input_062.txt | Az 1000. sor egy igaz if, a törzse lenne az 1001. → limit |
| input_063.txt | Végtelen ciklus üres hatású törzzsel |
| input_064.txt | Véletlen #1 (hibaesély 0%) |
| input_065.txt | Véletlen #2 (hibaesély 0%) |
| input_066.txt | Véletlen #3 (hibaesély 3%) |
| input_067.txt | Véletlen #4 (hibaesély 3%) |
| input_068.txt | Véletlen #5 (hibaesély 0%) |
| input_069.txt | Véletlen #6 (hibaesély 3%) |
| input_070.txt | Véletlen #7 (hibaesély 0%) |
| input_071.txt | Véletlen #8 (hibaesély 0%) |
| input_072.txt | Véletlen #9 (hibaesély 0%) |
| input_073.txt | Véletlen #10 (hibaesély 10%) |
| input_074.txt | Véletlen #11 (hibaesély 0%) |
| input_075.txt | Véletlen #12 (hibaesély 10%) |
| input_076.txt | Véletlen #13 (hibaesély 0%) |
| input_077.txt | Véletlen #14 (hibaesély 3%) |
| input_078.txt | Véletlen #15 (hibaesély 10%) |
| input_079.txt | Véletlen #16 (hibaesély 10%) |
| input_080.txt | Véletlen #17 (hibaesély 0%) |
| input_081.txt | Véletlen #18 (hibaesély 0%) |
| input_082.txt | Véletlen #19 (hibaesély 0%) |
| input_083.txt | Véletlen #20 (hibaesély 3%) |
| input_084.txt | Véletlen #21 (hibaesély 3%) |
| input_085.txt | Véletlen #22 (hibaesély 0%) |
| input_086.txt | Véletlen #23 (hibaesély 3%) |
| input_087.txt | Véletlen #24 (hibaesély 10%) |
| input_088.txt | Véletlen #25 (hibaesély 0%) |
| input_089.txt | Véletlen #26 (hibaesély 3%) |
| input_090.txt | Véletlen #27 (hibaesély 3%) |
| input_091.txt | Véletlen #28 (hibaesély 0%) |
| input_092.txt | Véletlen #29 (hibaesély 0%) |
| input_093.txt | Véletlen #30 (hibaesély 3%) |
