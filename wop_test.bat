@echo off

IF "%1"=="/SL" (set SAVE_LAYOUT=1) ELSE set SAVE_LAYOUT=0

set SYS_ARCH=test
IF %PROCESSOR_ARCHITECTURE%==x86 set SYS_ARCH=win32
IF %PROCESSOR_ARCHITECTURE%==x86_64 set SYS_ARCH=win64
IF %PROCESSOR_ARCHITECTURE%==AMD64 set SYS_ARCH=win64
IF %SYS_ARCH%==test (
	echo Fatal Error: Unknown PROCESSOR_ARCHITECTURE
	set SYS_ARCH=
	exit /B 1 )

set WORK_DIR=%cd%
mkdir %WORK_DIR%\easyrsa3\bin
copy  %WORK_DIR%\distro\windows\bin\* %WORK_DIR%\easyrsa3\bin
copy  %WORK_DIR%\distro\windows\%SYS_ARCH%\* %WORK_DIR%\easyrsa3\bin
copy  %WORK_DIR%\distro\windows\EasyRSA-Start.bat %WORK_DIR%\easyrsa3\EasyRSA-Start.bat
PATH=%PATH%;%WORK_DIR%\easyrsa3\bin;C:\PROGRA~1\openssl

cmd /C "easyrsa3\bin\sh.exe wop_test.sh"
IF ERRORLEVEL 0 (
	IF %SAVE_LAYOUT% EQU 0 (
		echo rmdir /S /Q %WORK_DIR%\easyrsa3\bin
		rmdir /S /Q %WORK_DIR%\easyrsa3\bin
		echo del /Q %WORK_DIR%\easyrsa3\EasyRSA-Start.bat
		del /Q %WORK_DIR%\easyrsa3\EasyRSA-Start.bat
		echo rm %WORK_DIR%\easyrsa3\.rnd
		rm %WORK_DIR%\easyrsa3\.rnd
	) ELSE echo NOTICE; Saved Layout
) ELSE echo Error occurred, no clean up
	
set SAVE_LAYOUT=
set SYS_ARCH=
pause

