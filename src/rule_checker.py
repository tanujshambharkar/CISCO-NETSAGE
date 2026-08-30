"""
NetSage AI — Deterministic Rule Checker
========================================
Validates Cisco IOS configurations for common misconfigurations using regex
and Python's ipaddress module. No AI involved — purely deterministic.

Usage:
    python src/rule_checker.py --config <config_file> [--output <report.json>]

Checks:
    DUP-IP          Duplicate IP addresses across interfaces
    SUBNET-MISMATCH Interfaces on same VLAN/segment with different masks
    MISSING-VLAN    VLAN referenced in port config but not in VLAN database
    SHUTDOWN-INTF   Interfaces in administratively down state
    NO-GATEWAY      Missing default gateway (for host configs)
    TRUNK-NATIVE    Native VLAN mismatch on trunk links
    ACL-NO-PERMIT   ACL without any permit statement (implicit deny-all)
    DHCP-POOL       DHCP pool subnet mismatch with interface subnet

Python 3.10+ | Standard Library only
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Finding:
    """A single rule-check finding."""
    check_id: str
    severity: str
    detail: str
    affected_lines: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuleCheckReport:
    """Complete report from a rule-check run."""
    config_file: str
    total_findings: int
    errors: int
    warnings: int
    info: int
    findings: list[Finding]

    def to_dict(self) -> dict:
        return {
            "config_file": self.config_file,
            "total_findings": self.total_findings,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "findings": [f.to_dict() for f in self.findings],
        }


# ──────────────────────────────────────────────
# Regex Patterns
# ──────────────────────────────────────────────

# Matches: ip address 192.168.1.1 255.255.255.0
RE_IP_ADDRESS = re.compile(
    r"^\s*ip\s+address\s+"
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+"
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
    re.MULTILINE,
)

# Matches: interface GigabitEthernet0/0 or interface FastEthernet0/1 etc.
RE_INTERFACE = re.compile(
    r"^interface\s+([\w/:.]+)",
    re.MULTILINE,
)

# Matches: switchport access vlan 10
RE_ACCESS_VLAN = re.compile(
    r"^\s*switchport\s+access\s+vlan\s+(\d+)",
    re.MULTILINE,
)

# Matches: switchport trunk allowed vlan 1,10,20
RE_TRUNK_ALLOWED = re.compile(
    r"^\s*switchport\s+trunk\s+allowed\s+vlan\s+(.+)",
    re.MULTILINE,
)

# Matches: switchport trunk native vlan 99
RE_TRUNK_NATIVE = re.compile(
    r"^\s*switchport\s+trunk\s+native\s+vlan\s+(\d+)",
    re.MULTILINE,
)

# Matches: VLAN entries in 'show vlan brief' format
# e.g., "10   Sales                            active    Fa0/5, Fa0/6"
RE_VLAN_BRIEF = re.compile(
    r"^(\d+)\s+\S+\s+active",
    re.MULTILINE,
)

# Matches: shutdown (standalone on a line, indented)
RE_SHUTDOWN = re.compile(
    r"^\s+shutdown\s*$",
    re.MULTILINE,
)

# Matches: administratively down in show ip interface brief
RE_ADMIN_DOWN = re.compile(
    r"^(\S+)\s+\S+\s+\S+\s+\S+\s+administratively\s+down",
    re.MULTILINE,
)

# Matches: access-list <num> permit ...
RE_ACL_PERMIT = re.compile(
    r"^\s*(?:access-list\s+\d+\s+permit|(\d+\s+)?permit\s)",
    re.MULTILINE,
)

# Matches: access-list <num> deny ...
RE_ACL_ENTRY = re.compile(
    r"^\s*(?:access-list\s+(\d+)\s+(permit|deny))",
    re.MULTILINE,
)

# Matches: ip access-list standard/extended <name>
RE_NAMED_ACL = re.compile(
    r"^ip\s+access-list\s+(standard|extended)\s+(\S+)",
    re.MULTILINE,
)

# Matches: ip dhcp pool <name>
RE_DHCP_POOL = re.compile(
    r"^ip\s+dhcp\s+pool\s+(\S+)",
    re.MULTILINE,
)

# Matches: network 192.168.1.0 255.255.255.0  (inside DHCP pool)
RE_DHCP_NETWORK = re.compile(
    r"^\s+network\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+"
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
    re.MULTILINE,
)

# Matches: default-router 192.168.1.1
RE_DHCP_GATEWAY = re.compile(
    r"^\s+default-router\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
    re.MULTILINE,
)

# Matches: ip default-gateway 192.168.1.1  (for switches / hosts)
RE_DEFAULT_GATEWAY = re.compile(
    r"^ip\s+default-gateway\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
    re.MULTILINE,
)

# ── New Patterns (Phase 1 expansion) ──────────────────────────

# Matches: ip ospf hello-interval <sec>
RE_OSPF_HELLO = re.compile(
    r"^\s*ip\s+ospf\s+hello-interval\s+(\d+)",
    re.MULTILINE,
)

# Matches: ip ospf dead-interval <sec>
RE_OSPF_DEAD = re.compile(
    r"^\s*ip\s+ospf\s+dead-interval\s+(\d+)",
    re.MULTILINE,
)

# Matches: spanning-tree portfast
RE_PORTFAST = re.compile(
    r"^\s+spanning-tree\s+portfast",
    re.MULTILINE,
)

# Matches: switchport mode trunk
RE_TRUNK_MODE = re.compile(
    r"^\s+switchport\s+mode\s+trunk",
    re.MULTILINE,
)

# Matches: speed 100 / speed auto
RE_SPEED = re.compile(
    r"^\s+speed\s+(\S+)",
    re.MULTILINE,
)

# Matches: duplex full / duplex half / duplex auto
RE_DUPLEX = re.compile(
    r"^\s+duplex\s+(\S+)",
    re.MULTILINE,
)

# Matches: ip access-group <name/num> in|out
RE_ACL_APPLIED = re.compile(
    r"^\s+ip\s+access-group\s+(\S+)\s+(in|out)",
    re.MULTILINE,
)

# Matches: transport input ssh / transport input telnet / transport input all / etc.
RE_TRANSPORT_INPUT = re.compile(
    r"^\s+transport\s+input\s+(.+)",
    re.MULTILINE,
)

# Matches: line vty 0 4 / line vty 0 15
RE_LINE_VTY = re.compile(
    r"^line\s+vty\s+\d+\s+\d+",
    re.MULTILINE,
)

# Matches: ntp server <ip>
RE_NTP_SERVER = re.compile(
    r"^ntp\s+server\s+\S+",
    re.MULTILINE,
)

# Matches: logging buffered / logging host <ip>
RE_LOGGING = re.compile(
    r"^logging\s+(buffered|host)\b",
    re.MULTILINE,
)


# ──────────────────────────────────────────────
# Parser: Extract interface blocks from running-config
# ──────────────────────────────────────────────

@dataclass
class InterfaceBlock:
    """Parsed interface configuration block."""
    name: str
    start_line: int
    end_line: int
    ip_address: str | None = None
    subnet_mask: str | None = None
    access_vlan: int | None = None
    trunk_native_vlan: int | None = None
    trunk_allowed_vlans: list[int] | None = None
    is_shutdown: bool = False
    ospf_hello: int | None = None
    ospf_dead: int | None = None
    has_portfast: bool = False
    is_trunk: bool = False
    speed: str | None = None
    duplex: str | None = None
    acl_applied: list[str] | None = None


def parse_interface_blocks(config_text: str) -> list[InterfaceBlock]:
    """Parse running-config into interface blocks."""
    lines = config_text.splitlines()
    blocks: list[InterfaceBlock] = []
    current_block: InterfaceBlock | None = None

    for i, line in enumerate(lines, start=1):
        # Detect start of a new interface block
        intf_match = RE_INTERFACE.match(line)
        if intf_match:
            if current_block:
                current_block.end_line = i - 1
                blocks.append(current_block)
            current_block = InterfaceBlock(
                name=intf_match.group(1),
                start_line=i,
                end_line=i,
            )
            continue

        # Detect end of block (line starting with '!' or non-indented non-empty)
        if current_block and line and not line.startswith(" ") and not line.startswith("\t"):
            if line.strip() == "!":
                current_block.end_line = i
                blocks.append(current_block)
                current_block = None
                continue
            elif not line.startswith("interface"):
                current_block.end_line = i - 1
                blocks.append(current_block)
                current_block = None

        if not current_block:
            continue

        # Parse attributes within the interface block
        ip_match = RE_IP_ADDRESS.match(line)
        if ip_match:
            current_block.ip_address = ip_match.group(1)
            current_block.subnet_mask = ip_match.group(2)

        access_match = RE_ACCESS_VLAN.match(line)
        if access_match:
            current_block.access_vlan = int(access_match.group(1))

        native_match = RE_TRUNK_NATIVE.match(line)
        if native_match:
            current_block.trunk_native_vlan = int(native_match.group(1))

        allowed_match = RE_TRUNK_ALLOWED.match(line)
        if allowed_match:
            vlan_str = allowed_match.group(1).strip()
            current_block.trunk_allowed_vlans = _parse_vlan_list(vlan_str)

        if RE_SHUTDOWN.match(line):
            current_block.is_shutdown = True

        hello_match = RE_OSPF_HELLO.match(line)
        if hello_match:
            current_block.ospf_hello = int(hello_match.group(1))

        dead_match = RE_OSPF_DEAD.match(line)
        if dead_match:
            current_block.ospf_dead = int(dead_match.group(1))

        if RE_PORTFAST.match(line):
            current_block.has_portfast = True

        if RE_TRUNK_MODE.match(line):
            current_block.is_trunk = True

        speed_match = RE_SPEED.match(line)
        if speed_match:
            current_block.speed = speed_match.group(1)

        duplex_match = RE_DUPLEX.match(line)
        if duplex_match:
            current_block.duplex = duplex_match.group(1)

        acl_app_match = RE_ACL_APPLIED.match(line)
        if acl_app_match:
            if current_block.acl_applied is None:
                current_block.acl_applied = []
            current_block.acl_applied.append(acl_app_match.group(1))

    # Capture the last block
    if current_block:
        current_block.end_line = len(lines)
        blocks.append(current_block)

    return blocks


def _parse_vlan_list(vlan_str: str) -> list[int]:
    """Parse VLAN list strings like '1,10,20-30' into a list of integers."""
    vlans: list[int] = []
    if vlan_str.lower() in ("all", "none"):
        return vlans
    for part in vlan_str.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                vlans.extend(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                vlans.append(int(part))
            except ValueError:
                continue
    return vlans


# ──────────────────────────────────────────────
# Check Implementations
# ──────────────────────────────────────────────

def check_duplicate_ips(blocks: list[InterfaceBlock]) -> list[Finding]:
    """DUP-IP: Detect duplicate IP addresses across interfaces."""
    findings: list[Finding] = []
    ip_map: dict[str, list[tuple[str, int]]] = {}

    for block in blocks:
        if block.ip_address and not block.is_shutdown:
            ip_map.setdefault(block.ip_address, []).append(
                (block.name, block.start_line)
            )

    for ip_addr, interfaces in ip_map.items():
        if len(interfaces) > 1:
            names = ", ".join(f"{name} (line {line})" for name, line in interfaces)
            findings.append(Finding(
                check_id="DUP-IP",
                severity=Severity.ERROR,
                detail=f"Duplicate IP address {ip_addr} found on interfaces: {names}",
                affected_lines=[line for _, line in interfaces],
            ))

    return findings


def check_subnet_mismatch(blocks: list[InterfaceBlock]) -> list[Finding]:
    """SUBNET-MISMATCH: Interfaces with IPs in the same network but different masks."""
    findings: list[Finding] = []
    network_map: dict[str, list[tuple[str, str, str, int]]] = {}

    for block in blocks:
        if block.ip_address and block.subnet_mask:
            try:
                iface = ipaddress.IPv4Interface(
                    f"{block.ip_address}/{block.subnet_mask}"
                )
                net_key = str(iface.network.network_address)
                network_map.setdefault(net_key, []).append(
                    (block.name, block.ip_address, block.subnet_mask, block.start_line)
                )
            except (ValueError, ipaddress.AddressValueError):
                continue

    for net_addr, interfaces in network_map.items():
        masks = set(mask for _, _, mask, _ in interfaces)
        if len(masks) > 1:
            details = "; ".join(
                f"{name} ({ip}/{mask})" for name, ip, mask, _ in interfaces
            )
            findings.append(Finding(
                check_id="SUBNET-MISMATCH",
                severity=Severity.ERROR,
                detail=f"Subnet mask mismatch on network {net_addr}: {details}",
                affected_lines=[line for _, _, _, line in interfaces],
            ))

    return findings


def check_missing_vlans(
    blocks: list[InterfaceBlock], config_text: str
) -> list[Finding]:
    """MISSING-VLAN: VLANs referenced in port config but not in VLAN database."""
    findings: list[Finding] = []

    # Extract defined VLANs from 'show vlan brief' or 'vlan <id>' commands
    defined_vlans: set[int] = set()

    # From show vlan brief style output
    for match in RE_VLAN_BRIEF.finditer(config_text):
        defined_vlans.add(int(match.group(1)))

    # From 'vlan <id>' configuration commands
    for match in re.finditer(r"^vlan\s+(\d+)", config_text, re.MULTILINE):
        defined_vlans.add(int(match.group(1)))

    # VLAN 1 is always implicitly defined
    defined_vlans.add(1)

    # Check referenced VLANs
    referenced_vlans: dict[int, list[tuple[str, int]]] = {}

    for block in blocks:
        if block.access_vlan:
            referenced_vlans.setdefault(block.access_vlan, []).append(
                (block.name, block.start_line)
            )
        if block.trunk_native_vlan:
            referenced_vlans.setdefault(block.trunk_native_vlan, []).append(
                (block.name, block.start_line)
            )
        if block.trunk_allowed_vlans:
            for vlan_id in block.trunk_allowed_vlans:
                referenced_vlans.setdefault(vlan_id, []).append(
                    (block.name, block.start_line)
                )

    for vlan_id, interfaces in referenced_vlans.items():
        if vlan_id not in defined_vlans:
            names = ", ".join(f"{name}" for name, _ in interfaces)
            findings.append(Finding(
                check_id="MISSING-VLAN",
                severity=Severity.ERROR,
                detail=(
                    f"VLAN {vlan_id} is referenced on interface(s) {names} "
                    f"but is not defined in the VLAN database"
                ),
                affected_lines=[line for _, line in interfaces],
            ))

    return findings


def check_shutdown_interfaces(blocks: list[InterfaceBlock]) -> list[Finding]:
    """SHUTDOWN-INTF: Interfaces that are administratively shut down."""
    findings: list[Finding] = []

    for block in blocks:
        if block.is_shutdown:
            # Skip Loopback and Null interfaces
            if block.name.lower().startswith(("loopback", "null")):
                continue
            findings.append(Finding(
                check_id="SHUTDOWN-INTF",
                severity=Severity.WARNING,
                detail=f"Interface {block.name} is administratively shut down",
                affected_lines=[block.start_line],
            ))

    # Also check 'show ip interface brief' style output
    for match in RE_ADMIN_DOWN.finditer(""):
        # This would be populated if show output is included
        pass

    return findings


def check_no_gateway(config_text: str) -> list[Finding]:
    """NO-GATEWAY: Configuration missing a default gateway."""
    findings: list[Finding] = []

    # Check for ip default-gateway command
    has_gateway = RE_DEFAULT_GATEWAY.search(config_text)

    # Check for ip route 0.0.0.0 0.0.0.0 (default route)
    has_default_route = re.search(
        r"^ip\s+route\s+0\.0\.0\.0\s+0\.0\.0\.0\s+\S+",
        config_text,
        re.MULTILINE,
    )

    # Check for default gateway in OSPF/EIGRP (default-information originate)
    has_dynamic_default = re.search(
        r"default-information\s+originate",
        config_text,
        re.MULTILINE,
    )

    if not has_gateway and not has_default_route and not has_dynamic_default:
        findings.append(Finding(
            check_id="NO-GATEWAY",
            severity=Severity.INFO,
            detail=(
                "No default gateway or default route found in configuration. "
                "This may be expected for core routers or switches with dynamic routing."
            ),
            affected_lines=[],
        ))

    return findings


def check_trunk_native_vlan(blocks: list[InterfaceBlock]) -> list[Finding]:
    """TRUNK-NATIVE: Detect native VLAN mismatches across trunk interfaces."""
    findings: list[Finding] = []
    trunk_natives: dict[int, list[tuple[str, int]]] = {}

    for block in blocks:
        if block.trunk_native_vlan is not None:
            trunk_natives.setdefault(block.trunk_native_vlan, []).append(
                (block.name, block.start_line)
            )

    native_vlans_used = list(trunk_natives.keys())
    if len(native_vlans_used) > 1:
        details_parts = []
        all_lines = []
        for vlan_id, interfaces in trunk_natives.items():
            names = ", ".join(name for name, _ in interfaces)
            details_parts.append(f"VLAN {vlan_id} on {names}")
            all_lines.extend(line for _, line in interfaces)

        findings.append(Finding(
            check_id="TRUNK-NATIVE",
            severity=Severity.ERROR,
            detail=(
                f"Native VLAN mismatch detected across trunk ports: "
                f"{'; '.join(details_parts)}"
            ),
            affected_lines=all_lines,
        ))

    return findings


def check_acl_no_permit(config_text: str) -> list[Finding]:
    """ACL-NO-PERMIT: ACLs that have no permit statement (implicit deny-all)."""
    findings: list[Finding] = []

    # Track numbered ACLs
    numbered_acls: dict[str, dict[str, bool]] = {}
    for match in RE_ACL_ENTRY.finditer(config_text):
        acl_num = match.group(1)
        action = match.group(2)
        if acl_num not in numbered_acls:
            numbered_acls[acl_num] = {"has_permit": False, "has_deny": False}
        if action == "permit":
            numbered_acls[acl_num]["has_permit"] = True
        elif action == "deny":
            numbered_acls[acl_num]["has_deny"] = True

    for acl_num, info in numbered_acls.items():
        if not info["has_permit"]:
            # Find the line number of the first ACL entry
            acl_match = re.search(
                rf"^(\s*access-list\s+{re.escape(acl_num)}\s+)",
                config_text,
                re.MULTILINE,
            )
            line_num = (
                config_text[: acl_match.start()].count("\n") + 1
                if acl_match
                else 0
            )
            findings.append(Finding(
                check_id="ACL-NO-PERMIT",
                severity=Severity.ERROR,
                detail=(
                    f"ACL {acl_num} has no permit statement; "
                    f"all traffic will be denied by implicit deny at the end"
                ),
                affected_lines=[line_num] if line_num else [],
            ))

    # Track named ACLs
    named_sections = re.split(
        r"^ip\s+access-list\s+(standard|extended)\s+(\S+)",
        config_text,
        flags=re.MULTILINE,
    )
    # named_sections: ['before', 'type', 'name', 'body', 'type', 'name', 'body', ...]
    i = 1
    while i + 2 < len(named_sections):
        acl_type = named_sections[i]
        acl_name = named_sections[i + 1]
        acl_body = named_sections[i + 2]
        i += 3

        # Check if body has any permit
        if not re.search(r"^\s*\d*\s*permit\s", acl_body, re.MULTILINE):
            if re.search(r"^\s*\d*\s*deny\s", acl_body, re.MULTILINE):
                findings.append(Finding(
                    check_id="ACL-NO-PERMIT",
                    severity=Severity.ERROR,
                    detail=(
                        f"Named {acl_type} ACL '{acl_name}' has no permit statement; "
                        f"all traffic will be denied"
                    ),
                    affected_lines=[],
                ))

    return findings


def check_dhcp_pool_subnet(
    blocks: list[InterfaceBlock], config_text: str
) -> list[Finding]:
    """DHCP-POOL: Verify DHCP pool subnets match interface subnets."""
    findings: list[Finding] = []

    # Parse DHCP pools
    pool_matches = list(RE_DHCP_POOL.finditer(config_text))

    for idx, pool_match in enumerate(pool_matches):
        pool_name = pool_match.group(1)
        # Get the text between this pool and the next pool (or end)
        start = pool_match.end()
        end = pool_matches[idx + 1].start() if idx + 1 < len(pool_matches) else len(config_text)
        pool_body = config_text[start:end]

        # Find network statement
        net_match = RE_DHCP_NETWORK.search(pool_body)
        if not net_match:
            continue

        pool_network_ip = net_match.group(1)
        pool_mask = net_match.group(2)

        try:
            pool_network = ipaddress.IPv4Network(
                f"{pool_network_ip}/{pool_mask}", strict=False
            )
        except (ValueError, ipaddress.AddressValueError):
            continue

        # Find default-router
        gw_match = RE_DHCP_GATEWAY.search(pool_body)
        if not gw_match:
            continue

        gateway_ip = gw_match.group(1)

        try:
            gw_addr = ipaddress.IPv4Address(gateway_ip)
        except (ValueError, ipaddress.AddressValueError):
            continue

        # Check if gateway is within the pool's network
        if gw_addr not in pool_network:
            line_num = config_text[: pool_match.start()].count("\n") + 1
            findings.append(Finding(
                check_id="DHCP-POOL",
                severity=Severity.ERROR,
                detail=(
                    f"DHCP pool '{pool_name}' default-router {gateway_ip} "
                    f"is not within pool network {pool_network}"
                ),
                affected_lines=[line_num],
            ))
            continue

        # Check if any interface matches this subnet
        matched = False
        for block in blocks:
            if block.ip_address and block.subnet_mask:
                try:
                    iface_network = ipaddress.IPv4Network(
                        f"{block.ip_address}/{block.subnet_mask}", strict=False
                    )
                    if iface_network == pool_network:
                        matched = True
                        break
                except (ValueError, ipaddress.AddressValueError):
                    continue

        if not matched:
            line_num = config_text[: pool_match.start()].count("\n") + 1
            findings.append(Finding(
                check_id="DHCP-POOL",
                severity=Severity.WARNING,
                detail=(
                    f"DHCP pool '{pool_name}' network {pool_network} does not match "
                    f"any interface subnet (may require ip helper-address on remote router)"
                ),
                affected_lines=[line_num],
            ))

    return findings


# ──────────────────────────────────────────────
# New Checks (Phase 1 expansion)
# ──────────────────────────────────────────────

def check_ospf_timer_mismatch(blocks: list[InterfaceBlock]) -> list[Finding]:
    """OSPF-TIMER: Detect OSPF hello/dead timer mismatches across interfaces in same area."""
    findings: list[Finding] = []
    ospf_interfaces: list[tuple[str, int, int, int]] = []  # name, hello, dead, line

    for block in blocks:
        if block.ospf_hello is not None or block.ospf_dead is not None:
            hello = block.ospf_hello if block.ospf_hello is not None else 10
            dead = block.ospf_dead if block.ospf_dead is not None else 40
            ospf_interfaces.append((block.name, hello, dead, block.start_line))

    if len(ospf_interfaces) < 2:
        return findings

    # Check for dead != 4 * hello (common misconfiguration)
    for name, hello, dead, line in ospf_interfaces:
        if dead != hello * 4:
            findings.append(Finding(
                check_id="OSPF-TIMER",
                severity=Severity.WARNING,
                detail=(
                    f"Interface {name} has OSPF hello={hello}s, dead={dead}s; "
                    f"dead interval is typically 4× hello ({hello * 4}s)"
                ),
                affected_lines=[line],
            ))

    # Check for mismatched timers across interfaces
    hello_values = set(h for _, h, _, _ in ospf_interfaces)
    if len(hello_values) > 1:
        details = "; ".join(
            f"{name} hello={hello}s" for name, hello, _, _ in ospf_interfaces
        )
        findings.append(Finding(
            check_id="OSPF-TIMER",
            severity=Severity.ERROR,
            detail=f"OSPF hello timer mismatch across interfaces: {details}",
            affected_lines=[line for _, _, _, line in ospf_interfaces],
        ))

    return findings


def check_stp_portfast_trunk(blocks: list[InterfaceBlock]) -> list[Finding]:
    """STP-PORTFAST: PortFast enabled on trunk ports is dangerous."""
    findings: list[Finding] = []

    for block in blocks:
        if block.has_portfast and block.is_trunk:
            findings.append(Finding(
                check_id="STP-PORTFAST",
                severity=Severity.ERROR,
                detail=(
                    f"Interface {block.name} has spanning-tree portfast enabled on a "
                    f"trunk port; this can cause STP loops and network instability"
                ),
                affected_lines=[block.start_line],
            ))

    return findings


def check_duplex_mismatch(blocks: list[InterfaceBlock]) -> list[Finding]:
    """INTF-DUPLEX: Detect speed/duplex mismatch across connected interfaces."""
    findings: list[Finding] = []

    for block in blocks:
        if block.speed and block.duplex:
            # Flag hard-coded half-duplex with high speed
            if block.duplex == "half" and block.speed in ("1000", "100"):
                findings.append(Finding(
                    check_id="INTF-DUPLEX",
                    severity=Severity.WARNING,
                    detail=(
                        f"Interface {block.name} is set to speed {block.speed} "
                        f"with half-duplex; this may cause excessive collisions "
                        f"and poor throughput"
                    ),
                    affected_lines=[block.start_line],
                ))
        elif block.speed and not block.duplex:
            if block.speed != "auto":
                findings.append(Finding(
                    check_id="INTF-DUPLEX",
                    severity=Severity.INFO,
                    detail=(
                        f"Interface {block.name} has speed {block.speed} hard-coded "
                        f"but duplex is not explicitly set; auto-negotiation mismatch possible"
                    ),
                    affected_lines=[block.start_line],
                ))
        elif block.duplex and not block.speed:
            if block.duplex != "auto":
                findings.append(Finding(
                    check_id="INTF-DUPLEX",
                    severity=Severity.INFO,
                    detail=(
                        f"Interface {block.name} has duplex {block.duplex} hard-coded "
                        f"but speed is not explicitly set; auto-negotiation mismatch possible"
                    ),
                    affected_lines=[block.start_line],
                ))

    return findings


def check_unused_acl(blocks: list[InterfaceBlock], config_text: str) -> list[Finding]:
    """UNUSED-ACL: ACLs defined but not applied to any interface."""
    findings: list[Finding] = []

    # Collect all ACLs applied on interfaces
    applied_acls: set[str] = set()
    for block in blocks:
        if block.acl_applied:
            applied_acls.update(block.acl_applied)

    # Also check for NAT source list references
    for match in re.finditer(r"ip\s+nat\s+inside\s+source\s+list\s+(\S+)", config_text):
        applied_acls.add(match.group(1))

    # Find all defined numbered ACLs
    defined_numbered: set[str] = set()
    for match in RE_ACL_ENTRY.finditer(config_text):
        defined_numbered.add(match.group(1))

    # Find all defined named ACLs
    defined_named: set[str] = set()
    for match in RE_NAMED_ACL.finditer(config_text):
        defined_named.add(match.group(2))

    all_defined = defined_numbered | defined_named

    for acl_id in all_defined:
        if acl_id not in applied_acls:
            # Find the line number
            acl_match = re.search(
                rf"^(?:ip\s+access-list\s+\S+\s+{re.escape(acl_id)}|access-list\s+{re.escape(acl_id)})",
                config_text,
                re.MULTILINE,
            )
            line_num = (
                config_text[: acl_match.start()].count("\n") + 1
                if acl_match
                else 0
            )
            findings.append(Finding(
                check_id="UNUSED-ACL",
                severity=Severity.WARNING,
                detail=(
                    f"ACL '{acl_id}' is defined but not applied to any interface "
                    f"or referenced in NAT/route-map configuration"
                ),
                affected_lines=[line_num] if line_num else [],
            ))

    return findings


def check_no_ssh(config_text: str) -> list[Finding]:
    """NO-SSH: VTY lines allowing only Telnet without SSH is a security risk."""
    findings: list[Finding] = []

    # Check if VTY lines exist
    vty_matches = list(RE_LINE_VTY.finditer(config_text))
    if not vty_matches:
        return findings

    for vty_match in vty_matches:
        # Get the block after this line vty statement
        start = vty_match.end()
        # Find the next top-level command (non-indented line)
        next_block = re.search(r"\n\S", config_text[start:])
        end = start + next_block.start() if next_block else len(config_text)
        vty_body = config_text[start:end]

        transport_match = RE_TRANSPORT_INPUT.search(vty_body)
        if transport_match:
            transport_value = transport_match.group(1).strip().lower()
            if transport_value == "telnet":
                line_num = config_text[: vty_match.start()].count("\n") + 1
                findings.append(Finding(
                    check_id="NO-SSH",
                    severity=Severity.WARNING,
                    detail=(
                        f"VTY lines ({vty_match.group().strip()}) configured with "
                        f"'transport input telnet' only; SSH is not enabled — "
                        f"credentials are sent in plaintext"
                    ),
                    affected_lines=[line_num],
                ))
        else:
            # No transport input means default (all) which includes telnet
            line_num = config_text[: vty_match.start()].count("\n") + 1
            findings.append(Finding(
                check_id="NO-SSH",
                severity=Severity.INFO,
                detail=(
                    f"VTY lines ({vty_match.group().strip()}) have no explicit "
                    f"'transport input' configured; defaults to all protocols "
                    f"including insecure Telnet"
                ),
                affected_lines=[line_num],
            ))

    return findings


def check_logging_missing(config_text: str) -> list[Finding]:
    """LOGGING-MISSING: No logging buffered or logging host configured."""
    findings: list[Finding] = []

    if not RE_LOGGING.search(config_text):
        findings.append(Finding(
            check_id="LOGGING-MISSING",
            severity=Severity.INFO,
            detail=(
                "No 'logging buffered' or 'logging host' configured; "
                "system logs may be lost on reboot or unavailable for "
                "remote troubleshooting"
            ),
            affected_lines=[],
        ))

    return findings


def check_no_ntp(config_text: str) -> list[Finding]:
    """NO-NTP: No NTP server configured for time synchronization."""
    findings: list[Finding] = []

    if not RE_NTP_SERVER.search(config_text):
        findings.append(Finding(
            check_id="NO-NTP",
            severity=Severity.INFO,
            detail=(
                "No 'ntp server' configured; device clock may drift, "
                "causing inaccurate log timestamps and certificate "
                "validation issues"
            ),
            affected_lines=[],
        ))

    return findings


# ──────────────────────────────────────────────
# Main Runner
# ──────────────────────────────────────────────

def run_all_checks(config_text: str, config_file: str = "<stdin>") -> RuleCheckReport:
    """Execute all rule checks and return a consolidated report."""
    blocks = parse_interface_blocks(config_text)

    all_findings: list[Finding] = []

    # Run each check
    all_findings.extend(check_duplicate_ips(blocks))
    all_findings.extend(check_subnet_mismatch(blocks))
    all_findings.extend(check_missing_vlans(blocks, config_text))
    all_findings.extend(check_shutdown_interfaces(blocks))
    all_findings.extend(check_no_gateway(config_text))
    all_findings.extend(check_trunk_native_vlan(blocks))
    all_findings.extend(check_acl_no_permit(config_text))
    all_findings.extend(check_dhcp_pool_subnet(blocks, config_text))

    # Phase 1 expansion checks
    all_findings.extend(check_ospf_timer_mismatch(blocks))
    all_findings.extend(check_stp_portfast_trunk(blocks))
    all_findings.extend(check_duplex_mismatch(blocks))
    all_findings.extend(check_unused_acl(blocks, config_text))
    all_findings.extend(check_no_ssh(config_text))
    all_findings.extend(check_logging_missing(config_text))
    all_findings.extend(check_no_ntp(config_text))

    # Build report
    errors = sum(1 for f in all_findings if f.severity == Severity.ERROR)
    warnings = sum(1 for f in all_findings if f.severity == Severity.WARNING)
    info = sum(1 for f in all_findings if f.severity == Severity.INFO)

    return RuleCheckReport(
        config_file=config_file,
        total_findings=len(all_findings),
        errors=errors,
        warnings=warnings,
        info=info,
        findings=all_findings,
    )


def print_report(report: RuleCheckReport) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 70)
    print("  NetSage AI -- Deterministic Rule Checker Report")
    print("=" * 70)
    print(f"  Config File : {report.config_file}")
    print(f"  Total Findings : {report.total_findings}")
    print(f"  Errors         : {report.errors}")
    print(f"  Warnings       : {report.warnings}")
    print(f"  Info           : {report.info}")
    print("=" * 70)

    if not report.findings:
        print("\n  [OK] No issues detected.\n")
        return

    for i, finding in enumerate(report.findings, start=1):
        severity_icon = {
            Severity.ERROR: "[ERR]",
            Severity.WARNING: "[WARN]",
            Severity.INFO: "[INFO]",
        }.get(finding.severity, "[?]")

        print(f"\n  [{i}] {severity_icon} {finding.check_id} ({finding.severity})")
        print(f"      {finding.detail}")
        if finding.affected_lines:
            print(f"      Lines: {finding.affected_lines}")

    print("\n" + "=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NetSage AI — Deterministic Rule Checker",
        epilog="Validates Cisco IOS configurations for common misconfigurations.",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to the configuration text file to validate.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON report (default: stdout only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output to stdout instead of human-readable format.",
    )

    args = parser.parse_args()

    # Read config file
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    config_text = args.config.read_text(encoding="utf-8")
    report = run_all_checks(config_text, config_file=str(args.config))

    # Output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    # Write JSON report if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"\n  [OK] JSON report written to: {args.output}")

    # Exit with non-zero code if errors found
    if report.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
