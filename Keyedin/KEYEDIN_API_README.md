# KeyedIn Enhanced API Documentation

## Overview

The Enhanced KeyedIn API provides automatic session management, cookie extraction, validation, and refresh capabilities using Chrome DevTools Protocol (CDP).

## Features

✅ **Automatic Cookie Extraction** - Uses Chrome DevTools Protocol to extract cookies automatically  
✅ **Session Validation** - Validates sessions before each request  
✅ **Auto-Refresh** - Automatically refreshes cookies before they expire  
✅ **Background Monitoring** - Monitors session health in the background  
✅ **Expiry Detection** - Checks cookie expiry times and refreshes proactively  
✅ **Error Handling** - Gracefully handles expired sessions and retries requests  

## Files

- `keyedin_api_enhanced.py` - Main enhanced API class with all features
- `keyedin_cdp_extractor.py` - Standalone cookie extractor using Chrome CDP
- `test_enhanced_api.py` - Test suite for the enhanced API
- `keyedin_api.py` - Legacy API wrapper (for backward compatibility)

## Quick Start

### 1. Extract Cookies (First Time Setup)

```python
from keyedin_cdp_extractor import KeyedInCDPExtractor

extractor = KeyedInCDPExtractor(
    username='your_username',  # Optional
    password='your_password'    # Optional
)

result = extractor.extract_session(
    output_file='keyedin_chrome_session.json',
    capture_network=True
)
```

Or run from command line:
```bash
python keyedin_cdp_extractor.py username password
```

### 2. Use Enhanced API

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

# Initialize API with auto-refresh enabled
api = KeyedInAPIEnhanced(
    cookies_file='keyedin_chrome_session.json',
    auto_refresh=True,
    refresh_threshold_minutes=30  # Refresh if expires within 30 minutes
)

# Use the API - sessions are automatically validated and refreshed
menu = api.get_menu()
work_orders = api.get_work_order_form()

# Make custom requests
response = api.get('/cgi-bin/mvi.exe/WO.INQUIRY')
```

### 3. Test the API

```bash
python test_enhanced_api.py
```

## API Reference

### KeyedInAPIEnhanced

#### Initialization

```python
api = KeyedInAPIEnhanced(
    cookies_file='keyedin_chrome_session.json',  # Cookie file path
    base_url='https://eaglesign.keyedinsign.com',  # Base URL
    username=None,  # Optional username for auto-login
    password=None,  # Optional password for auto-login
    auto_refresh=True,  # Enable automatic refresh
    refresh_threshold_minutes=30  # Refresh threshold in minutes
)
```

#### Methods

**`validate_session() -> bool`**
- Validates that the current session is still active
- Returns `True` if valid, `False` otherwise
- Automatically called before requests if `auto_refresh` is enabled

**`refresh_session(force: bool = False) -> bool`**
- Refreshes the session by extracting fresh cookies from Chrome
- Opens Chrome, allows login, extracts cookies
- Returns `True` if successful
- Set `force=True` to refresh even if session appears valid

**`get(endpoint: str, **kwargs) -> requests.Response`**
- Makes a GET request with automatic session validation
- Automatically refreshes session if expired
- Retries request after refresh if needed
- Accepts all standard `requests.get()` arguments

**`post(endpoint: str, **kwargs) -> requests.Response`**
- Makes a POST request with automatic session validation
- Same behavior as `get()` but for POST requests

**`get_menu(username: str = None) -> Dict`**
- Convenience method to get menu structure
- Returns JSON menu data

**`get_work_order_form() -> str`**
- Convenience method to get work order inquiry form
- Returns HTML form content

**`test_endpoints() -> Dict[str, Any]`**
- Tests all discovered endpoints
- Returns dictionary with test results

**`stop_monitor() -> None`**
- Stops the background session monitor
- Call this when shutting down the application

## Session Management

### Automatic Refresh

The API automatically refreshes sessions when:
1. Cookies are expiring within the `refresh_threshold_minutes` window
2. Session validation fails
3. A request returns a login redirect

### Background Monitoring

When `auto_refresh=True`, a background thread:
- Checks session health every 5 minutes
- Validates cookies haven't expired
- Refreshes session proactively before expiry

### Cookie Expiry

Cookies are checked for expiry:
- On initialization
- Before each request
- Periodically by background monitor
- When manually calling `validate_session()`

## Error Handling

The API handles common errors:

- **Session Expired**: Automatically refreshes and retries request
- **Cookie File Missing**: Prompts to extract cookies first
- **Invalid Credentials**: Falls back to manual login
- **Network Errors**: Propagates standard `requests` exceptions

## Example Usage

### Basic Usage

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

api = KeyedInAPIEnhanced(auto_refresh=True)

# Session is automatically validated and refreshed
menu = api.get_menu()
print(menu)
```

### With Context Manager

```python
with KeyedInAPIEnhanced(auto_refresh=True) as api:
    menu = api.get_menu()
    work_orders = api.get_work_order_form()
    # Monitor automatically stops on exit
```

### Manual Refresh

```python
api = KeyedInAPIEnhanced(auto_refresh=False)

# Manually refresh when needed
if not api.validate_session():
    api.refresh_session()
```

### Custom Requests

```python
api = KeyedInAPIEnhanced()

# Make custom GET request
response = api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=30)
data = response.text

# Make custom POST request
response = api.post('/cgi-bin/mvi.exe/SUBMIT', data={'field': 'value'})
```

## Configuration

### Refresh Threshold

Set `refresh_threshold_minutes` to control when sessions refresh:
- `30` (default): Refresh if expires within 30 minutes
- `60`: Refresh if expires within 1 hour
- `5`: Refresh if expires within 5 minutes (more aggressive)

### Auto-Refresh

Disable auto-refresh for manual control:
```python
api = KeyedInAPIEnhanced(auto_refresh=False)
```

### Cookie File Location

Specify custom cookie file:
```python
api = KeyedInAPIEnhanced(cookies_file='custom/path/cookies.json')
```

## Troubleshooting

### Cookies Not Found

If you see "Cookie file not found":
1. Run `keyedin_cdp_extractor.py` to extract cookies
2. Or manually log in and extract cookies using the extractor

### Session Keeps Expiring

If sessions expire frequently:
1. Check cookie expiry times in the cookie file
2. Reduce `refresh_threshold_minutes` for more aggressive refresh
3. Ensure background monitor is running (`auto_refresh=True`)

### Chrome Not Opening

If Chrome doesn't open during cookie extraction:
1. Ensure Chrome is installed
2. Check that `webdriver_manager` can download ChromeDriver
3. Try running with elevated permissions

### Auto-Login Fails

If auto-login fails:
- The extractor will fall back to manual login
- Enter credentials manually in the Chrome window
- Cookies will still be extracted successfully

## Migration from Legacy API

Replace:
```python
from keyedin_api import KeyedInAPI
api = KeyedInAPI()
```

With:
```python
from keyedin_api_enhanced import KeyedInAPIEnhanced
api = KeyedInAPIEnhanced(auto_refresh=True)
```

The enhanced API is backward compatible with the same method names.

## Security Notes

- Cookies contain session tokens - keep `keyedin_chrome_session.json` secure
- Don't commit cookie files to version control
- Use environment variables for credentials when possible
- Sessions expire automatically for security

## Requirements

- Python 3.7+
- selenium
- webdriver-manager
- requests

Install dependencies:
```bash
pip install selenium webdriver-manager requests
```

## License

See project license file.

