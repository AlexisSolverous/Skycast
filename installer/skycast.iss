; Inno Setup installer for SkyCast.
; The app is installed under Program Files and keeps user data in %APPDATA%\SkyCast.

[Setup]
AppName=SkyCast
AppVersion=1.0.0
DefaultDirName={commonpf64}\SkyCast
DefaultGroupName=SkyCast
Compression=lzma
SolidCompression=yes
OutputBaseFilename=SkyCast-setup
OutputDir=.
AppPublisher=SkyCast
PrivilegesRequired=admin
CreateAppDir=yes
UninstallDisplayIcon={app}\SkyCast.exe

[Files]
Source: "C:\Users\kenne\.copilot\repos\copilot-worktrees\Skycast\godly-rimuru-vigilant-bassoon\dist\SkyCast\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{commonprograms}\SkyCast"; Filename: "{app}\SkyCast.exe"
Name: "{commondesktop}\SkyCast"; Filename: "{app}\SkyCast.exe"

[Run]
Filename: "{app}\SkyCast.exe"; Description: "Launch SkyCast"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\SkyCast"
