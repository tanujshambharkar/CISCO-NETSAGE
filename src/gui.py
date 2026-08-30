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
import re
import sys
import threading
from tkinter import filedialog, messagebox
import urllib.request
import urllib.error

import customtkinter as ctk

# ── Setup & Paths ────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Local imports
from src.rule_checker import run_all_checks
from src.guide import get_guide_markdown

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PROMPT_PATH = BASE_DIR / "prompts" / "diagnose_prompt.md"
ENV_PATH = BASE_DIR / ".env"

def _load_env_key() -> str:
    """Load API key from .env file if present."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("GEMINI_API_KEY", "")

def _load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        return "You are NetSage AI, an expert Cisco network troubleshooting assistant."
    content = PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*?)```", content, re.DOTALL)
    return match.group(1).strip() if match else content

# ── Main Application ─────────────────────────────
class NetSageApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NetSage AI - Troubleshooting Assistant")
        self.geometry("950x760")
        self.minsize(850, 650)

        # File variable
        self.config_file_path = None
        self.config_content = ""

        self._build_ui()

    def _build_ui(self):
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # API Key row
        self.grid_rowconfigure(2, weight=1) # Main content area

        # --- Header ---
        header = ctk.CTkLabel(self, text="NetSage AI Network Diagnostic Assistant", font=ctk.CTkFont(size=22, weight="bold"))
        header.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5))

        # --- API Key Bar ---
        key_frame = ctk.CTkFrame(self)
        key_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        
        lbl_key = ctk.CTkLabel(key_frame, text="Gemini API Key:", font=ctk.CTkFont(weight="bold"))
        lbl_key.pack(side="left", padx=(12, 8), pady=8)
        
        self.entry_api_key = ctk.CTkEntry(key_frame, placeholder_text="Enter Gemini API Key or leave blank to use .env / environment variable", show="*", width=450)
        self.entry_api_key.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        
        # Pre-fill if exists
        saved_key = _load_env_key()
        if saved_key:
            self.entry_api_key.insert(0, saved_key)

        btn_save_key = ctk.CTkButton(key_frame, text="Save to .env", width=100, command=self._save_api_key)
        btn_save_key.pack(side="right", padx=(8, 12), pady=8)

        # --- Left Panel: Input ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="nsew")
        left_frame.grid_columnconfigure(0, weight=1)
        
        # 1. File Picker
        file_frame = ctk.CTkFrame(left_frame)
        file_frame.pack(fill="x", pady=(0, 12))
        
        self.btn_select_file = ctk.CTkButton(file_frame, text="Select Config File (.txt / .cfg)", command=self.select_file)
        self.btn_select_file.pack(side="left", padx=10, pady=10)
        
        self.lbl_file_name = ctk.CTkLabel(file_frame, text="No file selected", text_color="gray")
        self.lbl_file_name.pack(side="left", padx=10, pady=10)

        # 2. Symptom Input
        lbl_symptom = ctk.CTkLabel(left_frame, text="Network Symptom:", font=ctk.CTkFont(weight="bold"))
        lbl_symptom.pack(anchor="w")
        
        self.txt_symptom = ctk.CTkTextbox(left_frame, height=75)
        self.txt_symptom.pack(fill="x", pady=(4, 12))

        # 3. Show Commands Input
        lbl_show = ctk.CTkLabel(left_frame, text="Show Command Outputs / Logs:", font=ctk.CTkFont(weight="bold"))
        lbl_show.pack(anchor="w")
        
        self.txt_show = ctk.CTkTextbox(left_frame, height=160)
        self.txt_show.pack(fill="both", expand=True, pady=(4, 12))

        # 4. Diagnose Button
        self.btn_diagnose = ctk.CTkButton(left_frame, text="Run AI & Rule Diagnosis", command=self.run_diagnosis_thread, height=42, font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_diagnose.pack(fill="x", pady=(0, 5))

        # --- Right Panel: Output & Guide Tabview ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=2, column=1, padx=(10, 20), pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(right_frame)
        self.tabview.grid(row=0, column=0, padx=12, pady=(10, 12), sticky="nsew")

        self.tabview.add("Diagnostics")
        self.tabview.add("Troubleshooting Guide")

        # Configure tab grids
        self.tabview.tab("Diagnostics").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Diagnostics").grid_rowconfigure(0, weight=1)
        self.tabview.tab("Troubleshooting Guide").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Troubleshooting Guide").grid_rowconfigure(0, weight=1)

        self.txt_output = ctk.CTkTextbox(self.tabview.tab("Diagnostics"), wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_output.grid(row=0, column=0, sticky="nsew")

        self.txt_guide = ctk.CTkTextbox(self.tabview.tab("Troubleshooting Guide"), wrap="word", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.txt_guide.grid(row=0, column=0, sticky="nsew")

        # Write Cisco Networking Troubleshooting Guide content
        guide_text = get_guide_markdown()
        self.txt_guide.insert("1.0", guide_text)
        self.txt_guide.configure(state="disabled")

    def _save_api_key(self):
        key = self.entry_api_key.get().strip()
        if key:
            ENV_PATH.write_text(f"GEMINI_API_KEY={key}\n", encoding="utf-8")
            messagebox.showinfo("NetSage AI", "Gemini API key saved to .env file successfully!")
        else:
            messagebox.showwarning("NetSage AI", "Please enter an API key before saving.")

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Cisco Config File",
            filetypes=[("Config Files", "*.txt *.cfg"), ("All Files", "*.*")]
        )
        if file_path:
            self.config_file_path = file_path
            self.lbl_file_name.configure(text=Path(file_path).name, text_color="white")
            with open(file_path, "r", encoding="utf-8") as f:
                self.config_content = f.read()

    def run_diagnosis_thread(self):
        self.tabview.set("Diagnostics")  # Switch to Diagnostics tab automatically
        self.btn_diagnose.configure(state="disabled", text="Analyzing...")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("end", "========================================================\n")
        self.txt_output.insert("end", " NetSage AI -- Diagnosis in Progress...\n")
        self.txt_output.insert("end", "========================================================\n\n")
        
        threading.Thread(target=self._process_diagnosis, daemon=True).start()

    def _process_diagnosis(self):
        try:
            # 1. Deterministic Rule Checker
            report_text = "[1] DETERMINISTIC RULE CHECKER REPORT\n"
            report_text += "--------------------------------------------------------\n"
            if self.config_content:
                report = run_all_checks(self.config_content, config_file=self.config_file_path)
                report_text += f"Config File   : {Path(self.config_file_path).name}\n"
                report_text += f"Total Findings: {report.total_findings} (Errors: {report.errors}, Warnings: {report.warnings}, Info: {report.info})\n\n"
                if report.findings:
                    for i, finding in enumerate(report.findings, 1):
                        report_text += f"  [{i}] [{finding.severity}] {finding.check_id}\n"
                        report_text += f"      {finding.detail}\n"
                        if finding.affected_lines:
                            report_text += f"      Lines: {finding.affected_lines}\n"
                        report_text += "\n"
                else:
                    report_text += "  [OK] No deterministic rule violations found in configuration.\n\n"
            else:
                report_text += "  [INFO] No config file selected. Skipping static rule checks.\n\n"
            
            self._update_output(report_text)

            # 2. Build AI Prompt
            symptom = self.txt_symptom.get("1.0", "end").strip()
            show_outputs = self.txt_show.get("1.0", "end").strip()

            if not symptom and not show_outputs:
                self._update_output("[2] AI DIAGNOSIS\n--------------------------------------------------------\nSkipped. Enter a symptom or show command output to run AI analysis.\n")
                return

            user_prompt = f"SYMPTOM:\n{symptom}\n\nSHOW COMMAND OUTPUTS:\n{show_outputs}\n\nDiagnose the root cause of this network issue. Respond with a single JSON object matching the NetSage AI schema."
            system_prompt = _load_system_prompt()

            # 3. Get API Key
            api_key = self.entry_api_key.get().strip() or _load_env_key()
            if not api_key:
                self._update_output("[2] AI DIAGNOSIS\n--------------------------------------------------------\n[NOTE] Gemini API Key not provided. Enter key above or set GEMINI_API_KEY.\n")
                return

            self._update_output("[2] AI DIAGNOSIS (Gemini 3.6 Flash)\n--------------------------------------------------------\nCalling Gemini AI for root cause analysis...\n\n")

            # Call Gemini via REST API (Stdlib, 100% reliable)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
            
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "parts": [{"text": user_prompt}]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    text_content = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    try:
                        result_json = json.loads(text_content)
                        formatted_json = json.dumps(result_json, indent=2)
                        self._update_output(formatted_json + "\n")
                    except Exception:
                        self._update_output(text_content + "\n")

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                self._update_output(f"[AI Error] HTTP {e.code}: {e.reason}\nDetails: {err_body}\n")
            except Exception as e:
                self._update_output(f"[AI Error] Request failed: {str(e)}\n")

        except Exception as e:
             self._update_output(f"\n[Unexpected Error] {str(e)}\n")
        finally:
            self.btn_diagnose.configure(state="normal", text="Run AI & Rule Diagnosis")

    def _update_output(self, text):
        self.txt_output.insert("end", text)
        self.txt_output.see("end")


if __name__ == "__main__":
    app = NetSageApp()
    app.mainloop()
