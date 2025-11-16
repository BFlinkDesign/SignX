#!/usr/bin/env python3
"""
Eagle Sign Analyzer GUI - Drag & Drop Interface
"""

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import threading
import os

class EagleAnalyzerGUI:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("Eagle Sign Analyzer v9.0")
        self.root.geometry("800x600")
        
        # Header
        header = tk.Label(self.root, text="🦅 EAGLE SIGN ANALYZER", 
                         font=("Arial", 16, "bold"))
        header.pack(pady=10)
        
        # Drop zone
        self.drop_frame = tk.Frame(self.root, bg="lightgray", 
                                  relief=tk.RAISED, bd=2)
        self.drop_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.drop_label = tk.Label(self.drop_frame, 
                                  text="Drag PDF here\nor click to browse",
                                  font=("Arial", 14), bg="lightgray")
        self.drop_label.pack(expand=True)
        
        # Configure drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.drop_file)
        self.drop_frame.bind("<Button-1>", self.browse_file)
        
        # Output text
        self.output_text = scrolledtext.ScrolledText(self.root, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        self.analyze_btn = tk.Button(button_frame, text="Analyze", 
                                    command=self.analyze, state=tk.DISABLED,
                                    bg="green", fg="white", font=("Arial", 12))
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Clear", 
                 command=self.clear).pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status = tk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.current_file = None
        
    def drop_file(self, event):
        """Handle dropped file"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0].strip('{}')
            if file_path.lower().endswith('.pdf'):
                self.load_file(file_path)
            else:
                messagebox.showerror("Error", "Please drop a PDF file")
    
    def browse_file(self, event=None):
        """Browse for file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load selected file"""
        self.current_file = file_path
        filename = os.path.basename(file_path)
        self.drop_label.config(text=f"Loaded: {filename}")
        self.analyze_btn.config(state=tk.NORMAL)
        self.status.config(text=f"Ready to analyze: {filename}")
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"File: {file_path}\n")
        self.output_text.insert(tk.END, f"Size: {os.path.getsize(file_path)/1024/1024:.1f} MB\n\n")
        self.output_text.insert(tk.END, "Click 'Analyze' to start...\n")
    
    def analyze(self):
        """Run analysis in background thread"""
        if not self.current_file:
            return
            
        self.analyze_btn.config(state=tk.DISABLED)
        self.status.config(text="Analyzing...")
        self.output_text.insert(tk.END, "\n" + "="*60 + "\n")
        self.output_text.insert(tk.END, "Starting analysis...\n")
        
        # Run in thread to prevent GUI freeze
        thread = threading.Thread(target=self.run_analysis)
        thread.start()
    
    def run_analysis(self):
        """Execute the analyzer"""
        try:
            # Run the analyzer
            cmd = ["python", "benchmark-v9-production.py", self.current_file]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            
            # Stream output
            for line in process.stdout:
                self.root.after(0, self.append_output, line)
            
            process.wait()
            
            if process.returncode == 0:
                self.root.after(0, self.analysis_complete)
            else:
                error = process.stderr.read()
                self.root.after(0, self.analysis_error, error)
                
        except Exception as e:
            self.root.after(0, self.analysis_error, str(e))
    
    def append_output(self, text):
        """Append text to output"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
    
    def analysis_complete(self):
        """Analysis completed"""
        self.status.config(text="Analysis complete!")
        self.analyze_btn.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, "\n✅ Analysis complete! Check output files.\n")
        messagebox.showinfo("Complete", "Analysis complete!\nCheck output files in the same directory.")
    
    def analysis_error(self, error):
        """Handle analysis error"""
        self.status.config(text="Error occurred")
        self.analyze_btn.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"\n❌ Error: {error}\n")
        messagebox.showerror("Error", f"Analysis failed:\n{error}")
    
    def clear(self):
        """Clear everything"""
        self.current_file = None
        self.drop_label.config(text="Drag PDF here\nor click to browse")
        self.analyze_btn.config(state=tk.DISABLED)
        self.output_text.delete(1.0, tk.END)
        self.status.config(text="Ready")
    
    def run(self):
        """Start GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    # Check if analyzer exists
    if not os.path.exists("benchmark-v9-production.py"):
        messagebox.showerror("Error", "benchmark-v9-production.py not found!\nPlease ensure it's in the same directory.")
        exit(1)
    
    # Install tkinterdnd2 if needed
    try:
        import tkinterdnd2
    except ImportError:
        print("Installing required GUI library...")
        subprocess.run(["pip", "install", "tkinterdnd2"])
        
    app = EagleAnalyzerGUI()
    app.run()