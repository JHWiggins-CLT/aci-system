# Facilities Index

> **Simulated data.** This is a portfolio demonstration. All facility IDs, locations, and operational details are fictional and produced by `conversion/scripts/simulate_facility_data.py`. None of these warehouses exist.

## Directory

| ID | Name | State | City | Type | Profile |
|----|------|-------|------|------|---------|
| dal-02 | Dallas Fulfillment 02 | TX | Dallas | Fulfillment | [profiles/dal-02.md](profiles/dal-02.md) |
| hou-01 | Houston Fulfillment 01 | TX | Houston | Fulfillment | [profiles/hou-01.md](profiles/hou-01.md) |
| atl-01 | Atlanta Fulfillment 01 | GA | Atlanta | Fulfillment | [profiles/atl-01.md](profiles/atl-01.md) |
| chr-03 | Charlotte Fulfillment 03 | NC | Charlotte | Fulfillment | [profiles/chr-03.md](profiles/chr-03.md) |
| atl-03 | Atlanta Distribution 03 | GA | Atlanta | Distribution | [profiles/atl-03.md](profiles/atl-03.md) |
| ral-02 | Raleigh Distribution 02 | NC | Raleigh | Distribution | [profiles/ral-02.md](profiles/ral-02.md) |
| chr-05 | Charlotte Cold Storage 05 | NC | Charlotte | Cold Storage | [profiles/chr-05.md](profiles/chr-05.md) |
| sav-01 | Savannah Cold Storage 01 | GA | Savannah | Cold Storage | [profiles/sav-01.md](profiles/sav-01.md) |

## Aliases

How operations actually refers to each site (used for fuzzy match by skills).

| ID | Aliases |
|----|---------|
| dal-02 | "Dallas", "Big D", "DAL2", "DFW Fulfillment", "DF2" |
| hou-01 | "Houston", "H-Town", "HOU1", "Houston FF" |
| atl-01 | "Atlanta", "ATL1", "Atlanta FF", "the A" |
| chr-03 | "Charlotte FF", "CHR3", "Queen City Fulfillment" |
| atl-03 | "ATL Distro", "ATL3", "Atlanta DC" |
| ral-02 | "Raleigh", "RAL2", "Raleigh DC", "Triangle Distro" |
| chr-05 | "Charlotte Cold", "CHR5", "Queen City Cold" |
| sav-01 | "Savannah", "SAV1", "Port City Cold" |

## Peer pairings

Used by `peer_benchmark.sh` and `divergence_analysis.sh`. Pairs are operationally comparable (same type, similar scale).

| Pair | Type | Why paired |
|------|------|------------|
| dal-02 ↔ hou-01 | Fulfillment | Texas metro fulfillment, similar SKU mix, similar shift structure |
| atl-01 ↔ chr-03 | Fulfillment | Southeast fulfillment, similar volume tier |
| atl-03 ↔ ral-02 | Distribution | Southeast distribution, similar throughput and equipment footprint |
| chr-05 ↔ sav-01 | Cold Storage | Cold-chain operations, similar refrigeration and dock-door counts |

## State rollups

- **TX**: dal-02, hou-01
- **GA**: atl-01, atl-03, sav-01
- **NC**: chr-03, ral-02, chr-05

## Type rollups

- **Fulfillment**: dal-02, hou-01, atl-01, chr-03
- **Distribution**: atl-03, ral-02
- **Cold Storage**: chr-05, sav-01

## Last reviewed
2026-05-18 — peer pairings confirmed, aliases initialized from simulator.
