# KeyedIn API Enhanced - Professional Package Structure

## Package Overview

This is a professionally packaged Python library for interacting with the KeyedIn Manufacturing system API with automatic session management.

## Installation

### From Source

```bash
# Clone or download the package
cd keyedin-api-enhanced

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Direct Installation

```bash
pip install -r requirements.txt
```

## Package Structure

```
keyedin-api-enhanced/
├── setup.py                 # Package setup configuration
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # Main documentation
├── KEYEDIN_API_README.md   # Detailed API documentation
│
├── keyedin_api_enhanced.py  # Main API class
├── keyedin_cdp_extractor.py # Chrome CDP cookie extractor
├── keyedin_api.py           # Legacy API wrapper
│
├── test_enhanced_api.py     # Enhanced API tests
├── test_api_with_cookies.py # Cookie-based tests
├── comprehensive_test.py    # Comprehensive test suite
├── verify_setup.py         # Setup verification
├── troubleshoot_chrome.py   # Chrome troubleshooting
│
├── investigate_login_flow.py # Login flow analysis
├── extract_with_credentials.py # Credential-based extraction
│
└── docs/                    # Additional documentation
    ├── VALIDATION_REPORT.md
    ├── API_REVIEW_SUMMARY.md
    └── SAVE_LOCATIONS.md
```

## Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
KEYEDIN_BASE_URL=https://eaglesign.keyedinsign.com
```

## Usage

### Basic Usage

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

# API automatically loads credentials from .env
api = KeyedInAPIEnhanced()

# Use the API
menu = api.get_menu()
work_orders = api.get_work_order_form()
```

### With Custom Configuration

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

api = KeyedInAPIEnhanced(
    cookies_file='custom_cookies.json',
    username='custom_user',
    password='custom_pass',
    auto_refresh=True
)
```

## Login Flow Analysis

Based on investigation of `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START`:

### Login Process

1. **GET /cgi-bin/mvi.exe/LOGIN.START**
   - Returns login form HTML (or redirects)
   - May set initial session cookies

2. **POST to Base URL**
   - Fields: `USERNAME`, `PASSWORD`, `SECURE`
   - Creates authenticated session
   - Sets `SESSIONID` cookie

3. **Session Management**
   - Server stores session data server-side
   - Client stores cookies (`SESSIONID`, `user`, `secure`, etc.)
   - Session ID links client cookies to server session

### Data Storage

- **Server-side**: Session data stored in server memory/database
- **Client-side**: Cookies stored in browser/JSON file
- **Session Link**: `SESSIONID` cookie links client to server session

## Features

✅ Automatic cookie extraction from Chrome  
✅ Session validation and expiry checking  
✅ Auto-refresh before timeout  
✅ Background session monitoring  
✅ Environment variable configuration  
✅ Professional package structure  

## Development

### Running Tests

```bash
# Run comprehensive test suite
python comprehensive_test.py

# Run specific tests
python test_enhanced_api.py
python test_api_with_cookies.py

# Verify setup
python verify_setup.py
```

### Code Quality

```bash
# Linting (if flake8 installed)
flake8 *.py

# Formatting (if black installed)
black *.py
```

## Distribution

### Building Distribution

```bash
# Build source distribution
python setup.py sdist

# Build wheel
python setup.py bdist_wheel
```

### Installing from Distribution

```bash
pip install dist/keyedin-api-enhanced-1.0.0.tar.gz
```

## License

See LICENSE file for details.

## Support

For issues or questions, see the documentation in `KEYEDIN_API_README.md`.


