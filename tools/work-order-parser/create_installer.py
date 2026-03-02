import os

# Path to the .exe and icon
exe_path = os.path.abspath('dist/work_order_parser.exe')
icon_path = os.path.abspath('assets/eagle_sign_icon.ico')

inno_script = f'''
[Setup]
AppName=Eagle Sign Co. Work Order Parser
AppVersion=1.0
DefaultDirName={{autopf}}\EagleSignCo\WorkOrderParser
DefaultGroupName=Eagle Sign Co
OutputDir=dist
OutputBaseFilename=WorkOrderParserInstaller
SetupIconFile={icon_path}
Compression=lzma
SolidCompression=yes

[Files]
Source: "{exe_path}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\Work Order Parser"; Filename: "{{app}}\work_order_parser.exe"; IconFilename: "{icon_path}"
Name: "{{userdesktop}}\Work Order Parser"; Filename: "{{app}}\work_order_parser.exe"; IconFilename: "{icon_path}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

; --- Future: Auto-update and advanced installer features ---
; [Run]
; Filename: "{{app}}\\updater.exe"; Description: "Check for updates automatically"; Flags: nowait postinstall skipifsilent
'''

with open('dist/installer.iss', 'w') as f:
    f.write(inno_script)

print('Inno Setup script generated at dist/installer.iss')
print('To build the installer, open installer.iss with Inno Setup Compiler and click Build.') 