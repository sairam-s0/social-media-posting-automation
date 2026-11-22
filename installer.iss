; Inno Setup Script for AutoSocial Poster
; Generates a professional Windows installer poster-v2.exe with activation check, desktop shortcut and clean uninstaller

#define MyAppName "AutoSocial Poster"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "AutoSocial Technologies"
#define MyAppURL "https://github.com/autosocial-poster"
#define MyAppExeName "poster-v2.exe"

[Setup]
AppId={{B42E7A91-2E91-4C5D-85B9-6C10D23F8901}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\AutoSocial Poster
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_dist
OutputBaseFilename=poster-v2
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
PasswordLabel1=This installation requires an Activation Key.
PasswordLabel3=Please enter your product Activation Key below to begin installation:
PasswordEditLabel=&Activation Key:

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\poster-v2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Dirs]
; Pre-provision user runtime data & log directories in %APPDATA%\AutoSocialPoster
Name: "{userappdata}\AutoSocialPoster\data"; Flags: uninsneveruninstall
Name: "{userappdata}\AutoSocialPoster\logs"; Flags: uninsneveruninstall
Name: "{userappdata}\AutoSocialPoster\config"; Flags: uninsneveruninstall

[Code]
var
  SavedActivationKey: String;

function CheckPassword(Password: String): Boolean;
var
  Key: String;
begin
  Key := Uppercase(Trim(Password));
  if (Key = 'ASPC-PRO2-2026-X999-9364') or (Key = 'POSTER-V2-PRO-2026') then
  begin
    SavedActivationKey := Key;
    Result := True;
  end
  else
    Result := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, LicenseFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ExpandConstant('{userappdata}\AutoSocialPoster\config');
    ForceDirectories(ConfigDir);
    LicenseFile := ConfigDir + '\license.key';
    SaveStringToFile(LicenseFile, SavedActivationKey, False);
  end;
end;
