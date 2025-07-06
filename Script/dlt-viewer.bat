@echo off
setlocal
rem ─── Define the correct path to the dlt-viewer executable ─────────────
set "EXE_PATH=%~1"
rem ─── Define correct arguments (with proper quoting) ──────────────────
set "ARGS1=-p %~5 -l %~4"
rem ─── Define correct arguments (with proper quoting) ──────────────────
set "ARGS2=-c %~3 %~4"
rem ─── Timeout before killing the viewer (in seconds) ──────────────────
set "TIMEOUT=%~2%"
rem ─── Launch via PowerShell and manage lifecycle ──────────────────────
for /f "usebackq delims=" %%P in (`
 powershell -NoLogo -NoProfile -Command ^
   "     $p = Start-Process -FilePath '%EXE_PATH%' -ArgumentList '%ARGS1%' -PassThru; if ($p) { Write-Output $p.Id; Start-Sleep -Seconds %TIMEOUT%; Stop-Process -Id $p.Id -Force } else { Write-Error 'Failed to start process' }"
`) do set "MY_PID=%%P"
if defined MY_PID (
 echo Launched "%EXE_PATH% %ARGS1%" with PID=%MY_PID%
 echo (after %TIMEOUT%s, it was terminated)
)
@REM else (
@REM  echo [ERROR] dlt-viewer failed to start. Please check the paths and arguments.)


for /f "usebackq delims=" %%P in (`
 powershell -NoLogo -NoProfile -Command ^
   "     $p = Start-Process -FilePath '%EXE_PATH%' -ArgumentList '%ARGS2%' -PassThru; if ($p) { Write-Output $p.Id; Start-Sleep -Seconds 15; Stop-Process -Id $p.Id -Force } else { Write-Error 'Failed to start process' }"
`) do set "MY_PID=%%P"
if defined MY_PID (
 echo Launched "%EXE_PATH% %ARGS2%" with PID=%MY_PID%
 echo (after 15s, it was terminated)
)
@REM else (
@REM  echo [ERROR] dlt-viewer failed to start. Please check the paths and arguments.)

endlocal
del /f %~4