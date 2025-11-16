' ============================================
' FLINK SIGN PRO - MODERN TOOLBAR SYSTEM
' Professional Sign Fabrication Suite for CorelDRAW
' Version 2.0 - Modern UI Implementation
' ============================================

Option Explicit

' Windows API declarations for modern UI
Private Declare PtrSafe Function SetWindowLong Lib "user32" Alias "SetWindowLongA" (ByVal hwnd As Long, ByVal nIndex As Long, ByVal dwNewLong As Long) As Long
Private Declare PtrSafe Function GetWindowLong Lib "user32" Alias "GetWindowLongA" (ByVal hwnd As Long, ByVal nIndex As Long) As Long
Private Declare PtrSafe Function SetWindowPos Lib "user32" (ByVal hwnd As Long, ByVal hWndInsertAfter As Long, ByVal x As Long, ByVal y As Long, ByVal cx As Long, ByVal cy As Long, ByVal wFlags As Long) As Long

' Global toolbar reference
Public g_FlinkToolbar As CommandBar
Public g_IsToolbarVisible As Boolean

' ============================================
' MAIN LAUNCHER - Add this to your toolbar icon
' ============================================
Sub FlinkSignPro_Launch()
    ' Toggle toolbar visibility
    If g_IsToolbarVisible Then
        HideFlinkToolbar
    Else
        ShowFlinkToolbar
    End If
End Sub

' ============================================
' SHOW MODERN TOOLBAR
' ============================================
Sub ShowFlinkToolbar()
    On Error Resume Next
    
    ' Remove existing toolbar if present
    Application.CommandBars("Flink Sign Pro").Delete
    
    ' Create new modern toolbar
    Set g_FlinkToolbar = Application.CommandBars.Add("Flink Sign Pro", msoBarFloating, False, True)
    
    With g_FlinkToolbar
        .Visible = True
        .Position = msoBarFloating
        .Left = Application.Width - 400
        .Top = 100
        .Protection = msoBarNoChangeVisible
        
        ' === HEADER SECTION ===
        AddToolbarHeader
        
        ' === TAKEOFF SECTION ===
        AddSectionHeader "TAKEOFF && MEASURE"
        AddModernButton "Complete Takeoff", "SignageTakeoffMaster", 3975, "Full sign measurement and material calculation"
        AddModernButton "Individual Letters", "AnalyzeIndividualLetters", 225, "Analyze each letter separately"
        AddModernButton "Quick Estimate", "QuickBoundingBoxMethod", 1088, "Fast bounding box calculation"
        
        ' === LED & POWER SECTION ===
        AddSectionHeader "LED && POWER"
        AddModernButton "LED System Calc", "FlinkLEDPowerSystem", 1952, "Complete LED and power configuration"
        AddModernButton "Quick Power Check", "FlinkQuickSystemCheck", 984, "Fast power requirements estimate"
        AddModernButton "Power Diagram", "FlinkPowerDiagram", 656, "Visual power layout diagram"
        
        ' === MATERIALS SECTION ===
        AddSectionHeader "MATERIALS"
        AddModernButton "Material Summary", "MaterialQuantitySummary", 928, "Complete material quantities"
        AddModernButton "Optimization Report", "GenerateMaterialOptimization", 1086, "Material usage optimization"
        AddModernButton "Raceway Calc", "CalculateRaceway", 3844, "Cabinet and raceway calculations"
        
        ' === EXPORT SECTION ===
        AddSectionHeader "EXPORT && REPORTS"
        AddModernButton "Modern Export", "ExportModernTakeoff", 3738, "Export to modern format"
        AddModernButton "ABC Labor Data", "GenerateABCLaborData", 3095, "Generate ABC pricing data"
        AddModernButton "Compare Methods", "ComparePerimeterMethods", 465, "Compare calculation methods"
        
        ' === SETTINGS SECTION ===
        AddSeparator
        AddModernButton "Settings", "FlinkSettings", 2950, "Configure defaults"
        AddModernButton "Help", "FlinkHelp", 984, "Documentation and support"
        
        ' Style the toolbar
        .Width = 220
    End With
    
    g_IsToolbarVisible = True
    
    ' Show welcome message on first launch
    If GetSetting("FlinkSignPro", "Settings", "FirstRun", "Yes") = "Yes" Then
        ShowWelcomeScreen
        SaveSetting "FlinkSignPro", "Settings", "FirstRun", "No"
    End If
    
End Sub

' ============================================
' ADD TOOLBAR HEADER
' ============================================
Sub AddToolbarHeader()
    Dim headerButton As CommandBarButton
    
    Set headerButton = g_FlinkToolbar.Controls.Add(msoControlButton)
    With headerButton
        .Caption = "FLINK SIGN PRO 2.0"
        .Style = msoButtonCaption
        .BeginGroup = True
        .Enabled = False
    End With
    
    AddSeparator
End Sub

' ============================================
' ADD SECTION HEADER
' ============================================
Sub AddSectionHeader(sectionName As String)
    Dim sectionButton As CommandBarButton
    
    AddSeparator
    
    Set sectionButton = g_FlinkToolbar.Controls.Add(msoControlButton)
    With sectionButton
        .Caption = "━━━ " & sectionName & " ━━━"
        .Style = msoButtonCaption
        .Enabled = False
    End With
End Sub

' ============================================
' ADD MODERN STYLED BUTTON
' ============================================
Sub AddModernButton(buttonCaption As String, macroName As String, iconID As Long, tooltip As String)
    Dim newButton As CommandBarButton
    
    Set newButton = g_FlinkToolbar.Controls.Add(msoControlButton)
    With newButton
        .Caption = "   " & buttonCaption
        .OnAction = macroName
        .Style = msoButtonIconAndCaption
        .FaceId = iconID
        .TooltipText = tooltip
        .BeginGroup = False
    End With
End Sub

' ============================================
' ADD SEPARATOR
' ============================================
Sub AddSeparator()
    Dim sepButton As CommandBarButton
    Set sepButton = g_FlinkToolbar.Controls.Add(msoControlButton)
    With sepButton
        .Caption = ""
        .Enabled = False
        .BeginGroup = True
    End With
End Sub

' ============================================
' HIDE TOOLBAR
' ============================================
Sub HideFlinkToolbar()
    On Error Resume Next
    g_FlinkToolbar.Visible = False
    g_IsToolbarVisible = False
End Sub

' ============================================
' SETTINGS DIALOG
' ============================================
Sub FlinkSettings()
    Dim msg As String
    Dim currentDepth As String
    Dim currentWaste As String
    
    ' Get current settings
    currentDepth = GetSetting("FlinkSignPro", "Defaults", "ReturnDepth", "5")
    currentWaste = GetSetting("FlinkSignPro", "Defaults", "WasteFactor", "15")
    
    msg = "FLINK SIGN PRO SETTINGS" & vbCrLf & vbCrLf
    msg = msg & "Current Defaults:" & vbCrLf
    msg = msg & "• Return Depth: " & currentDepth & " inches" & vbCrLf
    msg = msg & "• Waste Factor: " & currentWaste & "%" & vbCrLf & vbCrLf
    msg = msg & "1 = Change Return Depth" & vbCrLf
    msg = msg & "2 = Change Waste Factor" & vbCrLf
    msg = msg & "3 = Reset to Factory Defaults" & vbCrLf
    msg = msg & "4 = Export Settings" & vbCrLf
    
    Dim choice As String
    choice = InputBox(msg, "Flink Settings", "0")
    
    Select Case choice
        Case "1"
            Dim newDepth As String
            newDepth = InputBox("Enter default return depth (inches):", "Return Depth", currentDepth)
            If IsNumeric(newDepth) Then
                SaveSetting "FlinkSignPro", "Defaults", "ReturnDepth", newDepth
                MsgBox "Return depth updated to " & newDepth & " inches", vbInformation
            End If
            
        Case "2"
            Dim newWaste As String
            newWaste = InputBox("Enter waste factor (%):", "Waste Factor", currentWaste)
            If IsNumeric(newWaste) Then
                SaveSetting "FlinkSignPro", "Defaults", "WasteFactor", newWaste
                MsgBox "Waste factor updated to " & newWaste & "%", vbInformation
            End If
            
        Case "3"
            SaveSetting "FlinkSignPro", "Defaults", "ReturnDepth", "5"
            SaveSetting "FlinkSignPro", "Defaults", "WasteFactor", "15"
            MsgBox "Settings reset to factory defaults", vbInformation
            
        Case "4"
            ExportSettings
    End Select
End Sub

' ============================================
' HELP SYSTEM
' ============================================
Sub FlinkHelp()
    Dim helpText As String
    
    helpText = "FLINK SIGN PRO - QUICK REFERENCE" & vbCrLf & vbCrLf
    
    helpText = helpText & "TAKEOFF TOOLS:" & vbCrLf
    helpText = helpText & "• Complete Takeoff - Full analysis of selected shapes" & vbCrLf
    helpText = helpText & "• Individual Letters - Letter-by-letter breakdown" & vbCrLf
    helpText = helpText & "• Quick Estimate - Fast bounding box method" & vbCrLf & vbCrLf
    
    helpText = helpText & "KEY FEATURES:" & vbCrLf
    helpText = helpText & "✓ Actual perimeter calculation (not bounding box)" & vbCrLf
    helpText = helpText & "✓ Automatic material optimization" & vbCrLf
    helpText = helpText & "✓ UL 48 compliant electrical calculations" & vbCrLf
    helpText = helpText & "✓ 2025 labor rate integration" & vbCrLf & vbCrLf
    
    helpText = helpText & "WORKFLOW:" & vbCrLf
    helpText = helpText & "1. Select your sign artwork" & vbCrLf
    helpText = helpText & "2. Run Complete Takeoff" & vbCrLf
    helpText = helpText & "3. Run LED System Calc" & vbCrLf
    helpText = helpText & "4. Export results" & vbCrLf & vbCrLf
    
    helpText = helpText & "Support: support@flinksignpro.com" & vbCrLf
    helpText = helpText & "Version: 2.0.2025"
    
    MsgBox helpText, vbInformation, "Flink Sign Pro Help"
End Sub

' ============================================
' WELCOME SCREEN
' ============================================
Sub ShowWelcomeScreen()
    Dim welcome As String
    
    welcome = "Welcome to FLINK SIGN PRO 2.0!" & vbCrLf & vbCrLf
    welcome = welcome & "Professional Sign Fabrication Suite" & vbCrLf & vbCrLf
    welcome = welcome & "What's New:" & vbCrLf
    welcome = welcome & "• Modern floating toolbar interface" & vbCrLf
    welcome = welcome & "• Actual perimeter calculations" & vbCrLf
    welcome = welcome & "• Integrated LED & power system" & vbCrLf
    welcome = welcome & "• 2025 labor standards" & vbCrLf
    welcome = welcome & "• Material optimization reports" & vbCrLf & vbCrLf
    welcome = welcome & "Click the Flink icon anytime to show/hide toolbar"
    
    MsgBox welcome, vbInformation, "Welcome to Flink Sign Pro"
End Sub

' ============================================
' EXPORT SETTINGS
' ============================================
Sub ExportSettings()
    Dim filePath As String
    Dim content As String
    
    filePath = Application.Path & "\FlinkSignPro_Settings.ini"
    
    content = "[FlinkSignPro Settings]" & vbCrLf
    content = content & "Version=2.0" & vbCrLf
    content = content & "ReturnDepth=" & GetSetting("FlinkSignPro", "Defaults", "ReturnDepth", "5") & vbCrLf
    content = content & "WasteFactor=" & GetSetting("FlinkSignPro", "Defaults", "WasteFactor", "15") & vbCrLf
    content = content & "ExportPath=" & GetSetting("FlinkSignPro", "Defaults", "ExportPath", Application.Path) & vbCrLf
    
    Open filePath For Output As #1
    Print #1, content
    Close #1
    
    MsgBox "Settings exported to:" & vbCrLf & filePath, vbInformation
End Sub

' ============================================
' QUICK ACCESS TOOLBAR SETUP
' ============================================
Sub SetupQuickAccessButton()
    ' This creates the launcher button for your toolbar
    ' Add this macro to a button with your custom icon
    
    MsgBox "QUICK ACCESS SETUP" & vbCrLf & vbCrLf & _
           "To add Flink Sign Pro to your toolbar:" & vbCrLf & vbCrLf & _
           "1. Right-click any toolbar" & vbCrLf & _
           "2. Select Customize > Commands" & vbCrLf & _
           "3. Choose 'Macros' from categories" & vbCrLf & _
           "4. Drag 'FlinkSignPro_Launch' to toolbar" & vbCrLf & _
           "5. Right-click the new button" & vbCrLf & _
           "6. Change icon to your Flink logo" & vbCrLf & vbCrLf & _
           "The button will toggle the Flink toolbar on/off", _
           vbInformation, "Setup Instructions"
End Sub

' ============================================
' AUTO-SETUP ON FIRST RUN
' ============================================
Sub AutoSetup()
    ' Initialize default settings
    If GetSetting("FlinkSignPro", "Settings", "Initialized", "No") = "No" Then
        SaveSetting "FlinkSignPro", "Defaults", "ReturnDepth", "5"
        SaveSetting "FlinkSignPro", "Defaults", "WasteFactor", "15"
        SaveSetting "FlinkSignPro", "Defaults", "ExportPath", Application.Path
        SaveSetting "FlinkSignPro", "Settings", "Initialized", "Yes"
        SaveSetting "FlinkSignPro", "Settings", "FirstRun", "Yes"
    End If
End Sub

' ============================================
' INITIALIZATION
' ============================================
Sub FlinkSignPro_Initialize()
    AutoSetup
    ShowFlinkToolbar
End Sub