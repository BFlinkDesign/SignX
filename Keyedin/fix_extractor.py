#!/usr/bin/env python3
"""Fix the keyedin_data_extractor.py payload format"""

# Read the file
with open('keyedin_data_extractor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the wrong payload format
# Change 7|0|10| to 7|0|9|
content = content.replace("'7|0|10|'", "'7|0|9|'")

# Fix the trailing sequence
# Change 1|2|3|4|4|5|6|7|8|6|9|6|10| to 1|2|3|4|3|5|6|7|8|6|9|
content = content.replace(
    "'1|2|3|4|4|5|6|7|8|6|9|6|10|'",
    "'1|2|3|4|3|5|6|7|8|6|9|'"
)

# Write back
with open('keyedin_data_extractor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed keyedin_data_extractor.py")
print("✓ Changed payload format to match working version")
print("\nNow run:")
print("  python keyedin_data_extractor.py --session-file keyedin_session.json --limit 1")
