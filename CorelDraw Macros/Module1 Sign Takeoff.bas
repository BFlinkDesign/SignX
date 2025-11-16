Attribute VB_Name = "Module1"
' ============================================
' MODULE 1: MAIN TAKEOFF MACROS
' ============================================

' ============================================
' ULTIMATE SIGN TAKEOFF MACROS FOR CORELDRAW
' Modern Industry Standards 2025
' Labor Hours and Material Quantities Only
' Compatible with CorelDRAW 2021 and FlinkSignMakerPRO
' ============================================

Option Explicit

' Global constants for unit conversion
Private Const INCHES_TO_FEET As Double = 0.0833333
Private Const MM_TO_INCHES As Double = 0.0393701
Private Const CORELDRAW_TO_INCHES As Double = 0.001

' Main takeoff structure
Private Type SignTakeoff
    TotalFaceArea As Double
    TotalPerimeter As Double
    LetterCount As Long
    MaxHeight As Double
    MinHeight As Double
    TotalWidth As Double
    MaterialWaste As Double
    ReturnDepth As Double
    LaborHours As Double
End Type

' ============================================
' MAIN TAKEOFF MACRO - Run This First
' ============================================
Sub SignageTakeoffMaster()
    Dim s As Shape
    Dim sr As ShapeRange
    Dim takeoff As SignTakeoff
    Dim outputText As String
    
    ' Check if anything is selected
    If ActiveSelectionRange.Count = 0 Then
        MsgBox "Please select objects to measure", vbExclamation
        Exit Sub
    End If
    
    ' Initialize takeoff
    takeoff.ReturnDepth = 5 ' Default 5" return depth
    takeoff.MaterialWaste = 1.15 ' 15% waste factor
    
    ' Convert all to curves first
    ConvertAllToCurves
    
    ' Get measurements
    Set sr = ActiveSelectionRange
    takeoff = CalculateCompleteTakeoff(sr)
    
    ' Generate report
    outputText = GenerateTakeoffReport(takeoff)
    
    ' Display results
    DisplayTakeoffResults outputText
    
    ' Export to CSV
    If MsgBox("Export takeoff to CSV?", vbYesNo) = vbYes Then
        ExportTakeoffToCSV takeoff
    End If
End Sub

' ============================================
' CONVERT ALL TO CURVES/OUTLINES
' ============================================
Sub ConvertAllToCurves()
    Dim s As Shape
    Dim sr As ShapeRange
    
    On Error Resume Next
    
    Set sr = ActiveSelectionRange
    
    ' Convert text to curves
    For Each s In sr
        If s.Type = cdrTextShape Then
            s.ConvertToCurves
        End If
    Next s
    
    ' Convert all objects to curves
    sr.ConvertToCurves
    
    ' Break apart any combined curves
    For Each s In sr
        If s.Type = cdrCurveShape Then
            s.BreakApartEx
        End If
    Next s
    
End Sub

' ============================================
' CALCULATE COMPLETE TAKEOFF
' ============================================
Function CalculateCompleteTakeoff(sr As ShapeRange) As SignTakeoff
    Dim s As Shape
    Dim result As SignTakeoff
    Dim shapeArea As Double
    Dim shapePerimeter As Double
    
    result.LetterCount = 0
    result.TotalFaceArea = 0
    result.TotalPerimeter = 0
    result.MaxHeight = 0
    result.MinHeight = 999999
    
    For Each s In sr
        If s.Type = cdrCurveShape Or s.Type = cdrRectangleShape Or s.Type = cdrEllipseShape Then
            ' Get area in square inches
            shapeArea = GetShapeArea(s)
            result.TotalFaceArea = result.TotalFaceArea + shapeArea
            
            ' Get perimeter in inches - THIS IS THE KEY FOR RETURNS!
            shapePerimeter = GetShapePerimeter(s)
            result.TotalPerimeter = result.TotalPerimeter + shapePerimeter
            
            ' Track heights
            Dim height As Double
            height = s.SizeHeight * CORELDRAW_TO_INCHES
            If height > result.MaxHeight Then result.MaxHeight = height
            If height < result.MinHeight Then result.MinHeight = height
            
            ' Count letters
            result.LetterCount = result.LetterCount + 1
        End If
    Next s
    
    ' Get overall width
    result.TotalWidth = sr.SizeWidth * CORELDRAW_TO_INCHES
    
    ' Apply return depth (default 5")
    result.ReturnDepth = 5
    
    CalculateCompleteTakeoff = result
End Function

' ============================================
' GET ACTUAL SHAPE AREA (NOT BOUNDING BOX)
' ============================================
Function GetShapeArea(s As Shape) As Double
    Dim area As Double
    
    On Error Resume Next
    
    ' Get curve area
    If s.Type = cdrCurveShape Then
        area = s.Curve.area
    ElseIf s.Type = cdrRectangleShape Then
        area = s.SizeWidth * s.SizeHeight
    ElseIf s.Type = cdrEllipseShape Then
        area = (s.SizeWidth / 2) * (s.SizeHeight / 2) * 3.14159
    End If
    
    ' Convert to square inches
    GetShapeArea = area * CORELDRAW_TO_INCHES * CORELDRAW_TO_INCHES
End Function

' ============================================
' GET ACTUAL SHAPE PERIMETER (NOT BOUNDING BOX!)
' This is critical for channel letter returns
' ============================================
Function GetShapePerimeter(s As Shape) As Double
    Dim perimeter As Double
    Dim seg As Segment
    Dim subPath As subPath
    
    On Error Resume Next
    
    perimeter = 0
    
    If s.Type = cdrCurveShape Then
        ' Calculate actual curve length
        For Each subPath In s.Curve.SubPaths
            For Each seg In subPath.Segments
                perimeter = perimeter + seg.Length
            Next seg
        Next subPath
    ElseIf s.Type = cdrRectangleShape Then
        ' Rectangle perimeter
        perimeter = 2 * (s.SizeWidth + s.SizeHeight)
    ElseIf s.Type = cdrEllipseShape Then
        ' Ellipse perimeter (approximation)
        Dim a As Double, b As Double
        a = s.SizeWidth / 2
        b = s.SizeHeight / 2
        perimeter = 3.14159 * (3 * (a + b) - Sqr((3 * a + b) * (a + 3 * b)))
    End If
    
    ' Convert to inches
    GetShapePerimeter = perimeter * CORELDRAW_TO_INCHES
End Function

' ============================================
' GENERATE TAKEOFF REPORT
' ============================================
Function GenerateTakeoffReport(takeoff As SignTakeoff) As String
    Dim report As String
    Dim faceAreaSqFt As Double
    Dim perimeterFt As Double
    Dim returnAreaSqFt As Double
    
    ' Convert to feet
    faceAreaSqFt = (takeoff.TotalFaceArea / 144) ' Convert sq inches to sq ft
    perimeterFt = takeoff.TotalPerimeter / 12 ' Convert inches to feet
    returnAreaSqFt = (perimeterFt * takeoff.ReturnDepth) / 12
    
    report = "=== SIGNAGE TAKEOFF REPORT ===" & vbCrLf & vbCrLf
    
    report = report & "LETTER/ELEMENT COUNT: " & takeoff.LetterCount & vbCrLf
    report = report & "MAX HEIGHT: " & Format(takeoff.MaxHeight, "0.00") & " inches" & vbCrLf
    report = report & "MIN HEIGHT: " & Format(takeoff.MinHeight, "0.00") & " inches" & vbCrLf
    report = report & "OVERALL WIDTH: " & Format(takeoff.TotalWidth / 12, "0.00") & " feet" & vbCrLf & vbCrLf
    
    report = report & "CHANNEL LETTER CALCULATIONS:" & vbCrLf
    report = report & "Face Area (single): " & Format(faceAreaSqFt, "0.00") & " sq ft" & vbCrLf
    report = report & "Face Area (double): " & Format(faceAreaSqFt * 2, "0.00") & " sq ft" & vbCrLf
    report = report & "Perimeter (actual): " & Format(perimeterFt, "0.00") & " ft" & vbCrLf
    report = report & "Return Depth: " & takeoff.ReturnDepth & " inches" & vbCrLf
    report = report & "Return Area: " & Format(returnAreaSqFt, "0.00") & " sq ft" & vbCrLf & vbCrLf
    
    report = report & "MATERIAL REQUIREMENTS:" & vbCrLf
    report = report & "Letter Coil (" & takeoff.ReturnDepth & """): " & Format(perimeterFt * takeoff.MaterialWaste, "0.00") & " ft" & vbCrLf
    report = report & "Face Material: " & Format(faceAreaSqFt * 2 * takeoff.MaterialWaste, "0.00") & " sq ft" & vbCrLf
    report = report & "Total Material: " & Format((faceAreaSqFt * 2 + returnAreaSqFt) * takeoff.MaterialWaste, "0.00") & " sq ft" & vbCrLf
    
    GenerateTakeoffReport = report
End Function

' ============================================
' INDIVIDUAL LETTER ANALYSIS
' ============================================
Sub AnalyzeIndividualLetters()
    Dim s As Shape
    Dim report As String
    Dim letterNum As Long
    
    report = "INDIVIDUAL LETTER ANALYSIS" & vbCrLf & vbCrLf
    letterNum = 1
    
    For Each s In ActiveSelectionRange
        If s.Type = cdrCurveShape Then
            report = report & "Letter " & letterNum & ":" & vbCrLf
            report = report & "  Height: " & Format(s.SizeHeight * CORELDRAW_TO_INCHES, "0.00") & " in" & vbCrLf
            report = report & "  Width: " & Format(s.SizeWidth * CORELDRAW_TO_INCHES, "0.00") & " in" & vbCrLf
            report = report & "  Area: " & Format(GetShapeArea(s) / 144, "0.00") & " sq ft" & vbCrLf
            report = report & "  Perimeter: " & Format(GetShapePerimeter(s) / 12, "0.00") & " ft" & vbCrLf & vbCrLf
            letterNum = letterNum + 1
        End If
    Next s
    
    DisplayTakeoffResults report
End Sub

' ============================================
' RACEWAY/CABINET CALCULATOR
' ============================================
Sub CalculateRaceway()
    Dim sr As ShapeRange
    Dim width As Double, height As Double, depth As Double
    Dim faceArea As Double, returnArea As Double
    Dim report As String
    
    Set sr = ActiveSelectionRange
    
    ' Get overall dimensions
    width = sr.SizeWidth * CORELDRAW_TO_INCHES / 12 ' Convert to feet
    height = sr.SizeHeight * CORELDRAW_TO_INCHES / 12
    
    ' Assume 6" deep raceway
    depth = 0.5 ' feet
    
    ' Calculate areas
    faceArea = width * height
    returnArea = 2 * (width + height) * depth
    
    report = "RACEWAY/CABINET CALCULATIONS" & vbCrLf & vbCrLf
    report = report & "Width: " & Format(width, "0.00") & " ft" & vbCrLf
    report = report & "Height: " & Format(height, "0.00") & " ft" & vbCrLf
    report = report & "Depth: " & Format(depth * 12, "0.00") & " in" & vbCrLf & vbCrLf
    report = report & "Face Area: " & Format(faceArea, "0.00") & " sq ft" & vbCrLf
    report = report & "Return Area: " & Format(returnArea, "0.00") & " sq ft" & vbCrLf
    report = report & "Total Material: " & Format(faceArea + returnArea, "0.00") & " sq ft" & vbCrLf
    
    DisplayTakeoffResults report
End Sub

' ============================================
' DISPLAY RESULTS
' ============================================
Sub DisplayTakeoffResults(results As String)
    ' Create a text shape with results
    Dim textShape As Shape
    Dim doc As Document
    
    Set doc = ActiveDocument
    Set textShape = ActiveLayer.CreateArtisticText(0, doc.SizeHeight, results)
    textShape.Text.FontProperties.Size = 12
    textShape.Text.FontProperties.Name = "Arial"
End Sub

' ============================================
' EXPORT TO CSV FOR ESTIMATING
' ============================================
Sub ExportTakeoffToCSV(takeoff As SignTakeoff)
    Dim filePath As String
    Dim fileNum As Integer
    Dim csvContent As String
    
    filePath = Application.Path & "\SignTakeoff_" & Format(Now, "yyyymmdd_hhmmss") & ".csv"
    fileNum = FreeFile
    
    ' Create CSV content
    csvContent = "Measurement,Value,Unit" & vbCrLf
    csvContent = csvContent & "Letter Count," & takeoff.LetterCount & ",ea" & vbCrLf
    csvContent = csvContent & "Face Area (Single)," & Format(takeoff.TotalFaceArea / 144, "0.00") & ",sq ft" & vbCrLf
    csvContent = csvContent & "Face Area (Double)," & Format(takeoff.TotalFaceArea / 72, "0.00") & ",sq ft" & vbCrLf
    csvContent = csvContent & "Perimeter," & Format(takeoff.TotalPerimeter / 12, "0.00") & ",ft" & vbCrLf
    csvContent = csvContent & "Return Area," & Format((takeoff.TotalPerimeter / 12) * (takeoff.ReturnDepth / 12), "0.00") & ",sq ft" & vbCrLf
    csvContent = csvContent & "Coil Length," & Format((takeoff.TotalPerimeter / 12) * takeoff.MaterialWaste, "0.00") & ",ft" & vbCrLf
    
    ' Write to file
    Open filePath For Output As fileNum
    Print #fileNum, csvContent
    Close fileNum
    
    MsgBox "Takeoff exported to: " & filePath, vbInformation
End Sub

' ============================================
' QUICK BOUNDING BOX METHOD (For Comparison)
' ============================================
Sub QuickBoundingBoxMethod()
    Dim sr As ShapeRange
    Dim boundingArea As Double
    
    Set sr = ActiveSelectionRange
    boundingArea = (sr.SizeWidth * CORELDRAW_TO_INCHES / 12) * (sr.SizeHeight * CORELDRAW_TO_INCHES / 12)
    
    MsgBox "Bounding Box Area: " & Format(boundingArea, "0.00") & " sq ft" & vbCrLf & _
           "Note: This is NOT accurate for channel letter returns!", vbInformation
End Sub

' ============================================
' ABC PRICING INTEGRATION - LABOR HOURS ONLY
' ============================================
Sub GenerateABCLaborData()
    Dim sr As ShapeRange
    Dim takeoff As SignTakeoff
    Dim report As String
    
    Set sr = ActiveSelectionRange
    takeoff = CalculateCompleteTakeoff(sr)
    
    report = "ABC LABOR HOURS CALCULATOR INPUT DATA" & vbCrLf & vbCrLf
    
    ' Pattern Making Department
    report = report & "PATTERN MAKING:" & vbCrLf
    report = report & "Square Feet: " & Format(takeoff.TotalFaceArea / 144, "0.00") & vbCrLf & vbCrLf
    
    ' Metal Letters Department
    report = report & "METAL LETTERS:" & vbCrLf
    report = report & "Peripheral Feet: " & Format(takeoff.TotalPerimeter / 12, "0.00") & vbCrLf
    report = report & "Height Range: " & Format(takeoff.MinHeight, "0") & """ to " & Format(takeoff.MaxHeight, "0") & """" & vbCrLf & vbCrLf
    
    ' Sheet Metal Cabinet
    report = report & "SHEET METAL:" & vbCrLf
    report = report & "Cabinet Area: " & Format((sr.SizeWidth * sr.SizeHeight * CORELDRAW_TO_INCHES * CORELDRAW_TO_INCHES) / 144, "0.00") & " sq ft" & vbCrLf
    
    DisplayTakeoffResults report
End Sub

' ============================================
' MATERIAL QUANTITY SUMMARY
' ============================================
Sub MaterialQuantitySummary()
    Dim sr As ShapeRange
    Dim takeoff As SignTakeoff
    Dim report As String
    
    Set sr = ActiveSelectionRange
    takeoff = CalculateCompleteTakeoff(sr)
    
    ' Convert measurements
    Dim faceAreaSqFt As Double
    Dim perimeterFt As Double
    Dim returnAreaSqFt As Double
    
    faceAreaSqFt = takeoff.TotalFaceArea / 144
    perimeterFt = takeoff.TotalPerimeter / 12
    returnAreaSqFt = (perimeterFt * takeoff.ReturnDepth) / 12
    
    report = "MATERIAL QUANTITY SUMMARY" & vbCrLf & vbCrLf
    
    report = report & "ALUMINUM SHEET:" & vbCrLf
    report = report & "  Face Material: " & Format(faceAreaSqFt * 2 * takeoff.MaterialWaste, "0.00") & " sq ft" & vbCrLf
    report = report & "  Standard Sheets (4x8): " & Format((faceAreaSqFt * 2 * takeoff.MaterialWaste) / 32, "0.0") & " sheets" & vbCrLf & vbCrLf
    
    report = report & "ALUMINUM COIL:" & vbCrLf
    report = report & "  " & takeoff.ReturnDepth & """ Coil: " & Format(perimeterFt * takeoff.MaterialWaste, "0.00") & " linear ft" & vbCrLf
    report = report & "  Return Area: " & Format(returnAreaSqFt * takeoff.MaterialWaste, "0.00") & " sq ft" & vbCrLf & vbCrLf
    
    report = report & "FABRICATION DATA:" & vbCrLf
    report = report & "  Letter Count: " & takeoff.LetterCount & vbCrLf
    report = report & "  Average Height: " & Format((takeoff.MaxHeight + takeoff.MinHeight) / 2, "0.0") & " inches" & vbCrLf
    report = report & "  Total Width: " & Format(takeoff.TotalWidth / 12, "0.00") & " feet" & vbCrLf
    
    DisplayTakeoffResults report
End Sub

