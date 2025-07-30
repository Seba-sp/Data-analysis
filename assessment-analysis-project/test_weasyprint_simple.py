#!/usr/bin/env python3
"""
Simple test to check WeasyPrint installation and provide detailed error information
"""
import sys
import os

def test_weasyprint_import():
    """Test WeasyPrint import and provide detailed error information"""
    print("Testing WeasyPrint installation...")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Architecture: {sys.maxsize > 2**32 and '64 bit' or '32 bit'}")
    
    try:
        print("\nAttempting to import weasyprint...")
        import weasyprint
        print("✅ WeasyPrint imported successfully!")
        
        try:
            version = weasyprint.__version__
            print(f"✅ WeasyPrint version: {version}")
        except AttributeError:
            print("✅ WeasyPrint imported (version unknown)")
            
        return True
        
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print("💡 Solution: pip install weasyprint")
        return False
        
    except Exception as e:
        print(f"❌ Error importing WeasyPrint: {e}")
        print("\n🔧 This is likely a system library issue on Windows.")
        print("💡 Solutions:")
        print("   1. Install GTK+ Runtime Environment")
        print("   2. Use WSL (Windows Subsystem for Linux)")
        print("   3. Install MSYS2 and required libraries")
        return False

def check_system_libraries():
    """Check for common system library paths"""
    print("\nChecking for system libraries...")
    
    # Common GTK+ library paths on Windows
    possible_paths = [
        r"C:\Program Files\GTK3-Runtime\bin",
        r"C:\Program Files (x86)\GTK3-Runtime\bin",
        r"C:\msys64\mingw64\bin",
        r"C:\msys64\usr\bin",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found: {path}")
        else:
            print(f"❌ Not found: {path}")
    
    # Check PATH environment
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    gtk_in_path = any('gtk' in dir.lower() for dir in path_dirs)
    print(f"GTK in PATH: {'✅' if gtk_in_path else '❌'}")

def main():
    """Main test function"""
    print("=" * 50)
    print("WeasyPrint Installation Test")
    print("=" * 50)
    
    success = test_weasyprint_import()
    check_system_libraries()
    
    if not success:
        print("\n" + "=" * 50)
        print("INSTALLATION INSTRUCTIONS FOR WINDOWS:")
        print("=" * 50)
        print("1. Download GTK+ Runtime Environment:")
        print("   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        print("2. Install with default settings")
        print("3. Restart your computer")
        print("4. Test again with: python test_weasyprint_simple.py")
        print("\nAlternative: Use WSL or Docker for better compatibility")

if __name__ == "__main__":
    main() 