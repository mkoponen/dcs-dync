!include "x64.nsh"
!include "LogicLib.nsh"
!include "include\GetFolderPath.nsh"
!include "MUI2.nsh"
!include "version.nsh"

!define MUI_ICON "..\dyncserver\resources\dync.ico"
!define MUI_WELCOMEPAGE_TEXT "Setup will guide you through the installation of DCS DynC.$\r$\n\
$\r$\n\
The server software for managing the dynamic campaigns will be installed. You will have the option to have this setup install everything necessary to your DCS World game installation for communicating with the server, or you can leave that checkbox off and do it manually with the instructions in the README.md text file in the server installation folder."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE English

VIProductVersion                 "${VERSION}"
VIAddVersionKey ProductName      "DCS DynC"
VIAddVersionKey Comments         "Dynamic Campaign server for DCS World"
VIAddVersionKey CompanyName      "Markku Koponen"
VIAddVersionKey LegalCopyright   "Markku Koponen"
VIAddVersionKey FileDescription  "Dynamic Campaign server for DCS World"
VIAddVersionKey FileVersion      "${VERSION}"
VIAddVersionKey ProductVersion   "${VERSION}"
VIAddVersionKey InternalName     "DCS-DynC"

Name "DCS DynC"
OutFile "dync-installer.exe"

InstallDirRegKey HKLM "Software\DCS-DynC" "Install_Dir"
RequestExecutionLevel admin

Function .onInit
  ${If} ${RunningX64}
    StrCpy $INSTDIR "$PROGRAMFILES64\DCS-DynC"
  ${Else}
    MessageBox MB_OK "Only 64-bit Windows is supported. Installer will now abort. It is possible to make 32-bit work by using the Python source code directly."
    Abort
  ${EndIf}
 FunctionEnd
 
 InstallDir $INSTDIR


Section "Install Server"

  SectionIn RO
  
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Copy all the Python files to the root of the install directory.
  File /r "..\dyncserver\dist\dyncserver\*"
  
  ; The .bat that updates MissionScripting is not in the Python folder, so copy it specifically to root.
  File "..\bin\update-missionscripting.bat"

  CreateDirectory "$InstDir\DCS World Files"

  File "/oname=DCS World Files\DynC.lua" "..\lua\DynC.lua"
  File "/oname=DCS World Files\dync_httpfix.lua" "..\lua\dync_httpfix.lua"
  File "/oname=DCS World Files\dync_urlfix.lua" "..\lua\dync_urlfix.lua"
  File "/oname=DCS World Files\DynCMissionInclude.lua" "..\lua\DynCMissionInclude.lua"
  File "/oname=DCS World Files\mist_4_3_74.lua" "..\lua\mist_4_3_74.lua"
  
  ; File "/oname=DCS World Files\beachparty-example1.miz" "..\bin\beachparty-example1.miz"
  File "/oname=DCS World Files\mozdok-example1.miz" "..\bin\mozdok-example1.miz"
  File "/oname=DCS World Files\mozdok-example1-background-image.png" "..\bin\mozdok-example1-background-image.png"
  
  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\DCS-DynC "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Example2" "DisplayName" "DCS DynC"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Example2" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Example2" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Example2" "NoRepair" 1
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\DynC Server"
  CreateShortcut "$SMPROGRAMS\DynC Server\DynCServer.lnk" "$INSTDIR\dyncserver.exe" "" "$INSTDIR\dyncserver.exe" 0
  CreateShortcut "$SMPROGRAMS\DynC Server\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  
SectionEnd

; Optional section (can be disabled by the user)
Section "Install files required by DCS World"

  ; Uses code by Erik Pilsits (in include-directory) to get the Saved Games folder and supporting non-English Windows language.
  ${SHGetKnownFolderPath} "${FOLDERID_SavedGames}" "" $0  
  ; $0 will contain the location of the user's saved games folder for a while
  
  ; If we have the DCS World OpenBeta, we install the necessary script to its user data folder, creating the Scripts folder into it if doesn't exist.
  ${If} ${FileExists} "$0\DCS.openbeta\*"
    ; We do have the OpenBeta folder in Saved Games
    ${If} ${FileExists} "$0\DCS.openbeta\Scripts\*"
	  ; Scripts folder exists, don't do anything
	${Else}
      CreateDirectory "$0\DCS.openbeta\Scripts"
	${EndIf}
	; Now the folder is guaranteed to exist. Copy the file.
	File /oname=$0\DCS.openbeta\Scripts\DynC.lua "..\lua\DynC.lua"
  ${EndIf}
  
  ; We do the same to the release version folder, if exists.
  ${If} ${FileExists} "$0\DCS\*"
    ; We do have the release version. Note that we can have both versions. The code is essentially the same as above.
    ${If} ${FileExists} "$0\DCS\Scripts\*"
	  ;...
	${Else}
      CreateDirectory "$0\DCS\Scripts"
	${EndIf}
	File /oname=$0\DCS\Scripts\DynC.lua "..\lua\DynC.lua"
  ${EndIf}
  
  ; Ok, $0 is no longer needed. Now we put the game installation folder to it.
  ReadRegStr $0 HKCU "Software\Eagle Dynamics\DCS World OpenBeta" "Path"
  ${If} $0 == ""
    ; We don't have OpenBeta, don't do anything.
  ${Else}
    ; We have OpenBeta. Copy the files to it. This doesn't overwrite anything so we don't ask for user confirmation like we do when ultimately editing MissionScripting.lua .
    File /oname=$0\LuaSocket\dync_httpfix.lua "..\lua\dync_httpfix.lua"
	File /oname=$0\LuaSocket\dync_urlfix.lua "..\lua\dync_urlfix.lua"
  ${EndIf}
  
  ; If we have Release version, we do the same things as with OpenBeta. Note that we can have both.
  ReadRegStr $0 HKCU "Software\Eagle Dynamics\DCS World" "Path"
  ${If} $0 == ""
    ;...
  ${Else}
    File /oname=$0\LuaSocket\dync_httpfix.lua "..\lua\dync_httpfix.lua"
	File /oname=$0\LuaSocket\dync_urlfix.lua "..\lua\dync_urlfix.lua"
  ${EndIf}
  ; Answering yes means simply executing update-missionscripting.bat . The user can also do this later, or edit the file by hand.
  MessageBox MB_YESNO "Do we automatically add the necessary lines to your game install folder's Scripts\MissionScripting.lua? (It is safe to answer Yes even if they already exist. Answer No if you'd like to do this manually later.)" IDYES true IDNO false
true:
  ExecWait '$INSTDIR\update-missionscripting.bat'
  Goto next
false:
  ; User wants to do it manually, don't do anything.
next:
  ; Installation is done.
SectionEnd

;--------------------------------
; From here starts some boilerplate code taken directly from NSIS source. You don't need to understand any of this starting from here...
;--------------------------------

; This is taken directly from NSIS includes, it is merely renamed so that Uninstall will accept it. (Names must start with un.*)
Function un.LineFind
	!define un.LineFind `!insertmacro LineFindCall`
 
	!macro LineFindCall _INPUT _OUTPUT _RANGE _FUNC
		Push $0
		Push `${_INPUT}`
		Push `${_OUTPUT}`
		Push `${_RANGE}`
		GetFunctionAddress $0 `${_FUNC}`
		Push `$0`
		Call un.LineFind
		Pop $0
	!macroend
 
	Exch $3
	Exch
	Exch $2
	Exch
	Exch 2
	Exch $1
	Exch 2
	Exch 3
	Exch $0
	Exch 3
	Push $4
	Push $5
	Push $6
	Push $7
	Push $8
	Push $9
	Push $R4
	Push $R5
	Push $R6
	Push $R7
	Push $R8
	Push $R9
	ClearErrors
 
	IfFileExists '$0' 0 error
	StrCmp $1 '/NUL' begin
	StrCpy $8 0
	IntOp $8 $8 - 1
	StrCpy $9 $1 1 $8
	StrCmp $9 \ +2
	StrCmp $9 '' +3 -3
	StrCpy $9 $1 $8
	IfFileExists '$9\*.*' 0 error
 
	begin:
	StrCpy $4 1
	StrCpy $5 -1
	StrCpy $6 0
	StrCpy $7 0
	StrCpy $R4 ''
	StrCpy $R6 ''
	StrCpy $R7 ''
	StrCpy $R8 0
 
	StrCpy $8 $2 1
	StrCmp $8 '{' 0 delspaces
	StrCpy $2 $2 '' 1
	StrCpy $8 $2 1 -1
	StrCmp $8 '}' 0 delspaces
	StrCpy $2 $2 -1
	StrCpy $R6 cut
 
	delspaces:
	StrCpy $8 $2 1
	StrCmp $8 ' ' 0 +3
	StrCpy $2 $2 '' 1
	goto -3
	StrCmp $2$7 '0' file
	StrCpy $4 ''
	StrCpy $5 ''
	StrCmp $2 '' writechk
 
	range:
	StrCpy $8 0
	StrCpy $9 $2 1 $8
	StrCmp $9 '' +5
	StrCmp $9 ' ' +4
	StrCmp $9 ':' +3
	IntOp $8 $8 + 1
	goto -5
	StrCpy $5 $2 $8
	IntOp $5 $5 + 0
	IntOp $8 $8 + 1
	StrCpy $2 $2 '' $8
	StrCmp $4 '' 0 +2
	StrCpy $4 $5
	StrCmp $9 ':' range
 
	IntCmp $4 0 0 +2
	IntCmp $5 -1 goto 0 growthcmp
	StrCmp $R7 '' 0 minus2plus
	StrCpy $R7 0
	FileOpen $8 $0 r
	FileRead $8 $9
	IfErrors +3
	IntOp $R7 $R7 + 1
	Goto -3
	FileClose $8
 
	minus2plus:
	IntCmp $4 0 +5 0 +5
	IntOp $4 $R7 + $4
	IntOp $4 $4 + 1
	IntCmp $4 0 +2 0 +2
	StrCpy $4 0
	IntCmp $5 -1 goto 0 growthcmp
	IntOp $5 $R7 + $5
	IntOp $5 $5 + 1
	growthcmp:
	IntCmp $4 $5 goto goto
	StrCpy $5 $4
	goto:
	goto $7
 
	file:
	StrCmp $1 '/NUL' +4
	GetTempFileName $R4
	Push $R4
	FileOpen $R4 $R4 w
	FileOpen $R5 $0 r
	IfErrors preerror
 
	loop:
	IntOp $R8 $R8 + 1
	FileRead $R5 $R9
	IfErrors handleclose
 
	cmp:
	StrCmp $2$4$5 '' writechk
	IntCmp $4 $R8 call 0 writechk
	StrCmp $5 -1 call
	IntCmp $5 $R8 call 0 call
 
	GetLabelAddress $7 cmp
	goto delspaces
 
	call:
	StrCpy $7 $R9
	Push $0
	Push $1
	Push $2
	Push $3
	Push $4
	Push $5
	Push $6
	Push $7
	Push $R4
	Push $R5
	Push $R6
	Push $R7
	Push $R8
	StrCpy $R6 '$4:$5'
	StrCmp $R7 '' +3
	IntOp $R7 $R8 - $R7
	IntOp $R7 $R7 - 1
	Call $3
	Pop $9
	Pop $R8
	Pop $R7
	Pop $R6
	Pop $R5
	Pop $R4
	Pop $7
	Pop $6
	Pop $5
	Pop $4
	Pop $3
	Pop $2
	Pop $1
	Pop $0
	IfErrors preerror
	StrCmp $9 'StopLineFind' 0 +3
	IntOp $6 $6 + 1
	goto handleclose
	StrCmp $1 '/NUL' loop
	StrCmp $9 'SkipWrite' 0 +3
	IntOp $6 $6 + 1
	goto loop
	StrCmp $7 $R9 write
	IntOp $6 $6 + 1
	goto write
 
	writechk:
	StrCmp $1 '/NUL' loop
	StrCmp $R6 cut 0 write
	IntOp $6 $6 + 1
	goto loop
 
	write:
	FileWrite $R4 $R9
	goto loop
 
	preerror:
	SetErrors
 
	handleclose:
	StrCmp $1 '/NUL' +3
	FileClose $R4
	Pop $R4
	FileClose $R5
	IfErrors error
 
	StrCmp $1 '/NUL' end
	StrCmp $1 '' 0 +2
	StrCpy $1 $0
	StrCmp $6 0 0 rename
	FileOpen $7 $0 r
	FileSeek $7 0 END $8
	FileClose $7
	FileOpen $7 $R4 r
	FileSeek $7 0 END $9
	FileClose $7
	IntCmp $8 $9 0 rename
	Delete $R4
	StrCmp $1 $0 end
	CopyFiles /SILENT $0 $1
	goto end
 
	rename:
	Delete '$EXEDIR\$1'
	Rename $R4 '$EXEDIR\$1'
	IfErrors 0 end
	Delete $1
	Rename $R4 $1
	IfErrors 0 end
 
	error:
	SetErrors
 
	end:
	Pop $R9
	Pop $R8
	Pop $R7
	Pop $R6
	Pop $R5
	Pop $R4
	Pop $9
	Pop $8
	Pop $7
	Pop $6
	Pop $5
	Pop $4
	Pop $3
	Pop $2
	Pop $1
	Pop $0
FunctionEnd

; This is the actual function that deletes between two specific lines, endpoint inclusive. It is adapted from Example6 of LineFind at NSIS website
Function un.DeleteLines
	StrCmp $R0 finish code
	StrCmp $R0 start finish
	
	; This determines from what string to delete
	StrCmp $R9 'dync = {}$\r$\n' 0 code
	StrCpy $R0 start
	StrCpy $R1 $R8
	goto skip
	finish:
	; This determines up to and including what string to delete
	StrCmp $R9 'dofile(lfs.writedir().."\\Scripts\\DynC.lua")$\r$\n' 0 skip
	StrCpy $R0 finish
	StrCpy $R2 $R8
	skip:
	StrCpy $0 SkipWrite
	goto output
 
	code:
	; Possible additional processing here if necessary at some point
 
	output:
	Push $0
FunctionEnd
;--------------------------------
; ...to here. Now it's time to start understanding again.
;--------------------------------


Section "Uninstall"
  
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DCS-DynC"
  DeleteRegKey HKLM SOFTWARE\DCS-DynC
  Delete "$SMPROGRAMS\DynC Server\*.*"
  RMDir "$SMPROGRAMS\DynC Server"
  RMDir /r "$INSTDIR"
  
  MessageBox MB_YESNO "Would you like the uninstaller to automatically remove the previously added DynC -lines from your DCS World install directory's MissionScripting.lua?$\r$\n\
  $\r$\n\
  (If you have done it by hand, you may want to remove it by hand too, and answer No. The uninstaller is very strict about their format. If they were added by the installer, or update-missionscripting.bat file, answer Yes.)" IDYES true IDNO false
true:
  ReadRegStr $0 HKCU "Software\Eagle Dynamics\DCS World OpenBeta" "Path"
  ${un.LineFind} "$0\Scripts\MissionScripting.lua" "$0\Scripts\MissionScripting.lua" "1:-1" "un.DeleteLines"
  Goto next
false:
  ; User wants to remove lines manually
next:
  ; Uninstallation is done
SectionEnd
