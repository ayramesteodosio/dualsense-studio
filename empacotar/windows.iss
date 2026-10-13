#define HidHideUrl "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe"

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
ShowLanguageDialog=auto
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
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
ptbr.Complementos=Complementos:
en.Complementos=Extras:
ptbr.Autostart=Iniciar com o Windows (abre escondido, para o modo carregar e os avisos funcionarem sozinhos)
en.Autostart=Start with Windows (opens hidden, so charging mode and alerts work on their own)
ptbr.HidHide=Instalar o HidHide (recomendado): no modo carregar, esconde o controle dos jogos e da Steam
en.HidHide=Install HidHide (recommended): hides the controller from games and Steam in charging mode
ptbr.InstalandoHidHide=Instalando o HidHide...
en.InstalandoHidHide=Installing HidHide...
ptbr.BaixandoTitulo=Baixando o HidHide
en.BaixandoTitulo=Downloading HidHide
ptbr.BaixandoTexto=Aguarde enquanto o HidHide é baixado do site oficial.
en.BaixandoTexto=Please wait while HidHide is downloaded from its official site.
ptbr.FalhaBaixar=Não consegui baixar o HidHide (%1). O app será instalado sem ele.
en.FalhaBaixar=Couldn't download HidHide (%1). The app will be installed without it.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "{cm:Autostart}"; GroupDescription: "{cm:Complementos}"; Flags: unchecked
Name: "hidhide"; Description: "{cm:HidHide}"; GroupDescription: "{cm:Complementos}"; Check: not HidHideInstalado

[Files]
Source: "..\dist\DualSense Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DualSense Studio"; ValueData: """{app}\DualSense Studio.exe"" --segundo-plano"; Flags: uninsdeletevalue; Tasks: autostart; Check: not WizardSilent
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Painel do DualSense"; Flags: deletevalue; Tasks: autostart; Check: not WizardSilent

[Icons]
Name: "{autoprograms}\DualSense Studio"; Filename: "{app}\DualSense Studio.exe"
Name: "{autodesktop}\DualSense Studio"; Filename: "{app}\DualSense Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\HidHide.exe"; StatusMsg: "{cm:InstalandoHidHide}"; Flags: shellexec waituntilterminated skipifdoesntexist; Tasks: hidhide
Filename: "{app}\DualSense Studio.exe"; Description: "{cm:LaunchProgram,DualSense Studio}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\DualSense Studio.exe"; Flags: nowait; Check: WizardSilent

[Code]
var
  Baixar: TDownloadWizardPage;

function HidHideInstalado: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe')) or
    FileExists(ExpandConstant('{commonpf64}\Nefarius Software Solutions e.U\HidHide\x64\HidHideCLI.exe'));
end;

procedure InitializeWizard;
begin
  Baixar := CreateDownloadPage(CustomMessage('BaixandoTitulo'), CustomMessage('BaixandoTexto'), nil);
end;

function EntendeSair: Boolean;
var
  Versao: String;
begin
  Result := False;
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9C4A7E2B-1D3F-4A6C-8E5B-7F2A9D1C3E64}_is1', 'DisplayVersion', Versao) then
    if not RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9C4A7E2B-1D3F-4A6C-8E5B-7F2A9D1C3E64}_is1', 'DisplayVersion', Versao) then
      Exit;
  Result := (Versao <> '') and (Copy(Versao, 1, 4) <> '0.1.') and (Versao <> '0.2.0');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\DualSense Studio.exe')) and EntendeSair() then
  begin
    Exec(ExpandConstant('{app}\DualSense Studio.exe'), '--sair', '', SW_HIDE, ewWaitUntilTerminated, Codigo);
    Sleep(2500);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DualSense Studio');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('hidhide') then
  begin
    Baixar.Clear;
    Baixar.Add('{#HidHideUrl}', 'HidHide.exe', '');
    Baixar.Show;
    try
      try
        Baixar.Download;
      except
        SuppressibleMsgBox(FmtMessage(CustomMessage('FalhaBaixar'), [GetExceptionMessage]), mbError, MB_OK, IDOK);
      end;
    finally
      Baixar.Hide;
    end;
  end;
end;
