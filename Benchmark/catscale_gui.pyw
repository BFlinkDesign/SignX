import sys
import os
from pathlib import Path
# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import json
from datetime import datetime
import queue
import re


class CATScaleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAT Scale Benchmark System v7.3")
        self.root.geometry("1000x700")

        # Set icon if available
        icon_path = Path(__file__).parent / 'icon.ico'
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        # Variables
        self.processing = False
        self.files_to_process = []
        self.proc = None
        self.output_queue = queue.Queue()
        self.reader_thread = None
        self.progress_count = 0
        self.total_files = 0

        # Create UI
        self.create_widgets()

        # Load settings
        self.load_settings()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Header
        header_frame = ttk.LabelFrame(main_frame, text="CAT Scale Benchmark System v7.3", padding="10")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(header_frame, text="Professional Cost Analysis Tool - Bulletproof Edition",
                 font=('Arial', 10, 'italic')).pack()

        # Control Panel
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # File selection
        ttk.Button(control_frame, text="Select PDFs",
                  command=self.select_files).grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="Select Folder",
                  command=self.select_folder).grid(row=0, column=1, padx=5)

        # Options
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Include Subfolders",
                       variable=self.recursive_var).grid(row=0, column=2, padx=20)

        self.docpack_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Generate DocPack",
                       variable=self.docpack_var).grid(row=0, column=3, padx=5)

        # Process button
        self.process_btn = ttk.Button(control_frame, text="Process Files",
                                     command=self.process_files, state='disabled')
        self.process_btn.grid(row=0, column=4, padx=20)

        # Status
        self.status_label = ttk.Label(control_frame, text="No files selected")
        self.status_label.grid(row=1, column=0, columnspan=5, pady=5)

        # Progress
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Output
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(output_frame,
                                                     height=20, width=100,
                                                     font=('Courier', 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="Open Reports Folder",
                  command=self.open_reports).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Settings",
                  command=self.open_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Output",
                  command=lambda: self.output_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="View Logs",
                  command=self.open_logs).pack(side=tk.LEFT, padx=5)

        # Cancel button
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_processing, state='disabled')
        self.cancel_btn.pack(side=tk.RIGHT, padx=5)

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if files:
            self.files_to_process = list(files)
            self.update_status()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing PDFs")
        if folder:
            path = Path(folder)
            if self.recursive_var.get():
                self.files_to_process = list(path.rglob("*.pdf"))
            else:
                self.files_to_process = list(path.glob("*.pdf"))
            self.update_status()

    def update_status(self):
        count = len(self.files_to_process)
        if count > 0:
            self.status_label.config(text=f"{count} PDF file(s) selected")
            self.process_btn.config(state='normal')
        else:
            self.status_label.config(text="No files selected")
            self.process_btn.config(state='disabled')

    def process_files(self):
        if not self.files_to_process:
            messagebox.showwarning("No Files", "Please select files to process")
            return
        
        if self.processing:
            messagebox.showwarning("Processing", "Already processing files")
            return
        
        self.processing = True
        self.process_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.progress_count = 0
        self.total_files = len(self.files_to_process)
        if self.total_files > 0:
            self.progress.config(mode='determinate', maximum=self.total_files, value=0)
        self.progress.config(mode='indeterminate')
        self.progress.start()
        
        # Run in thread
        thread = threading.Thread(target=self.run_processing, daemon=True)
        thread.start()
        # Start UI pump for output
        self.root.after(100, self.poll_output_queue)

    def run_processing(self):
        try:
            # Build command
            script_dir = Path(__file__).parent
            python_exe = script_dir / "venv" / "Scripts" / "python.exe"
            if not python_exe.exists():
                python_exe = Path(sys.executable)
            
            parser_script = script_dir / "catscale_delta_parser.py"
            
            # Run parser
            cmd = [str(python_exe), str(parser_script)]
            
            if self.docpack_var.get():
                cmd.append("--docpack")
            
            cmd.extend([str(f) for f in self.files_to_process])
            
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Separate thread to read stdout non-blocking
            def reader(p: subprocess.Popen, q: queue.Queue):
                try:
                    if p.stdout is None:
                        return
                    for line in iter(p.stdout.readline, ''):
                        q.put(line)
                finally:
                    try:
                        if p.stdout:
                            p.stdout.close()
                    except Exception:
                        pass

            self.reader_thread = threading.Thread(target=reader, args=(self.proc, self.output_queue), daemon=True)
            self.reader_thread.start()

            # Wait for process in this background thread
            self.proc.wait()

            # Signal completion to UI via queue
            self.output_queue.put(None)
                
        except Exception as e:
            self.output_queue.put(f"[GUI ERROR] {e}\n")
            self.output_queue.put(None)
        finally:
            pass

    def poll_output_queue(self):
        consumed_any = False
        try:
            while True:
                item = self.output_queue.get_nowait()
                consumed_any = True
                if item is None:
                    # process finished
                    rc = None
                    try:
                        if self.proc is not None:
                            rc = self.proc.returncode
                    except Exception:
                        pass
                    # finalize UI
                    self.processing = False
                    self.process_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    self.progress.stop()
                    self.progress.config(mode='determinate')
                    if rc == 0:
                        self.show_success()
                    elif rc is not None:
                        self.show_error("Processing failed. Check output for details.")
                    self.proc = None
                    break
                else:
                    line = item
                    # Append to output safely
                    self.output_text.insert(tk.END, line)
                    self.output_text.see(tk.END)
                    # Progress heuristic: count lines starting with a checkmark
                    if line.lstrip().startswith("✓ "):
                        self.progress_count += 1
                        if self.total_files > 0:
                            self.progress.config(mode='determinate', maximum=self.total_files, value=self.progress_count)
        except queue.Empty:
            pass
        finally:
            if self.processing:
                # keep polling
                self.root.after(100, self.poll_output_queue)

    def show_success(self):
        messagebox.showinfo(
            "Success",
            "Processing complete!\n\nReports have been generated in the reports folder."
        )

    def show_error(self, message):
        messagebox.showerror("Error", message)

    def open_reports(self):
        reports_dir = Path(__file__).parent / "reports"
        if reports_dir.exists():
            os.startfile(str(reports_dir))

    def open_settings(self):
        settings_file = Path(__file__).parent / "config" / "settings.json"
        if settings_file.exists():
            os.startfile(str(settings_file))

    def open_logs(self):
        logs_dir = Path(__file__).parent / "logs"
        if logs_dir.exists():
            os.startfile(str(logs_dir))

    def cancel_processing(self):
        if not self.processing:
            return
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                self.output_queue.put("[GUI] Cancellation requested. Terminating process...\n")
        except Exception as e:
            self.output_queue.put(f"[GUI ERROR] Cancel failed: {e}\n")

    def load_settings(self):
        try:
            settings_file = Path(__file__).parent / "config" / "settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.docpack_var.set(settings.get('docpack', True))
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = CATScaleGUI(root)
    root.mainloop()


