@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ========================================
echo MINIFICATION DE TOUS LES FICHIERS CSS
echo ========================================

cd /d "C:\Users\losia\Documents\IT-monitoring"

rem Compter le nombre de fichiers CSS
set FILE_COUNT=0
for /r "static_dev\assets\css" %%f in (*.css) do (
    set /a FILE_COUNT+=1
)

echo Fichiers CSS trouvés: %FILE_COUNT%
echo ========================================

set PROCESSED=0
set SUCCESS=0
set ERRORS=0

rem Traiter tous les fichiers .css dans static_dev/assets/css et sous-dossiers
for /r "static_dev\assets\css" %%f in (*.css) do (
    set /a PROCESSED+=1
    set "FULL_PATH=%%f"

    rem Convertir le chemin absolu en chemin relatif
    set "REL_PATH=!FULL_PATH:%CD%\=!"

    echo.
    echo [!PROCESSED!/!FILE_COUNT!] Processing: !REL_PATH!
    echo ----------------------------------------

    rem Appeler le script de minification CSS
    call "minification\minify-css.bat" "!REL_PATH!"

    if !ERRORLEVEL! EQU 0 (
        set /a SUCCESS+=1
        echo ✅ SUCCESS: !REL_PATH!
    ) else (
        set /a ERRORS+=1
        echo ❌ ERROR: !REL_PATH!
    )
)

echo.
echo ========================================
echo RAPPORT FINAL CSS
echo ========================================
echo Total traités: %PROCESSED%
echo Succès: %SUCCESS%
echo Erreurs: %ERRORS%
echo ========================================

if %ERRORS% GTR 0 (
    echo ⚠️  Il y a eu %ERRORS% erreurs lors de la minification CSS
    exit /b 1
) else (
    echo ✅ Tous les fichiers CSS ont été traités avec succès!
    exit /b 0
)