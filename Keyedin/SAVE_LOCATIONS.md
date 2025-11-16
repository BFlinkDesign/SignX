# File Save Locations

All files are now saved to the **project root** directory, regardless of where you run the scripts from.

## Project Root

The project root is automatically determined as the directory where the script files are located:
- **Location**: `c:\Scripts\SignX\Keyedin\`

## Saved Files

### 1. Cookies File
- **Default filename**: `keyedin_chrome_session.json`
- **Full path**: `c:\Scripts\SignX\Keyedin\keyedin_chrome_session.json`
- **Contains**: Session cookies extracted from Chrome
- **Saved by**: 
  - `KeyedInAPIEnhanced` (when refreshing session)
  - `KeyedInCDPExtractor` (when extracting cookies)

### 2. Network Data File (Optional)
- **Default filename**: `keyedin_chrome_session_network.json`
- **Full path**: `c:\Scripts\SignX\Keyedin\keyedin_chrome_session_network.json`
- **Contains**: Network requests captured during extraction
- **Saved by**: `KeyedInCDPExtractor` when `capture_network=True`

## How It Works

Both `keyedin_api_enhanced.py` and `keyedin_cdp_extractor.py` use a `get_project_root()` function that:
1. Gets the directory where the script file is located
2. Resolves all relative paths relative to this project root
3. Preserves absolute paths if you specify them

## Examples

### Default Behavior (Saves to Project Root)
```python
from keyedin_api_enhanced import KeyedInAPIEnhanced

# This saves to: c:\Scripts\SignX\Keyedin\keyedin_chrome_session.json
api = KeyedInAPIEnhanced(cookies_file='keyedin_chrome_session.json')
```

### Custom Relative Path (Still in Project Root)
```python
# This saves to: c:\Scripts\SignX\Keyedin\data\cookies.json
api = KeyedInAPIEnhanced(cookies_file='data/cookies.json')
```

### Absolute Path (Overrides Project Root)
```python
# This saves to: C:\MyData\cookies.json (absolute path)
api = KeyedInAPIEnhanced(cookies_file='C:/MyData/cookies.json')
```

## Verification

To check where files will be saved:

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

print(f"Project root: {get_project_root()}")
api = KeyedInAPIEnhanced()
print(f"Cookies file: {api.cookies_file}")
```

Or run:
```bash
python verify_setup.py
```

## Benefits

✅ **Consistent location**: Files always saved in the same place  
✅ **Predictable**: Easy to find your cookies and data  
✅ **Works from anywhere**: Run scripts from any directory  
✅ **Version control friendly**: All project files in one place  


