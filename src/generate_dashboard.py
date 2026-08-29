"""
NetSage AI — Dashboard Generator
==================================
Generates a summary dashboard from the cases dataset and responsible AI log,
reporting issue type distribution, severity breakdown, and AI vs. human agreement rate.

Usage:
    python src/generate_dashboard.py --cases data/cases.csv --log logs/responsible_ai_log.md [--output dashboard_report.json]

Outputs:
    - Human-readable summary to stdout
    - JSON report file (optional)
    - HTML dashboard file (optional, --html flag)

Python 3.10+ | Standard Library only
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class CaseStats:
    """Statistics derived from cases.csv."""
    total_cases: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_osi_layer: dict[str, int] = field(default_factory=dict)
    by_difficulty: dict[str, int] = field(default_factory=dict)
    concept_tags: list[str] = field(default_factory=list)


@dataclass
class AILogEntry:
    """A single entry from the responsible AI log."""
    log_id: str
    case_ref: str
    ai_diagnosis: str
    ai_confidence: str
    actual_cause: str
    error_type: str
    correction: str
    lesson: str


@dataclass
class AgreementStats:
    """AI vs. Human agreement statistics."""
    total_reviewed: int = 0
    agreed: int = 0
    disagreed: int = 0
    agreement_rate: float = 0.0
    by_error_type: dict[str, int] = field(default_factory=dict)
    by_confidence: dict[str, int] = field(default_factory=dict)


@dataclass
class DashboardReport:
    """Complete dashboard report."""
    generated_at: str
    case_stats: CaseStats
    agreement_stats: AgreementStats

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "case_stats": {
                "total_cases": self.case_stats.total_cases,
                "by_category": self.case_stats.by_category,
                "by_osi_layer": self.case_stats.by_osi_layer,
                "by_difficulty": self.case_stats.by_difficulty,
                "concept_tags": self.case_stats.concept_tags,
            },
            "agreement_stats": {
                "total_reviewed": self.agreement_stats.total_reviewed,
                "agreed": self.agreement_stats.agreed,
                "disagreed": self.agreement_stats.disagreed,
                "agreement_rate_pct": round(
                    self.agreement_stats.agreement_rate * 100, 1
                ),
                "by_error_type": self.agreement_stats.by_error_type,
                "by_confidence_at_error": self.agreement_stats.by_confidence,
            },
        }


# ──────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────

def parse_cases(cases_path: Path) -> CaseStats:
    """Parse cases.csv and compute statistics."""
    stats = CaseStats()

    with cases_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    stats.total_cases = len(rows)

    cat_counter: Counter[str] = Counter()
    layer_counter: Counter[str] = Counter()
    diff_counter: Counter[str] = Counter()
    tags: list[str] = []

    for row in rows:
        cat_counter[row.get("category", "UNKNOWN")] += 1
        layer_counter[f"Layer {row.get('osi_layer', '?')}"] += 1
        diff_counter[row.get("difficulty", "Unknown")] += 1
        tag = row.get("concept_tag", "")
        if tag:
            tags.append(tag)

    stats.by_category = dict(sorted(cat_counter.items()))
    stats.by_osi_layer = dict(sorted(layer_counter.items()))
    stats.by_difficulty = dict(sorted(diff_counter.items()))
    stats.concept_tags = sorted(set(tags))

    return stats


def parse_ai_log(log_path: Path) -> list[AILogEntry]:
    """
    Parse the responsible_ai_log.md file to extract correction entries.

    Expected format in markdown: table rows with | delimiters, or
    structured sections with ## headers.
    """
    entries: list[AILogEntry] = []

    if not log_path.exists():
        return entries

    content = log_path.read_text(encoding="utf-8")

    # Pattern: Look for structured log entries
    # Match sections like "### LOG-001" or "## Entry 1"
    entry_pattern = re.compile(
        r"###?\s+(?:LOG-|Entry\s*)(\d+).*?"
        r"\|\s*Case Reference\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*AI Diagnosis\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*AI Confidence\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*Actual Root Cause\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*Error Type\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*Correction Applied\s*\|\s*(.+?)\s*\|.*?"
        r"\|\s*Lesson Learned\s*\|\s*(.+?)\s*\|",
        re.DOTALL,
    )

    for match in entry_pattern.finditer(content):
        entries.append(AILogEntry(
            log_id=f"LOG-{match.group(1).zfill(3)}",
            case_ref=match.group(2).strip(),
            ai_diagnosis=match.group(3).strip(),
            ai_confidence=match.group(4).strip(),
            actual_cause=match.group(5).strip(),
            error_type=match.group(6).strip(),
            correction=match.group(7).strip(),
            lesson=match.group(8).strip(),
        ))

    # Fallback: try simpler pipe-separated table rows
    if not entries:
        table_pattern = re.compile(
            r"\|\s*(LOG-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*"
            r"(HIGH|MEDIUM|LOW)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*"
            r"(.+?)\s*\|\s*(.+?)\s*\|"
        )
        for match in table_pattern.finditer(content):
            entries.append(AILogEntry(
                log_id=match.group(1),
                case_ref=match.group(2).strip(),
                ai_diagnosis=match.group(3).strip(),
                ai_confidence=match.group(4).strip(),
                actual_cause=match.group(5).strip(),
                error_type=match.group(6).strip(),
                correction=match.group(7).strip(),
                lesson=match.group(8).strip(),
            ))

    return entries


def compute_agreement(
    case_stats: CaseStats, log_entries: list[AILogEntry]
) -> AgreementStats:
    """Compute AI vs. human agreement statistics."""
    stats = AgreementStats()

    stats.total_reviewed = case_stats.total_cases
    stats.disagreed = len(log_entries)
    stats.agreed = max(0, stats.total_reviewed - stats.disagreed)

    if stats.total_reviewed > 0:
        stats.agreement_rate = stats.agreed / stats.total_reviewed
    else:
        stats.agreement_rate = 0.0

    # Breakdown by error type
    error_counter: Counter[str] = Counter()
    conf_counter: Counter[str] = Counter()
    for entry in log_entries:
        error_counter[entry.error_type] += 1
        conf_counter[entry.ai_confidence] += 1

    stats.by_error_type = dict(sorted(error_counter.items()))
    stats.by_confidence = dict(sorted(conf_counter.items()))

    return stats


# ──────────────────────────────────────────────
# Output Formatters
# ──────────────────────────────────────────────

def print_dashboard(report: DashboardReport) -> None:
    """Print a human-readable dashboard to stdout."""
    cs = report.case_stats
    ag = report.agreement_stats

    print()
    print("+" + "=" * 68 + "+")
    print("|" + "  NetSage AI -- Dashboard Summary".center(68) + "|")
    print("+" + "=" * 68 + "+")
    print(f"|  Generated: {report.generated_at}".ljust(69) + "|")
    print("+" + "=" * 68 + "+")

    # Case Statistics
    print("|" + "  [CASES] CASE STATISTICS".ljust(68) + "|")
    print("|" + f"  Total Cases: {cs.total_cases}".ljust(68) + "|")
    print("+" + "-" * 68 + "+")

    print("|" + "  By Category:".ljust(68) + "|")
    for cat, count in cs.by_category.items():
        bar = "#" * (count * 3)
        print("|" + f"    {cat:<12} {bar} {count}".ljust(68) + "|")

    print("+" + "-" * 68 + "+")
    print("|" + "  By OSI Layer:".ljust(68) + "|")
    for layer, count in cs.by_osi_layer.items():
        bar = "#" * (count * 2)
        print("|" + f"    {layer:<12} {bar} {count}".ljust(68) + "|")

    print("+" + "-" * 68 + "+")
    print("|" + "  By Difficulty:".ljust(68) + "|")
    for diff, count in cs.by_difficulty.items():
        bar = "#" * (count * 2)
        print("|" + f"    {diff:<12} {bar} {count}".ljust(68) + "|")

    # Agreement Statistics
    print("+" + "=" * 68 + "+")
    print("|" + "  [AI] AI vs. HUMAN AGREEMENT".ljust(68) + "|")
    print("+" + "-" * 68 + "+")
    print("|" + f"  Total Reviewed : {ag.total_reviewed}".ljust(68) + "|")
    print("|" + f"  Agreed         : {ag.agreed}".ljust(68) + "|")
    print("|" + f"  Disagreed      : {ag.disagreed}".ljust(68) + "|")

    rate_pct = round(ag.agreement_rate * 100, 1)
    rate_bar = "#" * int(rate_pct // 5)
    rate_empty = "." * (20 - len(rate_bar))
    print("|" + f"  Agreement Rate : {rate_bar}{rate_empty} {rate_pct}%".ljust(68) + "|")

    if ag.by_error_type:
        print("+" + "-" * 68 + "+")
        print("|" + "  Error Type Breakdown:".ljust(68) + "|")
        for etype, count in ag.by_error_type.items():
            print("|" + f"    {etype:<25} {count}".ljust(68) + "|")

    if ag.by_confidence:
        print("+" + "-" * 68 + "+")
        print("|" + "  AI Confidence at Error:".ljust(68) + "|")
        for conf, count in ag.by_confidence.items():
            print("|" + f"    {conf:<10} {count}".ljust(68) + "|")

    print("+" + "=" * 68 + "+")
    print()


def generate_html_dashboard(report: DashboardReport) -> str:
    """Generate an HTML dashboard page."""
    cs = report.case_stats
    ag = report.agreement_stats
    rate_pct = round(ag.agreement_rate * 100, 1)

    # Generate category chart data
    cat_labels = list(cs.by_category.keys())
    cat_values = list(cs.by_category.values())
    cat_colors = [
        "#6366f1", "#8b5cf6", "#a855f7", "#d946ef",
        "#ec4899", "#f43f5e", "#f97316", "#eab308",
    ]

    # Generate difficulty data
    diff_labels = list(cs.by_difficulty.keys())
    diff_values = list(cs.by_difficulty.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetSage AI — Dashboard</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --border: #334155;
            --shadow: rgba(0, 0, 0, 0.3);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }}

        .dashboard-header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            border-radius: 16px;
            box-shadow: 0 8px 32px var(--shadow);
        }}

        .dashboard-header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .dashboard-header p {{
            font-size: 0.9rem;
            opacity: 0.85;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px var(--shadow);
        }}

        .stat-card .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}

        .stat-card .stat-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .stat-card.blue .stat-value {{ color: var(--accent-blue); }}
        .stat-card.green .stat-value {{ color: var(--accent-green); }}
        .stat-card.red .stat-value {{ color: var(--accent-red); }}
        .stat-card.amber .stat-value {{ color: var(--accent-amber); }}
        .stat-card.purple .stat-value {{ color: var(--accent-purple); }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .chart-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }}

        .chart-card h3 {{
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}

        .bar-chart {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .bar-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .bar-label {{
            width: 100px;
            text-align: right;
            font-size: 0.85rem;
            color: var(--text-secondary);
            flex-shrink: 0;
        }}

        .bar-container {{
            flex: 1;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            height: 28px;
            overflow: hidden;
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 6px;
            display: flex;
            align-items: center;
            padding-left: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            min-width: 30px;
            transition: width 0.6s ease;
        }}

        .agreement-ring {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }}

        .ring-container {{
            position: relative;
            width: 180px;
            height: 180px;
        }}

        .ring-container svg {{
            transform: rotate(-90deg);
        }}

        .ring-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }}

        .ring-text .rate {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent-green);
        }}

        .ring-text .label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .legend {{
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}

        .error-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 0.5rem;
        }}

        .error-table th, .error-table td {{
            padding: 0.6rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 0.85rem;
        }}

        .error-table th {{
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}

        .error-table td {{
            color: var(--text-primary);
        }}

        .footer {{
            text-align: center;
            padding: 1.5rem;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>🧠 NetSage AI — Dashboard</h1>
        <p>Generated: {report.generated_at}</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card blue">
            <div class="stat-value">{cs.total_cases}</div>
            <div class="stat-label">Total Cases</div>
        </div>
        <div class="stat-card green">
            <div class="stat-value">{ag.agreed}</div>
            <div class="stat-label">AI Agreed</div>
        </div>
        <div class="stat-card red">
            <div class="stat-value">{ag.disagreed}</div>
            <div class="stat-label">AI Corrected</div>
        </div>
        <div class="stat-card purple">
            <div class="stat-value">{rate_pct}%</div>
            <div class="stat-label">Agreement Rate</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 Cases by Category</h3>
            <div class="bar-chart">
"""

    max_cat = max(cat_values) if cat_values else 1
    for i, (label, value) in enumerate(zip(cat_labels, cat_values)):
        width_pct = (value / max_cat) * 100
        color = cat_colors[i % len(cat_colors)]
        html += f"""                <div class="bar-row">
                    <span class="bar-label">{label}</span>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_pct}%; background: {color};">{value}</div>
                    </div>
                </div>
"""

    html += """            </div>
        </div>

        <div class="chart-card">
            <h3>🎯 AI vs. Human Agreement</h3>
            <div class="agreement-ring">
                <div class="ring-container">
                    <svg width="180" height="180" viewBox="0 0 180 180">
                        <circle cx="90" cy="90" r="75" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="14" />
"""

    circumference = 2 * 3.14159 * 75
    filled = circumference * ag.agreement_rate
    html += f"""                        <circle cx="90" cy="90" r="75" fill="none" stroke="var(--accent-green)"
                            stroke-width="14" stroke-dasharray="{filled} {circumference}"
                            stroke-linecap="round" />
                    </svg>
                    <div class="ring-text">
                        <div class="rate">{rate_pct}%</div>
                        <div class="label">Agreement</div>
                    </div>
                </div>
                <div class="legend">
                    <div class="legend-item">
                        <span class="legend-dot" style="background: var(--accent-green);"></span>
                        Agreed ({ag.agreed})
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: var(--accent-red);"></span>
                        Corrected ({ag.disagreed})
                    </div>
                </div>
            </div>
        </div>

        <div class="chart-card">
            <h3>📈 Cases by Difficulty</h3>
            <div class="bar-chart">
"""

    diff_colors = {"Easy": "#22c55e", "Medium": "#f59e0b", "Hard": "#ef4444"}
    max_diff = max(diff_values) if diff_values else 1
    for label, value in zip(diff_labels, diff_values):
        width_pct = (value / max_diff) * 100
        color = diff_colors.get(label, "#6366f1")
        html += f"""                <div class="bar-row">
                    <span class="bar-label">{label}</span>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {width_pct}%; background: {color};">{value}</div>
                    </div>
                </div>
"""

    html += """            </div>
        </div>

        <div class="chart-card">
            <h3>⚠️ Error Type Breakdown</h3>
"""

    if ag.by_error_type:
        html += """            <table class="error-table">
                <thead>
                    <tr><th>Error Type</th><th>Count</th></tr>
                </thead>
                <tbody>
"""
        for etype, count in ag.by_error_type.items():
            html += f"""                    <tr><td>{etype}</td><td>{count}</td></tr>
"""
        html += """                </tbody>
            </table>
"""
    else:
        html += """            <p style="color: var(--text-secondary); padding: 1rem;">No AI corrections logged yet. Run cases through the AI and log corrections to see data here.</p>
"""

    html += f"""        </div>
    </div>

    <div class="footer">
        <p>NetSage AI — Responsible AI Dashboard | {len(cs.concept_tags)} unique concept tags across {cs.total_cases} cases</p>
    </div>
</body>
</html>
"""
    return html


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NetSage AI — Dashboard Generator",
    )
    parser.add_argument(
        "--cases",
        required=True,
        type=Path,
        help="Path to cases.csv dataset.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Path to responsible_ai_log.md (optional).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write JSON report.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Path to write HTML dashboard.",
    )

    args = parser.parse_args()

    # Parse cases
    if not args.cases.exists():
        print(f"Error: Cases file not found: {args.cases}", file=sys.stderr)
        sys.exit(1)

    case_stats = parse_cases(args.cases)

    # Parse AI log if provided
    log_entries: list[AILogEntry] = []
    if args.log and args.log.exists():
        log_entries = parse_ai_log(args.log)

    # Compute agreement
    agreement = compute_agreement(case_stats, log_entries)

    # Build report
    report = DashboardReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        case_stats=case_stats,
        agreement_stats=agreement,
    )

    # Output
    print_dashboard(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"  [OK] JSON report: {args.output}")

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        html_content = generate_html_dashboard(report)
        args.html.write_text(html_content, encoding="utf-8")
        print(f"  [OK] HTML dashboard: {args.html}")


if __name__ == "__main__":
    main()
