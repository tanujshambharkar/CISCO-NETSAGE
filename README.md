# NetSage AI

**AI-Assisted Troubleshooting Helper for Cisco Packet Tracer Lab Networks**

NetSage AI combines structured AI prompts with deterministic validation to diagnose network faults in Packet Tracer lab environments. Every AI diagnosis must be reviewed and approved by a human before any fix is applied.

---

## Project Structure

```
Project/
├── README.md                        # This file
├── requirements.txt                 # fastapi, uvicorn, google-genai
├── data/
│   └── cases.csv                    # 50 realistic troubleshooting cases
├── prompts/
│   └── diagnose_prompt.md           # AI prompt library with 4 worked examples
├── src/
│   ├── __init__.py
│   ├── rule_checker.py              # Deterministic config validator (15 checks)
│   ├── generate_dashboard.py        # Dashboard summary generator
│   └── api.py                       # FastAPI REST API (6 endpoints)
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
- **fastapi** and **uvicorn** for the REST API
- **google-genai** (optional, for live AI diagnosis via Gemini)

```bash
pip install -r requirements.txt
```

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

### 3. Start the REST API

Launch the FastAPI server:

```bash
uvicorn src.api:app --reload --port 8000
```

Open the interactive API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

**Quick API examples:**

```bash
# Health check
curl http://localhost:8000/api/health

# List all STP cases
curl "http://localhost:8000/api/cases?category=STP"

# Get a specific case
curl http://localhost:8000/api/cases/CASE-031

# Get dashboard stats
curl http://localhost:8000/api/stats

# Analyze a config file
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"config_text": "hostname R1\n!\ninterface Gi0/0\n ip address 192.168.1.1 255.255.255.0\n no shutdown\n!\nend"}'

# Build a diagnosis prompt (no AI call)
curl -X POST "http://localhost:8000/api/diagnose?execute=false" \
  -H "Content-Type: application/json" \
  -d '{"symptom": "PC cannot reach remote subnet", "show_outputs": ">>> show ip route\nGateway of last resort is not set"}'

# Execute live AI diagnosis via Gemini (requires GEMINI_API_KEY env var)
export GEMINI_API_KEY=your-api-key-here
curl -X POST "http://localhost:8000/api/diagnose?execute=true" \
  -H "Content-Type: application/json" \
  -d '{"symptom": "PC cannot reach remote subnet", "show_outputs": ">>> show ip route\nGateway of last resort is not set"}'
```

### 4. Use the AI Prompt

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

50 cases across 14 fault categories:

| Category       | Cases | Example Faults |
|----------------|-------|----------------|
| VLAN           | 6     | Missing VLAN, trunk misconfiguration, native VLAN mismatch, VTP domain mismatch, DTP auto-auto |
| Gateway        | 4     | Wrong gateway, missing gateway, gateway on wrong subnet |
| DHCP           | 6     | Pool exhaustion, missing helper-address, wrong excluded range, snooping untrusted port, option 82 |
| DNS            | 3     | Wrong DNS IP, DNS unreachable, missing A record |
| Routing        | 7     | Missing route, OSPF area mismatch, EIGRP AS mismatch, OSPF timer mismatch, redistribution metric |
| ACL            | 4     | Implicit deny, wrong direction, wrong wildcard mask |
| NAT            | 5     | Missing inside/outside, pool exhausted, no PAT overload, static conflict, ACL mismatch |
| Wireless       | 3     | Wrong SSID/password, channel overlap, WLC join failure |
| STP            | 3     | Root bridge election, STP loop, BPDU guard violation |
| HSRP/FHRP      | 2     | Dual active (split-brain), no preempt |
| EtherChannel   | 2     | Protocol mismatch (LACP/PAgP), load-balance issue |
| Security       | 3     | Port security violation, SSH not configured, console no auth |
| IPv6           | 2     | Missing unicast-routing, SLAAC no global address |

### 2. Prompt Library (`prompts/diagnose_prompt.md`)

- System prompt enforcing evidence-based JSON responses
- JSON response schema with validation rules
- 7 guardrails preventing hallucination and destructive commands
- 4 worked examples: Easy (VLAN), Medium (DHCP relay), Hard (NAT + ACL), Medium (STP BPDU Guard)

### 3. Rule Checker (`src/rule_checker.py`)

15 deterministic checks using regex and `ipaddress` module:

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
| OSPF-TIMER | OSPF hello/dead timer mismatches |
| STP-PORTFAST | PortFast enabled on trunk ports |
| INTF-DUPLEX | Speed/duplex mismatch detection |
| UNUSED-ACL | ACLs defined but not applied |
| NO-SSH | VTY lines with Telnet only (no SSH) |
| LOGGING-MISSING | No logging buffered/host configured |
| NO-NTP | No NTP server configured |

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

### 6. REST API (`src/api.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/analyze` | Submit config text → rule checker report |
| `GET`  | `/api/cases` | List/filter cases by category, difficulty, OSI layer |
| `GET`  | `/api/cases/{id}` | Get full case details including show outputs |
| `GET`  | `/api/stats` | Dashboard statistics |
| `POST` | `/api/diagnose` | Build prompt (`?execute=false`) or call Gemini (`?execute=true`) |

## Human-in-the-Loop Policy

Every AI diagnosis includes `"human_approved": false` by default. The workflow requires:

1. AI generates a structured JSON diagnosis
2. Rule checker independently validates the configuration
3. Human reviewer compares both outputs
4. Reviewer either approves the fix or logs a correction
5. Corrections feed back into prompt improvements

## License

This project is for educational use in Cisco Packet Tracer lab environments.
