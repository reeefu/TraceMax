@echo off
REM =========================================================================
REM  build_windows.bat — Build TraceMax executable for Windows
REM
REM  Usage:
REM      build_windows.bat           (build using tracemax.spec)
REM      build_windows.bat clean     (remove previous build artifacts first)
REM =========================================================================

setlocal EnableDelayedExpansion

echo.
echo ====================================
echo   TraceMax — Windows Build Script
echo ====================================
echo.

REM --- Optional clean step ---
if /I "%1"=="clean" (
    echo [1/4] Cleaning previous builds...
    if exist dist rmdir /s /q dist
    if exist build rmdir /s /q build
    echo        Done.
) else (
    echo [1/4] Skipping clean (pass "clean" to remove previous artifacts^)
)

REM --- Generate icon ---
echo [2/4] Generating icon files...
python generate_icon.py
if %ERRORLEVEL% neq 0 (
    echo ERROR: Icon generation failed.
    exit /b 1
)

REM --- Build ---
echo [3/4] Running PyInstaller...
pyinstaller --noconfirm tracemax.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM --- Summary ---
echo [4/4] Build complete!
echo.
echo   Output directory: dist\TraceMax\
echo   Executable:       dist\TraceMax\TraceMax.exe
echo.
echo To run:
echo   dist\TraceMax\TraceMax.exe
echo.

endlocal
