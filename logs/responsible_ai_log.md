# NetSage AI — Responsible AI Correction Log

> **Purpose:** Document instances where the AI diagnosis was incorrect and required human correction.  
> **Policy:** Every AI diagnosis must be reviewed by a human before any fix is applied. This log captures disagreements to improve future prompt engineering.

---

## Summary

| Metric | Value |
|---|---|
| Total Cases Reviewed | 30 |
| AI Corrections Logged | 5 |
| Agreement Rate | 83.3% |
| Most Common Error Type | Misdiagnosis |

---

### LOG-001

| Field | Value |
|---|---|
| Case Reference | CASE-007 |
| AI Diagnosis | PC1 default gateway is misconfigured; gateway 10.0.0.1 is unreachable because the router interface is down |
| AI Confidence | MEDIUM |
| Actual Root Cause | Gateway 10.0.0.1 is on a completely different subnet (10.0.0.0/24) than the host (172.16.0.0/16); the router interface is up and reachable directly |
| Error Type | Misdiagnosis |
| Correction Applied | Changed PC1 default gateway from 10.0.0.1 to 172.16.0.1 (the router's actual Gi0/0 interface IP) |
| Lesson Learned | The AI incorrectly assumed an interface-down scenario instead of performing subnet math to verify the gateway was in the host's subnet. Future prompts should instruct the AI to explicitly calculate whether the gateway IP falls within the host's configured subnet before checking interface status. |
| Reviewer | Lab Instructor |
| Date | 2026-08-28T10:30:00+05:30 |

---

### LOG-002

| Field | Value |
|---|---|
| Case Reference | CASE-011 |
| AI Diagnosis | DHCP pool is exhausted; no addresses remain for new clients |
| AI Confidence | HIGH |
| Actual Root Cause | The DHCP pool has available addresses, but the router's own IP (192.168.1.1) was not excluded from the pool, causing IP conflicts when DHCP assigns 192.168.1.1 to a client |
| Error Type | Misdiagnosis |
| Correction Applied | Added `ip dhcp excluded-address 192.168.1.1` to prevent the router's IP from being assigned to DHCP clients |
| Lesson Learned | The AI fixated on pool exhaustion (a common issue) and did not cross-reference the DHCP pool range against static IP assignments on local interfaces. The prompt should require checking for `ip dhcp conflict` output and comparing assigned IPs against interface IPs before concluding exhaustion. |
| Reviewer | Lab Instructor |
| Date | 2026-08-28T11:15:00+05:30 |

---

### LOG-003

| Field | Value |
|---|---|
| Case Reference | CASE-018 |
| AI Diagnosis | OSPF neighbors are not forming because the hello/dead timers are mismatched between R1 and R2 |
| AI Confidence | MEDIUM |
| Actual Root Cause | OSPF area mismatch on the shared Serial0/0/0 link — R1 is in Area 0, R2 is in Area 1; timer values are at defaults on both sides |
| Error Type | Hallucinated Evidence |
| Correction Applied | Changed R2's OSPF network statement to place Serial0/0/0 in Area 0: `network 172.16.0.0 0.0.0.3 area 0` |
| Lesson Learned | The AI fabricated a timer mismatch diagnosis despite no hello/dead timer values being present in the show output. This is a direct violation of the evidence-only constraint. The system prompt guardrail (G1: only cite evidence present in the provided show output) must be reinforced with an explicit negative example showing timer-based misdiagnosis when timer data is absent. |
| Reviewer | Lab Instructor |
| Date | 2026-08-28T14:00:00+05:30 |

---

### LOG-004

| Field | Value |
|---|---|
| Case Reference | CASE-024 |
| AI Diagnosis | ACL 130 is correctly configured; the issue is likely a routing problem preventing return traffic from reaching the source host |
| AI Confidence | LOW |
| Actual Root Cause | ACL 130 permits only TCP (established, port 80, 443) but has no permit entry for ICMP; echo-reply packets from 192.168.1.0/24 are dropped by the implicit deny at the end of the ACL |
| Error Type | Incomplete Fix |
| Correction Applied | Added `permit icmp any any echo-reply` to ACL 130 to allow ICMP echo replies |
| Lesson Learned | The AI correctly identified that return traffic was blocked but attributed it to routing instead of the ACL. When an ACL is applied to an interface and the symptom is one-directional failure (ping out works, reply blocked), the AI should enumerate every protocol permitted by the ACL and check if the blocked protocol (ICMP in this case) is explicitly permitted. |
| Reviewer | Lab Instructor |
| Date | 2026-08-29T09:20:00+05:30 |

---

### LOG-005

| Field | Value |
|---|---|
| Case Reference | CASE-012 |
| AI Diagnosis | DHCP pool has incorrect DNS server configuration; hosts cannot resolve external names |
| AI Confidence | MEDIUM |
| Actual Root Cause | The DHCP pool's `default-router` is set to 192.168.5.100 (a non-existent IP) instead of 192.168.5.1 (the router's Gi0/0 interface); DNS is working correctly — the actual issue is hosts have no valid gateway to reach anything beyond the local subnet |
| Error Type | Wrong Layer |
| Correction Applied | Changed DHCP pool `default-router` from 192.168.5.100 to 192.168.5.1 |
| Lesson Learned | The AI jumped to Layer 7 (DNS) because the symptom mentioned "cannot reach networks" and DNS was configured in the DHCP pool. The AI should follow a bottom-up OSI diagnostic approach: verify Layer 3 (routing/gateway) before Layer 7 (application). The prompt should mandate checking default-router IP against interface IPs before analyzing DNS/application-layer settings. |
| Reviewer | Lab Instructor |
| Date | 2026-08-29T11:45:00+05:30 |

---

## Error Type Definitions

| Error Type | Definition |
|---|---|
| **Misdiagnosis** | AI identified the wrong root cause despite sufficient evidence being available |
| **Hallucinated Evidence** | AI cited evidence not present in the provided show-command outputs |
| **Incomplete Fix** | AI identified a related issue but missed the actual root cause or provided partial remediation |
| **Wrong Layer** | AI attributed the fault to the wrong OSI layer, leading to misguided troubleshooting |

---

## Improvement Actions

Based on the patterns observed in corrections above:

1. **Subnet Validation** (from LOG-001, LOG-005): Add explicit instructions to the system prompt requiring the AI to verify that gateway IPs are within the host's subnet using CIDR math before checking interface status.

2. **Evidence-Only Enforcement** (from LOG-003): Add a negative example in the prompt library showing what a hallucinated diagnosis looks like and why it's rejected.

3. **Protocol Enumeration for ACLs** (from LOG-004): When an ACL is involved and traffic is one-directional, require the AI to list every permitted protocol and check if the failing protocol is included.

4. **Bottom-Up OSI Approach** (from LOG-005): Mandate that the AI check lower layers (1→2→3) before higher layers (4→7) when the symptom is generic "cannot reach."

5. **Cross-Reference DHCP Fields** (from LOG-002): Require the AI to compare every field in a DHCP pool (network, default-router, dns-server, excluded-addresses) against the actual device configurations.
