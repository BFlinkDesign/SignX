# BOT TRAINING → SignX Migration Summary
Date: 2026-02-08

## Successfully Migrated

### 1. EagleHub v1
**Source**: `H:\brady\BOT TRAINING\Estimating\EagleHub`  
**Destination**: `C:\Scripts\SignX\tools\eaglehub\`  
**Size**: 14KB  
**Contents**:
- Dashboard.html - Main dashboard interface
- Eagle-Hub-Engine.ps1 - PowerShell automation engine
- Config/, Documentation/, Patterns/, Logs/ directories

### 2. EagleHub v2
**Source**: `H:\brady\BOT TRAINING\Estimating\EagleHub_v2`  
**Destination**: `C:\Scripts\SignX\tools\eaglehub-v2\`  
**Size**: 49KB  
**Contents**:
- Enhanced dashboard (Eagle-Hub-Dashboard-v2.html)
- Scripts/, Projects/, Reports/, Historical/, Backups/ directories
- VERSION.txt

### 3. ABC Estimating Extracted Data
**Source**: `H:\brady\BOT TRAINING\Scripts\SignX\ABC_Estimating_Extracted`  
**Destination**: `C:\Scripts\SignX\data\abc-estimating\`  
**Size**: 4.1MB  
**Contents**:
- abcsignc.mdb database (2.5MB)
- 7 data files (.abc): bill_mat_nm, dept_nm, descript_nm, invent_nm, labor_nm, macros_nm, menu_nm
- 3 executables: AbcEng.exe, abceng.dll, abcapi.dll
- 8 documentation files including LABOR_FORMULAS_COMPLETE.txt (63KB)

### 4. Legacy ABC Database
**Source**: `H:\brady\Adam-Z4\abcsignc.mdb`  
**Destination**: `C:\Scripts\SignX\data\legacy-databases\`  
**Size**: 2.5MB  
**Contents**:
- abcsignc.mdb from 2006-09-07

### 5. BradyMagic VBA (Note)
**Source**: `H:\brady\BOT TRAINING\VBA\BradyMagic`  
**Destination**: `C:\Scripts\SignX\tools\vba-macros\` (README only)  
**Note**: BradyMagic contains only Python trading strategy scripts (ICT scalping), not VBA macros. Actual VBA macros may be in CorelDraw or other locations.

## Total Data Migrated
- **EagleHub tools**: 63KB
- **ABC data + database**: 6.6MB
- **Total**: ~6.7MB

## Next Steps
1. Review ABC Estimating formulas in `data/abc-estimating/LABOR_FORMULAS_COMPLETE.txt`
2. Extract pricing logic from `abcsignc.mdb` for integration into SignX calculators
3. Review EagleHub automation scripts for reusable patterns
4. Search for actual VBA macros in CorelDraw directories if needed

## Files NOT Copied
- .venv directories (virtual environments)
- .git directories (version control)
- __pycache__ (Python cache)
- node_modules (if any)

All copied content preserved original timestamps and structure.
