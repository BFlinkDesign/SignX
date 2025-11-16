# Eagle Sign - Gemini File Search Project Generator

Automatically scans your G:\ drive, identifies the 10 best diverse projects, and generates comprehensive HTML summaries ready for upload to Google Gemini File Search.

## What This Does

1. **Scans** your 2024 Work Order Tracking spreadsheet
2. **Classifies** projects by type (channel letters, monument, pole, cabinet, pylon)
3. **Selects** 10 diverse projects across different types and price ranges
4. **Finds** the corresponding project folders on G:\
5. **Generates** beautiful HTML summaries with:
   - Project details (customer, value, completion date)
   - File inventory (PDFs, drawings, photos)
   - Keywords for RAG retrieval
   - Professional formatting

## Quick Start

### Prerequisites
- Windows computer with G:\ drive mapped to \\ES-FS02\customers2\
- Python 3.8 or newer ([Download here](https://www.python.org/downloads/))
  - ⚠️ **IMPORTANT:** Check "Add Python to PATH" during installation

### Running the Generator

**Method 1: Double-click** (Easiest)
1. Double-click `RUN_ME.bat`
2. Wait 2-3 minutes while it processes
3. Your Desktop will open with the generated files

**Method 2: Command line**
```cmd
python generate_gemini_docs.py
```

## Output

Creates `~/Desktop/Gemini_Project_Summaries/` containing:
- 10 HTML files (one per project)
- Professional formatting
- Ready to upload to Gemini

Example filename: `WO12345_FirstBank_monument.html`

## What's Selected

The script automatically picks:
- **2 Channel Letter projects** ($5K-$30K range)
- **2 Monument Sign projects** ($15K-$75K range)
- **2 Pole Sign projects** ($50K-$150K range)
- **2 Cabinet Sign projects** ($10K-$60K range)
- **1 Pylon project** ($75K-$250K range)
- **1 Complex project** ($40K-$120K range)

This gives Gemini diverse training data across your project portfolio.

## Next Steps: Upload to Gemini

1. Visit **https://aistudio.google.com**
2. Sign in with your Google account (the one with Gemini subscription)
3. Click **"Create new corpus"**
4. Name it **"eagle_sign_projects"**
5. **Upload all 10 HTML files**
6. Test with queries:
   ```
   Find monument sign projects in Iowa
   What mounting methods for channel letters?
   LED specifications for cabinet signs
   Installation challenges for pole signs
   ```

## Free Tier Usage

Your expected usage:
- **1,500 API calls/day FREE** (Gemini API)
- You'll use ~60 calls/day for 30 quotes
- **25x under the free limit**
- Storage and queries are FREE forever
- One-time indexing cost: ~$1,875 for 50GB (then free forever)

## Troubleshooting

### "Python is not installed"
- Install Python from https://www.python.org/downloads/
- **Check "Add Python to PATH"** during installation
- Restart your computer after installing

### "No work orders found"
- Verify `G:\2024 Work order tracking.xlsx` exists
- Make sure G:\ is mapped to \\ES-FS02\customers2\

### "No project folders found"
- Script will still generate summaries from work order data
- Project folders aren't strictly required

### Permission errors
- Make sure you have read access to G:\
- Try running as administrator (right-click RUN_ME.bat → "Run as administrator")

## File Structure

```
Gemini_Generator/
├── generate_gemini_docs.py    # Main script
├── requirements.txt            # Python dependencies  
├── RUN_ME.bat                 # Windows launcher
└── README.md                  # This file
```

## Technical Details

### Dependencies
- `pandas` - Excel file reading
- `openpyxl` - Excel format support

### Project Classification Logic
Analyzes work order descriptions for keywords:
- **Channel Letters**: "channel", "letter", "reverse", "halo"
- **Monument**: "monument", "ground", "entry"
- **Pole**: "pole", "tall", "freestanding"
- **Cabinet**: "cabinet", "box", "lightbox"
- **Pylon**: "pylon", "tower"

### File Discovery
Searches G:\ alphabetically organized folders (A/, B/, C/, etc.) for folders containing the work order number.

## Why HTML Instead of PDF?

HTML files work great for Gemini RAG:
- ✅ Semantic structure (headers, sections)
- ✅ Readable by both humans and AI
- ✅ Smaller file size
- ✅ Easy to edit if needed
- ✅ No conversion tools required

You can open them in any browser to review before uploading.

## Support

Questions? Issues? Contact Brady Flink.

## Version

- **Version:** 1.0
- **Date:** May 2025
- **Author:** Brady Flink / Claude Sonnet 4
