@echo off
setlocal
title Token Blast Explorer
cd /d "%~dp0"

rem The app's packages live in this folder instead of a virtual environment,
rem because some PCs (Device Guard / Smart App Control) block Python inside .venv folders.
set "PKGS=%~dp0.packages"

rem ---- 1. Find Python ----
set "RUNPY="
set "UV="
where py >nul 2>nul && set "RUNPY=py -3"
if defined RUNPY goto :have_python
python --version >nul 2>nul && set "RUNPY=python"
if defined RUNPY goto :have_python

rem No regular Python on PATH. If the "uv" Python manager is installed, use its Python.
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV goto :nopython
echo No regular Python found, using uv's Python instead...
rem Run from the user folder so uv doesn't pick up a .venv in this folder.
pushd "%USERPROFILE%"
call "%UV%" python install 3.11 >nul 2>nul
set "UVPY="
for /f "delims=" %%i in ('call "%UV%" python find 3.11') do set "UVPY=%%i"
popd
if not defined UVPY goto :nopython
set "RUNPY="%UVPY%""

rem ---- 2. Install packages (only when requirements.txt has changed) ----
:have_python
fc /b requirements.txt "%PKGS%\installed-requirements.txt" >nul 2>nul
if not errorlevel 1 goto :run

echo Installing the packages this app needs. This takes a minute or two the first time...
if exist "%PKGS%" rmdir /s /q "%PKGS%"
if defined UV goto :install_with_uv
%RUNPY% -m pip install -q --disable-pip-version-check --target "%PKGS%" -r requirements.txt
if errorlevel 1 goto :piperror
goto :installed
:install_with_uv
call "%UV%" pip install -q --target "%PKGS%" --python %RUNPY% -r requirements.txt
if errorlevel 1 goto :piperror
:installed
copy /y requirements.txt "%PKGS%\installed-requirements.txt" >nul

rem ---- 3. Start the app ----
:run
set "PYTHONPATH=%PKGS%"
echo.
echo Starting Token Blast Explorer. It will open in your browser.
echo Keep this window open while you use the app. Close it to quit.
echo.
%RUNPY% launch.py
if errorlevel 1 pause
exit /b 0

:nopython
echo.
echo Python was not found on this computer.
echo Install it from https://www.python.org/downloads/
echo During setup, tick "Add python.exe to PATH". Then double-click Start.bat again.
echo.
pause
exit /b 1

:piperror
echo.
echo Installing packages failed. Check your internet connection and try again.
echo If it keeps failing, delete the ".packages" folder next to Start.bat and retry.
echo.
pause
exit /b 1
