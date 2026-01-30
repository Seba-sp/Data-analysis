import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import sys
import os

class PAESLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("PAES Pipeline Launcher")
        self.root.geometry("900x800")
        
        # Variables
        self.mode_var = tk.StringVar(value="batch")
        self.batches_var = tk.IntVar(value=1)
        self.topic_var = tk.StringVar()
        self.count_var = tk.IntVar(value=30)
        self.agent1_mode_var = tk.StringVar(value="agent")
        self.start_from_var = tk.StringVar(value="agent1")
        self.tsv_file_path = tk.StringVar()
        self.candidatos_file_path = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.reverse_var = tk.BooleanVar(value=False)
        
        self.process = None

        self._create_ui()

    def _create_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: Operation Mode ---
        mode_frame = ttk.LabelFrame(main_frame, text="Operation Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)

        modes = [
            ("Production Batch Mode", "batch"),
            ("Standalone Review (Agent 4)", "review"),
            ("Validate Config Only", "validate")
        ]

        for text, mode in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=mode, command=self._update_state).pack(anchor=tk.W)

        # --- Section 2: Pipeline Configuration (Agents 1-3) ---
        self.pipeline_frame = ttk.LabelFrame(main_frame, text="Pipeline Configuration (Agents 1-3)", padding="10")
        self.pipeline_frame.pack(fill=tk.X, pady=5)

        # Grid layout for config
        ttk.Label(self.pipeline_frame, text="Batches (for Production):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.batches_entry = ttk.Entry(self.pipeline_frame, textvariable=self.batches_var, width=10)
        self.batches_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.pipeline_frame, text="Topic (Optional):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.topic_entry = ttk.Entry(self.pipeline_frame, textvariable=self.topic_var, width=30)
        self.topic_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(self.pipeline_frame, text="Count (per batch):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.count_entry = ttk.Entry(self.pipeline_frame, textvariable=self.count_var, width=10)
        self.count_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.pipeline_frame, text="Agent 1 Mode:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        agent_modes = ["agent", "model"]
        self.agent1_combo = ttk.Combobox(self.pipeline_frame, textvariable=self.agent1_mode_var, values=agent_modes, state="readonly", width=10)
        self.agent1_combo.grid(row=1, column=3, sticky=tk.W, padx=5)

        ttk.Separator(self.pipeline_frame, orient='horizontal').grid(row=2, column=0, columnspan=4, sticky='ew', pady=10)

        # Advanced / Resume within Pipeline Frame
        ttk.Label(self.pipeline_frame, text="Start From:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        start_options = ["agent1", "agent2", "agent3"]
        self.start_combo = ttk.Combobox(self.pipeline_frame, textvariable=self.start_from_var, values=start_options, state="readonly", width=10)
        self.start_combo.grid(row=3, column=1, sticky=tk.W, padx=5)
        self.start_combo.bind("<<ComboboxSelected>>", self._update_state)

        self.reverse_check = ttk.Checkbutton(self.pipeline_frame, text="Reverse Order", variable=self.reverse_var)
        self.reverse_check.grid(row=3, column=2, sticky=tk.W, padx=5)

        # File Inputs
        ttk.Label(self.pipeline_frame, text="TSV/CSV File:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.tsv_entry = ttk.Entry(self.pipeline_frame, textvariable=self.tsv_file_path, width=50)
        self.tsv_entry.grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=5)
        self.tsv_btn = ttk.Button(self.pipeline_frame, text="Browse...", command=lambda: self._browse_file(self.tsv_file_path))
        self.tsv_btn.grid(row=4, column=3, padx=5)

        ttk.Label(self.pipeline_frame, text="Candidatos File (Optional):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.cand_entry = ttk.Entry(self.pipeline_frame, textvariable=self.candidatos_file_path, width=50)
        self.cand_entry.grid(row=5, column=1, columnspan=2, sticky=tk.W, padx=5)
        self.cand_btn = ttk.Button(self.pipeline_frame, text="Browse...", command=lambda: self._browse_file(self.candidatos_file_path))
        self.cand_btn.grid(row=5, column=3, padx=5)

        # --- Section 3: Standalone Review Configuration ---
        self.review_frame = ttk.LabelFrame(main_frame, text="Standalone Review Configuration (Agent 4)", padding="10")
        self.review_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.review_frame, text="Folder (Review Mode):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.folder_entry = ttk.Entry(self.review_frame, textvariable=self.folder_path, width=50)
        self.folder_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5)
        self.folder_btn = ttk.Button(self.review_frame, text="Browse...", command=lambda: self._browse_folder(self.folder_path))
        self.folder_btn.grid(row=0, column=3, padx=5)

        # --- Section 4: Execution & Output ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X, pady=5)

        self.run_btn = ttk.Button(action_frame, text="RUN PIPELINE", command=self.run_process)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(action_frame, text="STOP", command=self.stop_process, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Clear Console", command=self.clear_console).pack(side=tk.RIGHT, padx=5)

        # Console Output
        self.console = scrolledtext.ScrolledText(main_frame, height=15, state='disabled', bg="black", fg="white", font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True, pady=5)

        # Initial state update
        self._update_state()

    def _update_state(self, event=None):
        mode = self.mode_var.get()
        
        # Pipeline widgets to toggle
        pipeline_widgets = [
            self.batches_entry, self.topic_entry, self.count_entry, self.agent1_combo,
            self.start_combo, self.reverse_check, 
            self.tsv_entry, self.tsv_btn,
            self.cand_entry, self.cand_btn
        ]
        
        # Review widgets to toggle
        review_widgets = [self.folder_entry, self.folder_btn]

        if mode == "batch":
            self._set_widgets_state(pipeline_widgets, tk.NORMAL)
            self._set_widgets_state(review_widgets, tk.DISABLED)
            # Batches specific logic
            self.batches_entry.config(state=tk.NORMAL)
            
        elif mode == "review":
            self._set_widgets_state(pipeline_widgets, tk.DISABLED)
            self._set_widgets_state(review_widgets, tk.NORMAL)
            
        elif mode == "validate":
            self._set_widgets_state(pipeline_widgets, tk.DISABLED)
            self._set_widgets_state(review_widgets, tk.DISABLED)

    def _set_widgets_state(self, widgets, state):
        for widget in widgets:
            widget.config(state=state)

    def _browse_file(self, var):
        filename = filedialog.askopenfilename(filetypes=[("Data Files", "*.tsv *.csv *.txt"), ("All Files", "*.*")])
        if filename:
            var.set(filename)

    def _browse_folder(self, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def log(self, message):
        self.console.config(state='normal')
        self.console.insert(tk.END, message)
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def clear_console(self):
        self.console.config(state='normal')
        self.console.delete(1.0, tk.END)
        self.console.config(state='disabled')

    def build_command(self):
        cmd = [sys.executable, "main.py"]
        mode = self.mode_var.get()

        if mode == "batch":
            cmd.extend(["--batches", str(self.batches_var.get())])
        elif mode == "validate":
            cmd.append("--validate-only")
        elif mode == "review":
            cmd.append("--review-standalone")
            if not self.folder_path.get():
                messagebox.showerror("Error", "Folder path is required for Review Mode")
                return None
            cmd.extend(["--folder", self.folder_path.get()])
            return cmd # Review mode doesn't use other params typically

        # Common params for pipeline modes
        if mode == "batch":
            if self.topic_var.get():
                cmd.extend(["--topic", self.topic_var.get()])
            
            cmd.extend(["--count", str(self.count_var.get())])
            cmd.extend(["--agent1-mode", self.agent1_mode_var.get()])
            
            start_from = self.start_from_var.get()
            cmd.extend(["--start-from", start_from])

            if start_from in ["agent2", "agent3"]:
                if not self.tsv_file_path.get():
                    messagebox.showerror("Error", f"--tsv-file is required when starting from {start_from}")
                    return None
                cmd.extend(["--tsv-file", self.tsv_file_path.get()])
            
            if self.candidatos_file_path.get():
                cmd.extend(["--candidatos-file", self.candidatos_file_path.get()])
            
            if self.reverse_var.get():
                cmd.append("--reverse")

        return cmd

    def run_process(self):
        cmd = self.build_command()
        if not cmd:
            return

        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.clear_console()
        self.log(f"Executing: {' '.join(cmd)}\n{'-'*50}\n")
        
        def run_thread():
            try:
                # Use subprocess to run the command and capture output
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )

                for line in iter(self.process.stdout.readline, ''):
                    self.root.after(0, self.log, line)

                self.process.stdout.close()
                return_code = self.process.wait()
                
                self.root.after(0, self.log, f"\nProcess finished with exit code {return_code}\n")
            except Exception as e:
                self.root.after(0, self.log, f"\nError starting process: {e}\n")
            finally:
                self.root.after(0, self._process_finished)

        threading.Thread(target=run_thread, daemon=True).start()

    def stop_process(self):
        if self.process:
            self.process.terminate()
            self.log("\n[Stopping process...]\n")

    def _process_finished(self):
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.process = None

if __name__ == "__main__":
    root = tk.Tk()
    # Set icon if available, otherwise skip
    # root.iconbitmap("icon.ico") 
    app = PAESLauncher(root)
    root.mainloop()
