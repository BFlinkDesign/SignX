# Work Order Parser

A professional desktop application for parsing and processing work order data.

## Features

- Modern, native Windows interface
- Advanced pattern recognition
- Multiple export formats (Excel, CSV, JSON)
- Real-time processing statistics
- System tray integration
- Background processing
- Comprehensive error handling
- Department code recognition
- Batch processing support
- Auto-updates

## Installation

### For Users
1. Download the latest `Work Order Parser.exe` from the releases
2. Run the installer
3. Follow the installation wizard
4. Launch the application from the Start menu or desktop shortcut

### For Developers
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python work_order_parser.py
   ```
4. To build the executable:
   ```bash
   python build.py
   ```

## Usage

1. Launch the Work Order Parser
2. Paste your work order data into the input area
3. Click "Parse Work Orders"
4. View the results in the preview area
5. Choose your preferred export format
6. Save the processed data

## Data Format

The tool expects work order data in the following format:
```
Part Number: ABC123
Work Order #12345
01/15/2024
Work Order #67890
01/16/2024
```

## Supported Patterns

### Work Orders
- Standard format: `12345`
- With prefix: `WO12345`
- With department code: `ES12345`
- With suffix: `12345A`

### Dates
- MM/DD/YY or MM/DD/YYYY
- YYYY-MM-DD
- MM-DD-YY or MM-DD-YYYY
- MMM DD, YYYY

### Part Numbers
- Standard format: `ABC123`
- With department code: `ESABC123`
- With prefix: `PABC123`
- With extension: `ABC123.001`

## Department Codes

The tool recognizes the following department codes:
- ES: Engineering Services
- SC: Sales
- PR: Production
- MFG: Manufacturing
- ENG: Engineering
- QA: Quality Assurance

## Features

### User Interface
- Modern, native Windows interface
- System tray integration
- Progress indicators
- Status bar updates
- Error dialogs
- File dialogs

### Processing
- Background processing
- Real-time progress updates
- Error handling
- Data validation
- Pattern recognition
- Department code extraction

### Export Options
- Excel (.xlsx)
- CSV (.csv)
- JSON (.json)
- Custom file locations
- Automatic file naming

### System Integration
- Windows file associations
- System tray icon
- Start menu integration
- Desktop shortcut
- Auto-updates

## Error Handling

The tool provides comprehensive error handling:
- Input validation
- Pattern matching errors
- Processing errors
- Export errors
- Detailed error messages
- Error logging

## Performance

- Efficient processing of large datasets
- Background processing
- Memory optimization
- Fast export capabilities
- Minimal system impact

## Security

- Input sanitization
- Secure file handling
- Local processing only
- No data sent to external servers
- Windows security integration

## Support

For issues or feature requests, please contact the development team.

## License

This tool is proprietary software. Unauthorized distribution or modification is prohibited.

## How to Use (Office Users)

1. Double-click `dist/work_order_parser.exe` to launch the Work Order Parser app. No installation or setup is required.
2. The app is fully self-contained and branded for Eagle Sign Co.
3. If you see any security prompts, click 'Allow' or 'Run'.

## Developer Note: Suppressed win32* Import Warnings
- All 'win32*' import warnings are now suppressed in VS Code and Pyright for a clean developer experience.
- This is handled by `pyrightconfig.json` and `.vscode/settings.json`.

## Automation Features
- The app now supports:
  - Automated dependency management
  - Automated packaging as a .exe with company branding
  - Automated installer script generation
  - Suppression of irrelevant IDE warnings
  - (Planned) Auto-updates and advanced installer features for seamless office deployment
