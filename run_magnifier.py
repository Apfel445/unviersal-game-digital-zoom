#!/usr/bin/env python3
"""
Simple launcher for the Screen Magnifier application.
"""

import sys
import importlib.util

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = {
        'mss': 'mss',
        'PyQt5': 'PyQt5.QtWidgets',
        'keyboard': 'keyboard',
        'cv2': 'cv2',
        'numpy': 'numpy'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"✗ {package_name} missing")
    
    if missing_packages:
        print(f"\nInstall missing packages: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("Screen Magnifier Launcher")
    print("=" * 25)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Run the magnifier
    try:
        print("\nStarting Screen Magnifier...")
        from magnifier import run_magnifier_app
        return run_magnifier_app()
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())