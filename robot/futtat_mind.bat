@echo off
rem Verseny tesztek futtatasa: minden input_NNN.txt -> output_NNN.txt, majd results.zip
rem Hasznalat:  futtat_mind.bat [mappa] [egyenkent]
rem   mappa      : ahol az input fajlok vannak (alapertelmezes: az aktualis mappa)
rem   egyenkent  : minden fajlt kulon "robot.exe -q BE KI" hivassal futtat (lassabb);
rem                enelkul egyetlen "robot.exe -m MAPPA" hivas fut (200+ fajl par masodperc)
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROBOT=%~dp0robot.exe"
if not exist "%ROBOT%" set "ROBOT=%~dp0dist\robot.exe"
if not exist "%ROBOT%" (
    echo Nem talalhato a robot.exe, a python main.py fut helyette.
    set "ROBOT=python "%~dp0main.py""
)

set "MAPPA=%~1"
if "%MAPPA%"=="" set "MAPPA=."
pushd "%MAPPA%"

if /i "%~2"=="egyenkent" (
    set /a DARAB=0
    for %%F in (input_*.txt) do (
        set "NEV=%%~nF"
        set "AZON=!NEV:input_=!"
        %ROBOT% -q "%%F" "output_!AZON!.txt" >nul
        set /a DARAB+=1
    )
    echo Kesz: !DARAB! fajl lefuttatva.
) else (
    %ROBOT% -m .
)

if exist results.zip del results.zip
powershell -NoProfile -Command "Compress-Archive -Path 'output_*.txt' -DestinationPath 'results.zip'" && echo results.zip elkeszult: %CD%\results.zip

popd
endlocal
