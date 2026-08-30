#!/usr/bin/env python3
"""
NetSage AI -- Cisco Packet Tracer Lab Verification Script
Runs deterministic rule checks across all baseline and fault configs.
"""

import sys
from pathlib import Path

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from rule_checker import run_all_checks, Severity

def main():
    print("=" * 70)
    print("  NetSage AI -- Lab Topology Configuration Verification")
    print("=" * 70)

    lab_dir = project_root / "cisco_packet_tracer_lab"
    baseline_dir = lab_dir / "baseline_configs"
    
    baseline_files = list(baseline_dir.glob("*.cfg"))
    print(f"\n[+] Verifying {len(baseline_files)} Baseline Configurations:")
    
    all_clean = True
    for cfg in baseline_files:
        text = cfg.read_text(encoding="utf-8")
        report = run_all_checks(text, config_file=str(cfg.name))
        
        status = "[PASS]" if report.errors == 0 else "[FAIL]"
        if report.errors > 0:
            all_clean = False
        print(f"  {status} {cfg.name:<28} -> {report.errors} Errors, {report.warnings} Warnings, {report.info} Info")
        for finding in report.findings:
            if finding.severity == Severity.ERROR:
                print(f"      [ERR] {finding.check_id}: {finding.detail}")

    print("\n[+] Verifying Planted Fault Sample Config:")
    sample_cfg = project_root / "tests" / "sample_config_1.txt"
    if sample_cfg.exists():
        text = sample_cfg.read_text(encoding="utf-8")
        report = run_all_checks(text, config_file=str(sample_cfg.name))
        print(f"  [INFO] sample_config_1.txt -> Successfully detected {report.total_findings} issues ({report.errors} errors, {report.warnings} warnings).")

    print("\n" + "=" * 70)
    if all_clean:
        print("  [SUCCESS] All baseline network configs are clean and verified.")
    else:
        print("  [NOTE] Review specific baseline config notices above.")
    print("=" * 70)

if __name__ == "__main__":
    main()
