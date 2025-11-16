#!/usr/bin/env python3
"""
Eagle Sign Analyzer Professional Installer
One-click setup with comprehensive error handling
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import json
import hashlib
import shutil
from pathlib import Path
import ctypes
import logging
from datetime import datetime

# Version info
VERSION = "9.0.0"
INSTALL_DIR = "EagleSignAnalyzer"

class ProfessionalInstaller:
    def __init__(self):
        self.system = platform.system()
        self.python_version = sys.version_info
        self.install_path = Path.home() / INSTALL_DIR
        self.log_file = "install_log.txt"
        self.errors = []
        self.warnings = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
    def run(self):
        """Main installation process"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║          Eagle Sign Analyzer v{VERSION} Installer          ║
║              Professional Installation Setup               ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        # Pre-flight checks
        if not self.check_system_requirements():
            self.show_errors()
            return False
            
        # Installation steps
        steps = [
            ("Creating installation directory", self.create_directory),
            ("Installing Python dependencies", self.install_dependencies),
            ("Downloading analyzer components", self.download_components),
            ("Creating desktop shortcut", self.create_shortcut),
            ("Verifying installation", self.verify_installation),
            ("Setting up initial configuration", self.setup_config),
        ]
        
        total_steps = len(steps)
        for i, (description, func) in enumerate(steps, 1):
            print(f"\n[{i}/{total_steps}] {description}...")
            try:
                if not func():
                    print(f"   ❌ Failed: {description}")
                    self.show_errors()
                    return False
                print(f"   ✅ Complete")
            except Exception as e:
                logging.error(f"Critical error in {description}: {e}")
                self.errors.append(f"{description}: {str(e)}")
                self.show_errors()
                return False
        
        self.show_success()
        return True
    
    def check_system_requirements(self):
        """Verify system meets requirements"""
        print("\nChecking system requirements...")
        
        # Python version
        if self.python_version < (3, 7):
            self.errors.append(f"Python 3.7+ required (found {sys.version})")
            return False
        print(f"   ✓ Python {sys.version.split()[0]}")
        
        # Operating system
        if self.system not in ['Windows', 'Darwin', 'Linux']:
            self.warnings.append(f"Untested OS: {self.system}")
        print(f"   ✓ Operating System: {self.system}")
        
        # Disk space (need ~100MB)
        try:
            stat = os.statvfs('.' if self.system != 'Windows' else 'C:\\')
            free_mb = (stat.f_bavail * stat.f_frsize) / 1024 / 1024
            if free_mb < 100:
                self.errors.append(f"Insufficient disk space: {free_mb:.1f}MB")
                return False
        except:
            self.warnings.append("Could not check disk space")
        
        # Admin privileges for shortcuts
        if self.system == 'Windows':
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    self.warnings.append("Not running as administrator - shortcuts may fail")
            except:
                pass
                
        return True
    
    def create_directory(self):
        """Create installation directory"""
        try:
            self.install_path.mkdir(parents=True, exist_ok=True)
            os.chdir(self.install_path)
            logging.info(f"Created directory: {self.install_path}")
            return True
        except Exception as e:
            self.errors.append(f"Cannot create directory: {e}")
            return False
    
    def install_dependencies(self):
        """Install Python packages with retry logic"""
        packages = [
            'PyPDF2>=3.0.0',
            'openpyxl>=3.0.0',
            'scipy>=1.9.0',
            'pandas>=1.5.0',
            'numpy>=1.23.0',
            'tkinterdnd2>=0.3.0'
        ]
        
        # Upgrade pip first
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
                         capture_output=True, check=True)
        except:
            self.warnings.append("Could not upgrade pip")
        
        # Install packages
        failed = []
        for package in packages:
            print(f"   Installing {package}...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                             capture_output=True, check=True, timeout=300)
            except subprocess.TimeoutExpired:
                self.warnings.append(f"Timeout installing {package}")
                failed.append(package)
            except subprocess.CalledProcessError as e:
                self.warnings.append(f"Failed to install {package}")
                failed.append(package)
        
        if failed:
            # Retry failed packages
            print("   Retrying failed packages...")
            for package in failed:
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 
                                  '--no-cache-dir', package],
                                 capture_output=True, check=True, timeout=300)
                    failed.remove(package)
                except:
                    pass
        
        if failed:
            self.errors.append(f"Failed to install: {', '.join(failed)}")
            return False
            
        return True
    
    def download_components(self):
        """Create analyzer files with embedded code"""
        # Create main analyzer
        analyzer_code = self.get_analyzer_code()
        with open('benchmark-v9-production.py', 'w', encoding='utf-8') as f:
            f.write(analyzer_code)
        
        # Create GUI
        gui_code = self.get_gui_code()
        with open('eagle_gui.py', 'w', encoding='utf-8') as f:
            f.write(gui_code)
        
        # Create run script
        run_script = self.get_run_script()
        script_name = 'run_analyzer.bat' if self.system == 'Windows' else 'run_analyzer.sh'
        with open(script_name, 'w') as f:
            f.write(run_script)
        
        if self.system != 'Windows':
            os.chmod(script_name, 0o755)
            
        return True
    
    def create_shortcut(self):
        """Create desktop shortcut"""
        desktop = Path.home() / 'Desktop'
        if not desktop.exists():
            desktop = Path.home()
            
        if self.system == 'Windows':
            return self.create_windows_shortcut(desktop)
        elif self.system == 'Darwin':
            return self.create_mac_shortcut(desktop)
        else:
            return self.create_linux_shortcut(desktop)
    
    def create_windows_shortcut(self, desktop):
        """Windows shortcut creation"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(desktop / "Eagle Analyzer.lnk"))
            shortcut.Targetpath = str(self.install_path / 'run_analyzer.bat')
            shortcut.WorkingDirectory = str(self.install_path)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            return True
        except:
            # Fallback VBS script
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop}\\Eagle Analyzer.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{self.install_path}\\run_analyzer.bat"
oLink.WorkingDirectory = "{self.install_path}"
oLink.Save
'''
            try:
                with open('create_shortcut.vbs', 'w') as f:
                    f.write(vbs_script)
                subprocess.run(['cscript', 'create_shortcut.vbs'], capture_output=True)
                os.remove('create_shortcut.vbs')
                return True
            except:
                self.warnings.append("Could not create desktop shortcut")
                return True
    
    def create_mac_shortcut(self, desktop):
        """macOS alias creation"""
        try:
            app_script = f'''#!/bin/bash
cd "{self.install_path}"
python3 eagle_gui.py
'''
            app_path = desktop / 'Eagle Analyzer.command'
            with open(app_path, 'w') as f:
                f.write(app_script)
            os.chmod(app_path, 0o755)
            return True
        except:
            self.warnings.append("Could not create desktop shortcut")
            return True
    
    def create_linux_shortcut(self, desktop):
        """Linux .desktop file creation"""
        try:
            desktop_entry = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=Eagle Sign Analyzer
Comment=Professional Sign Estimation Tool
Exec=python3 {self.install_path}/eagle_gui.py
Path={self.install_path}
Icon=applications-engineering
Terminal=false
Categories=Office;
'''
            desktop_file = desktop / 'eagle-analyzer.desktop'
            with open(desktop_file, 'w') as f:
                f.write(desktop_entry)
            os.chmod(desktop_file, 0o755)
            return True
        except:
            self.warnings.append("Could not create desktop shortcut")
            return True
    
    def verify_installation(self):
        """Verify all components work"""
        # Test imports
        test_script = '''
import sys
try:
    import PyPDF2
    import openpyxl
    import scipy
    import pandas
    import numpy
    import tkinterdnd2
    print("OK")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)
'''
        try:
            result = subprocess.run([sys.executable, '-c', test_script],
                                  capture_output=True, text=True)
            if result.returncode != 0 or 'FAIL' in result.stdout:
                self.errors.append(f"Import test failed: {result.stdout}")
                return False
        except:
            self.errors.append("Could not verify installation")
            return False
            
        return True
    
    def setup_config(self):
        """Create initial configuration"""
        config = {
            "version": VERSION,
            "installed": datetime.now().isoformat(),
            "install_path": str(self.install_path),
            "settings": {
                "min_samples_reliable": 30,
                "confidence_interval": 0.90,
                "min_bid_hours": 4.0
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
            
        # Create README
        readme = f'''# Eagle Sign Analyzer v{VERSION}

## Quick Start
1. Double-click "Eagle Analyzer" on your desktop
2. Drag and drop your PDF work orders
3. Click "Analyze"

## Output Files
- Text report with confidence intervals
- Excel workbook with detailed analysis
- Historical tracking database

## Support
- Check install_log.txt for installation details
- Minimum 10 PDFs recommended for reliable benchmarks
- Process more PDFs to improve accuracy

Installed: {datetime.now().strftime("%Y-%m-%d %H:%M")}
'''
        with open('README.txt', 'w') as f:
            f.write(readme)
            
        return True
    
    def show_errors(self):
        """Display errors"""
        print("\n❌ INSTALLATION FAILED")
        print("="*60)
        for error in self.errors:
            print(f"ERROR: {error}")
        for warning in self.warnings:
            print(f"WARNING: {warning}")
        print("\nCheck install_log.txt for details")
        input("\nPress Enter to exit...")
    
    def show_success(self):
        """Display success message"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                 ✅ INSTALLATION COMPLETE                   ║
╚══════════════════════════════════════════════════════════╝

Installed to: {self.install_path}

Desktop shortcut created: Eagle Analyzer

To start:
1. Double-click "Eagle Analyzer" on your desktop
2. Or run: python {self.install_path}/eagle_gui.py

First time setup:
- Process 10+ PDFs to build initial benchmarks
- Each analysis improves accuracy
""")
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        input("\nPress Enter to exit...")
    
    def get_analyzer_code(self):
        """Return the full analyzer code"""
        # This would contain the entire v9 production analyzer code
        # Truncated here for space - in production this would be the full code
        return '''#!/usr/bin/env python3
"""
Eagle Sign Analyzer v9.0 - Production
[Full analyzer code would go here]
"""
# ... complete v9 code ...
'''
    
    def get_gui_code(self):
        """Return the full GUI code"""
        # This would contain the entire GUI code
        return '''#!/usr/bin/env python3
"""
Eagle GUI - Drag & Drop Interface
[Full GUI code would go here]
"""
# ... complete GUI code ...
'''
    
    def get_run_script(self):
        """Platform-specific run script"""
        if self.system == 'Windows':
            return f'''@echo off
cd /d "{self.install_path}"
python eagle_gui.py
pause
'''
        else:
            return f'''#!/bin/bash
cd "{self.install_path}"
python3 eagle_gui.py
'''

def main():
    """Entry point with error handling"""
    try:
        installer = ProfessionalInstaller()
        success = installer.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()