Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "C:\Scripts\GandHSync\auto_sync_when_connected.bat" & Chr(34), 0
Set WshShell = Nothing