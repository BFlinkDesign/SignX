# ♊ Gemini Integration Guide for Eagle Sign

This document outlines the setup, configuration, and usage of the Google Gemini integration for the Eagle Sign platform. This integration powers the **Instant Quote** and **RAG (Retrieval-Augmented Generation)** features.

## 🚀 Overview

The system uses Gemini 1.5 Pro to:
1.  **Analyze Projects**: Understand complex sign requirements from natural language.
2.  **Retrieve Knowledge**: Search 95 years of Eagle Sign history (pricing, engineering specs, past projects).
3.  **Generate Quotes**: Produce accurate, itemized quotes in seconds.

## 📋 Prerequisites

*   **Google Account**: With access to [Google AI Studio](https://aistudio.google.com).
*   **Python 3.11+**: Installed on your system.
*   **Eagle Data**: Access to the `BOT TRAINING` directory (source of knowledge).

## 🛠️ Setup Instructions

### 1. Get Your API Key
1.  Go to [Google AI Studio](https://aistudio.google.com).
2.  Click **"Get API Key"**.
3.  Create a key in a new or existing project.
4.  **Save this key securely.** You will need it for the environment configuration.

### 2. Generate Knowledge Corpus
The system needs to convert your raw files (PDFs, Excel, etc.) into a format Gemini can understand.

1.  Open a terminal in `C:\Scripts\SignX\SignX-Studio`.
2.  Run the corpus generator script:
    ```powershell
    python scripts/setup_gemini_corpus.py
    ```
3.  This will:
    *   Scan `C:\Scripts\SignX\Eagle Data\BOT TRAINING`.
    *   Generate HTML summaries for ~800+ documents.
    *   Save the output to `Desktop/Gemini_Eagle_Knowledge_Base`.

### 3. Upload to Gemini
1.  Return to [Google AI Studio](https://aistudio.google.com).
2.  Click **"Create Corpus"** (or "New Tuning/Corpus").
3.  Name it: `eagle_sign_master_knowledge`.
4.  **Upload**: Drag and drop the folders from `Desktop/Gemini_Eagle_Knowledge_Base` into the upload area.
5.  Wait for indexing to complete (status will change to "Active").

## ⚙️ Configuration

Set your API key in the environment to enable the platform to talk to Gemini.

**Option A: Temporary (PowerShell)**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**Option B: Permanent (System Environment Variable)**
1.  Search Windows for "Edit the system environment variables".
2.  Click "Environment Variables".
3.  Under "User variables", click "New".
4.  Variable name: `GEMINI_API_KEY`
5.  Variable value: `your_api_key_here`

## 🧪 Testing the Integration

### 1. Verify Corpus
In AI Studio, try asking a question like:
> "What is the standard pricing for a 40ft Cat Scale pole?"

If it retrieves the correct document, your corpus is working.

### 2. Test API Endpoint
Run the platform locally:
```powershell
cd C:\Scripts\SignX\SignX-Studio
python platform/api/main.py
```

Send a test request (using curl or Postman):
```bash
curl -X POST http://localhost:8000/api/v1/quoting/instant \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Test Monument",
    "sign_type": "monument",
    "description": "Need a 10x5 monument sign with internal illumination."
  }'
```

## 🔍 Troubleshooting

*   **"403 Permission Denied"**: Check your API key is correct and has billing enabled (if exceeding free tier).
*   **"Corpus not found"**: Ensure the corpus name in your code matches what you created in AI Studio.
*   **"Empty responses"**: The RAG retrieval might not be finding relevant docs. Check your search query or corpus content.
