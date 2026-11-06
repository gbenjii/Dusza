@echo off
rem Minden input_NNN.txt fajlra lefuttatja a robotot -q modban: input_NNN.txt -> output_NNN.txt
rem Hasznalat: futtat_mind.bat [mappa]   (alapertelmezes: az aktualis mappa)
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

set /a DARAB=0
for %%F in (input_*.txt) do (
    set "NEV=%%~nF"
    set "AZON=!NEV:input_=!"
    %ROBOT% -q "%%F" "output_!AZON!.txt" >nul
    set /a DARAB+=1
)

popd
echo Kesz: !DARAB! fajl lefuttatva.
endlocal
