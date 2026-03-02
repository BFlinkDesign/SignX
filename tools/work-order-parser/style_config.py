"""
Eagle Sign Work Order Parser Style Configuration
"""

# Brand Colors
BRAND_COLORS = {
    'red': '#DA291C',      # PMS 485 Red
    'black': '#000000',    # 100% Black
    'gray': '#A7A8AA',     # 50% Black (Gray)
    'white': '#FFFFFF',    # White
}

# Mode Color Palettes
COLOR_MODES = {
    'light': {
        'background': BRAND_COLORS['white'],
        'text': BRAND_COLORS['black'],
        'primary': BRAND_COLORS['red'],
        'secondary': BRAND_COLORS['black'],
        'accent': BRAND_COLORS['gray'],
        'button': BRAND_COLORS['red'],
        'button_text': BRAND_COLORS['white'],
        'button_hover': BRAND_COLORS['black'],
        'table_header': BRAND_COLORS['red'],
        'table_header_text': BRAND_COLORS['white'],
        'table_row_even': BRAND_COLORS['white'],
        'table_row_odd': '#F5F5F5',
        'border': BRAND_COLORS['gray'],
    },
    'gray': {
        'background': BRAND_COLORS['gray'],
        'text': BRAND_COLORS['black'],
        'primary': BRAND_COLORS['red'],
        'secondary': BRAND_COLORS['black'],
        'accent': BRAND_COLORS['white'],
        'button': BRAND_COLORS['red'],
        'button_text': BRAND_COLORS['white'],
        'button_hover': BRAND_COLORS['black'],
        'table_header': BRAND_COLORS['red'],
        'table_header_text': BRAND_COLORS['white'],
        'table_row_even': BRAND_COLORS['gray'],
        'table_row_odd': '#C0C0C0',
        'border': BRAND_COLORS['black'],
    },
    'dark': {
        'background': BRAND_COLORS['black'],
        'text': BRAND_COLORS['white'],
        'primary': BRAND_COLORS['red'],
        'secondary': BRAND_COLORS['gray'],
        'accent': BRAND_COLORS['white'],
        'button': BRAND_COLORS['red'],
        'button_text': BRAND_COLORS['white'],
        'button_hover': BRAND_COLORS['gray'],
        'table_header': BRAND_COLORS['red'],
        'table_header_text': BRAND_COLORS['white'],
        'table_row_even': '#222222',
        'table_row_odd': '#333333',
        'border': BRAND_COLORS['gray'],
    },
}

# Font Configuration
FONTS = {
    'main': 'Arial Black, Impact, Segoe UI, Arial, sans-serif',
    'heading': 'Arial Black, Impact, Segoe UI, Arial, sans-serif',
    'monospace': 'Consolas, monospace'
}

# Font Sizes
FONT_SIZES = {
    'small': 10,
    'normal': 12,
    'large': 14,
    'xlarge': 16,
    'xxlarge': 20,
    'title': 28
}

# Styles
STYLES = {
    'button': {
        'background-color': BRAND_COLORS['red'],
        'color': BRAND_COLORS['white'],
        'border': 'none',
        'padding': '8px 16px',
        'border-radius': '4px',
        'font-weight': 'bold'
    },
    'button_hover': {
        'background-color': BRAND_COLORS['black']
    },
    'input': {
        'border': f'1px solid {BRAND_COLORS["gray"]}',
        'border-radius': '4px',
        'padding': '8px',
        'font-size': FONT_SIZES['normal']
    },
    'table': {
        'header_background': BRAND_COLORS['red'],
        'header_color': BRAND_COLORS['white'],
        'row_even': BRAND_COLORS['white'],
        'row_odd': '#F5F5F5',
        'border': f'1px solid {BRAND_COLORS["gray"]}'
    },
    'progress_bar': {
        'background': BRAND_COLORS['gray'],
        'progress': BRAND_COLORS['red'],
        'text': BRAND_COLORS['black']
    }
}

# Application Theme
THEME = {
    'name': 'Eagle Sign Theme',
    'version': '1.0',
    'description': 'Eagle Sign Work Order Parser Theme',
    'author': 'Eagle Sign Co.',
    'company': 'Eagle Sign Co.',
    'website': 'www.eaglesign.net',
    'logo_path': 'assets/eagle_sign_logo.png',
    'icon_path': 'assets/eagle_sign_icon.ico'
}

# Window Configuration
WINDOW = {
    'title': 'Eagle Sign Work Order Parser',
    'min_width': 1024,
    'min_height': 768,
    'icon': THEME['icon_path']
}

# Export Formats
EXPORT_FORMATS = {
    'excel': {
        'name': 'Excel Spreadsheet',
        'extension': '.xlsx',
        'icon': 'assets/excel_icon.png'
    },
    'csv': {
        'name': 'CSV File',
        'extension': '.csv',
        'icon': 'assets/csv_icon.png'
    },
    'json': {
        'name': 'JSON File',
        'extension': '.json',
        'icon': 'assets/json_icon.png'
    },
    'pdf': {
        'name': 'PDF Document',
        'extension': '.pdf',
        'icon': 'assets/pdf_icon.png'
    },
    'word': {
        'name': 'Word Document',
        'extension': '.docx',
        'icon': 'assets/word_icon.png'
    }
}

# Department Colors
DEPARTMENT_COLORS = {
    'ES': BRAND_COLORS['red'],    # Engineering Services
    'SC': BRAND_COLORS['black'],   # Sales
    'PR': '#28A745',               # Production
    'MFG': '#17A2B8',              # Manufacturing
    'ENG': BRAND_COLORS['gray'],   # Engineering
    'QA': BRAND_COLORS['red']      # Quality Assurance
} 