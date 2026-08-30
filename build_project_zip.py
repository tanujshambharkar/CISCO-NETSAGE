#!/usr/bin/env python3
"""
NetSage AI -- Package Builder Script
Bundles the complete project report, source code, data, prompts, logs,
and Cisco Packet Tracer lab configs into a standalone ZIP file.
"""

import os
import zipfile
from pathlib import Path

def create_project_zip():
    root = Path(__file__).resolve().parent
    zip_name = "Cisco_NetSage_AI_Complete_Project_Package.zip"
    zip_path = root / zip_name

    # Files and folders to include
    include_paths = [
        "README.md",
        "PROJECT_REPORT.md",
        "PROJECT_REPORT.html",
        "requirements.txt",
        "data",
        "prompts",
        "src",
        "logs",
        "cisco_packet_tracer_lab",
        "tests",
    ]

    print(f"[+] Creating package: {zip_name}...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item_name in include_paths:
            item_path = root / item_name
            if item_path.is_file():
                arcname = item_path.relative_to(root)
                zf.write(item_path, arcname)
                print(f"  [FILE] Added {arcname}")
            elif item_path.is_dir():
                for file_path in item_path.rglob("*"):
                    if file_path.is_file() and not file_path.name.endswith(".pyc") and "__pycache__" not in str(file_path):
                        arcname = file_path.relative_to(root)
                        zf.write(file_path, arcname)
                        print(f"  [FILE] Added {arcname}")

    print(f"\n[SUCCESS] Package successfully created: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    create_project_zip()
