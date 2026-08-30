# CISCO NETSAGE AI: Hybrid Deterministic & Large Language Model Architecture for Network Troubleshooting in Cisco Packet Tracer Environments

**Project Report & Comprehensive Technical Documentation**  
**Author / Engineering Team:** Tanuj Shambharkar & NetSage AI Contributors  
**Repository:** [CISCO-NETSAGE](https://github.com/tanujshambharkar/CISCO-NETSAGE.git)  
**Date:** August 2026  
**Status:** Production / Academic Capstone Release  

---

## Executive Summary

Enterprise computer networks require rapid, precise, and safe diagnostics to maintain business continuity. As network architectures grow increasingly complex—spanning multi-VLAN switching, inter-VLAN routing, dynamic OSPF/EIGRP topologies, DHCP relay agents, NAT/PAT translation boundaries, and stateful access control lists—network engineers face immense cognitive load during incident resolution.

While modern Generative AI and Large Language Models (LLMs) demonstrate significant promise in synthesizing unstructured diagnostics (`show` commands, syslog entries, host reports), unconstrained LLMs suffer from severe limitations: **hallucinated topology artifacts**, **arithmetic errors in CIDR calculations**, **layer-hopping misdiagnoses**, and **risky remediation commands** (`reload`, `erase startup-config`, blanket wildcard deletions).

**Cisco NetSage AI** introduces a **dual-engine hybrid framework** designed specifically for Cisco Packet Tracer lab networks:
1. **Deterministic Rule Engine (`rule_checker.py`)**: A fast, zero-hallucination static analyzer executing 8 deterministic algorithms (AST-like token parsing, CIDR subnet boundary verification, native VLAN mismatch detection, ACL emptiness auditing, and DHCP range containment).
2. **Constrained AI Diagnostic Agent (`diagnose_prompt.md`)**: A structured LLM system prompt enforcing a strict JSON schema, chain-of-thought evidence citation, 7 safety guardrails, and bottom-up OSI Layer 1–7 diagnostics.
3. **Human-in-the-Loop (HITL) Safety Framework (`responsible_ai_log.md`)**: A governance layer requiring explicit human verification before change execution, backed by a empirical error taxonomy and continuous prompt refinement loop.

NetSage AI was evaluated on a benchmark dataset of **30 realistic enterprise failure cases** across 8 fault categories, achieving an **83.3% initial AI-human agreement rate**, with 100% of LLM discrepancies successfully caught and corrected by the deterministic checker and HITL governance workflow.

---

## 1. Problem Statement & Motivation

### 1.1 The Challenge of Network Troubleshooting
Troubleshooting modern TCP/IP networks requires systematic multi-layer correlation. A single symptom (e.g., "Finance PC cannot access accounting web portal") can stem from any of the 7 OSI layers:
- **Layer 1/2**: Access port assigned to a deleted VLAN, shutdown interface, trunk encapsulation mismatch, or native VLAN mismatch.
- **Layer 3**: Incorrect host default gateway, misconfigured DHCP scope, missing `ip helper-address`, subnet mask arithmetic error, or dynamic OSPF area mismatch.
- **Layer 4**: Transport-layer port blocking in extended ACLs, asymmetric routing dropping stateful TCP sessions.
- **Layer 7**: DNS server unreachable, missing A-record, or HTTP application server failure.

### 1.2 Limitations of Pure LLM Approaches
When general-purpose LLMs diagnose raw Cisco IOS CLI outputs without guardrails, four critical failure modes emerge:
1. **Hallucination of Network Evidence**: Generating imaginary timer mismatches or link flaps when no corresponding `show` data exists.
2. **Subnet & Wildcard Mask Inversion**: Failing to calculate correct host address ranges in non-octet aligned CIDR blocks (/27, /29, /30) or confusing subnet masks (`255.255.255.0`) with wildcard masks (`0.0.0.255`).
3. **Layer Hopping**: Jumping prematurely to Layer 7 (e.g., blaming DNS) before validating Layer 3 default gateway reachability.
4. **Destructive Remediation**: Proposing risky commands such as `default interface`, `no ip access-group`, or device reloads that disrupt production traffic.

### 1.3 The NetSage AI Solution
NetSage AI marries **deterministic algorithmic rigor** with **LLM contextual reasoning**, ensuring network diagnostics are safe, evidence-grounded, and auditable.

---

## 2. System Architecture

The following diagram illustrates the end-to-end NetSage AI diagnostic pipeline:

```
                          +-------------------------------+
                          |    Network Incident / Symptom  |
                          |  (Cisco Packet Tracer Lab)    |
                          +---------------+---------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      | Extract IOS Configs & Show Outputs    |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
        +-------------------------------+   +-------------------------------+
        |   Deterministic Rule Engine   |   |   Constrained AI Prompt Agent |
        |      (rule_checker.py)        |   |     (diagnose_prompt.md)      |
        | - Python ipaddress module     |   | - 7 Safety Guardrails         |
        | - Regex token parser          |   | - JSON Schema Enforcement     |
        | - 8 Deterministic Checks      |   | - Chain-of-Thought Citations  |
        +---------------+---------------+   +---------------+---------------+
                        |                                   |
                        | JSON Rule Report                  | JSON AI Diagnosis
                        | (Findings & Line Nos)             | (Layer, Cause, Fix)
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |   Human-in-the-Loop Reviewer Gate     |
                      |   (Lab Instructor / NetOps Admin)     |
                      +-------------------+-------------------+
                                          |
                         +----------------+----------------+
                         |                                 |
                         v (Approved)                      v (Disagreement / Error)
        +--------------------------------+   +--------------------------------+
        | Apply Approved Remediation     |   | Log into Responsible AI System |
        | to Cisco Packet Tracer Network |   | (responsible_ai_log.md)        |
        +--------------------------------+   +----------------+---------------+
                                                              |
                                                              v
                                             +--------------------------------+
                                             | Metric Aggregation & Dashboard |
                                             | (generate_dashboard.py)        |
                                             +--------------------------------+
```

---

## 3. Dataset & Troubleshooting Benchmark (`data/cases.csv`)

To systematically benchmark and validate NetSage AI, a dataset of **30 realistic enterprise failure cases** was curated across 8 core networking domains:

| Category | Cases Count | Primary OSI Layers | Representative Faults |
|---|---|---|---|
| **VLAN & Trunking** | 4 | Layer 2 | Deleted VLAN in database, trunk allowed list exclusion, native VLAN mismatch, DTP access/trunk mode misnegotiation |
| **Gateway & Subnet** | 4 | Layer 3 | Wrong host CIDR mask, missing default gateway, gateway on foreign subnet, switch SVI missing gateway |
| **DHCP & Relay** | 4 | Layer 3 / 7 | Missing `ip helper-address`, DHCP pool subnet mismatch, router IP unexcluded (conflict), wrong `default-router` |
| **DNS Resolution** | 3 | Layer 7 | Invalid DNS server IP on client, DNS server interface down, `no ip domain lookup` on router |
| **Routing Protocols** | 5 | Layer 3 | Missing default route, OSPF area mismatch on P2P link, passive interface on neighbor link, missing OSPF network statement, EIGRP AS mismatch |
| **Access Control (ACL)** | 4 | Layer 3 / 4 | ACL applied in wrong direction, empty ACL (implicit deny-all), inverted wildcard mask, ACL blocking ICMP return replies |
| **NAT & PAT** | 3 | Layer 3 / 4 | Missing `ip nat outside`, missing `overload` keyword for PAT, NAT source ACL mismatching local subnets |
| **Wireless LAN (WLAN)** | 3 | Layer 1 / 2 | WPA2-PSK passphrase mismatch, 2.4GHz co-channel interference (overlapping channels 1/2), AP missing DHCP Option 43 |

### 3.1 Difficulty Tier Distribution
- **Easy (10 Cases / 33.3%)**: Single-device, single-layer syntax or configuration omission (e.g., missing gateway, shutdown port).
- **Medium (14 Cases / 46.7%)**: Multi-device or cross-layer interaction (e.g., DHCP relay agent missing helper-address across routers, OSPF area mismatch).
- **Hard (6 Cases / 20.0%)**: Multi-variable or asymmetric failure (e.g., NAT overload omission dropping secondary flows, extended ACL blocking return ICMP while permitting TCP).

---

## 4. Deterministic Rule Engine (`src/rule_checker.py`)

The deterministic engine inspects Cisco IOS configuration files without external dependencies, relying strictly on Python's built-in `ipaddress`, `re`, `json`, and `argparse` libraries.

### 4.1 Implemented Rule Modules

```
+------------------+-------------------------------------------------------------------------+
| Rule ID          | Algorithmic Check & Detection Logic                                     |
+------------------+-------------------------------------------------------------------------+
| DUP-IP           | Parses all 'ip address <ip> <mask>' tokens; flags collisions if same IP |
|                  | appears across two or more distinct interfaces.                         |
| SUBNET-MISMATCH  | Groups interfaces by network address; detects conflicting prefix lengths|
|                  | (e.g. 192.168.1.1/24 vs 192.168.1.1/25 on identical segment).           |
| MISSING-VLAN     | Extracts all referenced VLANs ('access vlan X', 'trunk allowed vlan X') |
|                  | and cross-checks against defined 'vlan <id>' blocks in database.        |
| SHUTDOWN-INTF    | Identifies interfaces lacking 'no shutdown' or containing 'shutdown'.  |
| NO-GATEWAY       | Detects absence of 'ip default-gateway' or static 'ip route 0.0.0.0'.   |
| TRUNK-NATIVE     | Compares 'switchport trunk native vlan X' across all trunk interfaces   |
|                  | to identify native VLAN tag mismatches.                                 |
| ACL-NO-PERMIT    | Parses numbered and named ACL blocks; flags ACLs containing only deny   |
|                  | statements where the trailing implicit deny will blackhole all traffic. |
| DHCP-POOL        | Validates that 'default-router' and 'dns-server' IPs fall strictly      |
|                  | within the CIDR boundary specified by 'network <net> <mask>'.           |
+------------------+-------------------------------------------------------------------------+
```

### 4.2 Deterministic Execution Output
When run on the planted-fault test suite (`tests/sample_config_1.txt`), the rule engine instantly identifies 9 distinct faults with exact line numbers in < 15ms:
```
======================================================================
  NetSage AI -- Deterministic Rule Checker Report
======================================================================
  Config File    : tests/sample_config_1.txt
  Total Findings : 9 (Errors: 7, Warnings: 1, Info: 1)
  - [ERR] DUP-IP: Duplicate IP 192.168.1.1 on Gi0/0 (line 17), Gi0/1 (line 21)
  - [ERR] SUBNET-MISMATCH: Mask mismatch on 192.168.1.0 (Gi0/0 /24 vs Gi0/1 /25)
  - [ERR] MISSING-VLAN: VLAN 50 referenced on Gi0/2, Gi0/4 but not in database
  - [ERR] MISSING-VLAN: VLAN 99 referenced on Gi0/3 but not in database
  - [WARN] SHUTDOWN-INTF: Interface Serial0/0/0 is administratively shut down
  - [INFO] NO-GATEWAY: No default gateway or default route found
  - [ERR] TRUNK-NATIVE: Native VLAN mismatch (VLAN 99 on Gi0/3 vs VLAN 1 on Gi0/4)
  - [ERR] ACL-NO-PERMIT: ACL 50 has no permit statement (implicit deny-all)
  - [ERR] DHCP-POOL: DHCP pool 'REMOTE_LAN' default-router 10.0.3.1 outside 10.0.2.0/24
======================================================================
```

---

## 5. AI Prompt Engineering & Safety Guardrails (`prompts/diagnose_prompt.md`)

To eliminate hallucinations and prevent destructive configuration changes, the LLM diagnostic system prompt incorporates **7 explicit safety guardrails** and a rigid JSON response contract.

### 5.1 The 7 Safety Guardrails
1. **G1 (Evidence-Only Constraint)**: Every cited observation must quote literal substrings from the provided `show` commands or configs.
2. **G2 (Bottom-Up OSI Methodology)**: Always evaluate Layer 1 (Physical/Interface Status) $\rightarrow$ Layer 2 (VLAN/Trunk) $\rightarrow$ Layer 3 (IP/Routing) $\rightarrow$ Layer 4/7 (ACL/Services).
3. **G3 (Subnet Arithmetic Verification)**: Mandate step-by-step CIDR prefix calculations for all gateway and host IP pairs.
4. **G4 (Zero Destructive Commands)**: Prohibit disruptive commands (`reload`, `erase`, `format`, `clear ip route *`).
5. **G5 (Minimal Remediation Principle)**: Only generate precise delta commands needed to resolve the root cause.
6. **G6 (Mandatory HITL Flag)**: Set `"human_approved": false` on every output.
7. **G7 (Deterministic Cross-Check)**: Flag high-confidence recommendations with corresponding rule IDs (`DUP-IP`, `MISSING-VLAN`, etc.).

### 5.2 JSON Response Schema
```json
{
  "case_id": "CASE-001",
  "fault_category": "VLAN",
  "osi_layer": "Layer 2",
  "root_cause": "Detailed technical root cause explanation",
  "evidence": [
    "show interface status: FastEthernet0/10 is assigned to VLAN 10",
    "show vlan brief: VLAN 10 does not exist in switch VLAN database"
  ],
  "confidence": "HIGH",
  "remediation_commands": [
    "configure terminal",
    "vlan 10",
    "name Finance",
    "exit"
  ],
  "verification_commands": [
    "show vlan brief",
    "show interface FastEthernet0/10 switchport"
  ],
  "human_approved": false
}
```

---

## 6. Responsible AI & Error Governance (`logs/responsible_ai_log.md`)

During the evaluation of the 30 benchmark cases, 5 cases resulted in initial AI disagreements that were flagged, analyzed, and categorized into an empirical error taxonomy:

```
+-----------------------------------------------------------------------------------+
|                         AI vs. Human Agreement (30 Cases)                         |
|   =============================================================================   |
|   [####################################################..........] 83.3% Agreed   |
|   Agreed Cases: 25 / 30  |  Disagreements Logged: 5 / 30                         |
+-----------------------------------------------------------------------------------+
```

### 6.1 Error Taxonomy & Breakdown
```
+-----------------------------------------------------------------------------------+
| Error Type               | Count | Primary Root Cause                             |
+--------------------------+-------+------------------------------------------------+
| Misdiagnosis             |   2   | Subnet math omission / Unchecked IP conflict   |
| Hallucinated Evidence    |   1   | Fabricated OSPF timer mismatch when data absent|
| Incomplete Fix           |   1   | Missing ICMP return permit in unidirectional ACL|
| Wrong Layer              |   1   | Blamed Layer 7 DNS when Layer 3 gateway invalid|
+--------------------------+-------+------------------------------------------------+
```

### 6.2 Detailed Case Studies of AI Failures
1. **LOG-001 (CASE-007 - Gateway Subnet Mismatch)**:
   - *AI Diagnosis*: PC1 default gateway unreachable due to router interface shutdown.
   - *Actual Cause*: PC1 IP (172.16.10.5/16) and Gateway (10.0.0.1/24) belonged to entirely disjoint IP subnets.
   - *Prompt Refinement*: Added explicit instruction to perform CIDR network address bitwise AND operations before evaluating interface state.
2. **LOG-003 (CASE-018 - Hallucinated OSPF Timer Mismatch)**:
   - *AI Diagnosis*: Claimed OSPF Hello/Dead timer mismatch caused neighbor adjacencies to fail.
   - *Actual Cause*: `show ip ospf interface` contained no custom timers; the actual fault was Area 0 vs Area 1 mismatch on the serial link.
   - *Prompt Refinement*: Added negative few-shot example explicitly forbidding inferring missing configuration parameters.
3. **LOG-005 (CASE-012 - Layer Hopping to DNS)**:
   - *AI Diagnosis*: Claimed DHCP pool DNS server failed.
   - *Actual Cause*: DHCP pool `default-router` pointed to non-existent IP `192.168.5.100`.
   - *Prompt Refinement*: Strictly enforced bottom-up OSI diagnostic ordering.

---

## 7. Metrics & Dashboard Generator (`src/generate_dashboard.py`)

The project includes an automated reporting pipeline that parses `cases.csv` and `responsible_ai_log.md` to produce:
1. **Console ASCII Dashboard**: Real-time terminal charts and breakdown.
2. **JSON Machine-Readable Report (`tests/dashboard_report.json`)**: Formatted metrics for CI/CD pipelines.
3. **Responsive HTML Dashboard (`tests/dashboard.html`)**: Interactive web dashboard with CSS bar charts, badges, and breakdown cards.

---

## 8. Cisco Packet Tracer Lab Topology & Replication Guide

The accompanying `cisco_packet_tracer_lab/` directory provides complete Cisco IOS configurations to replicate an enterprise branch and campus network:

### 8.1 Device Roles
- **R1-Core (Cisco 2911/4321)**: WAN Gateway, PAT Overload, OSPF Area 0, Centralized DHCP Server.
- **R2-Branch (Cisco 2911/4321)**: Inter-VLAN Router-on-a-Stick (802.1Q sub-interfaces for VLAN 10, 20, 30, 99), DHCP Relay Agent (`ip helper-address`).
- **SW1-Core (Catalyst 3560/2960)**: Distribution Switch, 802.1Q Trunks, Native VLAN 99.
- **SW2-Access (Catalyst 2960)**: Access Switch, Edge PortFast, VLAN 10/20 access ports.
- **WLC-2504 & APs**: Wireless LAN Controller managing CorpWiFi SSID and lightweight access points.

---

## 9. Deliverables & Project Package Structure

```
CISCO-NETSAGE / Project Package
├── PROJECT_REPORT.md                        # Formal Technical Project Report (This document)
├── PROJECT_REPORT.html                      # Beautifully styled standalone HTML report
├── README.md                                # Project summary & Quick Start Guide
├── requirements.txt                         # Zero-dependency specification (Python stdlib)
├── build_project_zip.py                     # Automated packaging & verification script
├── Cisco_NetSage_Complete_Package.zip       # All-in-one distribution bundle
├── data/
│   └── cases.csv                            # 30 Comprehensive troubleshooting benchmark cases
├── prompts/
│   └── diagnose_prompt.md                   # AI Prompt Library with 7 Guardrails & 3 Worked Examples
├── src/
│   ├── __init__.py
│   ├── rule_checker.py                      # Deterministic Config Validator (8 rules)
│   └── generate_dashboard.py                # Dashboard & Metrics Reporting Engine
├── logs/
│   └── responsible_ai_log.md                # HITL Disagreement & Governance Log (5 entries)
├── cisco_packet_tracer_lab/
│   ├── README_LAB_SETUP.md                  # Packet Tracer setup & replication guide
│   ├── verify_lab.py                        # Automated lab configuration verification
│   ├── baseline_configs/                    # Clean gold-standard Cisco IOS configurations
│   │   ├── R1_Core_Router.cfg
│   │   ├── R2_Branch_Router.cfg
│   │   ├── SW1_Core_Switch.cfg
│   │   ├── SW2_Access_Switch.cfg
│   │   └── WLC_Config.cfg
│   └── fault_scenarios/                     # 30 Fault Injection scenario configs
│       └── all_fault_injection_scenarios.cfg
└── tests/
    ├── sample_config_1.txt                  # Test config with 9 planted faults
    ├── report_1.json                        # Rule checker output
    ├── dashboard_report.json                # Summary metrics JSON
    └── dashboard.html                       # HTML dashboard report
```

---

## 10. Conclusion & Future Scope

Cisco NetSage AI demonstrates that combining deterministic static analysis with large language model diagnostics creates a resilient, high-accuracy network troubleshooting assistant. By enforcing strict safety guardrails, structured JSON outputs, and mandatory human-in-the-loop approvals, NetSage AI eliminates hallucinations while accelerating mean-time-to-resolution (MTTR).

### Future Roadmap
1. **Automated Packet Tracer API Integration**: Direct integration via Python `ptcontrol` / Packet Tracer IPC API for automatic fault injection and real-time topology extraction.
2. **Multi-Vendor Support**: Extending regex and parsing engines to Arista EOS, Juniper JunOS, and Cumulus Linux.
3. **Reinforcement Learning from Human Feedback (RLHF)**: Tuning open-source models (e.g. Llama-3, Mistral) on NetSage AI's responsible correction logs to further boost agreement rates above 95%.
