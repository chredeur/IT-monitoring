@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ========================================
echo MINIFICATION COMPLÈTE - JS ET CSS
echo ========================================

cd /d "C:\Users\losia\Documents\IT-monitoring"

echo Étape 1: Minification des fichiers JavaScript...
echo ========================================
call "minification\minify-all.bat"
set JS_EXIT_CODE=%ERRORLEVEL%

echo.
echo.
echo Étape 2: Minification des fichiers CSS...
echo ========================================
call "minification\minify-all-css.bat"
set CSS_EXIT_CODE=%ERRORLEVEL%

echo.
echo.
echo ========================================
echo RAPPORT FINAL COMPLET
echo ========================================

if %JS_EXIT_CODE% EQU 0 (
    echo ✅ JavaScript: Tous les fichiers traités avec succès
) else (
    echo ❌ JavaScript: %JS_EXIT_CODE% erreurs détectées
)

if %CSS_EXIT_CODE% EQU 0 (
    echo ✅ CSS: Tous les fichiers traités avec succès
) else (
    echo ❌ CSS: %CSS_EXIT_CODE% erreurs détectées
)

echo ========================================

if %JS_EXIT_CODE% GTR 0 (
    set /a TOTAL_ERRORS+=%JS_EXIT_CODE%
)
if %CSS_EXIT_CODE% GTR 0 (
    set /a TOTAL_ERRORS+=%CSS_EXIT_CODE%
)

if %TOTAL_ERRORS% GTR 0 (
    echo ⚠️  Total des erreurs: %TOTAL_ERRORS%
    exit /b 1
) else (
    echo ✅ Minification complète terminée avec succès!
    exit /b 0
)