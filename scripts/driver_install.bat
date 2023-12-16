@echo off
REM Installation of the USB probe usb driver on windows
REM Written by Micah Johnson
REM 12/15/2023
echo.
echo ========== LYTE PROBE USB DRIVER INSTALL ==========
echo.

REM Download the Zip file
echo Downloading Lyte probe usb drivers zip file...
powershell -command "& { (New-Object Net.WebClient).DownloadFile('https://drive.google.com/u/1/uc?id=18t1XQvWoSRbmwd9GQrSo6ij6BaIVpXsY&export=download', 'rad_drivers.zip') }"

REM Unzip the path locally
echo Unzipping...
powershell -command "Expand-Archive -Path 'rad_drivers.zip' -DestinationPath './rad_drivers' -Force"
REM Execute the setup
echo Launching installers...
"rad_drivers/VCP_V1.4.0_Setup.exe"
REM Install virtual com port
"C:\Program Files (x86)\STMicroelectronics\Software\Virtual comport driver\Win8\dpinst_amd64.exe"

REM clean up
echo Cleaning up...
del "rad_drivers.zip"
rmdir /s /q "./rad_drivers"
echo.
echo Lyte probe USB driver installation script finished!
echo Closing...
REM Delay closing for readability
timeout /nobreak /t 3 >nul
