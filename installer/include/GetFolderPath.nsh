/*************************************************************************
*	Copyright Erik Pilsits 2008
**************************************************************************
*	HRESULT SHGetFolderPath(      
*		HWND hwndOwner,
*		int nFolder,
*		HANDLE hToken,
*		DWORD dwFlags,
*		LPTSTR pszPath
*	)
*
*	HRESULT SHGetKnownFolderPath(      
*		REFKNOWNFOLDERID rfid,
*		DWORD dwFlags,
*		HANDLE hToken,
*		PWSTR *ppszPath
*	)
**************************************************************************
*	${SHGetFolderPath} "${CSIDL}|${FLAG}|${FLAG}" "${TYPE}" $var
*
*	$var		[path] - path to folder
*			"fail" - function failed
**************************************************************************
*	VISTA ONLY
*
*	${SHGetKnownFolderPath} "${FOLDERID}" "${FLAG}|${FLAG}|${FLAG}" $var
*
*	$var		[path] - path to folder
*			"fail" - function failed
*************************************************************************/

!include LogicLib.nsh

;**********************************************************************
;* SHGetFolderPath Constants                                          *
;**********************************************************************
!define CSIDL_DESKTOP "0x0000"
!define CSIDL_INTERNET "0x0001"
!define CSIDL_PROGRAMS "0x0002"
!define CSIDL_CONTROLS "0x0003"
!define CSIDL_PRINTERS "0x0004"
!define CSIDL_PERSONAL "0x0005"
!define CSIDL_FAVORITES "0x0006"
!define CSIDL_STARTUP "0x0007"
!define CSIDL_RECENT "0x0008"
!define CSIDL_SENDTO "0x0009"
!define CSIDL_BITBUCKET "0x000A"
!define CSIDL_STARTMENU "0x000B"
!define CSIDL_MYDOCUMENTS "0x000C"
!define CSIDL_MYMUSIC "0x000D"
!define CSIDL_MYVIDEO "0x000E"
!define CSIDL_DIRECTORY "0x0010"
!define CSIDL_DRIVES "0x0011"
!define CSIDL_NETWORK "0x0012"
!define CSIDL_NETHOOD "0x0013"
!define CSIDL_FONTS "0x0014"
!define CSIDL_TEMPLATES "0x0015"
!define CSIDL_COMMON_STARTMENU "0x016"
!define CSIDL_COMMON_PROGRAMS "0x0017"
!define CSIDL_COMMON_STARTUP "0x0018"
!define CSIDL_COMMON_DESKTOPDIRECTORY "0x0019"
!define CSIDL_APPDATA "0x001A"
!define CSIDL_PRINTHOOD "0x001B"
!define CSIDL_LOCAL_APPDATA "0x001C"
!define CSIDL_ALTSTARTUP "0x001D"
!define CSIDL_COMMON_ALTSTARTUP "0x001E"
!define CSIDL_COMMON_FAVORITES "0x001F"
!define CSIDL_INTERNET_CACHE "0x0020"
!define CSIDL_COOKIES "0x0021"
!define CSIDL_HISTORY "0x0022"
!define CSIDL_COMMON_APPDATA "0x0023"
!define CSIDL_WINDOWS "0x0024"
!define CSIDL_SYSTEM "0x0025"
!define CSIDL_PROGRAM_FILES "0x0026"
!define CSIDL_MYPICTURES "0x0027"
!define CSIDL_PROFILE "0x0028"
!define CSIDL_SYSTEMX86 "0x0029"
!define CSIDL_PROGRAM_FILESX86 "0x002A"
!define CSIDL_PROGRAM_FILES_COMMON "0x002B"
!define CSIDL_PROGRAM_FILES_COMMONX86 "0x002C"
!define CSIDL_COMMON_TEMPLATES "0x002D"
!define CSIDL_COMMON_DOCUMENTS "0x002E"
!define CSIDL_COMMON_ADMINTOOLS "0x002F"
!define CSIDL_ADMINTOOLS "0x0030"
!define CSIDL_CONNECTIONS "0x0031"
!define CSIDL_COMMON_MUSIC "0x0035"
!define CSIDL_COMMON_PICTURES "0x0036"
!define CSIDL_COMMON_VIDEO "0x0037"
!define CSIDL_RESOURCES "0x0038"
!define CSIDL_RESOURCES_LOCALIZED "0x0039"
!define CSIDL_COMMON_OEM_LINKS "0x003A"
!define CSIDL_CDBURN_AREA "0x003B"
!define CSIDL_COMPUTERSNEARME "0x003D"

; combine with CSIDL_ value to force folder creation in SHGetFolderPath()
!define CSIDL_FLAG_CREATE "0x8000"
; combine with CSIDL_ value to return an unverified folder path
!define CSIDL_FLAG_DONT_VERIFY "0x4000"
; combine with CSIDL_ value to insure non-alias versions of the pidl
!define CSIDL_FLAG_NO_ALIAS "0x1000"
; combine with CSIDL_ value to indicate per-user init (eg. upgrade)
!define CSIDL_FLAG_PER_USER_INIT "0x0800"
; mask for all possible flag values
!define CSIDL_FLAG_MASK "0xFF00"

; dwFlags values for use with SHGetFolderPath
; current value for user, verify it exists
!define SHGFP_TYPE_CURRENT "0x0000"
; default value
!define SHGFP_TYPE_DEFAULT "0x0001"


;**********************************************************************
;* SHGetKnownFolderPath Constants                                     *
;**********************************************************************
!define FOLDERID_AddNewPrograms "{de61d971-5ebc-4f02-a3a9-6c82895e5c04}"
!define FOLDERID_AdminTools  "{724EF170-A42D-4FEF-9F26-B60E846FBA4F}"
!define FOLDERID_AppUpdates "{a305ce99-f527-492b-8b1a-7e76fa98d6e4}"
!define FOLDERID_CDBurning "{9E52AB10-F80D-49DF-ACB8-4330F5687855}"
!define FOLDERID_ChangeRemovePrograms "{df7266ac-9274-4867-8d55-3bd661de872d}"
!define FOLDERID_CommonAdminTools "{D0384E7D-BAC3-4797-8F14-CBA229B392B5}"
!define FOLDERID_CommonOEMLinks "{C1BAE2D0-10DF-4334-BEDD-7AA20B227A9D}"
!define FOLDERID_CommonPrograms "{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}"
!define FOLDERID_CommonStartMenu "{A4115719-D62E-491D-AA7C-E74B8BE3B067}"
!define FOLDERID_CommonStartup "{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}"
!define FOLDERID_CommonTemplates "{B94237E7-57AC-4347-9151-B08C6C32D1F7}"
!define FOLDERID_ComputerFolder "{0AC0837C-BBF8-452A-850D-79D08E667CA7}"
!define FOLDERID_ConflictFolder "{4bfefb45-347d-4006-a5be-ac0cb0567192}"
!define FOLDERID_ConnectionsFolder "{6F0CD92B-2E97-45D1-88FF-B0D186B8DEDD}"
!define FOLDERID_Contact "{56784854-C6CB-462b-8169-88E350ACB882}"
!define FOLDERID_ControlPanelFolder "{82A74AEB-AEB4-465C-A014-D097EE346D63}"
!define FOLDERID_Cookies "{2B0F765D-C0E9-4171-908E-08A611B84FF6}"
!define FOLDERID_Desktop "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"
!define FOLDERID_Documents "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
!define FOLDERID_Downloads "{374DE290-123F-4565-9164-39C4925E467B}"
!define FOLDERID_Favorites "{1777F761-68AD-4D8A-87BD-30B759FA33DD}"
!define FOLDERID_Fonts "{FD228CB7-AE11-4AE3-864C-16F3910AB8FE}"
!define FOLDERID_Games "{CAC52C1A-B53D-4edc-92D7-6B2E8AC19434}"
!define FOLDERID_GameTasks "{054FAE61-4DD8-4787-80B6-090220C4B700}"
!define FOLDERID_History "{D9DC8A3B-B784-432E-A781-5A1130A75963}"
!define FOLDERID_InternetCache "{352481E8-33BE-4251-BA85-6007CAEDCF9D}"
!define FOLDERID_InternetFolder "{4D9F7874-4E0C-4904-967B-40B0D20C3E4B}"
!define FOLDERID_Links "{bfb9d5e0-c6a9-404c-b2b2-ae6db6af4968}"
!define FOLDERID_LocalAppData "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"
!define FOLDERID_LocalAppDataLow "{A520A1A4-1780-4FF6-BD18-167343C5AF16}"
!define FOLDERID_LocalizedResourcesDir "{2A00375E-224C-49DE-B8D1-440DF7EF3DDC}"
!define FOLDERID_Music "{4BD8D571-6D19-48D3-BE97-422220080E43}"
!define FOLDERID_NetHood "{C5ABBF53-E17F-4121-8900-86626FC2C973}"
!define FOLDERID_NetworkFolder "{D20BEEC4-5CA8-4905-AE3B-BF251EA09B53}"
!define FOLDERID_OriginalImages "{2C36C0AA-5812-4b87-BFD0-4CD0DFB19B39}"
!define FOLDERID_PhotoAlbums "{69D2CF90-FC33-4FB7-9A0C-EBB0F0FCB43C}"
!define FOLDERID_Pictures "{33E28130-4E1E-4676-835A-98395C3BC3BB}"
!define FOLDERID_Playlists "{DE92C1C7-837F-4F69-A3BB-86E631204A23}"
!define FOLDERID_PrintersFolder "{76FC4E2D-D6AD-4519-A663-37BD56068185}"
!define FOLDERID_PrintHood "{9274BD8D-CFD1-41C3-B35E-B13F55A758F4}"
!define FOLDERID_Profile "{5E6C858F-0E22-4760-9AFE-EA3317B67173}"
!define FOLDERID_ProgramData "{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}"
!define FOLDERID_ProgramFiles "{905e63b6-c1bf-494e-b29c-65b732d3d21a}"
!define FOLDERID_ProgramFilesX64 "{6D809377-6AF0-444b-8957-A3773F02200E}"
!define FOLDERID_ProgramFilesX86 "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}"
!define FOLDERID_ProgramFilesCommon "{F7F1ED05-9F6D-47A2-AAAE-29D317C6F066}"
!define FOLDERID_ProgramFilesCommonX64 "{6365D5A7-0F0D-45E5-87F6-0DA56B6A4F7D}"
!define FOLDERID_ProgramFilesCommonX86 "{DE974D24-D9C6-4D3E-BF91-F4455120B917}"
!define FOLDERID_Programs "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"
!define FOLDERID_Public "{DFDF76A2-C82A-4D63-906A-5644AC457385}"
!define FOLDERID_PublicDesktop "{C4AA340D-F20F-4863-AFEF-F87EF2E6BA25}"
!define FOLDERID_PublicDocuments "{ED4824AF-DCE4-45A8-81E2-FC7965083634}"
!define FOLDERID_PublicDownloads "{3D644C9B-1FB8-4f30-9B45-F670235F79C0}"
!define FOLDERID_PublicGameTasks "{DEBF2536-E1A8-4c59-B6A2-414586476AEA}"
!define FOLDERID_PublicMusic "{3214FAB5-9757-4298-BB61-92A9DEAA44FF}"
!define FOLDERID_PublicPictures "{B6EBFB86-6907-413C-9AF7-4FC2ABF07CC5}"
!define FOLDERID_PublicVideos "{2400183A-6185-49FB-A2D8-4A392A602BA3}"
!define FOLDERID_QuickLaunch "{52a4f021-7b75-48a9-9f6b-4b87a210bc8f}"
!define FOLDERID_Recent "{AE50C081-EBD2-438A-8655-8A092E34987A}"
!define FOLDERID_RecycleBinFolder "{B7534046-3ECB-4C18-BE4E-64CD4CB7D6AC}"
!define FOLDERID_ResourceDir "{8AD10C31-2ADB-4296-A8F7-E4701232C972}"
!define FOLDERID_RoamingAppData "{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}"
!define FOLDERID_SampleMusic "{B250C668-F57D-4EE1-A63C-290EE7D1AA1F}"
!define FOLDERID_SamplePictures "{C4900540-2379-4C75-844B-64E6FAF8716B}"
!define FOLDERID_SamplePlaylists "{15CA69B3-30EE-49C1-ACE1-6B5EC372AFB5}"
!define FOLDERID_SampleVideos "{859EAD94-2E85-48AD-A71A-0969CB56A6CD}"
!define FOLDERID_SavedGames "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}"
!define FOLDERID_SavedSearches "{7d1d3a04-debb-4115-95cf-2f29da2920da}"
!define FOLDERID_SEARCH_CSC "{ee32e446-31ca-4aba-814f-a5ebd2fd6d5e}"
!define FOLDERID_SEARCH_MAPI "{98ec0e18-2098-4d44-8644-66979315a281}"
!define FOLDERID_SearchHome "{190337d1-b8ca-4121-a639-6d472d16972a}"
!define FOLDERID_SendTo "{8983036C-27C0-404B-8F08-102D10DCFD74}"
!define FOLDERID_SidebarDefaultParts "{7B396E54-9EC5-4300-BE0A-2482EBAE1A26}"
!define FOLDERID_SidebarParts "{A75D362E-50FC-4fb7-AC2C-A8BEAA314493}"
!define FOLDERID_StartMenu "{625B53C3-AB48-4EC1-BA1F-A1EF4146FC19}"
!define FOLDERID_Startup "{B97D20BB-F46A-4C97-BA10-5E3608430854}"
!define FOLDERID_SyncManagerFolder "{43668BF8-C14E-49B2-97C9-747784D784B7}"
!define FOLDERID_SyncResultsFolder "{289a9a43-be44-4057-a41b-587a76d7e7f9}"
!define FOLDERID_SyncSetupFolder "{0F214138-B1D3-4a90-BBA9-27CBC0C5389A}"
!define FOLDERID_System "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
!define FOLDERID_SystemX86 "{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}"
!define FOLDERID_Templates "{A63293E8-664E-48DB-A079-DF759E0509F7}"
!define FOLDERID_TreeProperties "{5b3749ad-b49f-49c1-83eb-15370fbd4882}"
!define FOLDERID_UserProfiles "{0762D272-C50A-4BB0-A382-697DCD729B80}"
!define FOLDERID_UsersFiles "{f3ce0f7c-4901-4acc-8648-d5d44b04ef8f}"
!define FOLDERID_Videos "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}"
!define FOLDERID_Windows "{F38BF404-1D43-42F2-9305-67DE0B28FC23}"

; KF_FLAG_ dwFlags values for use with SHGetKnownFolderPath
; force creation of the specified folder if it does not exist
!define KF_FLAG_CREATE "0x8000"
; specifies not to verify the folder's existence before attempting to retrieve the path or IDList
!define KF_FLAG_DONT_VERIFY "0x4000"
; gets the true system path for the folder, free of any aliased placeholders
!define KF_FLAG_NO_ALIAS "0x1000"
; initializes the folder using its Desktop.ini settings
!define KF_FLAG_INIT "0x0800"
; gets the default path for a known folder that is redirected elsewhere
!define KF_FLAG_DEFAULT_PATH "0x0400"
; gets the folder's default path independent of the current location of its parent
!define KF_FLAG_NOT_PARENT_RELATIVE "0x0200"
; build a simple pointer to an item identifier list (PIDL)
!define KF_FLAG_SIMPLE_IDLIST "0x0100"

!define SHGetFolderPath "!insertmacro _SHGetFolderPath"
!define SHGetKnownFolderPath "!insertmacro _SHGetKnownFolderPath"

!macro _SHGetFolderPath nFolder dwFlags outVar
	Push $0
	
	System::Call "shell32::SHGetFolderPath(in, i ${nFolder}, in, i ${dwFlags}, t .s) i.r0"
	${IfNot} $0 == 0
		Push "fail"
	${EndIf}
	
	Exch
	Pop $0
	Pop ${outVar}
!macroend

!macro _SHGetKnownFolderPath rfid dwFlags outVar
	Push $0
	Push $1
	Push $2
	System::Call "shell32::SHGetKnownFolderPath(g '${rfid}', i ${dwFlags} , in, *i.r1) i.r0"
	${If} $0 == 0
		System::Call 'kernel32::lstrlenW(i $1) i.r2'
		IntOp $2 $2 * 2
		System::Call '*$1(&w$2 .s)'
		System::Call 'ole32::CoTaskMemFree(i $1)'
	${Else}
		Push "fail"
	${EndIf}
	Exch 3
	Pop $0
	Pop $2
	Pop $1
	Pop ${outVar}
!macroend
