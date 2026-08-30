"""
NetSage AI — Desktop GUI
================================
A native desktop application built with CustomTkinter.
Provides a modern dark-mode interface for network engineers
to load configurations and generate AI diagnoses.
"""

import json
import os
from pathlib import Path
import sys
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

# ── Setup & Paths ────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Local imports
from src.rule_checker import run_all_checks

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PROMPT_PATH = BASE_DIR / "prompts" / "diagnose_prompt.md"

def _load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        return ""
    content = PROMPT_PATH.read_text(encoding="utf-8")
    import re
    match = re.search(r"```text\n(.*?)```", content, re.DOTALL)
    return match.group(1).strip() if match else ""

# ── Main Application ─────────────────────────────
class NetSageApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NetSage AI - Troubleshooting Assistant")
        self.geometry("900x700")
        self.minsize(800, 600)

        # File variable
        self.config_file_path = None
        self.config_content = ""

        self._build_ui()

    def _build_ui(self):
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Main content area

        # --- Header ---
        header = ctk.CTkLabel(self, text="NetSage AI Diagnosis", font=ctk.CTkFont(size=24, weight="bold"))
        header.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))

        # --- Left Panel: Input ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        left_frame.grid_columnconfigure(0, weight=1)
        
        # 1. File Picker
        file_frame = ctk.CTkFrame(left_frame)
        file_frame.pack(fill="x", pady=(0, 15))
        
        self.btn_select_file = ctk.CTkButton(file_frame, text="Select Config File (.txt)", command=self.select_file)
        self.btn_select_file.pack(side="left", padx=10, pady=10)
        
        self.lbl_file_name = ctk.CTkLabel(file_frame, text="No file selected", text_color="gray")
        self.lbl_file_name.pack(side="left", padx=10, pady=10)

        # 2. Symptom Input
        lbl_symptom = ctk.CTkLabel(left_frame, text="Symptom:", font=ctk.CTkFont(weight="bold"))
        lbl_symptom.pack(anchor="w")
        
        self.txt_symptom = ctk.CTkTextbox(left_frame, height=80)
        self.txt_symptom.pack(fill="x", pady=(5, 15))

        # 3. Show Commands Input
        lbl_show = ctk.CTkLabel(left_frame, text="Show Command Outputs:", font=ctk.CTkFont(weight="bold"))
        lbl_show.pack(anchor="w")
        
        self.txt_show = ctk.CTkTextbox(left_frame, height=150)
        self.txt_show.pack(fill="both", expand=True, pady=(5, 15))

        # 4. Diagnose Button
        self.btn_diagnose = ctk.CTkButton(left_frame, text="Run Diagnosis", command=self.run_diagnosis_thread, height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_diagnose.pack(fill="x", pady=(0, 10))

        # --- Right Panel: Output ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        lbl_output = ctk.CTkLabel(right_frame, text="Diagnosis Results", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_output.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.txt_output = ctk.CTkTextbox(right_frame, wrap="word", font=ctk.CTkFont(family="Consolas", size=13))
        self.txt_output.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Cisco Config File",
            filetypes=[("Text Files", "*.txt"), ("Config Files", "*.cfg"), ("All Files", "*.*")]
        )
        if file_path:
            self.config_file_path = file_path
            self.lbl_file_name.configure(text=Path(file_path).name, text_color="white")
            with open(file_path, "r", encoding="utf-8") as f:
                self.config_content = f.read()

    def run_diagnosis_thread(self):
        # Disable button to prevent multiple clicks
        self.btn_diagnose.configure(state="disabled", text="Analyzing...")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("end", "Running deterministic rule checker...\n")
        
        # Run in a background thread to keep GUI responsive
        threading.Thread(target=self._process_diagnosis, daemon=True).start()

    def _process_diagnosis(self):
        try:
            # 1. Rule Checker
            report_text = "=== Rule Checker Findings ===\n"
            if self.config_content:
                report = run_all_checks(self.config_content, config_file=self.config_file_path)
                report_text += f"Total Findings: {report.total_findings}\n\n"
                for finding in report.findings:
                    report_text += f"[{finding.severity}] {finding.check_id}: {finding.detail}\n"
            else:
                report_text += "No config file selected. Skipped.\n"
            
            self._update_output(report_text + "\n")

            # 2. Build AI Prompt
            symptom = self.txt_symptom.get("1.0", "end").strip()
            show_outputs = self.txt_show.get("1.0", "end").strip()

            if not symptom or not show_outputs:
                self._update_output("=== AI Diagnosis ===\nSkipped. Please provide both a symptom and show command outputs.")
                return

            user_prompt = f"SYMPTOM:\n{symptom}\n\nSHOW COMMAND OUTPUTS:\n{show_outputs}\n\nDiagnose the root cause of this network issue. Respond with a single JSON object matching the NetSage AI schema."
            system_prompt = _load_system_prompt()

            # 3. Call Gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                self._update_output("=== AI Diagnosis ===\nSkipped. GEMINI_API_KEY environment variable not set.")
                return

            self._update_output("Calling Gemini AI for analysis...\n\n")
            
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{system_prompt}\n\n{user_prompt}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                
                try:
                    # Pretty print JSON
                    result_json = json.loads(response.text)
                    formatted_json = json.dumps(result_json, indent=2)
                    self._update_output("=== AI Diagnosis ===\n" + formatted_json)
                except Exception:
                    self._update_output("=== AI Diagnosis ===\n" + response.text)

            except Exception as e:
                self._update_output(f"=== AI Error ===\nFailed to call Gemini: {str(e)}")

        except Exception as e:
             self._update_output(f"\nAn unexpected error occurred: {str(e)}")
        finally:
            # Re-enable button
            self.btn_diagnose.configure(state="normal", text="Run Diagnosis")

    def _update_output(self, text):
        # Update text box safely from thread
        self.txt_output.insert("end", text)
        self.txt_output.see("end")


if __name__ == "__main__":
    app = NetSageApp()
    app.mainloop()
