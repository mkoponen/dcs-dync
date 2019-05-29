@echo OFF
setlocal ENABLEEXTENSIONS
set KEY_NAME="HKEY_CURRENT_USER\Software\Eagle Dynamics\DCS World OpenBeta"
set VALUE_NAME=Path
set DCS_FOUND=0

FOR /F "usebackq skip=2 tokens=3*" %%A IN (`REG QUERY %KEY_NAME% /v %VALUE_NAME% 2^>nul`) DO (
    set PathBeta=%%A %%B
)

if defined PathBeta (
    @echo OpenBeta is installed at %PathBeta%
	set DCS_FOUND=1
) else (
    goto :nobeta
)
if "%PathBeta:~-1%" == " " (
	set PathBeta=%PathBeta:~0,-1%
)

FINDSTR /C:"dync = {}" "%PathBeta%\Scripts\MissionScripting.lua" 1>nul 2>nul

If "%errorlevel%" == "1" (
	@echo Must add lines to MissionScripting.lua
) else (
	@echo Your MissionScripting.lua is already correct, not doing anything.
	goto :dyncexistsdebug
)

FOR /F "usebackq tokens=1 delims=:" %%A IN (`FINDSTR /N /C:"dofile('Scripts/ScriptingSystem.lua')" "%PathBeta%\Scripts\MissionScripting.lua" 2^>nul`) DO (
	set /A LineNumber = %%A + 1
)
del /Q "%PathBeta%\Scripts\MissionScripting-backup.lua" 1>nul 2>nul
rename "%PathBeta%\Scripts\MissionScripting.lua" MissionScripting-backup.lua

set Output="%PathBeta%\Scripts\MissionScripting.lua"

(for /f "tokens=1* delims=[]" %%a in ('find /n /v "##" ^< "%PathBeta%\Scripts\MissionScripting-backup.lua"') do (
if "%%~a"=="%LineNumber%" (
echo dync = {}
echo dofile^(lfs.writedir^(^).."\\Scripts\\DynC.lua"^)
echo.
ECHO.%%b
) ELSE (
echo.%%b
)
)) > %Output%


:dyncexistsdebug
:nobeta

set KEY_NAME="HKEY_CURRENT_USER\Software\Eagle Dynamics\DCS World"

FOR /F "usebackq skip=2 tokens=3*" %%A IN (`REG QUERY %KEY_NAME% /v %VALUE_NAME% 2^>nul`) DO (
    set PathRel=%%A %%B
)
if defined PathRel (
    @echo Release version is installed at %PathRel%
	set DCS_FOUND=1
) else (
    goto :norel
)
if "%PathRel:~-1%" == " " (
	set PathRel=%PathRel:~0,-1%
)

FINDSTR /C:"dync = {}" "%PathRel%\Scripts\MissionScripting.lua" 1>nul 2>nul

If "%errorlevel%" == "1" (
	@echo Must add lines to MissionScripting.lua
) else (
	@echo Your MissionScripting.lua is already correct, not doing anything.
	goto :dyncexistsrel
)

FOR /F "usebackq tokens=1 delims=:" %%A IN (`FINDSTR /N /C:"dofile('Scripts/ScriptingSystem.lua')" "%PathRel%\Scripts\MissionScripting.lua" 2^>nul`) DO (
	set /A LineNumber = %%A + 1
)

del /Q "%PathRel%\Scripts\MissionScripting-backup.lua" 1>nul 2>nul
rename "%PathRel%\Scripts\MissionScripting.lua" MissionScripting-backup.lua

set Output="%PathRel%\Scripts\MissionScripting.lua"

(for /f "tokens=1* delims=[]" %%a in ('find /n /v "##" ^< "%PathRel%\Scripts\MissionScripting-backup.lua"') do (
if "%%~a"=="%LineNumber%" (
echo dync = {}
echo dofile^(lfs.writedir^(^).."\\Scripts\\DynC.lua"^)
echo.
ECHO.%%b
) ELSE (
echo.%%b
)
)) > %Output%

:dyncexistsrel
:norel

if %DCS_FOUND%==0 (
	ECHO Could not find any installed version of DCS World. Is it from Steam? That has not been tested yet.
)