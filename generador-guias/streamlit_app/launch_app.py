#!/usr/bin/env python3
"""
Launcher script for the Streamlit app with terminal-based subject selection.
This script handles subject selection in the terminal before starting the Streamlit app.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from config import SUBJECT_FOLDERS

def select_subject_in_terminal():
    """
    Display a numbered menu in the terminal for subject selection.
    Returns the selected subject.
    """
    subjects = list(SUBJECT_FOLDERS.keys())
    
    print("\n" + "="*50)
    print("🧠 GENERADOR DE GUÍAS M30M")
    print("="*50)
    print("\n📚 Selecciona una Asignatura:")
    print("Elige el número correspondiente a la asignatura que deseas cargar:\n")
    
    # Display numbered list of subjects
    for i, subject in enumerate(subjects, 1):
        print(f"  {i}. {subject}")
    
    print("\n" + "-"*50)
    
    while True:
        try:
            choice = input("Ingresa el número de la asignatura (1-{}): ".format(len(subjects)))
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(subjects):
                selected_subject = subjects[choice_num - 1]
                print(f"\n✅ Asignatura seleccionada: {selected_subject}")
                print("🚀 Iniciando aplicación...\n")
                return selected_subject
            else:
                print(f"❌ Por favor ingresa un número entre 1 y {len(subjects)}")
        except ValueError:
            print("❌ Por favor ingresa un número válido")
        except KeyboardInterrupt:
            print("\n\n👋 Aplicación cancelada por el usuario")
            sys.exit(0)

def main():
    """Main launcher function."""
    # Select subject in terminal
    selected_subject = select_subject_in_terminal()
    
    # Set the selected subject as an environment variable
    os.environ['STREAMLIT_SELECTED_SUBJECT'] = selected_subject
    
    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"
    
    # Launch Streamlit with the app
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(app_path),
            "--server.headless", "true",
            "--server.port", "8501"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Aplicación cerrada por el usuario")
        sys.exit(0)

if __name__ == "__main__":
    main()
