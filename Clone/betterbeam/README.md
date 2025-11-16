## BetterBeam (clean-room)

Vite + React + TypeScript with a minimal PDF viewer (pdf.js worker) and a Konva annotation overlay. Windows-friendly dev scripts included.

### Quickstart

```powershell
Set-Location C:\\Clone\\betterbeam
npm install
npm run dev:win
# open http://127.0.0.1:5173/
```

Or on other platforms:

```bash
npm install
npm run dev
```

### Scripts
- dev: Windows-stable host/port
- dev:win: sets polling in PowerShell
- typecheck: strict TS
- build: tsc -b then vite build

### Troubleshooting
- Second terminal: `Test-NetConnection 127.0.0.1 -Port 5173`
- Ensure Node 20+

### Notes
- pdf.js worker wired via `?worker`
- Konva overlay separate from PDF canvas


