"""Test the real parser against Gemini art files (1:1 scale)."""
from extract_pf_from_pdf import extract_pf_from_pdf
from pathlib import Path

files = [
    (r"G:\I\Iowa Dept of Transportation\2025\AMES - 800 LINCOLN WAY\GEMINI\IADOT Ames Bldg Letters Brushed Alum Q39946 12562-2.pdf",
     "IADOT Gemini Art", 78.64),
    (r"C:\Users\Brady.EAGLE\Downloads\Clemens Agency Interior Letters ART FOR GEMINI 12515-1.pdf",
     "Clemens Gemini Art", None),
    (r"C:\Users\Brady.EAGLE\Downloads\Versova 20'' Letters ART FOR GEMINI 12568-1.pdf",
     "Versova 20\" Gemini Art", None),
]

for fpath, label, expected in files:
    p = Path(fpath)
    if not p.exists():
        print(f"{label}: FILE NOT FOUND")
        continue

    with open(p, "rb") as f:
        data = f.read()

    result = extract_pf_from_pdf(data, filename=p.name)
    print(f"\n{label}:")
    print(f"  Shapes: {result.letter_count}")
    print(f"  Total PF: {result.total_pf:.2f} ft")
    print(f"  Face SF: {result.total_face_sf:.2f}")
    print(f"  Heights: {result.min_height_inches:.1f}\" - {result.max_height_inches:.1f}\"")
    if expected:
        variance = abs(result.total_pf - expected) / expected * 100
        print(f"  Expected: {expected:.2f} ft")
        print(f"  Variance: {variance:.1f}%")
        print(f"  Status: {'PASS' if variance < 5 else 'FAIL'}")
    if result.warnings:
        for w in result.warnings:
            print(f"  WARNING: {w}")
    if result.letters:
        print(f"  Top shapes:")
        sorted_letters = sorted(result.letters, key=lambda x: x.perimeter_feet, reverse=True)
        for l in sorted_letters[:5]:
            print(f"    #{l.index}: PF={l.perimeter_feet:.2f} ft, H={l.height_inches:.1f}\", W={l.width_inches:.1f}\"")
