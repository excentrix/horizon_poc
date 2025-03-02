# main.py
import subprocess
import os
import sys

def main():
    """Run the Streamlit app"""
    try:
        subprocess.run([
            "streamlit", "run", 
            os.path.join("frontend", "app.py")
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()