"""
NetSage AI — Troubleshooting Guide Data
==================================================
Shared reference for common Cisco network faults, diagnostic commands,
and remediation steps. Used by both the API and GUI.
"""

TROUBLESHOOTING_GUIDE = {
    "title": "Cisco Network Troubleshooting & Remediation Guide",
    "sections": [
        {
            "layer": "1. LAYER 2: SWITCHING, VLANS & TRUNKS",
            "topics": [
                {
                    "name": "Access Port Issues (VLAN Mismatch)",
                    "symptom": "Host in VLAN X cannot communicate with other hosts in VLAN X.",
                    "diagnose": [
                        "show mac address-table",
                        "show interfaces status",
                        "show interfaces switchport"
                    ],
                    "remediation": [
                        "interface <interface_name>",
                        "switchport mode access",
                        "switchport access vlan <vlan_id>",
                        "no shutdown"
                    ]
                },
                {
                    "name": "Trunk Allowed VLANs & Native VLAN Mismatches",
                    "symptom": "Traffic fails between switches; syslog reports %CDP-4-NATIVE_VLAN_MISMATCH.",
                    "diagnose": [
                        "show interfaces trunk"
                    ],
                    "remediation": [
                        "interface <interface_name>",
                        "switchport trunk allowed vlan add <vlan_id>",
                        "switchport trunk native vlan <vlan_id>"
                    ]
                },
                {
                    "name": "Spanning Tree (STP) Loops & PortFast",
                    "symptom": "High CPU usage, flapping MAC tables, or port err-disabled by BPDU Guard.",
                    "diagnose": [
                        "show spanning-tree"
                    ],
                    "remediation": [
                        "interface <interface_name>",
                        "shutdown",
                        "no shutdown"
                    ]
                }
            ]
        },
        {
            "layer": "2. LAYER 3: IP GATEWAYS, DHCP & ROUTING",
            "topics": [
                {
                    "name": "Default Gateway Configuration",
                    "symptom": "Host cannot reach external subnets, but can ping local hosts.",
                    "diagnose": [
                        "show ip route"
                    ],
                    "remediation": [
                        "interface vlan <vlan_id>",
                        "ip address <ip_addr> <subnet_mask>",
                        "no shutdown"
                    ]
                },
                {
                    "name": "DHCP Relay (ip helper-address)",
                    "symptom": "Hosts fail to get DHCP IP addresses (receive 169.254.x.x link-local).",
                    "diagnose": [
                        "show ip interface <interface_name>"
                    ],
                    "remediation": [
                        "interface <gateway_interface>",
                        "ip helper-address <dhcp_server_ip>"
                    ]
                },
                {
                    "name": "Dynamic Routing (OSPF & EIGRP) Neighbors",
                    "symptom": "Routing tables are empty; route advertisements are missing.",
                    "diagnose": [
                        "show ip ospf neighbor",
                        "show ip protocols"
                    ],
                    "remediation": [
                        "Verify hello/dead timers are identical on both ends.",
                        "Verify subnet masks and OSPF area match on connection interfaces.",
                        "Ensure active interface is not marked as passive:",
                        "router ospf <process_id>",
                        "no passive-interface <interface_name>"
                    ]
                }
            ]
        },
        {
            "layer": "3. LAYER 4: TRAFFIC SECURITY (ACLS)",
            "topics": [
                {
                    "name": "Access Control List (ACL) Blocks",
                    "symptom": "Pings fail one-way, or specific services (HTTP/SSH) are unreachable.",
                    "diagnose": [
                        "show access-lists",
                        "show ip interface <interface_name>"
                    ],
                    "remediation": [
                        "Remember the implicit 'deny any any' at the end.",
                        "Make sure to permit return traffic (e.g., established TCP traffic or ICMP echo-replies):",
                        "ip access-list extended <acl_name>",
                        "permit tcp any any established",
                        "permit icmp any any echo-reply"
                    ]
                }
            ]
        },
        {
            "layer": "4. LAYER 7 / APPS: NAT, DNS & SSH",
            "topics": [
                {
                    "name": "NAT Overload (PAT) Issues",
                    "symptom": "Internal hosts cannot access the public internet.",
                    "diagnose": [
                        "show ip nat translations",
                        "show ip nat statistics"
                    ],
                    "remediation": [
                        "Ensure interfaces are designated 'ip nat inside' and 'ip nat outside'.",
                        "Configure translation rule with 'overload':",
                        "ip nat inside source list <acl> interface <outside_int> overload"
                    ]
                }
            ]
        }
    ]
}

def get_guide_markdown() -> str:
    """Format the troubleshooting guide dictionary as a readable string for the GUI."""
    lines = []
    lines.append(f"{TROUBLESHOOTING_GUIDE['title']}")
    lines.append("=" * len(TROUBLESHOOTING_GUIDE['title']))
    lines.append("\nThis guide contains diagnostic flows and recommended Cisco IOS configuration commands to debug and fix common network issues.\n")
    
    for section in TROUBLESHOOTING_GUIDE["sections"]:
        lines.append(f"{section['layer']}")
        lines.append("-" * len(section['layer']))
        
        for topic in section["topics"]:
            lines.append(f"* {topic['name']}:")
            lines.append(f"  - Symptom: {topic['symptom']}")
            
            lines.append("  - Diagnose: Check configuration with:")
            for cmd in topic["diagnose"]:
                lines.append(f"    {cmd}")
                
            lines.append("  - Remediation:")
            for step in topic["remediation"]:
                lines.append(f"    {step}")
            lines.append("") # blank line between topics
            
    return "\n".join(lines)
