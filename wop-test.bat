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
mkdir "%WORK_DIR%\easyrsa3\bin"
copy  "%WORK_DIR%\distro\windows\bin\*" "%WORK_DIR%\easyrsa3\bin"
copy  "%WORK_DIR%\distro\windows\%SYS_ARCH%\*" "%WORK_DIR%\easyrsa3\bin"
copy  "%WORK_DIR%\distro\windows\EasyRSA-Start.bat" "%WORK_DIR%\easyrsa3\EasyRSA-Start.bat"
PATH=%PATH%;%WORK_DIR%\easyrsa3\bin;C:\PROGRA~1\openssl

cmd /C "easyrsa3\bin\sh.exe wop-test.sh"
IF ERRORLEVEL 1 (
	echo Error occurred, Exit 1
	exit /B 1 )

REM Success ..
	IF %SAVE_LAYOUT% EQU 0 (
		echo rmdir /S /Q "%WORK_DIR%\easyrsa3\bin"
		rmdir /S /Q "%WORK_DIR%\easyrsa3\bin"
		echo del /Q "%WORK_DIR%\easyrsa3\EasyRSA-Start.bat"
		del /Q "%WORK_DIR%\easyrsa3\EasyRSA-Start.bat"
		REM echo del "%WORK_DIR%\easyrsa3\.rnd"
		REM del /Q "%WORK_DIR%\easyrsa3\.rnd"
	) ELSE echo NOTICE; Saved Layout

set SAVE_LAYOUT=
set SYS_ARCH=
