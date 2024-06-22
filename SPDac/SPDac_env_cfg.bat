@echo off
set "source_folder=%~dp0..\SPDev"

pip install qcodes qcodes_contrib_drivers pyvisa pyvisa-py pyusb pyudev pyserial zeroconf 

REM Execute the "pip show qcodes_contrib_drivers" command and save the output to a temporary file
pip show qcodes_contrib_drivers > temp.txt

REM Extract the "location" field
for /f "tokens=2 delims=: " %%a in ('findstr /c:"Location:" temp.txt') do (
    set "locationA=%%a"
)

for /f "tokens=3 delims=: " %%a in ('findstr /c:"Location:" temp.txt') do (
    set "locationB=%%a"
)

REM Delete the temporary file
del temp.txt

set "destination_folder=%locationA%:%locationB%\qcodes_contrib_drivers\drivers\SPDev"

REM Display the extracted location
echo source_folder: %source_folder%
echo Location: %destination_folder%

if not exist "%destination_folder%" (
    mkdir "%destination_folder%"
)

xcopy /s /i "%source_folder%" "%destination_folder%"

echo The SPDev folder has been copied to %destination_folder%

PAUSE