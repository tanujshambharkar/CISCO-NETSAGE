# Cisco Packet Tracer Lab Environment — NetSage AI

This directory contains the Cisco IOS network configurations, topology definitions, and fault-injection scenarios used in the **NetSage AI** project.

---

## 1. Network Topology Architecture

The lab models a multi-tier Enterprise Branch and Campus network designed for Cisco Packet Tracer:

```
                          [ Internet / ISP ]
                                  | (Gi0/0/0: 203.0.113.1/30)
                                  |
                      +-----------v-----------+
                      |   R1 - Core Router    | (PAT / NAT Overload, OSPF Area 0, DHCP Relay)
                      +-----------+-----------+
                                  | (Gi0/0/1: 192.168.100.1/30)
                                  |
                                  | (Gi0/0/1: 192.168.100.2/30)
                      +-----------v-----------+
                      |   R2 - Branch Router  | (OSPF Area 0, Inter-VLAN Routing)
                      +-----------+-----------+
                                  | (Gi0/1 Trunk: 802.1Q Native VLAN 99)
                                  |
                      +-----------v-----------+
                      | SW1 - Core/Dist Switch| (Layer 2 Trunking, Management VLAN 99)
                      +-----+-----------+-----+
                            |           |
            (Fa0/1 Trunk)   |           | (Fa0/2 Trunk)
                            |           |
               +------------v--+     +--v------------+
               | SW2 - Access1 |     | SW3 - Access2 |
               +-------+-------+     +-------+-------+
                       |                     |
           +-----------+-----------+         |
           |                       |         |
     +-----v-----+           +-----v-----+   |   +-----------+
     |   PC-1    |           |   PC-2    |   +-->| WLC 2504  |
     | (VLAN 10) |           | (VLAN 20) |       +-----+-----+
     | Finance   |           | Sales     |             | (LAP-1 / LAP-2)
     +-----------+           +-----------+       +-----v-----+
                                                 | CorpWiFi  |
                                                 | (Laptop)  |
                                                 +-----------+
```

---

## 2. IP Addressing Matrix

| Device | Interface | IP Address | Subnet Mask | Description / VLAN |
|---|---|---|---|---|
| **R1 (Edge)** | Gi0/0/0 | 203.0.113.2 | 255.255.255.252 | WAN Link to ISP |
| **R1 (Edge)** | Gi0/0/1 | 192.168.100.1 | 255.255.255.252 | Point-to-Point Link to R2 |
| **R1 (Edge)** | Loopback0 | 1.1.1.1 | 255.255.255.255 | OSPF Router-ID |
| **R2 (Branch)** | Gi0/0/1 | 192.168.100.2 | 255.255.255.252 | Point-to-Point Link to R1 |
| **R2 (Branch)** | Gi0/0/0.10 | 192.168.10.1 | 255.255.255.0 | Sub-interface VLAN 10 (Finance) |
| **R2 (Branch)** | Gi0/0/0.20 | 192.168.20.1 | 255.255.255.0 | Sub-interface VLAN 20 (Sales) |
| **R2 (Branch)** | Gi0/0/0.30 | 192.168.30.1 | 255.255.255.0 | Sub-interface VLAN 30 (Engineering) |
| **R2 (Branch)** | Gi0/0/0.99 | 192.168.99.1 | 255.255.255.0 | Sub-interface VLAN 99 (Management/Native) |
| **SW1 (Core)** | VLAN 99 | 192.168.99.10 | 255.255.255.0 | Core Switch Management SVI |
| **SW2 (Access)**| VLAN 99 | 192.168.99.20 | 255.255.255.0 | Access Switch 1 Management SVI |
| **WLC 2504** | Management | 192.168.99.50 | 255.255.255.0 | Wireless Controller Management |
| **DNS/Web Server** | Gi0/0 | 192.168.10.50 | 255.255.255.0 | Internal DNS & Web Services |

---

## 3. Directory Contents

- `baseline_configs/`: Gold-standard, verified working Cisco IOS configurations.
  - `R1_Core_Router.cfg`
  - `R2_Branch_Router.cfg`
  - `SW1_Core_Switch.cfg`
  - `SW2_Access_Switch.cfg`
  - `WLC_Config.cfg`
- `fault_scenarios/`: 8 category-wise fault injection configurations matching the 30 benchmark cases in `cases.csv`.
  - `01_vlan_trunk_faults.cfg`
  - `02_gateway_subnet_faults.cfg`
  - `03_dhcp_relay_faults.cfg`
  - `04_dns_name_resolution_faults.cfg`
  - `05_ospf_routing_faults.cfg`
  - `06_extended_acl_faults.cfg`
  - `07_nat_pat_overload_faults.cfg`
  - `08_wireless_wpa2_faults.cfg`
- `verify_lab.py`: Python automation utility to test all configs against the NetSage rule checker.

---

## 4. How to Load and Test in Cisco Packet Tracer

1. Launch **Cisco Packet Tracer** (v8.0 or newer).
2. Create the devices (Cisco 2911 / 4321 Routers, 2960 / 3560 Switches, 2504 WLC, Lightweight APs, PCs).
3. Open the CLI tab of each device and copy-paste the corresponding configuration from `baseline_configs/`.
4. To test a specific troubleshooting case, copy the snippet from `fault_scenarios/` and paste it into the target device CLI.
5. Save the running configuration (`show run`) and feed it into `python src/rule_checker.py --config <file>` or submit the diagnostic output to the NetSage AI prompt.
