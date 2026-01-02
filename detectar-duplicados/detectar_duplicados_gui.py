"""
Simple GUI for Duplicate Question Detector
No coding knowledge required - just run this file!
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import sys
from pathlib import Path

# Import the detection functions from the main script
try:
    from detectar_duplicados import (
        extract_questions_with_alternatives,
        compare_questions,
        generate_report,
        generate_text_summary
    )
except ImportError:
    messagebox.showerror("Error", "Could not find detectar_duplicados.py in the same folder!")
    sys.exit(1)


class DuplicateDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Preguntas Duplicadas")
        self.root.geometry("850x800")
        self.root.resizable(True, True)
        
        # Set minimum window size
        self.root.minsize(750, 700)
        
        # Variables
        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.output_name = tk.StringVar(value="duplicate_report")
        self.threshold = tk.DoubleVar(value=0.04)
        self.debug_mode = tk.BooleanVar(value=False)
        self.comparison_mode = tk.StringVar(value="folder")  # "file" or "folder"
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Title
        title_label = ttk.Label(main_frame, text="Detector de Preguntas Duplicadas", 
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        row += 1
        
        # Subtitle
        subtitle = ttk.Label(main_frame, text="Detecta preguntas con 4 (A-D) o 5 (A-E) alternativas", 
                            font=('Arial', 9), foreground='gray')
        subtitle.grid(row=row, column=0, columnspan=3, pady=(0, 15))
        row += 1
        
        # File 1 selection (required)
        ttk.Label(main_frame, text="Archivo principal:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Entry(main_frame, textvariable=self.file1_path, width=60).grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Seleccionar", command=self.browse_file1).grid(
            row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Comparison mode selection
        ttk.Label(main_frame, text="Comparar con:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Radiobutton(mode_frame, text="Un solo archivo", variable=self.comparison_mode, 
                       value="file", command=self.update_mode).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Todos los archivos en una carpeta", 
                       variable=self.comparison_mode, value="folder", 
                       command=self.update_mode).pack(side=tk.LEFT, padx=10)
        row += 1
        
        # File 2 selection (for file mode)
        self.file2_label = ttk.Label(main_frame, text="Segundo archivo:")
        self.file2_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        self.file2_entry = ttk.Entry(main_frame, textvariable=self.file2_path, width=60)
        self.file2_entry.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.file2_button = ttk.Button(main_frame, text="Seleccionar", command=self.browse_file2)
        self.file2_button.grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Folder selection (for folder mode)
        self.folder_label = ttk.Label(main_frame, text="Carpeta con archivos:")
        self.folder_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        self.folder_entry = ttk.Entry(main_frame, textvariable=self.folder_path, width=60)
        self.folder_entry.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.folder_button = ttk.Button(main_frame, text="Seleccionar", command=self.browse_folder)
        self.folder_button.grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Options section - all on one line
        ttk.Label(main_frame, text="Opciones:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        # All options in a single frame on one line
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Output name
        ttk.Label(options_frame, text="Nombre:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(options_frame, textvariable=self.output_name, width=18).pack(side=tk.LEFT, padx=(0, 15))
        
        # Threshold slider
        ttk.Label(options_frame, text="Similitud:").pack(side=tk.LEFT, padx=(0, 5))
        threshold_slider = ttk.Scale(options_frame, from_=0.01, to=0.10, 
                                    variable=self.threshold, orient=tk.HORIZONTAL, length=120)
        threshold_slider.pack(side=tk.LEFT, padx=(0, 5))
        self.threshold_label = ttk.Label(options_frame, text="0.04", width=4)
        self.threshold_label.pack(side=tk.LEFT, padx=(0, 15))
        threshold_slider.config(command=self.update_threshold_label)
        
        # Debug checkbox
        ttk.Checkbutton(options_frame, text="Debug", variable=self.debug_mode).pack(side=tk.LEFT)
        
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Run button and progress bar on the same line
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="🔍 Buscar Duplicados", 
                                     command=self.run_detection, style='Accent.TButton')
        self.run_button.pack(side=tk.LEFT, padx=(0, 15))
        
        self.progress = ttk.Progressbar(button_frame, mode='indeterminate', length=450)
        self.progress.pack(side=tk.LEFT)
        
        row += 1
        
        # Status/Results text area
        ttk.Label(main_frame, text="Resultados:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1
        
        self.results_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, 
                                                     wrap=tk.WORD, font=('Consolas', 9))
        self.results_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), 
                              pady=5)
        main_frame.rowconfigure(row, weight=1)
        row += 1
        
        # Initial mode update
        self.update_mode()
        
        # Welcome message
        self.log("Bienvenido al Detector de Preguntas Duplicadas")
        self.log("1. Selecciona el archivo principal")
        self.log("2. Elige si comparar con un archivo o una carpeta")
        self.log("3. Presiona 'Buscar Duplicados'")
        self.log("-" * 60)
    
    def update_threshold_label(self, value):
        self.threshold_label.config(text=f"{float(value):.2f}")
    
    def update_mode(self):
        """Show/hide fields based on comparison mode"""
        if self.comparison_mode.get() == "file":
            # Show file2, hide folder
            self.file2_label.grid()
            self.file2_entry.grid()
            self.file2_button.grid()
            self.folder_label.grid_remove()
            self.folder_entry.grid_remove()
            self.folder_button.grid_remove()
        else:
            # Show folder, hide file2
            self.file2_label.grid_remove()
            self.file2_entry.grid_remove()
            self.file2_button.grid_remove()
            self.folder_label.grid()
            self.folder_entry.grid()
            self.folder_button.grid()
    
    def browse_file1(self):
        filename = filedialog.askopenfilename(
            title="Selecciona el archivo principal",
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        if filename:
            self.file1_path.set(filename)
    
    def browse_file2(self):
        filename = filedialog.askopenfilename(
            title="Selecciona el segundo archivo",
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        if filename:
            self.file2_path.set(filename)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta con archivos")
        if folder:
            self.folder_path.set(folder)
    
    def log(self, message):
        """Add message to results text area"""
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(tk.END)
        self.results_text.update()
    
    def clear_log(self):
        """Clear results text area"""
        self.results_text.delete(1.0, tk.END)
    
    def validate_inputs(self):
        """Validate that all required inputs are provided"""
        if not self.file1_path.get():
            messagebox.showerror("Error", "Debes seleccionar el archivo principal")
            return False
        
        if not Path(self.file1_path.get()).exists():
            messagebox.showerror("Error", f"El archivo no existe: {self.file1_path.get()}")
            return False
        
        if self.comparison_mode.get() == "file":
            if not self.file2_path.get():
                messagebox.showerror("Error", "Debes seleccionar el segundo archivo")
                return False
            if not Path(self.file2_path.get()).exists():
                messagebox.showerror("Error", f"El archivo no existe: {self.file2_path.get()}")
                return False
        else:
            if not self.folder_path.get():
                messagebox.showerror("Error", "Debes seleccionar una carpeta")
                return False
            if not Path(self.folder_path.get()).exists():
                messagebox.showerror("Error", f"La carpeta no existe: {self.folder_path.get()}")
                return False
        
        return True
    
    def run_detection(self):
        """Run the duplicate detection in a separate thread"""
        if not self.validate_inputs():
            return
        
        # Disable button and clear log
        self.run_button.config(state='disabled')
        self.clear_log()
        self.progress.start()
        
        # Run in thread to keep GUI responsive
        thread = threading.Thread(target=self.perform_detection, daemon=True)
        thread.start()
    
    def perform_detection(self):
        """Actual detection logic (runs in separate thread)"""
        try:
            file1_path = Path(self.file1_path.get())
            debug = self.debug_mode.get()
            threshold = self.threshold.get()
            
            self.log("=" * 60)
            self.log(f"Cargando preguntas de: {file1_path.name}")
            
            # Extract questions from file1
            file1_questions = extract_questions_with_alternatives(str(file1_path), debug=debug)
            self.log(f"✓ Encontradas {len(file1_questions)} preguntas")
            
            all_repeated = []
            all_possible = []
            
            # File to file comparison
            if self.comparison_mode.get() == "file":
                file2_path = Path(self.file2_path.get())
                self.log(f"\nComparando con: {file2_path.name}")
                
                file2_questions = extract_questions_with_alternatives(str(file2_path), debug=debug)
                self.log(f"✓ Encontradas {len(file2_questions)} preguntas")
                
                repeated, possible = compare_questions(
                    file1_questions, file2_questions,
                    file1_path.name, file2_path.name,
                    threshold
                )
                all_repeated.extend(repeated)
                all_possible.extend(possible)
            
            # File to folder comparison
            else:
                folder_path = Path(self.folder_path.get())
                docx_files = list(folder_path.glob('*.docx'))
                docx_files = [f for f in docx_files if not f.name.startswith('~$')]
                
                if not docx_files:
                    self.log(f"\n❌ No se encontraron archivos .docx en: {folder_path}")
                    return
                
                self.log(f"\n✓ Encontrados {len(docx_files)} archivos en la carpeta")
                
                for file2_path in docx_files:
                    # Skip comparing file with itself
                    if file2_path.resolve() == file1_path.resolve():
                        continue
                    
                    self.log(f"\nComparando con: {file2_path.name}")
                    file2_questions = extract_questions_with_alternatives(str(file2_path), debug=debug)
                    self.log(f"  Encontradas {len(file2_questions)} preguntas")
                    
                    repeated, possible = compare_questions(
                        file1_questions, file2_questions,
                        file1_path.name, file2_path.name,
                        threshold
                    )
                    all_repeated.extend(repeated)
                    all_possible.extend(possible)
            
            # Generate reports
            self.log("\n" + "=" * 60)
            self.log("RESULTADOS:")
            self.log(f"  ✓ Duplicados exactos: {len(all_repeated)}")
            self.log(f"  ~ Posibles coincidencias: {len(all_possible)}")
            self.log("=" * 60)
            
            output_dir = file1_path.parent
            output_name = self.output_name.get() or "duplicate_report"
            report_docx = output_dir / f"{output_name}.docx"
            report_txt = output_dir / f"{output_name}.txt"
            
            generate_report(all_repeated, all_possible, str(report_docx))
            generate_text_summary(all_repeated, all_possible, str(report_txt))
            
            self.log(f"\n📄 Reporte guardado en:")
            self.log(f"   {report_docx}")
            self.log(f"   {report_txt}")
            self.log("\n✅ ¡Proceso completado!")
            
            # Show success message
            self.root.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Proceso completado exitosamente!\n\n"
                f"Duplicados exactos: {len(all_repeated)}\n"
                f"Posibles coincidencias: {len(all_possible)}\n\n"
                f"Reportes guardados en:\n{output_dir}"
            ))
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.log(f"\n{error_msg}")
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        finally:
            # Re-enable button and stop progress
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.run_button.config(state='normal'))


def main():
    root = tk.Tk()
    app = DuplicateDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

