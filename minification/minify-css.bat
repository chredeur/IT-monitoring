@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

rem Changer vers le répertoire du projet
cd /d "C:\Users\losia\Documents\IT-monitoring"

rem Récupérer le fichier d'entrée (sans guillemets)
set INPUT_FILE=%~1

if "%INPUT_FILE%"=="" (
    echo ERROR: Please provide an input CSS file
    echo Usage: minify-css.bat "path/to/file.css"
    exit /b 1
)

rem Extraire le nom du fichier sans extension et le répertoire
for %%f in ("%INPUT_FILE%") do (
    set "FILE_NAME=%%~nf"
    set "FILE_DIR=%%~dpf"
)

rem Construire le chemin de sortie en remplaçant static_dev par static
set "OUTPUT_DIR=!FILE_DIR:static_dev=static!"
set "OUTPUT_FILE=!OUTPUT_DIR!!FILE_NAME!.css"

rem Debug - afficher les chemins
echo Working directory: %CD%
echo INPUT: %INPUT_FILE%
echo OUTPUT: !OUTPUT_FILE!

rem Créer les dossiers de sortie si nécessaire
if not exist "!OUTPUT_DIR!" mkdir "!OUTPUT_DIR!"

rem Vérifier que le fichier d'entrée existe
if not exist "%INPUT_FILE%" (
    echo ERROR: Input file does not exist: %INPUT_FILE%
    exit /b 1
)

rem Vérifier que csso est installé
if not exist "node_modules\.bin\csso.cmd" (
    echo ERROR: csso.cmd not found. Run: npm install csso-cli --save-dev
    exit /b 1
)

rem Minifier le CSS avec csso
echo Running CSS minification with csso...
echo Command: node_modules\.bin\csso.cmd -i "%INPUT_FILE%" -o "!OUTPUT_FILE!"

call node_modules\.bin\csso.cmd -i "%INPUT_FILE%" -o "!OUTPUT_FILE!" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Minified %INPUT_FILE% ^-^> !OUTPUT_FILE! 1>&2
) else (
    echo ERROR: CSS minification failed with code %ERRORLEVEL% 1>&2
    exit /b 1
)