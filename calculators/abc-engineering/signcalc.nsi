; SignCalc v2.0 NSIS Installer Script
; Eagle Sign & Design Inc.
; Modeled after ABCENG/InstallShield pattern

!define APP_NAME      "SignCalc"
!define APP_FULL_NAME "SignCalc -- Sign Engineering Calculator"
!define APP_VERSION   "2.0"
!define PUBLISHER     "Eagle Sign & Design Inc."
!define INSTALL_DIR   "$PROGRAMFILES\Eagle Sign\SignCalc"
!define REGKEY        "Software\Eagle Sign\SignCalc"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\SignCalc"
!define MAIN_EXE      "SignCalc.html"

Name "${APP_FULL_NAME} v${APP_VERSION}"
OutFile "C:\Users\Brady.EAGLE\Desktop\SignCalc-Setup-v${APP_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REGKEY}" "InstallPath"
RequestExecutionLevel admin

; Modern UI
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "C:\SignCalculator\logo\SignCalc.ico"
!define MUI_UNICON "C:\SignCalculator\logo\SignCalc.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH
!define MUI_HEADERIMAGE_UNSTRETCH

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch SignCalc now"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchApp"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ==================== INSTALLER ====================
Section "SignCalc (required)" SecMain
  SectionIn RO

  SetOutPath "${INSTALL_DIR}"
  File "C:\Users\Brady.EAGLE\Desktop\SignX\calculators\abc-engineering\sign-engineering-calculator.html"

  SetOutPath "${INSTALL_DIR}\logo"
  File "C:\SignCalculator\logo\SignCalc.ico"
  File "C:\SignCalculator\logo\signcalc_256.png"
  File "C:\SignCalculator\logo\signcalc_48.png"

  ; Desktop shortcut
  CreateShortCut "$DESKTOP\SignCalc.lnk" \
    "$INSTDIR\sign-engineering-calculator.html" "" \
    "$INSTDIR\logo\SignCalc.ico" 0

  ; Start Menu
  CreateDirectory "$SMPROGRAMS\Eagle Sign"
  CreateShortCut "$SMPROGRAMS\Eagle Sign\SignCalc.lnk" \
    "$INSTDIR\sign-engineering-calculator.html" "" \
    "$INSTDIR\logo\SignCalc.ico" 0
  CreateShortCut "$SMPROGRAMS\Eagle Sign\Uninstall SignCalc.lnk" \
    "$INSTDIR\Uninstall.exe"

  ; Registry — app key
  WriteRegStr HKLM "${REGKEY}" "InstallPath"  "$INSTDIR"
  WriteRegStr HKLM "${REGKEY}" "Version"      "${APP_VERSION}"
  WriteRegStr HKLM "${REGKEY}" "Publisher"    "${PUBLISHER}"

  ; Registry — Add/Remove Programs
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName"          "${APP_FULL_NAME}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion"       "${APP_VERSION}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher"            "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayIcon"          "$INSTDIR\logo\SignCalc.ico"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString"      "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair" 1
  ; Approximate size in KB
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" 200

  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; ==================== UNINSTALLER ====================
Section "Uninstall"
  Delete "$INSTDIR\sign-engineering-calculator.html"
  Delete "$INSTDIR\logo\SignCalc.ico"
  Delete "$INSTDIR\logo\signcalc_256.png"
  Delete "$INSTDIR\logo\signcalc_48.png"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR\logo"
  RMDir  "$INSTDIR"
  RMDir  "$PROGRAMFILES\Eagle Sign"

  Delete "$DESKTOP\SignCalc.lnk"
  Delete "$SMPROGRAMS\Eagle Sign\SignCalc.lnk"
  Delete "$SMPROGRAMS\Eagle Sign\Uninstall SignCalc.lnk"
  RMDir  "$SMPROGRAMS\Eagle Sign"

  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "${REGKEY}"
SectionEnd

; ==================== FUNCTIONS ====================
Function LaunchApp
  ExecShell "open" "$INSTDIR\sign-engineering-calculator.html"
FunctionEnd
