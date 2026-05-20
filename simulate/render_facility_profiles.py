#!/usr/bin/env python3
"""Render the 8 facility profile files from the template + facility config.

Demonstrates the maintain-skill pattern: copy a template, substitute fields,
write the file. Idempotent — safe to re-run.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".skills" / "maintain" / "templates" / "facility_profile.md"
OUT_DIR = ROOT / "data" / "facilities" / "profiles"

FACILITIES = [
    {
        "ID": "dal-02", "NAME": "Dallas Fulfillment 02", "TYPE": "Fulfillment",
        "CITY": "Dallas", "STATE": "TX", "PEER_ID": "hou-01",
        "HEADCOUNT": "420", "SHIFTS": "3 shifts, 24/6 operating week",
        "OP_DAYS": "Mon-Sat (Sun dark)",
        "SKU_MIX": "consumer goods, mid-velocity dry, multi-SKU orders (~30% complex)",
        "EQUIPMENT": "12 conveyor lines, 28 powered MHE units, RF/scanner-driven WMS",
        "CPH_TARGET": "140",
        "ERROR_TARGET": "2.5",
        "UNITS_TYPICAL": "24,000-28,000",
        "HOURS_TYPICAL": "62-68",
        "CONTEXT_NOTES": (
            "Largest Texas fulfillment node. Recurring cohort-driven throughput "
            "dips through the year as hiring waves backfill attrition. Cold-pick "
            "zone (zone 4) is a known training pain point."
        ),
    },
    {
        "ID": "hou-01", "NAME": "Houston Fulfillment 01", "TYPE": "Fulfillment",
        "CITY": "Houston", "STATE": "TX", "PEER_ID": "dal-02",
        "HEADCOUNT": "380", "SHIFTS": "3 shifts, 24/6 operating week",
        "OP_DAYS": "Mon-Sat (Sun dark)",
        "SKU_MIX": "consumer goods, slightly heavier durable goods than dal-02",
        "EQUIPMENT": "10 conveyor lines, 24 powered MHE units, RF/scanner-driven WMS",
        "CPH_TARGET": "135",
        "ERROR_TARGET": "2.5",
        "UNITS_TYPICAL": "21,000-25,000",
        "HOURS_TYPICAL": "58-64",
        "CONTEXT_NOTES": (
            "Smaller Texas fulfillment node. Reliable throughput; tends to absorb "
            "spill from dal-02 during dal-02 incidents."
        ),
    },
    {
        "ID": "atl-01", "NAME": "Atlanta Fulfillment 01", "TYPE": "Fulfillment",
        "CITY": "Atlanta", "STATE": "GA", "PEER_ID": "chr-03",
        "HEADCOUNT": "350", "SHIFTS": "3 shifts, 24/6 operating week",
        "OP_DAYS": "Mon-Sat (Sun dark)",
        "SKU_MIX": "consumer goods, southeast demand profile, ~25% complex orders",
        "EQUIPMENT": "11 conveyor lines, 26 powered MHE units, modern WMS (released 2025-Q4)",
        "CPH_TARGET": "138",
        "ERROR_TARGET": "2.5",
        "UNITS_TYPICAL": "20,000-24,000",
        "HOURS_TYPICAL": "56-62",
        "CONTEXT_NOTES": (
            "Reference site for the 2025-Q4 WMS release. Tends to set the pace "
            "for southeast fulfillment KPIs."
        ),
    },
    {
        "ID": "chr-03", "NAME": "Charlotte Fulfillment 03", "TYPE": "Fulfillment",
        "CITY": "Charlotte", "STATE": "NC", "PEER_ID": "atl-01",
        "HEADCOUNT": "330", "SHIFTS": "3 shifts, 24/6 operating week",
        "OP_DAYS": "Mon-Sat (Sun dark)",
        "SKU_MIX": "consumer goods, similar to atl-01 with marginally more apparel",
        "EQUIPMENT": "10 conveyor lines, 22 powered MHE units, WMS 2025-Q4",
        "CPH_TARGET": "135",
        "ERROR_TARGET": "2.8",
        "UNITS_TYPICAL": "18,000-22,000",
        "HOURS_TYPICAL": "54-60",
        "CONTEXT_NOTES": (
            "Newer leadership team (since 2025-Q3). Trainer bench is thinner "
            "than atl-01 — cohort-driven dips show up here more sharply."
        ),
    },
    {
        "ID": "atl-03", "NAME": "Atlanta Distribution 03", "TYPE": "Distribution",
        "CITY": "Atlanta", "STATE": "GA", "PEER_ID": "ral-02",
        "HEADCOUNT": "220", "SHIFTS": "2 shifts, 16/6",
        "OP_DAYS": "Mon-Sat",
        "SKU_MIX": "pallet/case-level outbound, low SKU complexity",
        "EQUIPMENT": "8 dock doors per side, 14 reach trucks, 6 fixed scanners, no full WMS",
        "CPH_TARGET": "92",
        "ERROR_TARGET": "1.5",
        "UNITS_TYPICAL": "36,000-42,000",
        "HOURS_TYPICAL": "30-34",
        "CONTEXT_NOTES": (
            "Pure DC operation — cases/pallets in and out. Equipment uptime "
            "(reach trucks, dock-door doors) dominates the diagnostic picture."
        ),
    },
    {
        "ID": "ral-02", "NAME": "Raleigh Distribution 02", "TYPE": "Distribution",
        "CITY": "Raleigh", "STATE": "NC", "PEER_ID": "atl-03",
        "HEADCOUNT": "200", "SHIFTS": "2 shifts, 16/6",
        "OP_DAYS": "Mon-Sat",
        "SKU_MIX": "pallet/case-level outbound, slightly higher SKU mix than atl-03",
        "EQUIPMENT": "7 dock doors per side, 12 reach trucks, 6 fixed scanners",
        "CPH_TARGET": "90",
        "ERROR_TARGET": "1.6",
        "UNITS_TYPICAL": "32,000-38,000",
        "HOURS_TYPICAL": "28-32",
        "CONTEXT_NOTES": (
            "Triangle-region DC. Older reach truck fleet — equipment downtime "
            "minutes typically higher than atl-03."
        ),
    },
    {
        "ID": "chr-05", "NAME": "Charlotte Cold Storage 05", "TYPE": "Cold Storage",
        "CITY": "Charlotte", "STATE": "NC", "PEER_ID": "sav-01",
        "HEADCOUNT": "160", "SHIFTS": "2 shifts, 16/6",
        "OP_DAYS": "Mon-Sat",
        "SKU_MIX": "frozen and refrigerated CPG, narrow SKU set",
        "EQUIPMENT": "4 refrigeration zones, 10 reach trucks (cold-rated), thermal scanners",
        "CPH_TARGET": "72",
        "ERROR_TARGET": "1.0",
        "UNITS_TYPICAL": "10,000-13,000",
        "HOURS_TYPICAL": "26-30",
        "CONTEXT_NOTES": (
            "Cold-chain operation. Temperature excursions and refrigeration "
            "downtime are leading indicators for damage and lost-inventory spikes."
        ),
    },
    {
        "ID": "sav-01", "NAME": "Savannah Cold Storage 01", "TYPE": "Cold Storage",
        "CITY": "Savannah", "STATE": "GA", "PEER_ID": "chr-05",
        "HEADCOUNT": "150", "SHIFTS": "2 shifts, 16/6",
        "OP_DAYS": "Mon-Sat",
        "SKU_MIX": "frozen and refrigerated CPG, port-adjacent import flow",
        "EQUIPMENT": "5 refrigeration zones, 9 reach trucks (cold-rated), thermal scanners",
        "CPH_TARGET": "70",
        "ERROR_TARGET": "1.0",
        "UNITS_TYPICAL": "10,000-12,500",
        "HOURS_TYPICAL": "26-30",
        "CONTEXT_NOTES": (
            "Port-adjacent cold storage; inbound volume spikes when ocean freight "
            "lands. Newer refrigeration plant than chr-05."
        ),
    },
]


def render(template: str, values: dict) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    review_date = "2026-05-18"
    for fac in FACILITIES:
        fac = {**fac, "REVIEW_DATE": review_date}
        rendered = render(template, fac)
        out = OUT_DIR / f"{fac['ID']}.md"
        out.write_text(rendered, encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
