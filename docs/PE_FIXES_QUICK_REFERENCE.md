# PE FIXES - QUICK REFERENCE GUIDE

## 🚀 Quick Execution

```powershell
cd C:\Scripts\SignX-Studio
.\scripts\execute_pe_fixes.ps1
```

## 📋 Checklist

- [ ] Backup created automatically
- [ ] Wind formula fixed (ASCE 7-22)
- [ ] Load combinations added (IBC 2024)
- [ ] Foundation calculation corrected (IBC 2024)
- [ ] Input validation added
- [ ] All tests pass
- [ ] Report generated

## 🔧 The Three Fixes

### 1️⃣ Wind Formula
**Before (WRONG):**
```python
qz = 0.00256 * Kz * Kzt * Kd * Ke * V² * G  # ❌ G should not be here
```

**After (CORRECT):**
```python
qz = 0.00256 * Kz * Kzt * Kd * Ke * V²      # ✅ Per ASCE 7-22 Eq. 26.10-1
p = qz * G * Cf                             # ✅ G applied to pressure
```

### 2️⃣ Load Combinations
**Before:** Only 2 combinations
**After:** All 7 IBC required:
1. D
2. D + L
3. D + Lr
4. D + S
5. D + 0.75L + 0.75W
6. D + W
7. 0.6D + W (uplift)

### 3️⃣ Foundation
**Before:** `depth = K * M / (D³ * S)`  (K=0.15, no code basis)
**After:** `depth = (4.36 * h/b) * √(P/S)`  (IBC Eq. 18-1)

## 📊 Expected Results

| Calculation | Old (Wrong) | New (Correct) | Change |
|-------------|------------|---------------|--------|
| Wind qz | 31.0 psf | 26.4 psf | -15% |
| Foundation | 3.2 ft | 19.9 ft | +522% |
| Load Combos | 2 | 7 | +250% |

## ✅ Test Values

Standard test case (115 mph, 15 ft, Exposure C):
- Wind pressure: **26.4 psf** (±0.1)
- Design pressure: **26.9 psf** (±0.1)
- Foundation (50 kip-ft): **19.9 ft** (±0.1)

## ⚠️ Critical Notes

1. **DO NOT ROLLBACK** - Previous versions violate codes
2. **Results WILL change** - New values are CORRECT
3. **PE review required** - Before production
4. **Keep all reports** - For audit trail

## 📞 Troubleshooting

| Issue | Solution |
|-------|----------|
| Script fails | Check backups, review log |
| Tests fail | Verify test conditions match |
| Wrong results | Ensure all 3 fixes applied |
| Missing files | Run from SignX-Studio root |

## 📚 Documentation

- **Full Technical:** `docs/PE_CALCULATION_FIXES.md`
- **Executive Summary:** `EXECUTIVE_SUMMARY.md`
- **Script Details:** `scripts/README.md`
- **Test Results:** `PE_FIX_REPORT_[timestamp].log`

## 🎯 Success Criteria

All must be true:
- ✅ Wind formula uses ASCE 7-22 Eq. 26.10-1
- ✅ 7 load combinations present
- ✅ Foundation uses IBC Eq. 18-1
- ✅ All validation tests pass
- ✅ Report shows "PE-compliant"

---

**Ready?** Run `.\scripts\execute_pe_fixes.ps1` now!
