# dcs-dync

Dynamic Campaign server for DCS World flight simulator

#### Notice about MarkDown

If you allow the installer to perform all the optional operations, the following will not matter, but if you do it
manually, it will:

You will probably want to read this file in an application which supports MarkDown rendering, or the number of
backslashes at different places of the text will be confusing. In the text body, two backslashes make for one backslash
in rendered text, but in literal sections (between three backticks) two backslashes mean two literal backslashes. 

## Regarding updates to DCS World

DCS World may revert one of the necessary changes whenever it updates itself. If this happens, there will be a message
box in DCS World upon mission start to inform you that the change needs to be made again. You can either use 
"update-missionscripting.bat" in the server installation folder to make it automatically (a backup of your original file
is made to the same folder, named "MissionScripting-backup.lua") or you can look up the change in the manual
installation section below. It is the change to the file [DCS World folder]\\Scripts\\MissionScripting.lua .

## Installation

The easiest way to install the software is to use the executable installer that is supplied for all release versions. It
will install the server software as a normal Windows application. Python 3.7 with the necessary libraries is bundled
with the executable. The installer will offer the option to automatically modify your DCS World game installation to
communicate with the software, or you can make the changes yourself. If you allow the installer to make them, the
uninstaller will be able to automatically revert the changes upon uninstallation.

### Making the changes to DCS World Manually

If you allowed the installer to do everything, you can skip this section. If you didn't, then the necessary files to
make the changes to your DCS World game installation are found in the folder "DCS World Files" in your server
installation folder. First, create the folder C:\\Users\\[Your Windows user name]\\Saved Games\\
["DCS" or "DCS.openbeta"]\\Scripts\\ if it doesn't already exist. The exact path depends on whether you have the Release
version or the OpenBeta version. If you have both, then do the same to both locations.

Then place these files in the following locations:

- dync_httpfix.lua: [DCS World folder]\\LuaSocket\\
- dync_urlfix.lua: [DCS World folder]\\LuaSocket\\
- DynC.lua: C:\\Users\\[Your Windows user name]\\Saved Games\\["DCS" or "DCS.openbeta"]\\Scripts\\

You do not need the other two files yet. They are for creating new campaigns from scratch, and are to be included in
.miz files. Next, open the file [DCS World folder]\\Scripts\\MissionScripting.lua . Two lines must be added to it. These
will give DynC.lua certain additional permissions that such scripts would not normally have. This is needed for the
http-based communications between DCS World and the server software. If you add these lines manually, add them exactly
as below, and don't put any whitespace after the lines. This will allow the uninstaller to remove the lines when you
uninstall the software. *These lines go below the already existing line which says:
dofile('Scripts/ScriptingSystem.lua')*

```
dync = {}
dofile(lfs.writedir().."\\Scripts\\DynC.lua")
```

## Using the software

The server software must be running before you start a mission file that has a dynamic campaign. If a campaign was
already in progress, there will be a simplified map of it in the server window when you launch it. If you are starting a
new campaign, the map will appear when you first start the mission as the multiplayer host in DCS World. The game will
communicate the structure of the map to the server at this point.

The campaign situation is saved to C:\\Users\\[Your Windows user name]\\DCS-DynC\\ and is persistent, so that you can
shut down the server between "turns". The server log and configuration file are in the same folder. If a .cfg file
didn't already exist, it will be created with default contents. You can also always reset the entire state of the server
by deleting the file "campaign.json".

Every time the DCS World multiplayer host ends the mission, the campaign will be simulated for one turn. Units will move
by the distance of two adjacent nodes. If enemy forces move through the same path on the same turn, combat between them
will take place on the next mission. Infantry units slow down the advance of enemy vehicles, taking casualties along the
way, and the support unit will heal infantry. When at least one tank is at the enemy headquarters, and would have killed
all the infantry in it by the next turn, that side is declared the winner. If both players enter each other's bases on
the same turn, it is declared a draw. Otherwise the campaign can only end with the players agreeing to stop playing. The
rules will be described more accurately in another file, soon.

If the campaign creator has chosen to support it in a campaign, you can place the campaign map from DCS World Mission
Editor as the background of the dynamically created map in the server window. In the Mozdok example campaign this is
supported, and you will find the appropriate background in the same folder as the .miz file. Activate it by clicking
File - Set background image, making sure that Background visible is checked.

## Creating campaigns

See [Campaign Creator Guide](doc/campaign-creator-guide.md).

## Optional advanced section: Not using the precompiled installer

Skip the two sections below if you used the installer.

### Running the server with your own Python interpreter

For advanced users, it is not necessary to use the installer at all. You can use your own Python 3.6 or 3.7 environment,
and optionally create a virtualenv based on requirements.txt, available at the root of the project directory.
Instructions are not provided here, but it is no different than running any Python program that supplies a
requirements.txt with it. The file to run is dyncserver.py . Working directory must be the subdirectory "dyncserver" of
the project directory.

### Building your own installer

In a Python environment that contains everything in requirements.txt and a Python 3.6 or 3.7 interpreter, and the
PyInstaller library, execute "pyinstaller dyncserver.spec" in command prompt. Use the default output directory (in other
words, no additional parameters to pyinstaller), so that NSIS will locate the created files. After the "dist" directory
has been created under dyncserver, use NSIS from https://nsis.sourceforge.io/Main_Page to compile the file dync.nsi in
the "installer" directory under the project directory. If you allowed NSIS to create the context menu items, select the
file, right-click on it, and choose "Compile NSIS Script". This will create the installer executable in the same folder.

### Other operating systems

The intention is to eventually support any operating system which can run Python 3.6/3.7 so that you can run the server
also remotely instead of only locally. At this point that is unsupported, and is to be attempted at your own risk.