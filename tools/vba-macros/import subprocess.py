import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_pandas():
    try:
        import pandas as pd
        print(f"Pandas version: {pd.__version__}")
    except ImportError:
        print("Pandas is not installed. Installing now...")
        install('pandas')
        try:
            import pandas as pd
            print(f"Pandas version: {pd.__version__}")
        except ImportError:
            print("Failed to install pandas")

check_pandas()
