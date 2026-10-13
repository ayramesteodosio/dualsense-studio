#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{9C4A7E2B-1D3F-4A6C-8E5B-7F2A9D1C3E64}
AppName=DualSense Studio
AppVersion={#Versao}
AppPublisher=ayramesteodosio
AppPublisherURL=https://github.com/ayramesteodosio/dualsense-studio
DefaultDirName={autopf}\DualSense Studio
DefaultGroupName=DualSense Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Instalar-DualSense-Studio
SetupIconFile=icones\dualsense-studio.ico
UninstallDisplayIcon={app}\DualSense Studio.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\DualSense Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DualSense Studio"; Filename: "{app}\DualSense Studio.exe"
Name: "{autodesktop}\DualSense Studio"; Filename: "{app}\DualSense Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DualSense Studio.exe"; Description: "{cm:LaunchProgram,DualSense Studio}"; Flags: nowait postinstall skipifsilent
