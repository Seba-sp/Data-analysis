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
        self.root.minsize(700, 600)
        self.root.resizable(True, True)
        
        # Variables
        self.mode_var = tk.StringVar(value="batch")
        self.batches_var = tk.IntVar(value=1)
        self.topic_var = tk.StringVar()
        self.count_var = tk.IntVar(value=30)
        self.agent1_mode_var = tk.StringVar(value="agent")
        self.start_from_var = tk.StringVar(value="agent1")
        self.tsv_file_path = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.txt_folder_path = tk.StringVar()
        self.docx_folder_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.txt_file_path = tk.StringVar()
        self.docx_file_path = tk.StringVar()
        self.output_file_folder_path = tk.StringVar()
        self.reverse_var = tk.BooleanVar(value=False)
        
        self.process = None

        self._create_ui()

    def _create_ui(self):
        # Scrollable container
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_frame = ttk.Frame(canvas, padding="10")
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        main_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Section 1: Primary Mode Selection ---
        mode_frame = ttk.LabelFrame(main_frame, text="Select Primary Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(mode_frame, text="Pipeline (Agents 1-3)", variable=self.mode_var, value="batch", command=self._update_state).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Standalone Review (Agent 4)", variable=self.mode_var, value="review", command=self._update_state).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Debug TXT + DOCX Batch", variable=self.mode_var, value="debug", command=self._update_state).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Debug TXT + DOCX Single", variable=self.mode_var, value="debug_single", command=self._update_state).pack(anchor=tk.W)

        # --- Section 2: Pipeline Configuration ---
        self.pipeline_frame = ttk.LabelFrame(main_frame, text="Pipeline Configuration", padding="10")
        self.pipeline_frame.pack(fill=tk.X, pady=5)

        # Start From
        ttk.Label(self.pipeline_frame, text="Start From:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        start_options = ["agent1", "agent2", "agent3"]
        self.start_combo = ttk.Combobox(self.pipeline_frame, textvariable=self.start_from_var, values=start_options, state="readonly", width=15)
        self.start_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.start_combo.bind("<<ComboboxSelected>>", self._update_state)

        self.reverse_check = ttk.Checkbutton(self.pipeline_frame, text="Reverse Order", variable=self.reverse_var)
        self.reverse_check.grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Separator(self.pipeline_frame, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky='ew', pady=10)

        # Agent 1 Config Section
        self.agent1_frame = ttk.LabelFrame(self.pipeline_frame, text="Agent 1 Settings", padding="5")
        self.agent1_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(self.agent1_frame, text="Batches:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.batches_entry = ttk.Entry(self.agent1_frame, textvariable=self.batches_var, width=10)
        self.batches_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.agent1_frame, text="Count:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.count_entry = ttk.Entry(self.agent1_frame, textvariable=self.count_var, width=10)
        self.count_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(self.agent1_frame, text="Topic:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.topic_entry = ttk.Entry(self.agent1_frame, textvariable=self.topic_var, width=30)
        self.topic_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5)

        ttk.Label(self.agent1_frame, text="Mode:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.agent1_combo = ttk.Combobox(self.agent1_frame, textvariable=self.agent1_mode_var, values=["agent", "model"], state="readonly", width=10)
        self.agent1_combo.grid(row=2, column=1, sticky=tk.W, padx=5)

        # Agent 2/3 Config Section
        self.files_frame = ttk.LabelFrame(self.pipeline_frame, text="Agent 2/3 Settings (File Inputs)", padding="5")
        self.files_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=5, pady=5)

        ttk.Label(self.files_frame, text="TSV/CSV File:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.tsv_entry = ttk.Entry(self.files_frame, textvariable=self.tsv_file_path, width=40)
        self.tsv_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.tsv_btn = ttk.Button(self.files_frame, text="Browse...", command=lambda: self._browse_file(self.tsv_file_path))
        self.tsv_btn.grid(row=0, column=2, padx=5)

        # --- Section 3: Standalone Review Configuration ---
        self.review_frame = ttk.LabelFrame(main_frame, text="Standalone Review Configuration", padding="10")
        self.review_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.review_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.folder_entry = ttk.Entry(self.review_frame, textvariable=self.folder_path, width=50)
        self.folder_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.folder_btn = ttk.Button(self.review_frame, text="Browse...", command=lambda: self._browse_folder(self.folder_path))
        self.folder_btn.grid(row=0, column=2, padx=5)

        # --- Section 4: Debug TXT + DOCX Configuration (Side-by-Side) ---
        self.debug_container = ttk.Frame(main_frame, padding="0")
        self.debug_container.pack(fill=tk.X, pady=5)

        self.debug_frame = ttk.LabelFrame(self.debug_container, text="Debug TXT + DOCX Batch", padding="10")
        self.debug_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.debug_container.columnconfigure(0, weight=1)

        ttk.Label(self.debug_frame, text="TXT Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.txt_folder_entry = ttk.Entry(self.debug_frame, textvariable=self.txt_folder_path, width=50)
        self.txt_folder_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.txt_folder_btn = ttk.Button(self.debug_frame, text="Browse...", command=lambda: self._browse_folder(self.txt_folder_path))
        self.txt_folder_btn.grid(row=0, column=2, padx=5)

        ttk.Label(self.debug_frame, text="DOCX Folder:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.docx_folder_entry = ttk.Entry(self.debug_frame, textvariable=self.docx_folder_path, width=50)
        self.docx_folder_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.docx_folder_btn = ttk.Button(self.debug_frame, text="Browse...", command=lambda: self._browse_folder(self.docx_folder_path))
        self.docx_folder_btn.grid(row=1, column=2, padx=5)

        ttk.Label(self.debug_frame, text="Output Folder (optional):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_folder_entry = ttk.Entry(self.debug_frame, textvariable=self.output_folder_path, width=50)
        self.output_folder_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.output_folder_btn = ttk.Button(self.debug_frame, text="Browse...", command=lambda: self._browse_folder(self.output_folder_path))
        self.output_folder_btn.grid(row=2, column=2, padx=5)

        self.debug_single_frame = ttk.LabelFrame(self.debug_container, text="Debug TXT + DOCX Single", padding="10")
        self.debug_single_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.debug_container.columnconfigure(1, weight=1)

        ttk.Label(self.debug_single_frame, text="TXT File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.txt_file_entry = ttk.Entry(self.debug_single_frame, textvariable=self.txt_file_path, width=50)
        self.txt_file_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.txt_file_btn = ttk.Button(self.debug_single_frame, text="Browse...", command=lambda: self._browse_file(self.txt_file_path))
        self.txt_file_btn.grid(row=0, column=2, padx=5)

        ttk.Label(self.debug_single_frame, text="DOCX File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.docx_file_entry = ttk.Entry(self.debug_single_frame, textvariable=self.docx_file_path, width=50)
        self.docx_file_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.docx_file_btn = ttk.Button(self.debug_single_frame, text="Browse...", command=lambda: self._browse_file(self.docx_file_path))
        self.docx_file_btn.grid(row=1, column=2, padx=5)

        ttk.Label(self.debug_single_frame, text="Output Folder (optional):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_file_folder_entry = ttk.Entry(self.debug_single_frame, textvariable=self.output_file_folder_path, width=50)
        self.output_file_folder_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.output_file_folder_btn = ttk.Button(self.debug_single_frame, text="Browse...", command=lambda: self._browse_folder(self.output_file_folder_path))
        self.output_file_folder_btn.grid(row=2, column=2, padx=5)

        # --- Section 5: Execution & Output ---
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
        start_from = self.start_from_var.get()
        
        # Helper to enable/disable all children of a frame
        def set_frame_state(frame, state):
            for child in frame.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton)):
                    child.configure(state=state)

        if mode == "batch":
            # Enable Pipeline Section
            set_frame_state(self.pipeline_frame, tk.NORMAL)
            
            # Start From Combo and Reverse are always active in Pipeline mode
            self.start_combo.configure(state="readonly")
            self.reverse_check.configure(state=tk.NORMAL)
            
            # Toggle sub-sections based on start_from
            if start_from == "agent1":
                set_frame_state(self.agent1_frame, tk.NORMAL)
                self.agent1_combo.configure(state="readonly") # Combobox needs readonly, not normal
                set_frame_state(self.files_frame, tk.DISABLED)
            else:
                set_frame_state(self.agent1_frame, tk.DISABLED)
                set_frame_state(self.files_frame, tk.NORMAL)

            # Disable Standalone Section
            set_frame_state(self.review_frame, tk.DISABLED)
            set_frame_state(self.debug_frame, tk.DISABLED)
            set_frame_state(self.debug_single_frame, tk.DISABLED)
            
        elif mode == "review":
            # Disable Pipeline Section
            set_frame_state(self.pipeline_frame, tk.DISABLED)
            set_frame_state(self.agent1_frame, tk.DISABLED)
            set_frame_state(self.files_frame, tk.DISABLED)
            
            # Enable Standalone Section
            set_frame_state(self.review_frame, tk.NORMAL)
            set_frame_state(self.debug_frame, tk.DISABLED)
            set_frame_state(self.debug_single_frame, tk.DISABLED)

        elif mode == "debug":
            # Disable Pipeline and Review Sections
            set_frame_state(self.pipeline_frame, tk.DISABLED)
            set_frame_state(self.agent1_frame, tk.DISABLED)
            set_frame_state(self.files_frame, tk.DISABLED)
            set_frame_state(self.review_frame, tk.DISABLED)

            # Enable Debug Section
            set_frame_state(self.debug_frame, tk.NORMAL)
            set_frame_state(self.debug_single_frame, tk.DISABLED)

        elif mode == "debug_single":
            # Disable Pipeline and Review Sections
            set_frame_state(self.pipeline_frame, tk.DISABLED)
            set_frame_state(self.agent1_frame, tk.DISABLED)
            set_frame_state(self.files_frame, tk.DISABLED)
            set_frame_state(self.review_frame, tk.DISABLED)
            set_frame_state(self.debug_frame, tk.DISABLED)

            # Enable Single Debug Section
            set_frame_state(self.debug_single_frame, tk.NORMAL)

    def _set_widgets_state(self, widgets, state):
        pass # Not used anymore, replaced by set_frame_state logic inside _update_state

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
        start_from = self.start_from_var.get()

        if mode == "batch":
            # Only add agent1 specific params if starting from agent1
            if start_from == "agent1":
                cmd.extend(["--batches", str(self.batches_var.get())])
                if self.topic_var.get():
                    cmd.extend(["--topic", self.topic_var.get()])
                cmd.extend(["--count", str(self.count_var.get())])
                cmd.extend(["--agent1-mode", self.agent1_mode_var.get()])
            
            # Common params
            cmd.extend(["--start-from", start_from])

            if start_from in ["agent2", "agent3"]:
                if not self.tsv_file_path.get():
                    messagebox.showerror("Error", f"--tsv-file is required when starting from {start_from}")
                    return None
                cmd.extend(["--tsv-file", self.tsv_file_path.get()])
            
            if self.reverse_var.get():
                cmd.append("--reverse")

        elif mode == "review":
            cmd.append("--review-standalone")
            if not self.folder_path.get():
                messagebox.showerror("Error", "Folder path is required for Review Mode")
                return None
            cmd.extend(["--folder", self.folder_path.get()])
        elif mode == "debug":
            cmd.append("--batch-debug")
            if not self.txt_folder_path.get() or not self.docx_folder_path.get():
                messagebox.showerror("Error", "TXT folder and DOCX folder are required for Debug Mode")
                return None
            cmd.extend(["--txt-folder", self.txt_folder_path.get()])
            cmd.extend(["--docx-folder", self.docx_folder_path.get()])
            if self.output_folder_path.get():
                cmd.extend(["--output-folder", self.output_folder_path.get()])
        elif mode == "debug_single":
            cmd.append("--single-debug")
            if not self.txt_file_path.get() or not self.docx_file_path.get():
                messagebox.showerror("Error", "TXT file and DOCX file are required for Single Debug Mode")
                return None
            cmd.extend(["--txt-file", self.txt_file_path.get()])
            cmd.extend(["--docx-file", self.docx_file_path.get()])
            if self.output_file_folder_path.get():
                cmd.extend(["--output-folder", self.output_file_folder_path.get()])

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
