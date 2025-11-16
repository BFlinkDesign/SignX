# 📜 SignX Platform Scripts

Automation scripts for setup, deployment, and maintenance.

---

## 🚀 **Setup Scripts**

### `setup_gemini_corpus.py`
**Purpose**: Generate Gemini File Search corpus from your BOT TRAINING directory

**What it does:**
- Scans `C:\Scripts\SignX\Eagle Data\BOT TRAINING` recursively
- Categorizes documents: Cat Scale, Engineering, Estimating, AI, Sales
- Generates HTML wrappers for each document (better for RAG)
- Creates master index for easy review
- Outputs to `~/Desktop/Gemini_Eagle_Knowledge_Base/`

**Usage:**
```powershell
cd C:\Scripts\SignX\SignX-Studio
python scripts/setup_gemini_corpus.py
```

**Expected output:**
```
✅ Generated 834 HTML documents
✅ Organized into 5 categories
✅ Output directory: ~/Desktop/Gemini_Eagle_Knowledge_Base/
✅ Master index: INDEX.html
```

**Next steps:**
1. Open `INDEX.html` in browser to review
2. Visit https://aistudio.google.com
3. Create corpus: `eagle_sign_master_knowledge`
4. Upload all HTML files (drag entire folder)
5. Test queries

**Cost**: $10-20 one-time indexing, $0 ongoing

---

## 📋 **To Be Created**

### `test_rag.py` (TODO)
Test Gemini RAG query quality

```python
# Test queries
test_queries = [
    "Cat Scale standard part pricing",
    "AISC structural steel specifications",
    "ABC estimating workflow",
    "Wind load calculations ASCE 7-22"
]

# Expected: 80%+ relevant results
```

### `migrate_existing_routes.py` (TODO)
Migrate existing SignX-Studio API routes into new platform module structure

### `deploy_to_railway.py` (TODO)
Automated deployment to Railway PaaS

### `run_integration_tests.py` (TODO)
Full integration test suite

---

## 🛠️ **Development Guidelines**

### Script Naming Convention
- `setup_*.py` - One-time setup tasks
- `test_*.py` - Testing/validation scripts
- `deploy_*.py` - Deployment automation
- `migrate_*.py` - Data/code migration tasks

### Error Handling
All scripts should:
- ✅ Verify prerequisites exist
- ✅ Provide clear progress indicators
- ✅ Handle errors gracefully
- ✅ Generate summary reports
- ✅ Include rollback/undo capability

### Example Template
```python
"""
Script Name - Brief Description

Author: Brady Flink / Claude
Date: November 2025
Version: 1.0
"""

import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("SCRIPT NAME")
    print("=" * 70 + "\n")
    
    # Step 1: Verify prerequisites
    print("Step 1: Checking prerequisites...")
    # ...
    
    # Step 2: Main work
    print("Step 2: Processing...")
    # ...
    
    # Step 3: Summary
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"✅ Summary here")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
```

---

## 📖 **Related Documentation**

- **Getting Started**: `../GETTING_STARTED.md`
- **instant quoting platform Quickstart**: `../instant quoting platform_QUICKSTART.md`
- **Integration Plan**: `../../INTEGRATION_PLAN.md`
- **Platform API**: `../platform/api/main.py`

---

**Built for Eagle Sign Co. | November 2025**
