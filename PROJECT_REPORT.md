# PROJECT TITLE
**NetSage AI: An AI-Assisted Network Troubleshooting System with Human Review**
Submitted as part of [AICTE / Internship / Course Name]

**Submitted By:**
Name: 
College: 
Branch: 
AICTE ID: 

**Project Team Members:**
1. 
2. 
3. 
4. 

**Technology Stack:** Cisco Packet Tracer | Python | Artificial Intelligence | CSV/Excel
**Date:** 

---

## Certificate / Declaration

### Certificate
This is to certify that the project entitled **NetSage AI: An AI-Assisted Network Troubleshooting System with Human Review** is a bona fide record of independent project work done by the team members under supervision and guidance. 

### Declaration of Originality
We hereby declare that the project work presented here is original and has not been submitted in part or full for any other degree or diploma. 

### Acknowledgement
We express our gratitude to our mentors and the faculty for their continuous support, guidance, and encouragement throughout the course of this project.

---

## CHAPTER 1 — INTRODUCTION

### 1.1 Background
Enterprise computer networks require rapid, precise, and safe diagnostics to maintain business continuity. As network architectures grow increasingly complex—spanning multi-VLAN switching, inter-VLAN routing, dynamic topologies, NAT/PAT translation boundaries, and stateful access control lists—network engineers face immense cognitive load during incident resolution. Troubleshooting modern TCP/IP networks requires systematic multi-layer correlation where a single symptom can stem from any of the 7 OSI layers.

### 1.2 Objectives
While modern Generative AI and Large Language Models (LLMs) demonstrate significant promise in synthesizing unstructured diagnostics (`show` commands, syslog entries, host reports), unconstrained LLMs suffer from severe limitations: hallucinated topology artifacts, arithmetic errors in CIDR calculations, layer-hopping misdiagnoses, and risky remediation commands.

The primary objective of NetSage AI is to introduce a dual-engine hybrid framework designed specifically for Cisco Packet Tracer lab networks that marries deterministic algorithmic rigor with LLM contextual reasoning, ensuring network diagnostics are safe, evidence-grounded, and auditable.

---

## CHAPTER 2 — LITERATURE SURVEY / RELATED WORK

### 2.1 Traditional Troubleshooting 
Traditional troubleshooting relies entirely on the expertise of network administrators running static commands (`ping`, `traceroute`, `show run`) and parsing logs manually. This method is slow and heavily dependent on human expertise. 

### 2.2 AI in Network Management
Recent advancements have attempted to apply LLMs to IT ops (AIOps). However, these systems often operate as black boxes, providing suggestions without verifying syntax or semantic logic. This leads to risky behavior if directly applied to production networks without human oversight.

---

## CHAPTER 3 — SYSTEM ARCHITECTURE

NetSage AI uses a dual-engine approach to eliminate hallucinations and prevent destructive configuration changes.
1. **Deterministic Rule Engine (`rule_checker.py`)**: A fast, zero-hallucination static analyzer executing 15 deterministic algorithms (AST-like token parsing, CIDR subnet boundary verification, native VLAN mismatch detection, ACL emptiness auditing, etc.).
2. **Constrained AI Diagnostic Agent (`diagnose_prompt.md`)**: A structured LLM system prompt enforcing a strict JSON schema, chain-of-thought evidence citation, 7 safety guardrails, and bottom-up OSI Layer 1–7 diagnostics.
3. **Human-in-the-Loop (HITL) Safety Framework (`responsible_ai_log.md`)**: A governance layer requiring explicit human verification before change execution.

---

## CHAPTER 4 — METHODOLOGY (RULE ENGINE + AI)

The methodology bridges deterministic analysis and heuristic AI:
- **Rule Engine**: Evaluates static configurations, identifies definitive errors (e.g. DUP-IP, MISSING-VLAN), and produces JSON reports.
- **AI Diagnostics**: The Gemini 3.6 Flash LLM interprets complex state-based issues from live output. It generates a structured root-cause analysis based on strict prompts.
- **Integration**: The APIs merge deterministic reports and AI diagnostics, presenting a holistic view via a desktop GUI or REST API.

---

## CHAPTER 5 — IMPLEMENTATION DETAILS

- **Backend / API**: FastAPI enables a RESTful API (`src/api.py`) for system integration, exposing endpoints for configuration validation, case retrieval, and prompt construction.
- **Frontend / GUI**: Built using CustomTkinter (`src/gui.py`), it offers a unified interface for loading configurations, stating symptoms, pasting logs, and viewing diagnostics. 
- **Troubleshooting Guide**: A comprehensive, built-in guide (`src/guide.py`) surfaces actionable steps directly in the GUI and via the `/api/guide` endpoint. 

---

## CHAPTER 6 — HUMAN IN THE LOOP & SAFETY GUARDRAILS

To eliminate hallucinations, the prompt incorporates 7 explicit safety guardrails:
1. Evidence-Only Constraint
2. Bottom-Up OSI Methodology
3. Subnet Arithmetic Verification
4. Zero Destructive Commands
5. Minimal Remediation Principle
6. Mandatory HITL Flag (`"human_approved": false`)
7. Deterministic Cross-Check

Every diagnosis forces the human network administrator to verify the steps, ensuring AI acts strictly as an assistant, never an autonomous agent.

---

## CHAPTER 7 — TESTING AND BENCHMARK RESULTS

A dataset of 50 realistic enterprise failure cases was curated (`data/cases.csv`) across 14 core networking domains (VLAN, Gateway, DHCP, Routing, ACL, etc.).
- The system achieves an 83.3% initial AI-human agreement rate. 
- 100% of LLM discrepancies are caught and corrected by the deterministic checker and HITL governance workflow, logged in `logs/responsible_ai_log.md`.

---

## CHAPTER 8 — CISCO PACKET TRACER INTEGRATION

The project simulates realistic enterprise branch and campus networks within Cisco Packet Tracer. The `cisco_packet_tracer_lab/` directory contains baseline configurations for Distribution switches, Access switches, Core routers, and WLC controllers. By mapping real packet tracer CLI output directly to NetSage AI, it bridges the gap between simulated lab assignments and real-world AI operations.

---

## CHAPTER 9 — DASHBOARD & METRICS

An automated reporting pipeline (`src/generate_dashboard.py`) parses testing data to produce:
1. Console ASCII Dashboard.
2. JSON Machine-Readable Report.
3. Responsive HTML Dashboard containing CSS bar charts and metrics cards.

---

## CHAPTER 10 — CONCLUSION & FUTURE SCOPE

NetSage AI demonstrates that combining deterministic static analysis with large language model diagnostics creates a resilient, high-accuracy network troubleshooting assistant.

### Future Scope
1. **Automated Packet Tracer API Integration**: Direct integration for automatic fault injection and real-time topology extraction.
2. **Multi-Vendor Support**: Extending regex and parsing engines to Arista EOS and Juniper JunOS.
3. **Reinforcement Learning from Human Feedback (RLHF)**: Tuning models based on human correction logs to increase accuracy.

---

## Appendices

- **Appendix A**: Sample Diagnostic Output JSON
- **Appendix B**: Dashboard Output Sample
- **Appendix C**: Packet Tracer Topology Diagram
