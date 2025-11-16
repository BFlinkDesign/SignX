# Security Scanning

SignX protects 95 years of structural engineering data and modern FastAPI services by running automated security scans on every push and pull request. The pipeline now uses Semgrep, Gitleaks, and Safety instead of SonarCloud.

## Tooling Overview

| Tool | Purpose | What It Catches |
| ---- | ------- | --------------- |
| **Semgrep** | Static analysis for Python 3.12, SQL, and TypeScript | Injection risks, auth bypasses, insecure defaults inside services and modules. |
| **Gitleaks** | Secret detection across git history | API keys, customer PII, and credentials committed accidentally. |
| **Safety** | Python dependency vulnerability scan | CVEs in every `requirements*.txt` installed by the workflow. |

## Why We Replaced SonarCloud
- Semgrep rulesets surfaced FastAPI and ASCE-specific issues SonarCloud missed.
- All three tools are free for private repositories; SonarCloud requires a paid tier.
- No organization tokens or project configuration—GitHub Actions orchestrates everything.
- Adding Gitleaks closes the secrets gap that SonarCloud never addressed.

## Running Scans Locally
```bash
# Semgrep
pip install semgrep
semgrep --config=auto .

# Gitleaks (Docker version shown)
docker run -v $(pwd):/repo zricethezav/gitleaks:latest detect --source=/repo --no-git -v

# Safety
pip install safety
pip install -r requirements.txt  # include other requirement files as needed
safety check --full-report
```
Run these before opening a PR to avoid CI failures.

## VBA Macro Coverage
CorelDraw and Excel VBA macros used for ASCE 7-22 calculations are **not** scanned automatically. Continue to run VBDepend manually before committing VBA changes to keep compliance intact.
