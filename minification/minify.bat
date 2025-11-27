@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

rem Changer vers le répertoire du projet
cd /d "C:\Users\losia\Documents\IT-monitoring"

rem Récupérer le fichier d'entrée (sans guillemets grâce au tilde ~)
set INPUT_FILE=%~1

rem Nettoyer le chemin : retirer .\ au début si présent
if "!INPUT_FILE:~0,2!"==".\" (
    set INPUT_FILE=!INPUT_FILE:~2!
)

set RELATIVE_PATH=!INPUT_FILE:static_dev=!

rem Validation : RELATIVE_PATH doit commencer par un backslash
if not "!RELATIVE_PATH:~0,1!"=="\" (
    echo ERROR: Invalid input path. Must be in format: static_dev\path\to\file.js
    echo Got: !INPUT_FILE!
    exit /b 1
)

rem Créer le chemin de sortie
set OUTPUT_FILE=static!RELATIVE_PATH!

rem Sécurité : vérifier que OUTPUT_FILE ne se termine pas par un point
if "!OUTPUT_FILE:~-1!"=="." (
    echo ERROR: Generated output path ends with a dot: !OUTPUT_FILE!
    echo This would create an invalid Windows directory name
    exit /b 1
)

rem Debug - afficher les chemins
echo Working directory: %CD%
echo INPUT: !INPUT_FILE!
echo OUTPUT: !OUTPUT_FILE!

rem Créer les dossiers étape par étape pour éviter les erreurs
if not exist "static" md "static"
if not exist "static\assets" md "static\assets"
if not exist "static\assets\js" md "static\assets\js"

rem Pour les sous-dossiers comme service/, extraire et créer
echo !OUTPUT_FILE! | findstr "\\service\\" >nul
if !ERRORLEVEL! EQU 0 (
    if not exist "static\assets\js\service" md "static\assets\js\service"
)

rem Vérifier que les fichiers existent
if not exist "!INPUT_FILE!" (
    echo ERROR: Input file does not exist: !INPUT_FILE!
    exit /b 1
)

if not exist "babel.config.json" (
    echo ERROR: babel.config.json not found
    exit /b 1
)

if not exist "node_modules\.bin\babel.cmd" (
    echo ERROR: babel.cmd not found
    exit /b 1
)

rem Étape 1: Déterminer la configuration Babel à utiliser
set BABEL_CONFIG=minification\babel.production.json
set IS_WHITELISTED=false

rem Vérifier la whitelist via PowerShell
echo Checking whitelist for: !INPUT_FILE!
powershell -ExecutionPolicy Bypass -File "minification\check-whitelist.ps1" -FilePath "!INPUT_FILE!" > temp_whitelist_result.txt 2>&1
set /p WHITELIST_RESULT=<temp_whitelist_result.txt
del temp_whitelist_result.txt

if "!WHITELIST_RESULT!"=="WHITELISTED" (
    set IS_WHITELISTED=true
    set BABEL_CONFIG=minification\babel.debug.json
    echo File is WHITELISTED: !INPUT_FILE! - keeping console.log statements
) else if "!WHITELIST_RESULT!"=="NOT_WHITELISTED" (
    echo File is NOT whitelisted: !INPUT_FILE! - removing console.log/debug/info statements
) else (
    echo Warning: Could not determine whitelist status, defaulting to production mode
)

rem Étape 1: Transpiler avec Babel
echo Step 1: Running Babel transpilation with !BABEL_CONFIG!...
echo Command: node_modules\.bin\babel.cmd "!INPUT_FILE!" --out-file "!OUTPUT_FILE!" --config-file "!BABEL_CONFIG!"

call node_modules\.bin\babel.cmd "!INPUT_FILE!" --out-file "!OUTPUT_FILE!" --config-file "%CD%\!BABEL_CONFIG!"

if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Babel failed with code !ERRORLEVEL!
    exit /b 1
)

rem Étape 2: Obfuscation avec Terser (avec ou sans suppression des logs)
echo Step 2: Running Terser obfuscation...
set TEMP_FILE=!OUTPUT_FILE!.tmp

if "!IS_WHITELISTED!"=="true" (
    echo Using standard Terser compression for whitelisted file
    echo Command: node_modules\.bin\terser.cmd "!OUTPUT_FILE!" --compress --mangle --keep-fnames --safari10 --output "!TEMP_FILE!"
    call node_modules\.bin\terser.cmd "!OUTPUT_FILE!" --compress --mangle --keep-fnames --safari10 --output "!TEMP_FILE!"
) else (
    echo Using aggressive Terser compression with selective console removal
    echo Command: node_modules\.bin\terser.cmd "!OUTPUT_FILE!" --compress drop_debugger=true,pure_funcs=['console.log','console.debug','console.info'] --mangle --keep-fnames --safari10 --output "!TEMP_FILE!"
    call node_modules\.bin\terser.cmd "!OUTPUT_FILE!" --compress drop_debugger=true,pure_funcs=['console.log','console.debug','console.info'] --mangle --keep-fnames --safari10 --output "!TEMP_FILE!"
)

if !ERRORLEVEL! EQU 0 (
    rem Remplacer le fichier original par la version obfusquée
    move "!TEMP_FILE!" "!OUTPUT_FILE!" >nul
    echo SUCCESS: Minified and obfuscated !INPUT_FILE! -^> !OUTPUT_FILE!
) else (
    echo ERROR: Terser failed with code !ERRORLEVEL!
    if exist "!TEMP_FILE!" del "!TEMP_FILE!"
    echo Keeping Babel-only version
)