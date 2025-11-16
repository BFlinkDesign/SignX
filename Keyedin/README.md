# KeyedIn API Enhanced

Professional Python API client for KeyedIn Manufacturing system with automatic session management, cookie extraction, and Chrome DevTools Protocol integration.

## Features

✅ **Automatic Session Management** - Validates and refreshes sessions automatically  
✅ **Chrome CDP Integration** - Extracts cookies automatically from Chrome  
✅ **Environment Variable Support** - Secure credential management via .env file  
✅ **Session Validation** - Checks session health before each request  
✅ **Auto-Refresh** - Refreshes cookies before expiry  
✅ **Background Monitoring** - Continuous session health checks  

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Quick Start

### 1. Configure Environment

Create a `.env` file in the project root:

```bash
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
KEYEDIN_BASE_URL=https://eaglesign.keyedinsign.com
```

### 2. Extract Cookies (First Time)

```bash
python keyedin_cdp_extractor.py
```

Or use the credential-based extractor:

```bash
python extract_with_credentials.py
```

### 3. Use the API

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

# API automatically loads credentials from .env
api = KeyedInAPIEnhanced()

# Use the API - sessions automatically managed
menu = api.get_menu()
work_orders = api.get_work_order_form()
```

## Login Flow

The API handles the KeyedIn login flow automatically:

1. **GET /cgi-bin/mvi.exe/LOGIN.START** - Redirects to base URL
2. **GET Base URL** - Returns login form HTML
3. **POST Base URL** - Authenticates with USERNAME, PASSWORD, SECURE
4. **Session Created** - Server sets SESSIONID cookie
5. **Subsequent Requests** - Use SESSIONID cookie for authentication

### Data Storage

- **Server-side**: Session data stored in server memory/database
- **Client-side**: Cookies stored in `keyedin_chrome_session.json`
- **Session Link**: SESSIONID cookie links client to server session

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYEDIN_USERNAME` | KeyedIn username | Required |
| `KEYEDIN_PASSWORD` | KeyedIn password | Required |
| `KEYEDIN_BASE_URL` | Base URL | `https://eaglesign.keyedinsign.com` |
| `KEYEDIN_COOKIES_FILE` | Cookie file path | `keyedin_chrome_session.json` |
| `KEYEDIN_AUTO_REFRESH` | Enable auto-refresh | `true` |
| `KEYEDIN_REFRESH_THRESHOLD_MINUTES` | Refresh threshold | `30` |

### Code Configuration

```python
api = KeyedInAPIEnhanced(
    cookies_file='custom_cookies.json',  # Optional
    base_url='https://custom.url.com',   # Optional
    username='user',                     # Optional (uses .env)
    password='pass',                     # Optional (uses .env)
    auto_refresh=True,                   # Optional
    refresh_threshold_minutes=30         # Optional
)
```

## API Reference

### KeyedInAPIEnhanced

Main API class with automatic session management.

#### Methods

- `get(endpoint, **kwargs)` - GET request with auto-validation
- `post(endpoint, **kwargs)` - POST request with auto-validation
- `get_menu(username=None)` - Get menu structure
- `get_work_order_form()` - Get work order form
- `validate_session()` - Validate current session
- `refresh_session(force=False)` - Refresh session cookies
- `test_endpoints()` - Test all discovered endpoints

See `KEYEDIN_API_README.md` for complete documentation.

## Testing

```bash
# Run comprehensive test suite
python comprehensive_test.py

# Run specific tests
python test_enhanced_api.py
python test_api_with_cookies.py

# Verify setup
python verify_setup.py
```

## Package Structure

```
keyedin-api-enhanced/
├── setup.py                    # Package setup
├── requirements.txt            # Dependencies
├── .env.example               # Environment template
├── README.md                  # This file
├── KEYEDIN_API_README.md     # Detailed docs
├── keyedin_api_enhanced.py   # Main API
├── keyedin_cdp_extractor.py  # Cookie extractor
└── tests/                     # Test files
```

## Troubleshooting

See `troubleshoot_chrome.py` for Chrome/ChromeDriver diagnostics.

Common issues:
- **Chrome not starting**: Close all Chrome windows and try again
- **Session expired**: Run cookie extractor to refresh
- **Credentials not found**: Check .env file exists and has correct values

## License

See LICENSE file for details.

## Support

For detailed documentation, see `KEYEDIN_API_README.md`.


