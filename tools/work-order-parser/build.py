import PyInstaller.__main__
import os

def build_exe():
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the icon path (you'll need to add an icon file)
    icon_path = os.path.join(current_dir, 'icon.ico')
    
    # Define the spec file path
    spec_path = os.path.join(current_dir, 'work_order_parser.spec')
    
    # PyInstaller arguments
    args = [
        'work_order_parser.py',  # Your main script
        '--name=Work Order Parser',  # Name of your executable
        '--onefile',  # Create a single executable
        '--windowed',  # Don't show console window
        '--clean',  # Clean PyInstaller cache
        '--add-data=README.md;.',  # Include README
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=openpyxl',
        '--hidden-import=PyPDF2',
        '--hidden-import=python-dateutil',
        '--hidden-import=pydantic',
        '--hidden-import=scikit-learn',
        '--hidden-import=python-dotenv',
    ]
    
    # Add icon if it exists
    if os.path.exists(icon_path):
        args.append(f'--icon={icon_path}')
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    build_exe() 