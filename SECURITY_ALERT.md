# CRITICAL SECURITY ALERT

## Exposed API Keys Found

**Date:** November 15, 2025
**Severity:** CRITICAL
**Status:** Partially Fixed

### Issue
Hardcoded Gemini API keys were found in multiple files in the repository. These keys are now exposed in the git history and should be considered compromised.

### Affected Files
The following files contained hardcoded API key: `<REDACTED>`

1. `scripts/test_gemini_api.py` - **FIXED**
2. `SignX-Studio/scripts/debug_rag_blocking.py` - **NEEDS FIX**
3. `SignX-Studio/scripts/check_upload_status.py` - **NEEDS FIX**
4. `SignX-Studio/scripts/fix_safety_blocking.py` - **NEEDS FIX**
5. `SignX-Studio/scripts/test_rag_accuracy.py` - **NEEDS FIX**
6. `SignX-Studio/scripts/test_quote_generation_simple.py` - **NEEDS FIX**
7. `SignX-Studio/scripts/upload_new_docs.py` - **NEEDS FIX**
8. `SignX-Studio/scripts/test_rag_working.py` - **NEEDS FIX**
9. `SignX-Studio/scripts/test_rag_immediately.py` - **NEEDS FIX**
10. `SignX-Studio/scripts/upload_corpus_to_gemini.py` - **NEEDS FIX**
11. `SignX-Studio/scripts/test_rag_final.py` - **NEEDS FIX**

### Immediate Actions Required

1. **ROTATE THE API KEY IMMEDIATELY**
   - Go to Google Cloud Console
   - Navigate to APIs & Services > Credentials
   - Delete the exposed API key: `<REDACTED>`
   - Create a new API key
   - Store the new key in environment variables

2. **Set Environment Variables**
   ```bash
   # Windows (PowerShell)
   $env:GEMINI_API_KEY = "your_new_api_key_here"

   # Windows (CMD)
   set GEMINI_API_KEY=your_new_api_key_here

   # Linux/Mac
   export GEMINI_API_KEY="your_new_api_key_here"
   ```

3. **Update Remaining Files**
   - All files listed above need to be updated to use `os.getenv("GEMINI_API_KEY")`
   - Never commit API keys, passwords, or secrets to source control

4. **Review Git History**
   - Consider using tools like `git-filter-repo` or `BFG Repo-Cleaner` to remove the exposed keys from git history
   - Note: This requires force-pushing and coordinating with all team members

### Prevention

1. **Use `.env` files for local development**
   ```
   # .env (add to .gitignore!)
   GEMINI_API_KEY=your_api_key_here
   GEMINI_PROJECT=your_project_id
   ```

2. **Update .gitignore**
   ```
   # Secrets
   .env
   .env.local
   secrets/
   *.key
   *.pem
   ```

3. **Use secret scanning tools**
   - Enable GitHub secret scanning
   - Use pre-commit hooks to prevent committing secrets
   - Consider tools like `truffleHog` or `git-secrets`

### References
- [OWASP Top 10: A07:2021 – Identification and Authentication Failures](https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/)
- [Google Cloud: Best practices for managing API keys](https://cloud.google.com/docs/authentication/api-keys)
