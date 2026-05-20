#!/usr/bin/env python3
"""Deterministic simulator for the 8-facility portfolio dataset.

Plays the role of a conversion script. Instead of reading an Excel file from
operations and extracting it, this script generates the canonical CSV that
operations *would have* produced — using a seeded RNG so the same seed always
yields the same data. The output is then validated against the schema before
being written into `data/metrics/` and `data/events/`. If validation fails,
no canonical file is written and a failure log lands in `conversion/logs/`.

The simulated data is shaped to support real investigations:
  * a new-hire cohort throughput dip at dal-02 in March
  * an SOP-change-driven damage spike at chr-03 in April
  * an equipment-driven throughput drop at ral-02 in late April
  * a refrigeration excursion at chr-05 causing a damage spike in March
  * background day-of-week patterns, weekly volume rhythm, and seasonality

Run as:    python conversion/scripts/simulate_facility_data.py
Run with:  python conversion/scripts/simulate_facility_data.py --seed 42
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "conversion"))
from validation.common import (  # noqa: E402
    SCHEMAS,
    ValidationReport,
    assert_passed,
    read_csv,
    validate_events_file,
    validate_metric_family,
    write_csv_atomic,
)

DATA_DIR = REPO_ROOT / "data"
METRICS_DIR = DATA_DIR / "metrics"
EVENTS_DIR = DATA_DIR / "events"


# --- Facility configuration --------------------------------------------------

@dataclass
class FacilityConfig:
    facility_id: str
    type: str  # Fulfillment | Distribution | Cold Storage
    cph_target: float
    cph_sigma: float
    error_rate_base: float  # per 1000 units
    error_rate_sigma: float
    units_typical: int
    units_sigma: int
    hours_typical: float
    hours_sigma: float
    headcount_total: int
    headcount_new_pct: float
    shift_split: tuple[float, float, float]  # day, evening, night
    inbound_typical: int
    order_mix_complex: float
    conveyor_baseline_down_m: int
    mhe_baseline_down_m: int
    operating_dow: tuple[int, ...] = (0, 1, 2, 3, 4, 5)  # Mon-Sat


FACILITIES: list[FacilityConfig] = [
    FacilityConfig("dal-02", "Fulfillment", 140.0, 4.0, 2.2, 0.4,
                   26_000, 1_800, 64.0, 2.5, 420, 0.06,
                   (0.45, 0.35, 0.20), 27_000, 0.30, 8, 22),
    FacilityConfig("hou-01", "Fulfillment", 135.0, 3.6, 2.3, 0.4,
                   23_000, 1_500, 61.0, 2.4, 380, 0.05,
                   (0.45, 0.35, 0.20), 24_000, 0.28, 6, 20),
    FacilityConfig("atl-01", "Fulfillment", 138.0, 3.4, 2.1, 0.35,
                   22_000, 1_500, 59.0, 2.3, 350, 0.05,
                   (0.45, 0.35, 0.20), 23_000, 0.27, 5, 18),
    FacilityConfig("chr-03", "Fulfillment", 135.0, 3.8, 2.4, 0.5,
                   20_000, 1_400, 57.0, 2.2, 330, 0.07,
                   (0.45, 0.35, 0.20), 21_000, 0.29, 6, 20),
    FacilityConfig("atl-03", "Distribution", 92.0, 2.5, 1.3, 0.25,
                   39_000, 2_500, 32.0, 1.5, 220, 0.04,
                   (0.55, 0.45, 0.00), 41_000, 0.10, 10, 28),
    FacilityConfig("ral-02", "Distribution", 90.0, 2.4, 1.4, 0.25,
                   35_000, 2_200, 30.0, 1.5, 200, 0.04,
                   (0.55, 0.45, 0.00), 37_000, 0.11, 12, 34),
    FacilityConfig("chr-05", "Cold Storage", 72.0, 1.8, 0.9, 0.2,
                   11_500, 900, 28.0, 1.2, 160, 0.03,
                   (0.55, 0.45, 0.00), 12_000, 0.08, 4, 14),
    FacilityConfig("sav-01", "Cold Storage", 70.0, 1.8, 0.9, 0.2,
                   11_000, 850, 28.0, 1.2, 150, 0.03,
                   (0.55, 0.45, 0.00), 11_500, 0.08, 3, 12),
]


# --- Scenarios ---------------------------------------------------------------
# Embedded "stories" the simulator threads through the data so that
# investigations have something real to find.

@dataclass
class Scenario:
    """A named perturbation applied to one facility over a date range."""
    facility_id: str
    name: str
    start: dt.date
    end: dt.date
    cph_mult: float = 1.0            # multiplicative shift on CPH
    error_mult: float = 1.0          # multiplicative shift on error_rate
    mispick_mult: float = 1.0
    damage_mult: float = 1.0
    missort_mult: float = 1.0
    headcount_new_add: int = 0
    conveyor_down_add_m: int = 0
    mhe_down_add_m: int = 0
    wms_incidents_add: int = 0

    def applies(self, day: dt.date) -> bool:
        return self.start <= day <= self.end


SCENARIOS: list[Scenario] = [
    # dal-02 cohort dip — cohort of 6 starts Mar 2; throughput drag Mar 8–22
    Scenario("dal-02", "cohort_throughput_dip",
             dt.date(2026, 3, 8), dt.date(2026, 3, 22),
             cph_mult=0.91, error_mult=1.35, mispick_mult=1.8,
             headcount_new_add=6),
    Scenario("dal-02", "cohort_onboarding_window",
             dt.date(2026, 3, 2), dt.date(2026, 3, 31),
             headcount_new_add=4),

    # chr-03 sop_change driven damage spike — bin relocation Apr 8; impact
    # window Apr 12-Apr 24
    Scenario("chr-03", "bin_relocation_damage",
             dt.date(2026, 4, 12), dt.date(2026, 4, 24),
             damage_mult=2.2, error_mult=1.3, missort_mult=1.5),

    # ral-02 equipment-driven dip — conveyor incident Apr 20, recovery Apr 21-27
    Scenario("ral-02", "conveyor_outage",
             dt.date(2026, 4, 20), dt.date(2026, 4, 27),
             cph_mult=0.86, conveyor_down_add_m=160, mhe_down_add_m=45),
    Scenario("ral-02", "wms_incidents_followup",
             dt.date(2026, 4, 21), dt.date(2026, 4, 25),
             wms_incidents_add=2),

    # --- Equipment-downtime throughput-drag pattern (peers of ral-02) ---
    # Two more instances of the SAME mechanism as ral-02's conveyor outage:
    # CPH drops while equipment downtime spikes, with quality (mispick/error)
    # left roughly flat — the distinguishing signature vs the cohort dip.
    # Together with ral-02 these three cases establish the
    # equipment_downtime_throughput_drag pattern (3+ same-mechanism cases).
    # sav-01 primary-sort MHE drive failure, Mar 9-16.
    Scenario("sav-01", "mhe_failure_throughput_drag",
             dt.date(2026, 3, 9), dt.date(2026, 3, 16),
             cph_mult=0.88, mhe_down_add_m=120, wms_incidents_add=1),
    # atl-03 conveyor gearbox failure, Apr 6-13.
    Scenario("atl-03", "conveyor_failure_throughput_drag",
             dt.date(2026, 4, 6), dt.date(2026, 4, 13),
             cph_mult=0.90, conveyor_down_add_m=150, mhe_down_add_m=30),

    # chr-05 cold-storage temperature excursion mid-March → damage spike
    Scenario("chr-05", "refrigeration_excursion",
             dt.date(2026, 3, 14), dt.date(2026, 3, 17),
             damage_mult=3.0, error_mult=1.6, cph_mult=0.94),

    # atl-01 slow improvement after Q4 WMS release (drift up)
    Scenario("atl-01", "post_wms_uplift",
             dt.date(2026, 3, 1), dt.date(2026, 5, 18),
             cph_mult=1.02, error_mult=0.92),
]


# --- Event seeding -----------------------------------------------------------

@dataclass
class EventSeed:
    facility_id: str | None  # None = network event
    date: dt.date
    event_type: str
    description: str
    source: str = "simulator-seed"


EVENT_SEEDS: list[EventSeed] = [
    # Network events
    EventSeed(None, dt.date(2026, 1, 19), "deployment",
              "WMS 2026.1 minor release across all facilities", "simulator-seed"),
    EventSeed(None, dt.date(2026, 2, 16), "holiday",
              "Presidents' Day observed; reduced inbound flow", "simulator-seed"),
    EventSeed(None, dt.date(2026, 5, 25), "holiday",
              "Memorial Day observed (upcoming, scheduling impact this week)", "simulator-seed"),

    # dal-02 cohort story
    EventSeed("dal-02", dt.date(2026, 3, 2), "training",
              "Cohort of 6 new hires onboarded; 4 to night shift",
              "simulator-seed"),
    EventSeed("dal-02", dt.date(2026, 3, 6), "training",
              "Pick certification week 1 begins for Mar-02 cohort", "simulator-seed"),
    EventSeed("dal-02", dt.date(2026, 2, 9), "audit",
              "Quarterly internal pick-accuracy audit (passed)", "simulator-seed"),
    EventSeed("dal-02", dt.date(2026, 4, 27), "leadership_change",
              "Night shift supervisor change (Reyes → Patel)", "simulator-seed"),

    # chr-03 bin relocation story
    EventSeed("chr-03", dt.date(2026, 4, 8), "sop_change",
              "Bin relocation in zones 3-4 to consolidate high-velocity SKUs",
              "simulator-seed"),
    EventSeed("chr-03", dt.date(2026, 4, 11), "training",
              "Brief team huddles introducing new bin map", "simulator-seed"),
    EventSeed("chr-03", dt.date(2026, 2, 1), "leadership_change",
              "New facility manager (Diaz) starts", "simulator-seed"),

    # ral-02 equipment story
    EventSeed("ral-02", dt.date(2026, 4, 20), "incident",
              "Conveyor line 3 belt failure; partial shutdown 4h", "simulator-seed"),
    EventSeed("ral-02", dt.date(2026, 4, 22), "equipment_install",
              "Replacement belt installed on line 3; commissioning Apr 22-23",
              "simulator-seed"),

    # chr-05 cold-storage story
    EventSeed("chr-05", dt.date(2026, 3, 14), "incident",
              "Refrigeration zone 2 temperature excursion +6°C for 90 min",
              "simulator-seed"),
    EventSeed("chr-05", dt.date(2026, 3, 15), "audit",
              "Cold-chain audit triggered by Mar-14 excursion", "simulator-seed"),

    # Misc routine events for cooccurrence richness
    EventSeed("atl-01", dt.date(2026, 1, 28), "system_change",
              "Scanner firmware update on handheld fleet", "simulator-seed"),
    EventSeed("atl-01", dt.date(2026, 3, 11), "training",
              "Cross-training cohort: 8 associates begin zone rotation",
              "simulator-seed"),
    EventSeed("hou-01", dt.date(2026, 2, 22), "weather",
              "Severe storms; reduced inbound trucks Feb 22-23", "simulator-seed"),
    EventSeed("hou-01", dt.date(2026, 4, 4), "volume_shock",
              "Promotional volume +18% over baseline Apr 4-7", "simulator-seed"),
    EventSeed("sav-01", dt.date(2026, 3, 25), "volume_shock",
              "Container surge from port (3 vessels in 48h)", "simulator-seed"),
    EventSeed("sav-01", dt.date(2026, 4, 18), "system_change",
              "WMS lane-assignment rule update", "simulator-seed"),
    EventSeed("atl-03", dt.date(2026, 2, 26), "equipment_install",
              "Dock door 7 motor replaced", "simulator-seed"),
    EventSeed("atl-03", dt.date(2026, 4, 14), "audit",
              "External transportation audit (advance notice)", "simulator-seed"),

    # Equipment-downtime throughput-drag pattern instances (peers of ral-02)
    EventSeed("sav-01", dt.date(2026, 3, 9), "incident",
              "Primary sort MHE drive failure; degraded throughput ~5h",
              "simulator-seed"),
    EventSeed("sav-01", dt.date(2026, 3, 11), "equipment_install",
              "MHE drive unit replaced on primary sorter", "simulator-seed"),
    EventSeed("atl-03", dt.date(2026, 4, 6), "incident",
              "Conveyor line 2 gearbox failure; partial shutdown",
              "simulator-seed"),
    EventSeed("atl-03", dt.date(2026, 4, 8), "equipment_install",
              "Line 2 gearbox replaced; recommissioned Apr 8", "simulator-seed"),
]


# --- Simulation core ---------------------------------------------------------

START_DATE = dt.date(2026, 1, 19)  # 120 days back from 2026-05-18
END_DATE = dt.date(2026, 5, 18)
EXPECTED_DAYS = 120  # inclusive 2026-01-19 .. 2026-05-18 = 120 days


def daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    return days


def dow_factor(d: dt.date) -> float:
    """Mild Monday-low, Friday-high pattern."""
    return 1.0 + 0.012 * (d.weekday() - 2)


def scenarios_for(facility_id: str, day: dt.date) -> list[Scenario]:
    return [s for s in SCENARIOS
            if s.facility_id == facility_id and s.applies(day)]


def simulate_operational(cfg: FacilityConfig, rng: random.Random,
                         days: list[dt.date]) -> tuple[list[list], list[float]]:
    """Return (rows, cph_series). cph_series is used by other families."""
    rows = []
    cph_series = []
    for day in days:
        if day.weekday() not in cfg.operating_dow:
            continue
        scens = scenarios_for(cfg.facility_id, day)
        cph_mult = math.prod(s.cph_mult for s in scens) if scens else 1.0
        err_mult = math.prod(s.error_mult for s in scens) if scens else 1.0

        cph = rng.gauss(cfg.cph_target, cfg.cph_sigma)
        cph *= dow_factor(day) * cph_mult
        cph = max(cph, cfg.cph_target * 0.6)  # floor

        units = int(rng.gauss(cfg.units_typical, cfg.units_sigma)
                    * dow_factor(day))
        units = max(units, int(cfg.units_typical * 0.4))

        error_rate = max(0.1, rng.gauss(cfg.error_rate_base,
                                        cfg.error_rate_sigma)) * err_mult
        hours_run = max(8.0, rng.gauss(cfg.hours_typical, cfg.hours_sigma))

        rows.append([
            day.isoformat(),
            cfg.facility_id,
            units,
            round(cph, 2),
            round(error_rate, 2),
            round(hours_run, 1),
        ])
        cph_series.append(cph)
    return rows, cph_series


def simulate_inputs(cfg: FacilityConfig, rng: random.Random,
                    days: list[dt.date]) -> list[list]:
    rows = []
    for day in days:
        if day.weekday() not in cfg.operating_dow:
            continue
        scens = scenarios_for(cfg.facility_id, day)
        hc_total = int(rng.gauss(cfg.headcount_total, cfg.headcount_total * 0.03))
        new_base = int(cfg.headcount_total * cfg.headcount_new_pct
                       + rng.gauss(0, cfg.headcount_total * 0.01))
        hc_new = max(0, new_base + sum(s.headcount_new_add for s in scens))
        s1 = int(hc_total * cfg.shift_split[0])
        s2 = int(hc_total * cfg.shift_split[1])
        s3 = hc_total - s1 - s2
        inbound = int(rng.gauss(cfg.inbound_typical,
                                cfg.inbound_typical * 0.08) * dow_factor(day))
        complex_pct = max(0.0, min(1.0, rng.gauss(cfg.order_mix_complex, 0.03)))
        rows.append([
            day.isoformat(),
            cfg.facility_id,
            hc_total, hc_new, s1, s2, s3,
            max(0, inbound),
            round(complex_pct, 3),
        ])
    return rows


def simulate_exceptions(cfg: FacilityConfig, rng: random.Random,
                        days: list[dt.date],
                        units_by_day: dict[dt.date, int]) -> list[list]:
    rows = []
    for day in days:
        if day not in units_by_day:
            continue
        units = units_by_day[day]
        scens = scenarios_for(cfg.facility_id, day)
        damage_mult = math.prod(s.damage_mult for s in scens) if scens else 1.0
        missort_mult = math.prod(s.missort_mult for s in scens) if scens else 1.0
        mispick_mult = math.prod(s.mispick_mult for s in scens) if scens else 1.0

        def draw(base_per_1k: float, mult: float = 1.0) -> int:
            mean = units * base_per_1k / 1000.0 * mult
            return max(0, int(rng.gauss(mean, max(1.0, mean * 0.25))))

        # Distribution-type facilities have lower error denominators
        scale = 0.6 if cfg.type == "Distribution" else 1.0
        cold = 0.7 if cfg.type == "Cold Storage" else 1.0
        base = scale * cold
        rows.append([
            day.isoformat(),
            cfg.facility_id,
            draw(0.6 * base, damage_mult),
            draw(0.4 * base, missort_mult),
            draw(0.8 * base, mispick_mult),
            draw(0.2 * base),
            draw(0.5 * base),
        ])
    return rows


def simulate_equipment(cfg: FacilityConfig, rng: random.Random,
                       days: list[dt.date]) -> list[list]:
    rows = []
    for day in days:
        if day.weekday() not in cfg.operating_dow:
            continue
        scens = scenarios_for(cfg.facility_id, day)
        conv = max(0, int(rng.gauss(cfg.conveyor_baseline_down_m, 5))
                   + sum(s.conveyor_down_add_m for s in scens))
        mhe = max(0, int(rng.gauss(cfg.mhe_baseline_down_m, 8))
                  + sum(s.mhe_down_add_m for s in scens))
        wms = max(0, int(rng.gauss(0.4, 0.6))
                  + sum(s.wms_incidents_add for s in scens))
        scanner = max(0, int(rng.gauss(1.5, 1.0)))
        rows.append([
            day.isoformat(),
            cfg.facility_id,
            conv, mhe, wms, scanner,
        ])
    return rows


def write_metric_family(family: str, facility_id: str, header: list[str],
                        rows: list[list], min_rows: int) -> Path:
    target = METRICS_DIR / family / f"{facility_id}.csv"
    write_csv_atomic(target, header, rows)
    report = ValidationReport(
        script="simulate_facility_data.py",
        target=str(target.relative_to(REPO_ROOT)).replace("\\", "/"),
    )
    validate_metric_family(family, read_csv(target), facility_id,
                           min_rows, report)
    log = report.write_log()
    assert_passed(report)
    return log


def write_events_file(facility_id: str | None, rows: list[list]) -> Path:
    if facility_id is None:
        target = EVENTS_DIR / "network.csv"
        header = list(SCHEMAS["events_network"])
    else:
        target = EVENTS_DIR / f"{facility_id}.csv"
        header = list(SCHEMAS["events"])

    # Preserve floor-attributed rows (source starts with "floor-intake") if the
    # target file already exists. The conversion boundary owns simulator-seed
    # rows; close-loop owns floor-intake rows. Re-running the simulator must
    # not erase floor work, but must also stay deterministic for its own rows.
    source_col = header.index("source")
    preserved: list[list] = []
    if target.exists():
        existing = read_csv(target)
        if existing and existing[0] == header:
            for row in existing[1:]:
                if len(row) > source_col and row[source_col].startswith("floor-intake"):
                    preserved.append(row)

    # Merge + sort ascending by date. The events validator enforces ascending
    # dates and no-nulls, so the merged file must remain sorted across runs.
    merged = list(rows) + preserved
    merged.sort(key=lambda r: r[0])

    write_csv_atomic(target, header, merged)
    report = ValidationReport(
        script="simulate_facility_data.py",
        target=str(target.relative_to(REPO_ROOT)).replace("\\", "/"),
    )
    validate_events_file(read_csv(target), facility_id, report)
    log = report.write_log()
    assert_passed(report)
    return log


def build_events() -> tuple[dict[str, list[list]], list[list]]:
    per_facility: dict[str, list[list]] = {cfg.facility_id: []
                                           for cfg in FACILITIES}
    network: list[list] = []
    for seed in sorted(EVENT_SEEDS, key=lambda s: (s.date, s.facility_id or "")):
        if seed.facility_id is None:
            network.append([
                seed.date.isoformat(),
                seed.event_type,
                seed.description,
                seed.source,
            ])
        else:
            per_facility[seed.facility_id].append([
                seed.date.isoformat(),
                seed.facility_id,
                seed.event_type,
                seed.description,
                seed.source,
            ])
    return per_facility, network


# --- Entry point -------------------------------------------------------------

def main(seed: int = 20260518) -> int:
    days = daterange(START_DATE, END_DATE)
    operating_min_rows = 90  # we expect ~103 operating days in 120 days
    written: list[str] = []

    for cfg in FACILITIES:
        # Use a per-facility derived seed so adding a facility doesn't shift
        # the existing facilities' RNG streams.
        rng = random.Random(f"{seed}:{cfg.facility_id}")

        op_rows, _ = simulate_operational(cfg, rng, days)
        units_by_day = {dt.date.fromisoformat(r[0]): int(r[2]) for r in op_rows}

        write_metric_family("operational", cfg.facility_id,
                            SCHEMAS["operational"], op_rows, operating_min_rows)
        written.append(f"data/metrics/operational/{cfg.facility_id}.csv")

        inp_rows = simulate_inputs(cfg, rng, days)
        write_metric_family("inputs", cfg.facility_id,
                            SCHEMAS["inputs"], inp_rows, operating_min_rows)
        written.append(f"data/metrics/inputs/{cfg.facility_id}.csv")

        ex_rows = simulate_exceptions(cfg, rng, days, units_by_day)
        write_metric_family("exceptions", cfg.facility_id,
                            SCHEMAS["exceptions"], ex_rows, operating_min_rows)
        written.append(f"data/metrics/exceptions/{cfg.facility_id}.csv")

        eq_rows = simulate_equipment(cfg, rng, days)
        write_metric_family("equipment", cfg.facility_id,
                            SCHEMAS["equipment"], eq_rows, operating_min_rows)
        written.append(f"data/metrics/equipment/{cfg.facility_id}.csv")

    per_facility_events, network_events = build_events()
    for cfg in FACILITIES:
        rows = per_facility_events.get(cfg.facility_id, [])
        write_events_file(cfg.facility_id, rows)
        written.append(f"data/events/{cfg.facility_id}.csv")
    write_events_file(None, network_events)
    written.append("data/events/network.csv")

    print(f"OK — wrote {len(written)} files; "
          f"period {START_DATE.isoformat()} .. {END_DATE.isoformat()}; "
          f"seed={seed}")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260518,
                        help="RNG seed (default: 20260518)")
    args = parser.parse_args()
    sys.exit(main(args.seed))
