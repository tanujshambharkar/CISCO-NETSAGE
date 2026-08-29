# NetSage AI

**AI-Assisted Troubleshooting Helper for Cisco Packet Tracer Lab Networks**

NetSage AI combines structured AI prompts with deterministic validation to diagnose network faults in Packet Tracer lab environments. Every AI diagnosis must be reviewed and approved by a human before any fix is applied.

---

## Project Structure

```
Project foid/
├── README.md                        # This file
├── requirements.txt                 # Dependencies (stdlib only)
├── data/
│   └── cases.csv                    # 30 realistic troubleshooting cases
├── prompts/
│   └── diagnose_prompt.md           # AI prompt library with 3 worked examples
├── src/
│   ├── __init__.py
│   ├── rule_checker.py              # Deterministic config validator (8 checks)
│   └── generate_dashboard.py        # Dashboard summary generator
├── logs/
│   └── responsible_ai_log.md        # AI correction log (5 entries)
└── tests/
    ├── sample_config_1.txt          # Test config with planted faults
    ├── report_1.json                # Rule checker output
    ├── dashboard_report.json        # Dashboard JSON output
    └── dashboard.html               # HTML dashboard
```

## Requirements

- **Python 3.10+**
- **No external dependencies** -- uses only Python standard library (`ipaddress`, `re`, `csv`, `json`, `argparse`)

## Quick Start

### 1. Run the Rule Checker

Validate a Cisco IOS configuration file for common misconfigurations:

```bash
python src/rule_checker.py --config tests/sample_config_1.txt
```

With JSON report output:

```bash
python src/rule_checker.py --config tests/sample_config_1.txt --output report.json
```

JSON-only mode (for pipeline integration):

```bash
python src/rule_checker.py --config tests/sample_config_1.txt --json
```

### 2. Generate the Dashboard

Summarize case distribution, severity, and AI vs. human agreement rate:

```bash
python src/generate_dashboard.py --cases data/cases.csv --log logs/responsible_ai_log.md
```

With HTML dashboard output:

```bash
python src/generate_dashboard.py --cases data/cases.csv --log logs/responsible_ai_log.md --html dashboard.html
```

### 3. Use the AI Prompt

Copy the system prompt from `prompts/diagnose_prompt.md` into your AI interface, then submit a case using the user prompt template. The AI will respond with a structured JSON diagnosis.

## Architecture

```
                    +------------------+
                    |   cases.csv      |
                    |  (30 cases)      |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v----------+      +-----------v---------+
    | diagnose_prompt.md |      |  rule_checker.py    |
    |  (AI Diagnosis)    |      | (Deterministic)     |
    +---------+----------+      +-----------+----------+
              |                             |
              |    JSON Diagnosis           |    JSON Report
              |                             |
              +--------->+---------<--------+
                         |  Human  |
                         | Reviewer|
                         +----+----+
                              |
                 +------------+------------+
                 |                         |
       +---------v---------+    +----------v---------+
       |   Apply Fix       |    | responsible_ai_log |
       |   (Approved)      |    |  (Corrected)       |
       +-------------------+    +----------+---------+
                                           |
                                +----------v----------+
                                | generate_dashboard  |
                                |  (Summary Report)   |
                                +---------------------+
```

## Deliverables

### 1. Troubleshooting Dataset (`data/cases.csv`)

30 cases across 8 fault categories:

| Category | Cases | Example Faults |
|----------|-------|----------------|
| VLAN     | 4     | Missing VLAN, trunk misconfiguration, native VLAN mismatch |
| Gateway  | 4     | Wrong gateway, missing gateway, gateway on wrong subnet |
| DHCP     | 4     | Pool exhaustion, missing helper-address, wrong excluded range |
| DNS      | 3     | Wrong DNS IP, DNS unreachable, missing A record |
| Routing  | 5     | Missing route, OSPF area mismatch, EIGRP AS mismatch |
| ACL      | 4     | Implicit deny, wrong direction, wrong wildcard mask |
| NAT      | 3     | Missing inside/outside, pool exhausted, no PAT overload |
| Wireless | 3     | Wrong SSID/password, channel overlap, WLC join failure |

### 2. Prompt Library (`prompts/diagnose_prompt.md`)

- System prompt enforcing evidence-based JSON responses
- JSON response schema with validation rules
- 7 guardrails preventing hallucination and destructive commands
- 3 worked examples: Easy (VLAN), Medium (DHCP relay), Hard (NAT + ACL)

### 3. Rule Checker (`src/rule_checker.py`)

8 deterministic checks using regex and `ipaddress` module:

| Check ID | Description |
|----------|-------------|
| DUP-IP | Duplicate IP addresses across interfaces |
| SUBNET-MISMATCH | Different masks on same network |
| MISSING-VLAN | VLANs referenced but not defined |
| SHUTDOWN-INTF | Administratively down interfaces |
| NO-GATEWAY | Missing default gateway or route |
| TRUNK-NATIVE | Native VLAN mismatch on trunks |
| ACL-NO-PERMIT | ACLs with no permit statement |
| DHCP-POOL | DHCP pool subnet mismatches |

### 4. Responsible AI Log (`logs/responsible_ai_log.md`)

5 documented correction instances with structured fields:
- AI diagnosis vs. actual root cause
- Error type classification (Misdiagnosis, Hallucinated Evidence, Incomplete Fix, Wrong Layer)
- Lessons learned and prompt improvement actions

### 5. Dashboard (`src/generate_dashboard.py`)

Summary of issue types, severity, and AI vs. human agreement rate:
- Console output with ASCII bar charts
- JSON report for programmatic access
- HTML dashboard with styled visualizations

## Human-in-the-Loop Policy

Every AI diagnosis includes `"human_approved": false` by default. The workflow requires:

1. AI generates a structured JSON diagnosis
2. Rule checker independently validates the configuration
3. Human reviewer compares both outputs
4. Reviewer either approves the fix or logs a correction
5. Corrections feed back into prompt improvements

## License

This project is for educational use in Cisco Packet Tracer lab environments.
